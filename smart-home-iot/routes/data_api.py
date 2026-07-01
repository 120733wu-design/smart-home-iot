from flask import Blueprint, request, jsonify
from models.sensor_data import SensorDataModel
from models.device import DeviceModel
from datetime import datetime, timedelta

data_api_bp = Blueprint('data_api', __name__)

# 分页历史数据接口
@data_api_bp.route('/devices/<int:device_id>/data', methods=['GET'])
def get_sensor_data(device_id):
    if not DeviceModel.find_by_id(device_id):
        return jsonify({'success': False, 'message': '设备不存在'}), 404
    st = request.args.get('type')
    s = request.args.get('start')
    e = request.args.get('end')
    p = int(request.args.get('page', 1))
    pp = int(request.args.get('per_page', 100))

    # 直接查询整行数据，不再按sensor_type过滤
    data = SensorDataModel.get_history(device_id, s, e, p, pp)
    total = SensorDataModel.count(device_id, s, e)

    # 格式化时间
    for row in data:
        if row.get('recorded_at'):
            row['time'] = row['recorded_at'].strftime('%Y-%m-%d %H:%M:%S')
    return jsonify({'success': True, 'data': data, 'total': total, 'page': p, 'per_page': pp})

# 最新一条实时数据
@data_api_bp.route('/devices/<int:device_id>/data/realtime', methods=['GET'])
def get_realtime(device_id):
    if not DeviceModel.find_by_id(device_id):
        return jsonify({'success': False, 'message': '设备不存在'}), 404
    r = SensorDataModel.get_realtime(device_id)
    for row in r:
        if row.get('recorded_at'):
            row['time'] = row['recorded_at'].strftime('%Y-%m-%d %H:%M:%S')
    return jsonify({'success': True, 'data': r})

# 单一类型最近N小时（兼容旧接口，拆分字段返回）
@data_api_bp.route('/devices/<int:device_id>/data/latest', methods=['GET'])
def get_latest_hours(device_id):
    if not DeviceModel.find_by_id(device_id):
        return jsonify({'success': False, 'message': '设备不存在'}), 404
    sensor_type = request.args.get('type', '')
    hours = int(request.args.get('hours', 1))
    rows_dict = SensorDataModel.get_latest_rows(device_id, hours)
    res_list = rows_dict.get(sensor_type, [])
    return jsonify({'success': True, 'data': res_list})

# 首页仪表盘接口 /devices/1/data/all-recent 修复核心
@data_api_bp.route('/devices/<int:device_id>/data/all-recent', methods=['GET'])
def get_all_recent(device_id):
    if not DeviceModel.find_by_id(device_id):
        return jsonify({'success': False, 'message': '设备不存在'}), 404
    h = int(request.args.get('hours', 2))
    rows_dict = SensorDataModel.get_latest_rows(device_id, h)

    return jsonify({
        'success': True,
        'data': {
            "temperature": rows_dict.get("temperature", []),
            "humidity": rows_dict.get("humidity", []),
            "light": rows_dict.get("light", [])
        }
    })
