from models.database import query, execute
class AlertModel:
    @staticmethod
    def create(device_id, alert_type, severity, message):
        sql = "INSERT INTO alerts (device_id, alert_type, severity, message) VALUES (%s, %s, %s, %s)"
        return execute(sql, (device_id, alert_type, severity, message), return_id=True)
    @staticmethod
    def list_all(severity=None, is_read=None, device_id=None, page=1, per_page=50):
        sql = "SELECT a.*, d.name as device_name FROM alerts a LEFT JOIN devices d ON a.device_id = d.id WHERE 1=1"; params = []
        if severity: sql += " AND a.severity = %s"; params.append(severity)
        if is_read is not None: sql += " AND a.is_read = %s"; params.append(1 if is_read else 0)
        if device_id: sql += " AND a.device_id = %s"; params.append(device_id)
        sql += " ORDER BY a.created_at DESC LIMIT %s OFFSET %s"
        params.extend([per_page, (page-1)*per_page])
        return query(sql, tuple(params))
    @staticmethod
    def mark_read(alert_id): return execute("UPDATE alerts SET is_read = 1 WHERE id = %s", (alert_id,))
    @staticmethod
    def mark_all_read(): return execute("UPDATE alerts SET is_read = 1 WHERE is_read = 0")
    @staticmethod
    def delete(alert_id): return execute("DELETE FROM alerts WHERE id = %s", (alert_id,))
    @staticmethod
    def count_unread():
        r = query("SELECT COUNT(*) as cnt FROM alerts WHERE is_read = 0", fetchone=True)
        return r['cnt'] if r else 0

    @staticmethod
    def count_by_severity():
        sql = "SELECT severity, COUNT(*) as cnt FROM alerts WHERE is_read = 0 GROUP BY severity"
        return query(sql)
