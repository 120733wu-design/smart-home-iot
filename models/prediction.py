from models.database import query, execute, get_db
from datetime import datetime, timedelta
class PredictionModel:
    @staticmethod
    def insert(device_id, sensor_type, predicted_value, confidence, predicted_at):
        sql = "INSERT INTO ml_predictions (device_id, sensor_type, predicted_value, confidence, predicted_at) VALUES (%s, %s, %s, %s, %s)"
        return execute(sql, (device_id, sensor_type, predicted_value, confidence, predicted_at), return_id=True)
    @staticmethod
    def batch_insert(predictions):
        """批量插入预测数据，支持 5 列或 6 列 tuple
           predictions: list of (device_id, sensor_type, predicted_value, confidence, predicted_at[, created_at])
        """
        conn = None
        try:
            conn = get_db()
            cursor = conn.cursor()
            sql = "INSERT INTO ml_predictions (device_id, sensor_type, predicted_value, confidence, predicted_at, created_at) VALUES (%s, %s, %s, %s, %s, %s)"
            cursor.executemany(sql, predictions)
            conn.commit()
            return cursor.rowcount
        except Exception as e:
            if conn: conn.rollback()
            raise e
        finally:
            if conn: conn.close()
        return 0
    @staticmethod
    def get_predictions(device_id, sensor_type, hours=6):
        threshold = (datetime.now() - timedelta(hours=hours)).strftime('%Y-%m-%d %H:%M:%S')
        sql = "SELECT * FROM ml_predictions WHERE device_id = %s AND sensor_type = %s AND created_at >= %s ORDER BY predicted_at ASC"
        return query(sql, (device_id, sensor_type, threshold))
    @staticmethod
    def delete_old(hours=24):
        threshold = (datetime.now() - timedelta(hours=hours)).strftime('%Y-%m-%d %H:%M:%S')
        return execute("DELETE FROM ml_predictions WHERE created_at < %s", (threshold,))
