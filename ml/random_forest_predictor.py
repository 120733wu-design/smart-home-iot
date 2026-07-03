import numpy as np, pandas as pd
from sklearn.ensemble import RandomForestRegressor
from datetime import datetime, timedelta
from models.sensor_data import SensorDataModel; from models.prediction import PredictionModel
from config import Config

_rf_predictor = None

class RandomForestPredictor:
    def __init__(self):
        self.models = {}
        self.metrics = {}
        self.feature_importances = {}

    def train(self, device_id, sensor_type):
        """训练随机森林模型"""
        raw = SensorDataModel.get_for_ml(device_id, sensor_type, 500)
        if not raw or len(raw) < 20:
            return False

        df = pd.DataFrame(raw)
        df['recorded_at'] = pd.to_datetime(df['recorded_at'])
        df = df.sort_values('recorded_at').reset_index(drop=True)
        df['value'] = pd.to_numeric(df['value'], errors='coerce')

        # 特征工程（与线性回归保持一致）
        df['hour'] = df['recorded_at'].dt.hour
        df['minute'] = df['recorded_at'].dt.minute
        df['day_of_week'] = df['recorded_at'].dt.dayofweek
        df['lag_1'] = df['value'].shift(1)
        df['lag_2'] = df['value'].shift(2)
        df['lag_3'] = df['value'].shift(3)
        df['rolling_mean'] = df['value'].rolling(window=5, min_periods=2).mean()
        df['rolling_std'] = df['value'].rolling(window=5, min_periods=2).std()

        df = df.dropna()
        if len(df) < 5:
            return False

        cols = ['hour', 'minute', 'day_of_week', 'lag_1', 'lag_2', 'lag_3',
                'rolling_mean', 'rolling_std']
        X = df[cols].values
        y = df['value'].values

        # 80/20 训练/验证切分
        sp = int(len(X) * 0.8)

        # 随机森林模型
        model = RandomForestRegressor(
            n_estimators=Config.RF_N_ESTIMATORS,
            max_depth=Config.RF_MAX_DEPTH,
            min_samples_split=Config.RF_MIN_SAMPLES_SPLIT,
            min_samples_leaf=Config.RF_MIN_SAMPLES_LEAF,
            random_state=Config.RF_RANDOM_STATE,
            n_jobs=-1
        )
        model.fit(X[:sp], y[:sp])

        # 验证集评估
        yp = model.predict(X[sp:])
        from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
        rmse = float(np.sqrt(mean_squared_error(y[sp:], yp)))
        mae = float(mean_absolute_error(y[sp:], yp))
        r2 = float(r2_score(y[sp:], yp))

        # 保存模型、指标和特征重要性
        key = (device_id, sensor_type)
        self.models[key] = model
        self.metrics[key] = {
            'rmse': round(rmse, 4),
            'mae': round(mae, 4),
            'r2': round(r2, 4),
            'n_estimators': Config.RF_N_ESTIMATORS,
            'max_depth': Config.RF_MAX_DEPTH
        }
        # 保存特征重要性
        self.feature_importances[key] = {
            col: round(float(imp), 4)
            for col, imp in zip(cols, model.feature_importances_)
        }

        print(f"[RF] {sensor_type} trained: RMSE={rmse:.4f} R²={r2:.4f} "
              f"n_estimators={Config.RF_N_ESTIMATORS}")
        return True

    def predict(self, device_id, sensor_type):
        """使用随机森林模型生成预测"""
        key = (device_id, sensor_type)
        if key not in self.models and not self.train(device_id, sensor_type):
            return None

        model = self.models[key]
        raw = SensorDataModel.get_for_ml(device_id, sensor_type, 50)
        if not raw or len(raw) < 5:
            return None

        df = pd.DataFrame(raw)
        df['recorded_at'] = pd.to_datetime(df['recorded_at'])
        df = df.sort_values('recorded_at')
        df['value'] = pd.to_numeric(df['value'], errors='coerce')

        lt = df['recorded_at'].iloc[-1]
        pts = [lt + timedelta(hours=i) for i in range(1, Config.ML_PREDICT_HOURS + 1)]

        preds = []
        lv = df['value'].tail(10).tolist()
        for ft in pts:
            fv = np.array([[
                ft.hour,
                ft.minute,
                ft.dayofweek,
                lv[-1],
                lv[-2] if len(lv) >= 2 else lv[-1],
                lv[-3] if len(lv) >= 3 else lv[-1],
                np.mean(lv[-5:]),
                np.std(lv[-5:])
            ]])
            pv = model.predict(fv)[0]
            r2 = self.metrics.get(key, {}).get('r2', 0)
            conf = max(0, min(100, r2 * 100))
            preds.append({
                'device_id': device_id,
                'sensor_type': sensor_type,
                'predicted_value': round(float(pv), 2),
                'confidence': round(float(conf), 2),
                'predicted_at': ft
            })
            lv.append(float(pv))

        batch = [(p['device_id'], p['sensor_type'], p['predicted_value'],
                  p['confidence'], p['predicted_at'], 'random_forest')
                 for p in preds]
        if batch:
            PredictionModel.batch_insert(batch)

        return {
            'device_id': device_id,
            'sensor_type': sensor_type,
            'model_type': 'random_forest',
            'predictions': [{
                **p,
                'predicted_at': p['predicted_at'].strftime('%Y-%m-%d %H:%M:%S')
            } for p in preds],
            'metrics': self.metrics.get(key, {}),
            'feature_importances': self.feature_importances.get(key, {})
        }

    def predict_all_devices(self):
        """为所有设备的所有传感器类型生成预测"""
        from models.device import DeviceModel
        for d in DeviceModel.list_all():
            for st in ['temperature', 'humidity']:
                self.predict(d['id'], st)

    def get_accuracy_metrics(self, device_id):
        """返回指定设备的精度指标和特征重要性"""
        results = {}
        for (did, st), m in self.metrics.items():
            if did == device_id:
                results[st] = {
                    **m,
                    'feature_importances': self.feature_importances.get((did, st), {})
                }
        if not results:
            for st in ['temperature', 'humidity']:
                self.train(device_id, st)
                key = (device_id, st)
                if key in self.metrics:
                    results[st] = {
                        **self.metrics[key],
                        'feature_importances': self.feature_importances.get(key, {})
                    }
        return results


def get_rf_predictor():
    """获取随机森林预测器全局单例"""
    global _rf_predictor
    if _rf_predictor is None:
        _rf_predictor = RandomForestPredictor()
    return _rf_predictor


def rf_scheduled_predict():
    """随机森林定时预测任务"""
    print("[RF] Scheduled prediction...")
    get_rf_predictor().predict_all_devices()
    print("[RF] Done")


def init_rf_scheduler(app):
    """初始化随机森林定时调度器"""
    from apscheduler.schedulers.background import BackgroundScheduler
    s = BackgroundScheduler()
    s.add_job(
        func=rf_scheduled_predict,
        trigger='interval',
        minutes=Config.ML_RETRAIN_INTERVAL_MINUTES,
        id='rf_ml_job',
        replace_existing=True
    )
    s.start()
    print(f"[RF] Scheduler started (every {Config.ML_RETRAIN_INTERVAL_MINUTES}min)")
