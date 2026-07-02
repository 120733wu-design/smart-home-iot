from models.database import query, execute
import json
class CommandModel:
    @staticmethod
    def create(device_id, command, params=None):
        p = json.dumps(params) if params else None
        sql = "INSERT INTO control_commands (device_id, command, params) VALUES (%s, %s, %s)"
        return execute(sql, (device_id, command, p), return_id=True)

    @staticmethod
    def create_with_key(device_key, command, params=None):
        """根据 device_key 找到 device_id 后创建命令记录"""
        dev = query("SELECT id FROM devices WHERE device_key = %s", (device_key,), fetchone=True)
        if not dev:
            return None
        return CommandModel.create(dev['id'], command, params)

    @staticmethod
    def update_status(cmd_id, status):
        return execute("UPDATE control_commands SET status = %s WHERE id = %s", (status, cmd_id))

    @staticmethod
    def list_by_device(device_id, page=1, per_page=20):
        sql = "SELECT * FROM control_commands WHERE device_id = %s ORDER BY created_at DESC LIMIT %s OFFSET %s"
        return query(sql, (device_id, per_page, (page-1)*per_page))

    @staticmethod
    def list_all(page=1, per_page=50):
        """查询所有设备的命令历史，带设备名称"""
        sql = """SELECT cc.*, d.name as device_name, d.device_key
                 FROM control_commands cc
                 LEFT JOIN devices d ON cc.device_id = d.id
                 ORDER BY cc.created_at DESC LIMIT %s OFFSET %s"""
        return query(sql, (per_page, (page-1)*per_page))

    @staticmethod
    def count_all():
        r = query("SELECT COUNT(*) as cnt FROM control_commands", fetchone=True)
        return r['cnt'] if r else 0
