from models.database import query, execute

class AlertModel:
    @staticmethod
    def create(device_id, alert_type, severity, message, created_at=None):
        if created_at:
            sql = "INSERT INTO alerts (device_id, alert_type, severity, message, created_at) VALUES (%s, %s, %s, %s, %s)"
            return execute(sql, (device_id, alert_type, severity, message, created_at), return_id=True)
        else:
            sql = "INSERT INTO alerts (device_id, alert_type, severity, message) VALUES (%s, %s, %s, %s)"
            return execute(sql, (device_id, alert_type, severity, message), return_id=True)

    @staticmethod
    def list_all(severity=None, is_read=None, device_id=None, page=1, per_page=10):
        # 分页查告警列表
        sql = "SELECT a.*, d.name as device_name FROM alerts a LEFT JOIN devices d ON a.device_id = d.id WHERE 1=1"
        params = []
        if severity:
            sql += " AND a.severity = %s"
            params.append(severity)
        if is_read is not None:
            sql += " AND a.is_read = %s"
            params.append(is_read)
        if device_id:
            sql += " AND a.device_id = %s"
            params.append(device_id)
        sql += " ORDER BY a.id DESC LIMIT %s OFFSET %s"
        params.extend([per_page, (page - 1) * per_page])
        data_rows = query(sql, tuple(params))

        # 统计总数，加别名cnt，适配字典结果
        count_sql = "SELECT COUNT(*) as cnt FROM alerts WHERE 1=1"
        count_params = []
        if severity:
            count_sql += " AND severity = %s"
            count_params.append(severity)
        if is_read is not None:
            count_sql += " AND is_read = %s"
            count_params.append(is_read)
        if device_id:
            count_sql += " AND device_id = %s"
            count_params.append(device_id)
        count_res = query(count_sql, tuple(count_params))
        # 字典取值，修复KeyError
        total = count_res[0]["cnt"] if count_res else 0

        return data_rows if data_rows else [], total

    @staticmethod
    def mark_read(alert_id):
        execute("UPDATE alerts SET is_read = 1 WHERE id = %s", (alert_id,))

    @staticmethod
    def mark_all_read():
        execute("UPDATE alerts SET is_read = 1 WHERE is_read = 0")

    @staticmethod
    def delete(alert_id):
        execute("DELETE FROM alerts WHERE id = %s", (alert_id,))