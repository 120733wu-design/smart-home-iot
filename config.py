import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'smart-home-iot-secret-key-2024')
    SESSION_TYPE = 'filesystem'
    SESSION_FILE_DIR = os.path.join(os.path.dirname(__file__), '.sessions')

    # MySQL 宝塔云端数据库配置
    MYSQL_HOST = os.environ.get('MYSQL_HOST', '127.0.0.1')
    MYSQL_PORT = int(os.environ.get('MYSQL_PORT', 3306))
    # 修复环境变量参数错误
    MYSQL_USER = os.environ.get('MYSQL_USER', 'smart_home')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', '1207yiwu')
    MYSQL_DB = os.environ.get('MYSQL_DB', 'smart_home')

    # SQLite 开发库：云端强制关闭，使用MySQL
    USE_SQLITE = os.environ.get('USE_SQLITE', 'False') == 'True'
    SQLITE_DB_PATH = os.path.join(os.path.dirname(__file__), 'dev.db')

    # MQTT 本地EMQX
    MQTT_BROKER_HOST = os.environ.get('MQTT_BROKER_HOST', '127.0.0.1')
    MQTT_BROKER_PORT = int(os.environ.get('MQTT_BROKER_PORT', 1883))
    MQTT_USERNAME = os.environ.get('MQTT_USERNAME', '')
    MQTT_PASSWORD = os.environ.get('MQTT_PASSWORD', '')
    MQTT_TOPIC_PREFIX = 'device'

    # 模拟数据关闭，仅接收ESP硬件真实数据
    MOCK_DATA_ENABLED = False

    # 全局默认告警阈值（页面配置阈值会覆盖这里）
    ALERT_TEMP_MIN = 5.0; ALERT_TEMP_MAX = 35.0
    ALERT_HUMI_MIN = 20.0; ALERT_HUMI_MAX = 80.0
    ALERT_LIGHT_MAX = 900.0

    # 机器学习预测配置
    ML_PREDICT_HOURS = 6
    ML_RETRAIN_INTERVAL_MINUTES = 30
    ML_MIN_DATA_HOURS = 48

    # Flask服务监听0.0.0.0，外网可访问
    DEBUG = os.environ.get('FLASK_DEBUG', '1') == '1'
    HOST = os.environ.get('FLASK_HOST', '0.0.0.0')
    PORT = int(os.environ.get('FLASK_PORT', 5000))