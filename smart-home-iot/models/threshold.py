from models.database import query, execute

class ThresholdModel:
    @staticmethod
    def set(device_id, sensor_type, min_value=None, max_value=None):
        # 删除原有配置
        execute("DELETE FROM device_thresholds WHERE device_id=%s AND sensor_type=%s", (device_id, sensor_type))
        # 新增
        sql = "INSERT INTO device_thresholds (device_id, sensor_type, min_value, max_value) VALUES (%s, %s, %s, %s)"
        execute(sql, (device_id, sensor_type, min_value, max_value))

    @staticmethod
    def get_by_device(device_id, sensor_type):
        sql = "SELECT * FROM device_thresholds WHERE device_id=%s AND sensor_type=%s LIMIT 1"
        return query(sql, (device_id, sensor_type), fetchone=True)