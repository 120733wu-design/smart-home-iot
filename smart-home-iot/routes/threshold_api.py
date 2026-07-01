from flask import Blueprint, render_template, request, jsonify
from models.threshold import ThresholdModel

threshold_bp = Blueprint('threshold', __name__)

# 阈值配置页面
@threshold_bp.route('/threshold')
def index():
    return render_template('threshold.html')

# 保存阈值接口
@threshold_bp.route('/api/threshold/save', methods=['POST'])
def save_threshold():
    data = request.json
    ThresholdModel.set(data['device_id'], data['sensor_type'], data.get('min_value'), data.get('max_value'))
    return jsonify({"success": True, "msg": "阈值保存成功"})

# 查询单设备传感器阈值
@threshold_bp.route('/api/threshold/<int:device_id>/<sensor_type>')
def get_threshold(device_id, sensor_type):
    row = ThresholdModel.get_by_device(device_id, sensor_type)
    return jsonify({"success": True, "data": row or {}})