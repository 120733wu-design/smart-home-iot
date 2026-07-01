from flask import Blueprint, request, jsonify
from models.device import DeviceModel
from models.alert import AlertModel
from models.sensor_data import SensorDataModel
from models.database import query

devices_api_bp = Blueprint('devices_api', __name__)

@devices_api_bp.route('/devices', methods=['GET'])
def list_devices():
    return jsonify({'success':True,'data':DeviceModel.list_all(status=request.args.get('status'),device_type=request.args.get('type'))})

@devices_api_bp.route('/devices', methods=['POST'])
def create_device():
    data = request.get_json()
    name = data.get('name','').strip()
    device_key = data.get('device_key','').strip()
    device_type = data.get('type','sensor')
    location = data.get('location','')
    if not name or not device_key:
        return jsonify({'success':False,'message':'设备名称和设备Key不能为空'}),400
    if DeviceModel.find_by_key(device_key):
        return jsonify({'success':False,'message':'设备Key已存在'}),409
    device_id = DeviceModel.create(name, device_key, device_type, location)
    return jsonify({'success':True,'message':'设备创建成功','data':{'id':device_id}}),201

@devices_api_bp.route('/devices/<int:device_id>', methods=['GET'])
def get_device(device_id):
    dev = DeviceModel.find_by_id(device_id)
    return jsonify({'success':True,'data':dev}) if dev else (jsonify({'success':False,'message':'设备不存在'}),404)

@devices_api_bp.route('/devices/<int:device_id>', methods=['PUT'])
def update_device(device_id):
    if not DeviceModel.find_by_id(device_id):
        return jsonify({'success':False,'message':'设备不存在'}),404
    data = request.get_json()
    kwargs = {k:data.get(k) for k in ['name','location','type'] if k in data}
    for f in ['threshold_temp_min','threshold_temp_max','threshold_humi_min','threshold_humi_max','threshold_light_max']:
        if f in data:
            kwargs[f] = data[f]
    if not kwargs:
        return jsonify({'success':False,'message':'没有需要更新的字段'}),400
    DeviceModel.update(device_id, **kwargs)
    return jsonify({'success':True,'message':'设备更新成功','data':DeviceModel.find_by_id(device_id)})

@devices_api_bp.route('/devices/<int:device_id>', methods=['DELETE'])
def delete_device(device_id):
    if not DeviceModel.find_by_id(device_id):
        return jsonify({'success':False,'message':'设备不存在'}),404
    DeviceModel.delete(device_id)
    return jsonify({'success':True,'message':'设备已删除'})

@devices_api_bp.route('/devices/<int:device_id>/status', methods=['PUT'])
def update_device_status(device_id):
    dev = DeviceModel.find_by_id(device_id)
    if not dev:
        return jsonify({'success':False,'message':'设备不存在'}),404
    status = request.get_json().get('status')
    if status not in ('online','offline'):
        return jsonify({'success':False,'message':'状态值无效'}),400
    DeviceModel.set_status(device_id, status)
    return jsonify({'success':True,'message':f'设备已{status}'})

@devices_api_bp.route('/statistics', methods=['GET'])
def get_statistics():
    total=DeviceModel.count()
    online=DeviceModel.count(status='online')
    d=DeviceModel.list_all()
    lr={}
    for dev in d:
        for r in SensorDataModel.get_realtime(dev['id']):
            lr[f"{r['sensor_type']}_{dev['id']}"] = {
                'value':float(r['value']),
                'unit':r.get('unit',''),
                'recorded_at':r['recorded_at'].strftime('%Y-%m-%d %H:%M:%S') if r.get('recorded_at') else None
            }
    # 直接SQL查询未读告警，彻底删除AlertModel.count_unread()调用
    unread_sql = "SELECT COUNT(*) as cnt FROM alerts WHERE is_read = 0"
    unread_res = query(unread_sql)
    unread_alerts = unread_res[0]["cnt"] if unread_res else 0

    return jsonify({
        'success':True,
        'data':{
            'total_devices':total,
            'online_devices':online,
            'offline_devices':total-online,
            'online_rate':round(online/total*100,1) if total>0 else 0,
            'unread_alerts': unread_alerts,
            'latest_readings':lr
        }
    })