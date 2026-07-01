from models.database import query, execute
import json
class CommandModel:
    @staticmethod
    def create(device_id, command, params=None):
        p = json.dumps(params) if params else None
        sql = "INSERT INTO control_commands (device_id, command, params) VALUES (%s, %s, %s)"
        return execute(sql, (device_id, command, p), return_id=True)
    @staticmethod
    def update_status(cmd_id, status):
        return execute("UPDATE control_commands SET status = %s WHERE id = %s", (status, cmd_id))
    @staticmethod
    def list_by_device(device_id, page=1, per_page=20):
        sql = "SELECT * FROM control_commands WHERE device_id = %s ORDER BY created_at DESC LIMIT %s OFFSET %s"
        return query(sql, (device_id, per_page, (page-1)*per_page))
