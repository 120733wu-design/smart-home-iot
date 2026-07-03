import json, time, threading, paho.mqtt.client as mqtt
from datetime import datetime, timedelta
from config import Config
# 数据库查询函数导入，用于防重复告警
from models.database import query
_mqtt_client = None

# 将短格式传感器类型映射为数据库中使用的枚举值
_SENSOR_TYPE_MAP = {
    'temp': 'temperature',
    'humi': 'humidity',
    'light': 'light',
}

def on_connect(client, userdata, flags, rc):
    print(f"[MQTT] Connected (rc={rc})")
    if rc==0:
        # 订阅通配符 device/# 全覆盖，兼容所有设备上报
        client.subscribe(f"{Config.MQTT_TOPIC_PREFIX}/#", qos=1)
        print(f"[MQTT] Subscribed topic: {Config.MQTT_TOPIC_PREFIX}/#")

def on_disconnect(client, userdata, rc):
    print(f"[MQTT] Disconnected (rc={rc}), retry in 5s")
    time.sleep(5)

def on_message(client, userdata, msg):
    try:
        topic = msg.topic
        payload = msg.payload.decode('utf-8')
        # 打印收到的原始消息，用来调试
        print(f"[MQTT RECV] Topic: {topic} | Payload: {payload}")

        parts = topic.split('/')
        device_key = parts[1] if len(parts) > 1 else ''
        sub_topic = parts[2] if len(parts) > 2 else ''

        from models.device import DeviceModel
        device = DeviceModel.find_by_key(device_key)

        # ===== 兼容三段式无设备ID主题 =====
        # ESP固件旧版可能发 device/sensor/temp（三段），device_key='sensor' 在DB中无匹配
        # 此时自动 fallback 到数据库第一个 type='sensor' 的设备
        if (not device or not device.get('id')) and sub_topic in _SENSOR_TYPE_MAP:
            # 三段式：device/<sensor_type_or_unknown>/<type>，尝试按传感器类型查找设备
            all_devices = DeviceModel.list_all()
            sensor_devices = [d for d in all_devices if d.get('type') == 'sensor']
            if sensor_devices:
                device = sensor_devices[0]
                print(f"[MQTT] 三段式Topic自动匹配设备: key={device['device_key']} id={device['id']} (原始topic={topic})")

        if not device or not device.get('id'):
            # 增强诊断：打印详细的 topic 信息帮助排查硬件连接问题
            print(f"[MQTT] 数据库无此设备 key={device_key} (topic={topic} parts={parts})")
            print(f"[MQTT] 诊断提示: 请确认硬件MQTT Broker地址一致 | 当前Broker={Config.MQTT_BROKER_HOST}:{Config.MQTT_BROKER_PORT}")
            print(f"[MQTT] 期望Topic格式: device/<device_key>/sensor/<type>")
            return
        did = device['id']

        # 兼容三种主题格式：
        # (1) device/<key>/sensor/<type>  四段标准 (ESP8266新固件)
        # (2) device/<key>/<type>         三段平铺 (带设备key)
        # (3) device/sensor/<type>        三段旧格式 (无设备key，已在上面fallback处理)
        sensor_type = None
        if sub_topic == 'sensor' and len(parts) > 3:
            sensor_type = _SENSOR_TYPE_MAP.get(parts[3], parts[3])
        elif sub_topic in _SENSOR_TYPE_MAP:
            sensor_type = _SENSOR_TYPE_MAP[sub_topic]

        if sensor_type:
            try:
                value = float(payload)
            except Exception as e:
                print(f"[MQTT] 数值转换失败 payload={payload}, err={e}")
                return
            from models.sensor_data import SensorDataModel
            # 关键：sensor_data 也改用Python本地时间入库，和告警完全同源
            now_cst = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            SensorDataModel.insert(did, sensor_type, value, recorded_at=now_cst)
            print(f"[MQTT] 入库成功 设备:{device_key} 传感器:{sensor_type} 值:{value}")
            if device['status'] != 'online':
                DeviceModel.set_status(did, "online")

            # ===================== 新增阈值告警判断 =====================
            if sensor_type in ["temperature", "humidity"]:
                from models.threshold import ThresholdModel
                from models.alert import AlertModel
                # 查询该设备对应传感器阈值配置
                threshold = ThresholdModel.get_by_device(did, sensor_type)
                if not threshold:
                    # 该设备未配置阈值，跳过告警判断
                    return
                min_val = threshold.get("min_value")
                max_val = threshold.get("max_value")
                alert_msg = ""
                sev = "warning"
                # 判断低于下限
                if min_val is not None and value < min_val:
                    alert_msg = f"{'温度' if sensor_type=='temperature' else '湿度'}低于下限：当前{value}，阈值{min_val}"
                # 判断超过上限
                elif max_val is not None and value > max_val:
                    alert_msg = f"{'温度' if sensor_type=='temperature' else '湿度'}超过上限：当前{value}，阈值{max_val}"
                    sev = "critical"
                # 存在异常则生成告警，60秒内同一条消息不重复创建
                if alert_msg:
                    # 统一本地北京时间，无手动+8
                    now_cst = datetime.now()
                    cut_time = (now_cst - timedelta(seconds=60)).strftime("%Y-%m-%d %H:%M:%S")
                    recent = query(
                        "SELECT id FROM alerts WHERE device_id=%s AND alert_type='threshold' AND message=%s AND created_at > %s LIMIT 1",
                        (did, alert_msg, cut_time),
                        fetchone=True
                    )
                    if not recent:
                        now_str = now_cst.strftime("%Y-%m-%d %H:%M:%S")
                        AlertModel.create(did, "threshold", sev, alert_msg, now_str)
                        print(f"[MQTT] 生成阈值告警：{alert_msg}")

                        # 蜂鸣器 auto 模式：阈值超标时自动触发蜂鸣器
                        buzzer_cfg = BuzzerModel.get_by_device_key(device_key)
                        if buzzer_cfg and buzzer_cfg.get('mode') == 'auto':
                            # 双协议下发: JSON 协议到 device/buzzer/control
                            publish_buzzer(device_key, 'auto', 'on')
                            print(f"[MQTT] 蜂鸣器(auto) 触发 → {device_key}")
            # ==========================================================

        elif sub_topic == 'status':
            try:
                sd = json.loads(payload)
                DeviceModel.set_status(did, sd.get('status', 'online'))
                buzzer_mode = sd.get('buzzer_mode')
                if buzzer_mode:
                    from models.buzzer import BuzzerModel
                    BuzzerModel.ensure_exists(did)
                    buzzer_cfg = BuzzerModel.get_or_create(did)
                    if buzzer_cfg.get('mode') != buzzer_mode:
                        BuzzerModel.set_mode(did, buzzer_mode)
            except Exception as e:
                print(f"[MQTT] status解析失败: {e}")

        elif sub_topic == 'control':
            if 'ack' in parts:
                try:
                    ack = json.loads(payload)
                    cmd_id = ack.get('command_id')
                    if cmd_id:
                        from models.command import CommandModel
                        CommandModel.update_status(cmd_id, ack.get('acknowledged'))
                except Exception as e:
                    print(f"[MQTT] control ack解析失败: {e}")
    except Exception as e:
        print(f"[MQTT] Global message error: {e}")

def init_mqtt(app):
    app.config['MQTT_CLIENT'] = None

def start_mqtt():
    global _mqtt_client
    # 确保已知硬件设备在数据库中存在，避免 MQTT 数据被丢弃
    try:
        from models.device import DeviceModel
        from models.buzzer import BuzzerModel
        known_keys = ['esp8266-001', 'esp8266-screen-001-0626']
        for k in known_keys:
            dev = DeviceModel.find_by_key(k)
            if not dev or not dev.get('id'):
                name = 'ESP8266屏幕版' if 'screen' in k else 'ESP8266客厅环境监测器'
                did = DeviceModel.create(name=name, device_key=k, type='sensor', location='客厅')
                print(f"[MQTT] 自动注册设备 key={k} id={did}")
                BuzzerModel.ensure_exists(did)
            else:
                BuzzerModel.ensure_exists(dev['id'])
    except Exception as e:
        print(f"[MQTT] 自动注册设备失败: {e}")

    def _run():
        global _mqtt_client
        c = mqtt.Client(client_id=f"flask-{int(time.time())}", protocol=mqtt.MQTTv311)
        c.will_set(f"{Config.MQTT_TOPIC_PREFIX}/backend/status", json.dumps({"status":"offline"}), qos=1, retain=True)
        c.on_connect = on_connect
        c.on_disconnect = on_disconnect
        c.on_message = on_message
        if Config.MQTT_USERNAME:
            c.username_pw_set(Config.MQTT_USERNAME, Config.MQTT_PASSWORD)
        _mqtt_client = c
        try:
            print(f"[MQTT] Connecting {Config.MQTT_BROKER_HOST}:{Config.MQTT_BROKER_PORT}...")
            c.connect(Config.MQTT_BROKER_HOST, Config.MQTT_BROKER_PORT, keepalive=60)
            c.loop_forever()
        except Exception as e:
            print(f"[MQTT] Connection failed: {e}")
            print("[MQTT] Running without MQTT (no real hardware data)")
    threading.Thread(target=_run, daemon=True).start()

def publish_control(device_key, command, params=None):
    """下发控制命令到设备，自动生成 command_id 并写入数据库"""
    global _mqtt_client
    if _mqtt_client is None:
        return None
    # 先在数据库中创建命令记录
    from models.command import CommandModel
    cmd_id = CommandModel.create_with_key(device_key, command, params)
    payload = json.dumps({
        'command': command,
        'command_id': cmd_id,
        'params': params or {},
        'timestamp': time.time()
    })
    topic = f"{Config.MQTT_TOPIC_PREFIX}/{device_key}/control"
    try:
        result = _mqtt_client.publish(topic, payload, qos=1)
        if result.rc == 0:
            return cmd_id
        return None
    except Exception as e:
        print(f"[MQTT] publish_control error: {e}")
        return None

def publish_buzzer(device_key, mode, buzzer_state='off'):
    """蜂鸣器MQTT下发 — JSON协议: {mode, buzzer} → device/buzzer/control"""
    global _mqtt_client
    if _mqtt_client is None:
        print("[MQTT] publish_buzzer: MQTT not connected")
        return False
    payload = json.dumps({'mode': mode, 'buzzer': buzzer_state})
    topic = f"{Config.MQTT_TOPIC_PREFIX}/buzzer/control"
    try:
        result = _mqtt_client.publish(topic, payload, qos=1)
        print(f"[MQTT] publish_buzzer -> {topic} | {payload}")
        return result.rc == 0
    except Exception as e:
        print(f"[MQTT] publish_buzzer error: {e}")
        return False

# 新增：通用MQTT发布，任意主题
def publish_raw(topic, payload):
    global _mqtt_client
    if _mqtt_client is None:
        return False
    if isinstance(payload, dict):
        payload = json.dumps(payload)
    result = _mqtt_client.publish(topic, payload, qos=1)
    return result.rc == 0