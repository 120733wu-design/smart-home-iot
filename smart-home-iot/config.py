import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'smart-home-iot-secret-key-2024')
    SESSION_TYPE = 'filesystem'
    SESSION_FILE_DIR = os.path.join(os.path.dirname(__file__), '.sessions')

    # MySQL 已修改为你刚设置的账号库
    MYSQL_HOST = os.environ.get('MYSQL_HOST', '127.0.0.1')
    MYSQL_PORT = int(os.environ.get('MYSQL_PORT', 3306))
    MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', 'root')
    MYSQL_DB = os.environ.get('MYSQL_DB', 'smart_home')

    # SQLite 开发库：现在不用，关闭SQLite强制使用MySQL
    USE_SQLITE = os.environ.get('USE_SQLITE', 'False') == 'True'
    SQLITE_DB_PATH = os.path.join(os.path.dirname(__file__), 'dev.db')

    # MQTT（本地EMQX不变）
    MQTT_BROKER_HOST = os.environ.get('MQTT_BROKER_HOST', '192.168.76.149')
    MQTT_BROKER_PORT = int(os.environ.get('MQTT_BROKER_PORT', 1883))
    MQTT_USERNAME = os.environ.get('MQTT_USERNAME', '')
    MQTT_PASSWORD = os.environ.get('MQTT_PASSWORD', '')
    MQTT_TOPIC_PREFIX = 'device'

    # 模拟数据关闭，只显示ESP8266真实温湿度
    #MOCK_DATA_ENABLED = os.environ.get('MOCK_DATA_ENABLED', 'False') == 'True'
    MOCK_DATA_ENABLED = False

    # 告警阈值
    ALERT_TEMP_MIN = 5.0; ALERT_TEMP_MAX = 35.0
    ALERT_HUMI_MIN = 20.0; ALERT_HUMI_MAX = 80.0
    ALERT_LIGHT_MAX = 900.0

    # ML
    ML_PREDICT_HOURS = 6
    ML_RETRAIN_INTERVAL_MINUTES = 30
    ML_MIN_DATA_HOURS = 48

    # Flask
    DEBUG = os.environ.get('FLASK_DEBUG', '1') == '1'
    HOST = os.environ.get('FLASK_HOST', '0.0.0.0')
    PORT = int(os.environ.get('FLASK_PORT', 5000))