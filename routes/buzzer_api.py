"""蜂鸣器控制 API — 三模式: auto / manual / mute"""
from flask import Blueprint, request, jsonify
from models.device import DeviceModel
from models.buzzer import BuzzerModel
from mqtt_client.client import publish_buzzer, _mqtt_client

buzzer_api_bp = Blueprint('buzzer_api', __name__)


@buzzer_api_bp.route('/buzzer/config', methods=['GET'])
def get_buzzer_config():
    device_key = request.args.get('device_key', '').strip()
    if not device_key:
        dev = DeviceModel.list_all()
        if not dev:
            return jsonify({'success': False, 'message': '没有可用设备'}), 404
        device_key = dev[0]['device_key']

    dev = DeviceModel.find_by_key(device_key)
    if not dev or not dev.get('id'):
        return jsonify({'success': False, 'message': f'设备不存在: {device_key}'}), 404

    cfg = BuzzerModel.get_or_create(dev['id'])
    return jsonify({
        'success': True,
        'data': {
            'device_id': dev['id'],
            'device_key': device_key,
            'device_name': dev.get('name', ''),
            'mode': cfg.get('mode', 'auto'),
            'manual_state': cfg.get('manual_state', 0),
            'updated_at': cfg.get('updated_at').strftime('%Y-%m-%d %H:%M:%S') if cfg.get('updated_at') else None
        }
    })


@buzzer_api_bp.route('/buzzer/mode', methods=['PUT'])
def set_buzzer_mode():
    data = request.get_json() or {}
    device_key = data.get('device_key', '').strip()
    mode = data.get('mode', '').strip()

    if mode not in ('auto', 'manual', 'mute'):
        return jsonify({'success': False, 'message': '无效模式，可选: auto/manual/mute'}), 400

    dev = DeviceModel.find_by_key(device_key)
    if not dev or not dev.get('id'):
        return jsonify({'success': False, 'message': f'设备不存在: {device_key}'}), 404

    BuzzerModel.get_or_create(dev['id'])
    BuzzerModel.set_mode(dev['id'], mode)

    # 通过 MQTT JSON 协议通知硬件
    if mode == 'auto':
        publish_buzzer(device_key, 'auto', 'off')
    elif mode == 'mute':
        publish_buzzer(device_key, 'mute', 'off')
    else:
        publish_buzzer(device_key, 'manual', 'off')

    return jsonify({
        'success': True,
        'message': f'蜂鸣器模式已设置为: {mode}',
        'data': {'device_key': device_key, 'mode': mode}
    })


@buzzer_api_bp.route('/buzzer/trigger', methods=['POST'])
def trigger_buzzer():
    data = request.get_json() or {}
    device_key = data.get('device_key', '').strip()
    state = int(data.get('state', 0))

    dev = DeviceModel.find_by_key(device_key)
    if not dev or not dev.get('id'):
        return jsonify({'success': False, 'message': f'设备不存在: {device_key}'}), 404

    cfg = BuzzerModel.get_or_create(dev['id'])
    if cfg.get('mode') != 'manual':
        return jsonify({'success': False, 'message': '仅在 manual 模式下可手动触发蜂鸣器'}), 400

    BuzzerModel.set_manual_state(dev['id'], state)

    if _mqtt_client:
        publish_buzzer(device_key, 'manual', 'on' if state else 'off')
        return jsonify({
            'success': True,
            'message': f'蜂鸣器已{"开启" if state else "关闭"}',
            'data': {'device_key': device_key, 'state': state}
        })
    else:
        return jsonify({'success': False, 'message': 'MQTT 未连接'}), 503


@buzzer_api_bp.route('/buzzer/status', methods=['GET'])
def get_buzzer_status():
    device_key = request.args.get('device_key', '').strip()
    if not device_key:
        dev = DeviceModel.list_all()
        if not dev:
            return jsonify({'success': False, 'message': '没有可用设备'}), 404
        device_key = dev[0]['device_key']

    dev = DeviceModel.find_by_key(device_key)
    if not dev or not dev.get('id'):
        return jsonify({'success': False, 'message': f'设备不存在: {device_key}'}), 404

    cfg = BuzzerModel.get_or_create(dev['id'])
    return jsonify({
        'success': True,
        'data': {
            'device_key': device_key,
            'device_online': dev.get('status') == 'online',
            'mqtt_connected': _mqtt_client is not None,
            'mode': cfg.get('mode', 'auto'),
            'manual_state': cfg.get('manual_state', 0),
        }
    })
