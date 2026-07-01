from models.database import query, execute
from datetime import datetime, timedelta

# ===== 传感器物理合法范围 =====
_SENSOR_RANGES = {
    'temperature': (-10.0, 60.0),   # 温度：-10℃ ~ 60℃（室内环境物理极限）
    'humidity':    (0.0, 100.0),    # 湿度：0% ~ 100%（物理定义）
    'light':       (0.0, 100000.0), # 光照：0 ~ 100000 lux（直射阳光下约10万lux）
}

# 滑动窗口：最近 N 个值用于突刺检测
_SPIKE_WINDOW = {}
_SPIKE_WINDOW_SIZE = 10            # 保留最近10个采样
_SPIKE_THRESHOLD = 3.0             # Z-score 阈值，超过3倍标准差视为突刺

def _validate_sensor_value(device_id, sensor_type, value):
    """校验传感器值是否合法。返回 (is_valid, reason)"""
    v = float(value)

    # 1. 物理范围检查
    rng = _SENSOR_RANGES.get(sensor_type)
    if rng:
        lo, hi = rng
        if v < lo or v > hi:
            return False, f"超出物理范围 [{lo}, {hi}]"

    # 2. 单点突刺检测（基于滑动窗口 Z-score）
    key = f"{device_id}_{sensor_type}"
    win = _SPIKE_WINDOW.get(key, [])
    if len(win) >= 3:  # 至少3个历史值才做检测
        import statistics
        mean = statistics.mean(win)
        std = statistics.stdev(win) if len(win) >= 2 else 1.0
        if std > 0.01:
            z = abs(v - mean) / std
            if z > _SPIKE_THRESHOLD:
                return False, f"突刺异常 z-score={z:.1f} (均值={mean:.1f} σ={std:.1f})"

    # 记录到滑动窗口
    win.append(v)
    if len(win) > _SPIKE_WINDOW_SIZE:
        win.pop(0)
    _SPIKE_WINDOW[key] = win
    return True, "OK"


class SensorDataModel:
    @staticmethod
    def insert(device_id, sensor_type, value, unit='', recorded_at=None):
        # 严格数据校验：不合法的数据直接拒绝入库
        is_valid, reason = _validate_sensor_value(device_id, sensor_type, value)
        if not is_valid:
            print(f"[DATA-REJECT] device={device_id} type={sensor_type} value={value} -> {reason}")
            return None

        v = float(value)
        if recorded_at:
            # 使用Python传入的标准北京时间
            sql = "INSERT INTO sensor_data (device_id, sensor_type, value, unit, recorded_at) VALUES (%s, %s, %s, %s, %s)"
            return execute(sql, (device_id, sensor_type, value, unit, recorded_at), return_id=True)
        else:
            # 无传入时间，沿用数据库默认NOW()
            sql = "INSERT INTO sensor_data (device_id, sensor_type, value, unit) VALUES (%s, %s, %s, %s)"
            return execute(sql, (device_id, sensor_type, value, unit), return_id=True)

    @staticmethod
    def get_history(device_id, start, end, page, per_page):
        sql = "SELECT sensor_type, value, recorded_at FROM sensor_data WHERE device_id = %s"
        params = [device_id]
        if start:
            sql += " AND recorded_at >= %s"
            params.append(start)
        if end:
            sql += " AND recorded_at <= %s"
            params.append(end)
        sql += " ORDER BY recorded_at DESC LIMIT %s OFFSET %s"
        params.append(per_page)
        params.append((page - 1) * per_page)
        rows = query(sql, tuple(params)) or []
        return rows

    @staticmethod
    def count(device_id, start, end):
        sql = "SELECT COUNT(*) cnt FROM sensor_data WHERE device_id = %s"
        params = [device_id]
        if start:
            sql += " AND recorded_at >= %s"
            params.append(start)
        if end:
            sql += " AND recorded_at <= %s"
            params.append(end)
        row = query(sql, tuple(params), fetchone=True)
        return row["cnt"] if row else 0

    @staticmethod
    def get_realtime(device_id):
        sql = "SELECT sensor_type, value, unit, recorded_at FROM sensor_data WHERE device_id = %s ORDER BY recorded_at DESC LIMIT 3"
        rows = query(sql, (device_id,)) or []
        return rows

    @staticmethod
    def get_latest_value(device_id, sensor_type, hours):
        cutoff = datetime.now() - timedelta(hours=hours)
        sql = "SELECT value, recorded_at FROM sensor_data WHERE device_id = %s AND sensor_type = %s AND recorded_at >= %s ORDER BY recorded_at ASC"
        rows = query(sql, (device_id, sensor_type, cutoff)) or []
        # 不做假插值，空数据就是断点，只返回真实数据点
        rng = _SENSOR_RANGES.get(sensor_type)
        res = []
        for r in rows:
            val = float(r["value"])
            # 跳过超出物理范围的值
            if rng and (val < rng[0] or val > rng[1]):
                continue
            res.append({
                "recorded_at": r["recorded_at"].strftime("%Y-%m-%d %H:%M:%S"),
                "value": val
            })
        return res

    @staticmethod
    def get_latest_n_rows(device_id, limit=100):
        """获取每个传感器类型最新的 N 条数据，并标记是否在合理范围内"""
        temp_arr = []
        hum_arr = []
        light_arr = []
        for st in ['temperature', 'humidity', 'light']:
            sql = "SELECT sensor_type, value, recorded_at FROM sensor_data WHERE device_id = %s AND sensor_type = %s ORDER BY recorded_at DESC LIMIT %s"
            rows = query(sql, (device_id, st, limit)) or []
            rows.reverse()
            arr = []
            for r in rows:
                val = float(r["value"])
                rng = _SENSOR_RANGES.get(st)
                in_range = True if not rng else (rng[0] <= val <= rng[1])
                arr.append({
                    "recorded_at": r["recorded_at"].strftime("%Y-%m-%d %H:%M:%S"),
                    "value": val,
                    "in_range": in_range  # True=正常数据, False=异常点
                })
            if st == 'temperature':
                temp_arr = arr
            elif st == 'humidity':
                hum_arr = arr
            else:
                light_arr = arr
        return {
            "temperature": temp_arr,
            "humidity": hum_arr,
            "light": light_arr
        }

    @staticmethod
    def get_latest_rows(device_id, hours):
        cutoff = datetime.now() - timedelta(hours=hours)
        sql = "SELECT sensor_type, value, recorded_at FROM sensor_data WHERE device_id = %s AND recorded_at >= %s ORDER BY recorded_at ASC"
        rows = query(sql, (device_id, cutoff)) or []
        temp_arr = []
        hum_arr = []
        light_arr = []
        for r in rows:
            fmt_time = r["recorded_at"].strftime("%Y-%m-%d %H:%M:%S")
            val = float(r["value"])
            if val <= 0:
                continue
            if r["sensor_type"] == "temperature":
                temp_arr.append({"recorded_at": fmt_time, "value": val})
            elif r["sensor_type"] == "humidity":
                hum_arr.append({"recorded_at": fmt_time, "value": val})
            elif r["sensor_type"] == "light":
                light_arr.append({"recorded_at": fmt_time, "value": val})
        return {
            "temperature": temp_arr,
            "humidity": hum_arr,
            "light": light_arr
        }

    @staticmethod
    def get_for_ml(device_id, sensor_type, limit=500):
        sql = "SELECT value, recorded_at FROM sensor_data WHERE device_id = %s AND sensor_type = %s ORDER BY recorded_at DESC LIMIT %s"
        return query(sql, (device_id, sensor_type, limit)) or []