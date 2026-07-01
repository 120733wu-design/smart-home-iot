from flask import Blueprint, render_template, request, jsonify
from models.threshold import ThresholdModel
import json
# 导入通用发布函数publish_raw
from mqtt_client.client import publish_raw

threshold_bp = Blueprint('threshold', __name__)

# 阈值配置页面
@threshold_bp.route('/threshold')
def index():
    return render_template('threshold.html')

# 保存阈值接口
@threshold_bp.route('/api/threshold/save', methods=['POST'])
def save_threshold():
    data = request.json
    device_id = data['device_id']
    sensor_type = data['sensor_type']
    min_val = data.get('min_value')
    max_val = data.get('max_value')
    
    # 1、保存到数据库（数据库操作不受MQTT影响，优先执行）
    ThresholdModel.set(device_id, sensor_type, min_val, max_val)

    # 2、仅温度上限下发到ESP硬件，增加异常捕获防止服务崩溃
    if sensor_type == "temperature" and max_val is not None:
        try:
            payload = json.dumps({"temp_max": float(max_val)})
            # 调用通用发布函数发送消息
            publish_raw("device/sensor/cfg", payload)
        except Exception as e:
            # MQTT下发失败不阻断保存，仅打印日志
            print(f"MQTT下发阈值失败: {e}")

    return jsonify({"success": True, "msg": "阈值保存成功"})

# 查询单设备传感器阈值
@threshold_bp.route('/api/threshold/<int:device_id>/<sensor_type>')
def get_threshold(device_id, sensor_type):
    try:
        row = ThresholdModel.get_by_device(device_id, sensor_type)
        return jsonify({"success": True, "data": row or {}})
    except Exception as e:
        print(f"查询阈值异常: {e}")
        return jsonify({"success": False, "msg": "查询阈值失败"})