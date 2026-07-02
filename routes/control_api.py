from flask import Blueprint, request, jsonify
from models.device import DeviceModel
from models.command import CommandModel
from mqtt_client.client import publish_control, _mqtt_client

control_api_bp = Blueprint('control_api', __name__)


@control_api_bp.route('/control/devices', methods=['GET'])
def get_controllable_devices():
    """获取可控制的设备列表（所有 sensor 类型设备）"""
    devices = DeviceModel.list_all()
    # 每个设备附加上控制能力描述
    result = []
    for d in devices:
        result.append({
            'id': d['id'],
            'name': d['name'],
            'device_key': d['device_key'],
            'status': d.get('status', 'offline'),
            'location': d.get('location', ''),
            'controls': [
                {'id': 'relay1_on',  'label': '继电器1 开', 'icon': 'toggle-on',  'group': 'relay1'},
                {'id': 'relay1_off', 'label': '继电器1 关', 'icon': 'toggle-off', 'group': 'relay1'},
                {'id': 'relay2_on',  'label': '继电器2 开', 'icon': 'toggle-on',  'group': 'relay2'},
                {'id': 'relay2_off', 'label': '继电器2 关', 'icon': 'toggle-off', 'group': 'relay2'},
            ]
        })
    return jsonify({'success': True, 'data': result})


@control_api_bp.route('/control/send', methods=['POST'])
def send_command():
    """向设备下发控制命令"""
    data = request.get_json() or {}
    device_key = data.get('device_key', '').strip()
    command = data.get('command', '').strip()
    params = data.get('params', None)

    if not device_key or not command:
        return jsonify({'success': False, 'message': '设备Key和命令不能为空'}), 400

    # 验证设备存在
    dev = DeviceModel.find_by_key(device_key)
    if not dev or not dev.get('id'):
        return jsonify({'success': False, 'message': f'设备不存在: {device_key}'}), 404

    # 检查 MQTT 连接状态
    if _mqtt_client is None:
        return jsonify({'success': False, 'message': 'MQTT服务未连接，命令无法下发'}), 503

    # 下发命令
    cmd_id = publish_control(device_key, command, params)
    if cmd_id:
        return jsonify({
            'success': True,
            'message': f'命令 {command} 已下发至 {dev["name"]}',
            'data': {'command_id': cmd_id, 'device_key': device_key, 'command': command}
        })
    else:
        return jsonify({'success': False, 'message': '命令发送失败，请检查MQTT连接'}), 500


@control_api_bp.route('/control/history', methods=['GET'])
def get_command_history():
    """获取命令历史记录"""
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 50))
    device_id = request.args.get('device_id', type=int)

    if device_id:
        commands = CommandModel.list_by_device(device_id, page, per_page)
    else:
        commands = CommandModel.list_all(page, per_page)

    # 格式化时间
    for c in commands:
        if c.get('created_at'):
            c['created_at_str'] = c['created_at'].strftime('%Y-%m-%d %H:%M:%S') if hasattr(c['created_at'], 'strftime') else str(c['created_at'])

    return jsonify({'success': True, 'data': commands, 'page': page, 'per_page': per_page})


@control_api_bp.route('/control/mqtt-status', methods=['GET'])
def get_mqtt_status():
    """获取 MQTT 连接状态"""
    return jsonify({
        'success': True,
        'data': {
            'connected': _mqtt_client is not None,
            'broker': f"{__import__('config').Config.MQTT_BROKER_HOST}:{__import__('config').Config.MQTT_BROKER_PORT}"
        }
    })
