from flask import Blueprint, request, jsonify
from models.sensor_data import SensorDataModel
from models.device import DeviceModel
from datetime import datetime, timedelta
import requests
from urllib.parse import unquote

data_api_bp = Blueprint('data_api', __name__)

# ========== open-meteo 免费天气配置 ==========
WEATHER_API_URL = "https://api.open-meteo.com/v1/forecast"
LAT = 39.0856
LON = 117.1951
# 全局缓存：10分钟有效期，减少公网请求
_weather_cache = {
    "cache_data": None,
    "expire_timestamp": 0
}

def get_outdoor_weather(city_name="天津"):
    global _weather_cache
    now_timestamp = datetime.now().timestamp()
    # 缓存有效直接返回
    if _weather_cache["cache_data"] and now_timestamp < _weather_cache["expire_timestamp"]:
        return _weather_cache["cache_data"]

    params = {
        "latitude": LAT,
        "longitude": LON,
        "current": "temperature_2m,relative_humidity_2m",
        "timezone": "Asia/Shanghai"
    }
    try:
        resp = requests.get(WEATHER_API_URL, params=params, timeout=10)
        resp_json = resp.json()
        current = resp_json.get("current", {})
        temp = float(current.get("temperature_2m", 0))
        humi = float(current.get("relative_humidity_2m", 0))

        result = {
            "success": True,
            "out_temp": temp,
            "out_humi": humi,
            "weather_text": "实时气象",
            "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        # 缓存10分钟
        _weather_cache["cache_data"] = result
        _weather_cache["expire_timestamp"] = now_timestamp + 600
        return result
    except Exception as err:
        return {
            "success": False,
            "msg": f"请求天气服务失败：{str(err)}"
        }

# 室外天气接口
@data_api_bp.route('/weather/outdoor', methods=['GET'])
def api_outdoor_weather():
    city = request.args.get("city", "天津")
    city = unquote(city, encoding="utf-8")
    weather_info = get_outdoor_weather(city)
    return jsonify(weather_info)

# 室外天气接口别名（兼容 dashboard.js 的 /api/data/weather/outdoor 路径）
@data_api_bp.route('/data/weather/outdoor', methods=['GET'])
def api_outdoor_weather_alias():
    city = request.args.get("city", "天津")
    city = unquote(city, encoding="utf-8")
    weather_info = get_outdoor_weather(city)
    return jsonify(weather_info)

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

    data = SensorDataModel.get_history(device_id, s, e, p, pp)
    total = SensorDataModel.count(device_id, s, e)

    for row in data:
        if row.get('recorded_at'):
            row['time'] = row['recorded_at'].strftime('%Y-%m-%d %H:%M:%S')
    return jsonify({'success': True, 'data': data, 'total': total, 'page': p, 'per_page': pp})

# 最新实时数据
@data_api_bp.route('/devices/<int:device_id>/data/realtime', methods=['GET'])
def get_realtime(device_id):
    if not DeviceModel.find_by_id(device_id):
        return jsonify({'success': False, 'message': '设备不存在'}), 404
    r = SensorDataModel.get_realtime(device_id)
    for row in r:
        if row.get('recorded_at'):
            row['time'] = row['recorded_at'].strftime('%Y-%m-%d %H:%M:%S')
    return jsonify({'success': True, 'data': r})

# 单传感器最近N小时曲线
@data_api_bp.route('/devices/<int:device_id>/data/latest', methods=['GET'])
def get_latest_hours(device_id):
    if not DeviceModel.find_by_id(device_id):
        return jsonify({'success': False, 'message': '设备不存在'}), 404
    sensor_type = request.args.get('type', '')
    hours = int(request.args.get('hours', 1))
    rows_dict = SensorDataModel.get_latest_rows(device_id, hours)
    res_list = rows_dict.get(sensor_type, [])
    return jsonify({'success': True, 'data': res_list})

# 首页全部传感器近期数据
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