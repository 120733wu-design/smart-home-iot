import random, time, threading, numpy as np
from datetime import datetime
from models.device import DeviceModel; from models.sensor_data import SensorDataModel
from models.alert import AlertModel
from config import Config
_running = False
def _gen(sensor_type, base=None):
    if sensor_type == 'temperature': base=base or random.uniform(20,30); return round(base+random.gauss(0,1),1)
    elif sensor_type == 'humidity': base=base or random.uniform(40,70); return round(base+random.gauss(0,2),1)
    elif sensor_type == 'light': base=base or random.uniform(100,600); return round(max(0,base+random.gauss(0,20)),1)
    return 0
def _unit(st): return {'temperature':'C','humidity':'%','light':'lux'}.get(st,'')
def start_mock_data(app):
    global _running
    if _running: return
    _running = True
    def _run():
        global _running
        print("[MOCK] Mock data generator started")
        time.sleep(1)
        # 确保有模拟设备
        for key,name,loc in [('esp8266-001','客厅环境监测器','客厅'),('esp8266-002','卧室环境监测器','卧室'),('esp8266-003','阳台环境监测器','阳台')]:
            if not DeviceModel.find_by_key(key):
                DeviceModel.create(name=name, device_key=key, type='sensor', location=loc)
        devices = DeviceModel.list_all()
        bases = {}
        for d in devices:
            loc=d.get('location','')
            if '卧室' in loc: bases[d['id']]={'temperature':24,'humidity':55,'light':200}
            elif '阳台' in loc: bases[d['id']]={'temperature':30,'humidity':45,'light':700}
            else: bases[d['id']]={'temperature':26,'humidity':50,'light':400}
        # 首次ML预测
        time.sleep(3)
        try:
            from ml.predictor import get_predictor; get_predictor().predict_all_devices()
        except: pass
        tick = 0
        while _running:
            try:
                now=datetime.now()
                for device in devices:
                    did=device['id']; dkey=device['device_key']; b=bases.get(did,{'temperature':25,'humidity':50,'light':300})
                    hf=1+0.15*np.sin((now.hour-14)*np.pi/12)
                    for st in ['temperature','humidity','light']:
                        bv=b[st]*(hf if st=='temperature' else 1)
                        SensorDataModel.insert(did,st,_gen(st,bv),_unit(st))
                    if tick%5==0 and tick>0:
                        ht=_gen('temperature',38)
                        SensorDataModel.insert(did,'temperature',ht,'C')
                        print(f"[MOCK] Alert: {dkey} temp {ht}C")
                tick+=1
                if tick%3==0:
                    try: from ml.predictor import get_predictor; get_predictor().predict_all_devices()
                    except: pass
                time.sleep(10)
            except Exception as e: print(f"[MOCK] Error: {e}"); time.sleep(10)
    threading.Thread(target=_run, daemon=True).start()
def stop_mock_data():
    global _running; _running = False
    print("[MOCK] Stopped")
