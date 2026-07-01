from models.database import query, execute

class DeviceModel:
    @staticmethod
    def create(name, device_key, type='sensor', location=''):
        sql = "INSERT INTO devices (name, device_key, type, location) VALUES (%s, %s, %s, %s)"
        return execute(sql, (name, device_key, type, location), return_id=True)

    @staticmethod
    def find_by_id(device_id):
        sql = "SELECT * FROM devices WHERE id = %s"
        row = query(sql, (device_id,), fetchone=True)
        # 兜底无数据返回空字典，防止接口取值None报错
        return row if row else {}

    @staticmethod
    def find_by_key(device_key):
        sql = "SELECT * FROM devices WHERE device_key = %s"
        row = query(sql, (device_key,), fetchone=True)
        return row if row else {}

    @staticmethod
    def list_all(status=None, device_type=None):
        sql = "SELECT * FROM devices WHERE 1=1"
        params = []
        if status:
            sql += " AND status = %s"
            params.append(status)
        if device_type:
            sql += " AND type = %s"
            params.append(device_type)
        sql += " ORDER BY created_at DESC"
        data = query(sql, tuple(params))
        return data if data else []

    @staticmethod
    def update(device_id, **kwargs):
        fields = []
        param_list = []
        for k, v in kwargs.items():
            if v is not None:
                fields.append(f"{k} = %s")
                param_list.append(v)
        if not fields:
            return 0
        param_list.append(device_id)
        sql = f"UPDATE devices SET {', '.join(fields)} WHERE id = %s"
        return execute(sql, tuple(param_list))

    @staticmethod
    def set_status(device_id, status):
        sql = "UPDATE devices SET status = %s, updated_at = NOW() WHERE id = %s"
        return execute(sql, (status, device_id))

    @staticmethod
    def delete(device_id):
        sql = "DELETE FROM devices WHERE id = %s"
        return execute(sql, (device_id,))

    @staticmethod
    def count(status=None):
        sql = "SELECT COUNT(*) as cnt FROM devices"
        params = []
        if status:
            sql += " WHERE status = %s"
            params.append(status)
        row = query(sql, tuple(params), fetchone=True)
        return row['cnt'] if row else 0