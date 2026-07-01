from models.database import query, execute
from datetime import datetime, timedelta

class SensorDataModel:
    @staticmethod
    def insert(device_id, sensor_type, value, unit='', recorded_at=None):
        # 只过滤明显非法的传感器值（负值超过物理极限），允许光照=0和温度=0等合法数据
        v = float(value)
        if v < -50 or v > 10000:
            return None
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
        sql = "SELECT sensor_type, value, recorded_at FROM sensor_data WHERE device_id = %s AND value > 0"
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
        sql = "SELECT COUNT(*) cnt FROM sensor_data WHERE device_id = %s AND value > 0"
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
        sql = "SELECT sensor_type, value, unit, recorded_at FROM sensor_data WHERE device_id = %s AND value > 0 ORDER BY recorded_at DESC LIMIT 3"
        rows = query(sql, (device_id,)) or []
        return rows

    @staticmethod
    def get_latest_value(device_id, sensor_type, hours):
        cutoff = datetime.now() - timedelta(hours=hours)
        sql = "SELECT value, recorded_at FROM sensor_data WHERE device_id = %s AND sensor_type = %s AND recorded_at >= %s AND value > 0 ORDER BY recorded_at ASC"
        rows = query(sql, (device_id, sensor_type, cutoff)) or []
        res = []
        for i, r in enumerate(rows):
            if i > 0:
                gap = r["recorded_at"] - rows[i-1]["recorded_at"]
                if gap > timedelta(minutes=7.5):
                    fill_time = rows[i-1]["recorded_at"] + timedelta(minutes=5)
                    while fill_time < r["recorded_at"]:
                        res.append({
                            "recorded_at": fill_time.strftime("%Y-%m-%d %H:%M:%S"),
                            "value": rows[i-1]["value"]
                        })
                        fill_time += timedelta(minutes=5)
            res.append({
                "recorded_at": r["recorded_at"].strftime("%Y-%m-%d %H:%M:%S"),
                "value": r["value"]
            })
        return res

    @staticmethod
    def get_latest_rows(device_id, hours):
        cutoff = datetime.now() - timedelta(hours=hours)
        sql = "SELECT sensor_type, value, recorded_at FROM sensor_data WHERE device_id = %s AND recorded_at >= %s AND value > 0 ORDER BY recorded_at ASC"
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
        sql = "SELECT value, recorded_at FROM sensor_data WHERE device_id = %s AND sensor_type = %s AND value > 0 ORDER BY recorded_at DESC LIMIT %s"
        return query(sql, (device_id, sensor_type, limit)) or []