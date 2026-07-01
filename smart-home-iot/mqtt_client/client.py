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

# ========== device_key → device_id 缓存映射 ==========
_device_id_cache = {}

def _lookup_device_id(device_key):
    """通过 device_key 查 device_id，带内存缓存，减少数据库查询"""
    if device_key in _device_id_cache:
        return _device_id_cache[device_key]
    from models.device import DeviceModel
    device = DeviceModel.find_by_key(device_key)
    if device and device.get('id'):
        _device_id_cache[device_key] = device['id']
        print(f"[MQTT] Cached device: key={device_key} -> id={device['id']}")
        return device['id']
    return None

def _invalidate_device_cache(device_key=None):
    """清除设备缓存（设备增删后调用）"""
    global _device_id_cache
    if device_key:
        _device_id_cache.pop(device_key, None)
    else:
        _device_id_cache = {}

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
        device_key = parts[1]
        sub_topic = parts[2] if len(parts) > 2 else ''

        # 使用缓存查询 device_id（首次查库，后续走缓存）
        did = _lookup_device_id(device_key)
        if not did:
            # 缓存未命中且数据库不存在 → 自动注册
            from models.device import DeviceModel
            try:
                auto_name = f"Auto-{device_key}"
                new_id = DeviceModel.create(name=auto_name, device_key=device_key, type='sensor', location='Auto')
                _device_id_cache[device_key] = new_id
                print(f"[MQTT] Auto-registered new device: key={device_key} id={new_id}")
                did = new_id
            except Exception as e:
                print(f"[MQTT] Cannot auto-register device key={device_key}: {e}，丢弃数据")
                return

        # 兼容两种主题格式：(1) device/<key>/sensor/<type> (2) device/<key>/<type> (flat)
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
            sensor_unit = 'C' if sensor_type == 'temperature' else ('%' if sensor_type == 'humidity' else 'lux')
            SensorDataModel.insert(did, sensor_type, value, unit=sensor_unit, recorded_at=now_cst)
            print(f"[MQTT] 入库成功 设备:{device_key}(id={did}) 传感器:{sensor_type} 值:{value}")
            # 更新设备在线状态
            from models.device import DeviceModel
            dev_status = DeviceModel.find_by_key(device_key)
            if dev_status and dev_status.get('status') != 'online':
                DeviceModel.set_status(did, "online")

            # ===================== 新增阈值告警判断 =====================
            if sensor_type in ["temperature", "humidity"]:
                from models.threshold import ThresholdModel
                from models.alert import AlertModel
                # 查询该设备对应传感器阈值配置
                threshold = ThresholdModel.get_by_device(did, sensor_type)
                if not threshold:
                    # 该设备未配置阈值，跳过告警判断（不阻断后续处理）
                    pass
                else:
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
            # ==========================================================

        elif sub_topic == 'status':
            try:
                sd = json.loads(payload)
                DeviceModel.set_status(did, sd.get('status', 'online'))
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
    # 同时预热 device_key → device_id 缓存
    try:
        from models.device import DeviceModel
        known_keys = ['esp8266-001', 'sensor']  # sensor 是 ESP8266 真实上报的 device_key
        for k in known_keys:
            dev = DeviceModel.find_by_key(k)
            if not dev or not dev.get('id'):
                new_id = DeviceModel.create(
                    name=f'ESP8266-{k}',
                    device_key=k,
                    type='sensor',
                    location='客厅' if '001' in k else 'Auto'
                )
                print(f"[MQTT] 自动注册设备 key={k} id={new_id}")
            else:
                print(f"[MQTT] 已存在设备 key={k} id={dev['id']}")
            # 预热缓存
            _device_id_cache[k] = DeviceModel.find_by_key(k)['id']
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
    global _mqtt_client
    if _mqtt_client is None:
        return False
    payload = json.dumps({'command':command,'params':params or {},'timestamp':time.time()})
    topic = f"{Config.MQTT_TOPIC_PREFIX}/{device_key}/control"
    result = _mqtt_client.publish(topic, qos=1)
    return result.rc == 0
# 新增：通用MQTT发布，任意主题
def publish_raw(topic, payload):
    global _mqtt_client
    if _mqtt_client is None:
        return False
    if isinstance(payload, dict):
        payload = json.dumps(payload)
    result = _mqtt_client.publish(topic, payload, qos=1)
    return result.rc == 0