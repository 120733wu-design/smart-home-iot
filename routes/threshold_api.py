from flask import Blueprint, render_template, request, jsonify
from models.threshold import ThresholdModel
import json
# 导入通用发布函数
from mqtt_client.client import publish_raw, publish_buzzer

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

    ThresholdModel.set(device_id, sensor_type, min_val, max_val)

    if sensor_type == "temperature" and max_val is not None:
        try:
            payload = json.dumps({"temp_max": float(max_val)})
            publish_raw("device/sensor/cfg", payload)
        except Exception as e:
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