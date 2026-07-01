from models.database import query, execute
import json

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

    # ========== 人脸特征 — face_feature TEXT (JSON) ==========
    # 单账号仅存储一组人脸特征，重复录入自动覆盖

    @staticmethod
    def save_face_feature(user_id, embedding_list):
        """存储人脸特征向量（JSON 序列化存 TEXT 字段），覆盖已有特征"""
        feature_json = json.dumps(embedding_list)
        sql = "UPDATE users SET face_feature = %s, face_enabled = 1 WHERE id = %s"
        return execute(sql, (feature_json, user_id))

    @staticmethod
    def disable_face(user_id):
        sql = "UPDATE users SET face_feature = NULL, face_enabled = 0 WHERE id = %s"
        return execute(sql, (user_id,))

    @staticmethod
    def get_all_face_users():
        """返回所有已注册人脸的用户（id, username, embedding）"""
        sql = "SELECT id, username, face_feature FROM users WHERE face_enabled = 1 AND face_feature IS NOT NULL"
        rows = query(sql) or []
        result = []
        for r in rows:
            try:
                emb = json.loads(r["face_feature"]) if isinstance(r["face_feature"], str) else None
            except Exception:
                emb = None
            if emb:
                result.append({"id": r["id"], "username": r["username"], "embedding": emb})
        return result

    @staticmethod
    def has_face(user_id):
        """检查用户是否已注册人脸"""
        sql = "SELECT face_enabled FROM users WHERE id = %s"
        row = query(sql, (user_id,), fetchone=True)
        return row and row.get("face_enabled") == 1
