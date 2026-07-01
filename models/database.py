import pymysql
import sqlite3
import os
from datetime import datetime
from config import Config

def get_db(config=None):
    cfg = config or Config
    if getattr(cfg, 'USE_SQLITE', False):
        db_path = getattr(cfg, 'SQLITE_DB_PATH', None) or os.path.join(os.path.dirname(__file__), '..', 'dev.db')
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn
    try:
        conn = pymysql.connect(host=cfg.MYSQL_HOST, port=cfg.MYSQL_PORT, user=cfg.MYSQL_USER,
            password=cfg.MYSQL_PASSWORD, database=cfg.MYSQL_DB, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
        return conn
    except Exception as e:
        raise ConnectionError(f"MySQL connection failed: {e}")

def close_db(conn):
    if conn: conn.close()

def migrate_db(config=None):
    """
    检查并迁移 MySQL 表结构，确保 sensor_data 表有预期的列。
    使用 try/except 逐一 ADD COLUMN，列已存在时忽略 Duplicate column 错误。
    """
    cfg = config or Config
    if getattr(cfg, 'USE_SQLITE', False):
        return
    conn = None
    try:
        conn = pymysql.connect(host=cfg.MYSQL_HOST, port=cfg.MYSQL_PORT, user=cfg.MYSQL_USER,
            password=cfg.MYSQL_PASSWORD, database=cfg.MYSQL_DB, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
        cursor = conn.cursor()
        migrations = [
            "ALTER TABLE sensor_data ADD COLUMN sensor_type VARCHAR(20) NOT NULL DEFAULT ''",
            "ALTER TABLE sensor_data ADD COLUMN value DECIMAL(10,2) NOT NULL DEFAULT 0.00",
            "ALTER TABLE sensor_data ADD COLUMN unit VARCHAR(20) DEFAULT ''",
            "ALTER TABLE sensor_data ADD COLUMN recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP",
            # 旧版宽表：将独立列改为可空，兼容新归一化 insert
            "ALTER TABLE sensor_data MODIFY temperature DECIMAL(5,1) DEFAULT NULL",
            "ALTER TABLE sensor_data MODIFY humidity DECIMAL(5,1) DEFAULT NULL",
            "ALTER TABLE sensor_data MODIFY lightness INT DEFAULT NULL",
            # 将 FK 从旧的 device (单数) 表重定向到 devices (复数)
            ("ALTER TABLE sensor_data DROP FOREIGN KEY sensor_data_ibfk_1", True),
            ("DROP TABLE IF EXISTS device", True),
            ("ALTER TABLE sensor_data ADD CONSTRAINT sensor_data_ibfk_devices "
             "FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE", True),
        ]
        for stmt in migrations:
            try:
                if isinstance(stmt, tuple):
                    sql, silent = stmt
                    cursor.execute(sql)
                else:
                    cursor.execute(stmt)
            except Exception:
                pass  # 列已存在则跳过
        conn.commit()
    except Exception as e:
        print(f"[DB] Migration warning: {e}")
    finally:
        if conn:
            conn.close()

def init_db(config=None):
    cfg = config or Config
    if getattr(cfg, 'USE_SQLITE', False):
        import sqlite3
        db_path = getattr(cfg, 'SQLITE_DB_PATH', None) or os.path.join(os.path.dirname(__file__), '..', 'dev.db')
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA foreign_keys=ON")
        return conn
    conn = pymysql.connect(host=cfg.MYSQL_HOST, port=cfg.MYSQL_PORT, user=cfg.MYSQL_USER,
        password=cfg.MYSQL_PASSWORD, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
    try:
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{cfg.MYSQL_DB}` CHARACTER SET utf8mb4")
        cursor.execute(f"USE `{cfg.MYSQL_DB}`")
        import os as _os
        schema_path = _os.path.join(_os.path.dirname(__file__), '..', 'database', 'schema.sql')
        with open(schema_path, 'r', encoding='utf-8') as f:
            statements = [s.strip() for s in f.read().split(';') if s.strip()]
        for stmt in statements:
            cursor.execute(stmt)
        conn.commit()
    except Exception as e:
        print(f"[DB] Init error: {e}"); raise
    finally:
        conn.close()
    migrate_db(config)
    return get_db(config)

def query(sql, params=None, config=None, fetchone=False):
    conn = get_db(config)
    try:
        cursor = conn.cursor()
        if isinstance(conn, sqlite3.Connection):
            sql = sql.replace('%s', '?')
        cursor.execute(sql, params or ())
        if fetchone:
            result = cursor.fetchone()
            return dict(result) if result else None
        rows = cursor.fetchall()
        result = [dict(r) for r in rows]
        if isinstance(conn, sqlite3.Connection):
            for row in result:
                for k, v in row.items():
                    if isinstance(v, str) and len(v) == 19 and v[4] == '-' and v[7] == '-':
                        try: row[k] = datetime.strptime(v, '%Y-%m-%d %H:%M:%S')
                        except: pass
        return result
    finally:
        close_db(conn)

def execute(sql, params=None, config=None, return_id=False):
    conn = get_db(config)
    try:
        cursor = conn.cursor()
        if isinstance(conn, sqlite3.Connection):
            sql = sql.replace('%s', '?')
        cursor.execute(sql, params or ())
        conn.commit()
        if return_id: return cursor.lastrowid
        return cursor.rowcount
    except Exception as e:
        conn.rollback(); raise e
    finally:
        close_db(conn)
