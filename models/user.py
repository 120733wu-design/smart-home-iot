from models.database import query, execute
class UserModel:
    @staticmethod
    def create(username, password_hash, role='user'):
        sql = "INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s)"
        return execute(sql, (username, password_hash, role), return_id=True)
    @staticmethod
    def find_by_username(username):
        sql = "SELECT * FROM users WHERE username = %s"
        return query(sql, (username,), fetchone=True)
    @staticmethod
    def find_by_id(user_id):
        sql = "SELECT * FROM users WHERE id = %s"
        return query(sql, (user_id,), fetchone=True)
    @staticmethod
    def list_all():
        sql = "SELECT id, username, role, created_at FROM users ORDER BY created_at DESC"
        return query(sql)
