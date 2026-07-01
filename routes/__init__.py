from routes.alerts_api import alerts_api_bp

def register_routes(app):
    # 统一接口前缀 /api
    app.register_blueprint(alerts_api_bp, url_prefix="/api")