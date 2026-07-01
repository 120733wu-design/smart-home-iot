import numpy as np, pandas as pd
from sklearn.linear_model import LinearRegression
from datetime import datetime, timedelta
from models.sensor_data import SensorDataModel; from models.prediction import PredictionModel
from config import Config
_predictor = None
class Predictor:
    def __init__(self): self.models={}; self.metrics={}
    def train(self, device_id, sensor_type):
        raw=SensorDataModel.get_for_ml(device_id,sensor_type,500)
        if not raw or len(raw)<20: return False
        df=pd.DataFrame(raw); df['recorded_at']=pd.to_datetime(df['recorded_at']); df=df.sort_values('recorded_at').reset_index(drop=True)
        df['value']=pd.to_numeric(df['value'], errors='coerce')
        df['hour']=df['recorded_at'].dt.hour; df['minute']=df['recorded_at'].dt.minute; df['day_of_week']=df['recorded_at'].dt.dayofweek
        df['lag_1']=df['value'].shift(1); df['lag_2']=df['value'].shift(2); df['lag_3']=df['value'].shift(3)
        df['rolling_mean']=df['value'].rolling(window=5,min_periods=2).mean()
        df['rolling_std']=df['value'].rolling(window=5,min_periods=2).std()
        df=df.dropna()
        if len(df)<5: return False
        cols=['hour','minute','day_of_week','lag_1','lag_2','lag_3','rolling_mean','rolling_std']
        X=df[cols].values; y=df['value'].values
        sp=int(len(X)*0.8); model=LinearRegression(); model.fit(X[:sp],y[:sp])
        yp=model.predict(X[sp:])
        from sklearn.metrics import mean_squared_error,mean_absolute_error,r2_score
        rmse=float(np.sqrt(mean_squared_error(y[sp:],yp))); mae=float(mean_absolute_error(y[sp:],yp)); r2=float(r2_score(y[sp:],yp))
        self.models[(device_id,sensor_type)]=model
        self.metrics[(device_id,sensor_type)]={'rmse':round(rmse,4),'mae':round(mae,4),'r2':round(r2,4)}
        print(f"[ML] {sensor_type} trained: RMSE={rmse:.4f} R2={r2:.4f}"); return True
    def predict(self, device_id, sensor_type):
        key=(device_id,sensor_type)
        if key not in self.models and not self.train(device_id,sensor_type): return None
        model=self.models[key]
        raw=SensorDataModel.get_for_ml(device_id,sensor_type,50)
        if not raw or len(raw)<5: return None
        df=pd.DataFrame(raw); df['recorded_at']=pd.to_datetime(df['recorded_at']); df=df.sort_values('recorded_at')
        df['value']=pd.to_numeric(df['value'], errors='coerce')
        lt=df['recorded_at'].iloc[-1]
        pts=[lt+timedelta(hours=i) for i in range(1,Config.ML_PREDICT_HOURS+1)]
        preds=[]; lv=df['value'].tail(10).tolist()
        for ft in pts:
            fv=np.array([[ft.hour,ft.minute,ft.dayofweek,lv[-1],lv[-2] if len(lv)>=2 else lv[-1],lv[-3] if len(lv)>=3 else lv[-1],np.mean(lv[-5:]),np.std(lv[-5:])]])
            pv=model.predict(fv)[0]
            r2=self.metrics.get(key,{}).get('r2',0); conf=max(0,min(100,r2*100))
            preds.append({'device_id':device_id,'sensor_type':sensor_type,'predicted_value':round(float(pv),2),'confidence':round(float(conf),2),'predicted_at':ft})
            lv.append(float(pv))
        # 新增：计算东八区当前创建时间，替代数据库默认UTC时间
        now_cst = datetime.utcnow() + timedelta(hours=8)
        created_str = now_cst.strftime("%Y-%m-%d %H:%M:%S")
        # batch 增加 created_at 字段作为第六个参数
        batch=[(p['device_id'],p['sensor_type'],p['predicted_value'],p['confidence'],p['predicted_at'], created_str) for p in preds]
        if batch: PredictionModel.batch_insert(batch)
        return {'device_id':device_id,'sensor_type':sensor_type,'predictions':[{**p,'predicted_at':p['predicted_at'].strftime('%Y-%m-%d %H:%M:%S')} for p in preds],'metrics':self.metrics.get(key,{})}
    def predict_all_devices(self):
        from models.device import DeviceModel
        for d in DeviceModel.list_all():
            for st in ['temperature','humidity']: self.predict(d['id'],st)
    def get_accuracy_metrics(self, device_id):
        """Return accuracy metrics for all sensor types belonging to a device."""
        results = {}
        for (did, st), m in self.metrics.items():
            if did == device_id:
                results[st] = m
        if not results:
            for st in ['temperature', 'humidity']:
                self.train(device_id, st)
                key = (device_id, st)
                if key in self.metrics:
                    results[st] = m
        return results
def get_predictor():
    global _predictor
    if _predictor is None: _predictor=Predictor()
    return _predictor
def scheduled_predict():
    print("[ML] Scheduled prediction..."); get_predictor().predict_all_devices(); print("[ML] Done")
def init_scheduler(app):
    from apscheduler.schedulers.background import BackgroundScheduler
    s=BackgroundScheduler()
    s.add_job(func=scheduled_predict,trigger='interval',minutes=Config.ML_RETRAIN_INTERVAL_MINUTES,id='ml_job',replace_existing=True)
    s.start(); print(f"[ML] Scheduler started (every {Config.ML_RETRAIN_INTERVAL_MINUTES}min)")
    app.config['SCHEDULER']=s