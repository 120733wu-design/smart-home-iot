import os, sys
from flask import Flask
from config import Config

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    os.makedirs(config_class.SESSION_FILE_DIR, exist_ok=True)

    # 导入路由蓝图
    from routes.pages import pages_bp
    from routes.auth import auth_bp
    from routes.devices_api import devices_api_bp
    from routes.data_api import data_api_bp
    from routes.alerts_api import alerts_api_bp
    from routes.predictions_api import predictions_api_bp
    # 新增：导入阈值配置蓝图
    from routes.threshold_api import threshold_bp
    # 新增：导入YOLOv5检测蓝图
    from routes.yolo_api import yolo_bp
    # 新增：导入远程控制蓝图
    from routes.control_api import control_api_bp
    # 新增：导入管理员蓝图
    from routes.admin_api import admin_bp

    # 注册蓝图：auth、页面类无/api前缀；接口统一/api
    app.register_blueprint(pages_bp)
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(threshold_bp)  # 阈值页面属于页面路由，不加/api
    app.register_blueprint(devices_api_bp, url_prefix='/api')
    app.register_blueprint(data_api_bp, url_prefix='/api')
    app.register_blueprint(alerts_api_bp, url_prefix='/api')
    app.register_blueprint(predictions_api_bp, url_prefix='/api')
    app.register_blueprint(yolo_bp, url_prefix='/yolo')
    app.register_blueprint(control_api_bp, url_prefix='/api')
    app.register_blueprint(admin_bp, url_prefix='/api')

    # 避免 favicon.ico 404
    @app.route('/favicon.ico')
    def favicon():
        return '', 204

    app.config['MQTT_CLIENT'] = None
    return app

if __name__ == '__main__':
    app = create_app()

    # 确保数据库和表结构存在（含迁移）
    from models.database import init_db
    try:
        init_db()
        print("[DB] Database initialized and migrated")
    except Exception as e:
        print(f"[DB] Init/migration warning (non-fatal): {e}")

    # MQTT、定时任务、模拟数据
    from mqtt_client.client import init_mqtt, start_mqtt
    init_mqtt(app)
    start_mqtt()

    from ml.predictor import init_scheduler
    init_scheduler(app)

    from ml.random_forest_predictor import init_rf_scheduler
    init_rf_scheduler(app)

    if Config.MOCK_DATA_ENABLED:
        try:
            from mock_data import start_mock_data
            start_mock_data(app)
        except ImportError:
            pass

    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG, use_reloader=False)