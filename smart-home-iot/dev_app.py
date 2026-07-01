"""
Dev mode: Uses SQLite, seeds initial data, starts MQTT + mock data
python dev_app.py
"""
import os, sys, sqlite3, random, threading, time, numpy as np
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash

import config as cfg
cfg.Config.USE_SQLITE = True
cfg.Config.SQLITE_DB_PATH = os.path.abspath("dev.db")

# 模拟数据开关：环境变量 MOCK_DATA_ENABLED=false 可关闭
# 有硬件时 MQTT 数据会实时写入，无硬件时模拟数据自动补位
import models.database as _db

def _init():
    conn = _db.get_db(); c = conn.cursor()
    c.executescript('''
CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, role TEXT DEFAULT 'user', created_at DATETIME DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS devices (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, device_key TEXT UNIQUE NOT NULL, type TEXT DEFAULT 'sensor', status TEXT DEFAULT 'offline', location TEXT DEFAULT '', threshold_temp_min REAL DEFAULT 5.0, threshold_temp_max REAL DEFAULT 35.0, threshold_humi_min REAL DEFAULT 20.0, threshold_humi_max REAL DEFAULT 80.0, threshold_light_max REAL DEFAULT 900.0, created_at DATETIME DEFAULT CURRENT_TIMESTAMP, updated_at DATETIME DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS sensor_data (id INTEGER PRIMARY KEY AUTOINCREMENT, device_id INTEGER NOT NULL, sensor_type TEXT NOT NULL, value REAL NOT NULL, unit TEXT DEFAULT '', recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP);
CREATE INDEX IF NOT EXISTS idx_st ON sensor_data(device_id, sensor_type, recorded_at);
CREATE TABLE IF NOT EXISTS alerts (id INTEGER PRIMARY KEY AUTOINCREMENT, device_id INTEGER NOT NULL, alert_type TEXT NOT NULL, severity TEXT DEFAULT 'warning', message TEXT NOT NULL, is_read INTEGER DEFAULT 0, created_at DATETIME DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS control_commands (id INTEGER PRIMARY KEY AUTOINCREMENT, device_id INTEGER NOT NULL, command TEXT NOT NULL, params TEXT, status TEXT DEFAULT 'pending', created_at DATETIME DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS ml_predictions (id INTEGER PRIMARY KEY AUTOINCREMENT, device_id INTEGER NOT NULL, sensor_type TEXT NOT NULL, predicted_value REAL NOT NULL, confidence REAL, predicted_at DATETIME NOT NULL, created_at DATETIME DEFAULT CURRENT_TIMESTAMP);
''')
    conn.commit(); conn.close()

def _seed():
    conn = _db.get_db(); c = conn.cursor()
    # Admin user
    if not c.execute("SELECT id FROM users WHERE username='admin'").fetchone():
        c.execute("INSERT INTO users (username,password_hash,role) VALUES (?,?,?)", ('admin', generate_password_hash('admin123'), 'admin'))
    # Devices
    devs = [('esp8266-001','客厅环境监测器','客厅'),('esp8266-002','卧室环境监测器','卧室'),('esp8266-003','阳台环境监测器','阳台')]
    for k,n,l in devs:
        if not c.execute("SELECT id FROM devices WHERE device_key=?",(k,)).fetchone():
            c.execute("INSERT INTO devices (name,device_key,type,status,location) VALUES (?,?,'sensor','offline',?)",(n,k,l))
    conn.commit()
    dids = [r[0] for r in c.execute("SELECT id FROM devices").fetchall()]
    # Seed 72h of history data
    bases = {1:{'t':26,'h':50,'l':400},2:{'t':24,'h':55,'l':200},3:{'t':30,'h':45,'l':700}}
    now = datetime.now(); batch = []
    for did in dids:
        b = bases.get(did,{'t':25,'h':50,'l':300})
        for ha in range(72,0,-1):
            for mn in range(0,60,10):
                t = now - timedelta(hours=ha, minutes=mn)
                hf = 1 + 0.15 * np.sin((t.hour - 14) * np.pi / 12)
                ts = t.strftime('%Y-%m-%d %H:%M:%S')
                batch.append((did,'temperature',round(b['t']*hf+random.gauss(0,0.5),1),'C',ts))
                batch.append((did,'humidity',round(b['h']+random.gauss(0,1),1),'%',ts))
                batch.append((did,'light',round(b['l']+random.gauss(0,10),1),'lux',ts))
    c.executemany("INSERT INTO sensor_data (device_id,sensor_type,value,unit,recorded_at) VALUES (?,?,?,?,?)", batch)
    conn.commit()
    # Alerts
    for did in dids:
        for i in range(5):
            t = now - timedelta(hours=random.randint(1,48))
            c.execute("INSERT INTO alerts (device_id,alert_type,severity,message,is_read,created_at) VALUES (?,?,?,?,?,?)",
                      (did,'threshold',random.choice(['warning','critical','info']),f'Sensor anomaly ({random.uniform(30,38):.1f})',1 if i<3 else 0,t.strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit(); conn.close()
    print(f'[DEV] Seeded: {len(batch)} sensor rows')

if __name__ == '__main__':
    print('[DEV] Initializing SQLite...')
    _init(); _seed()
    from app import create_app
    app = create_app()
    # Start MQTT (try connecting to EMQX, silently fail if not available)
    from mqtt_client.client import init_mqtt, start_mqtt
    init_mqtt(app); start_mqtt()
    # Start ML scheduler
    from ml.predictor import init_scheduler; init_scheduler(app)
    # Start mock data (toggle with MOCK_DATA_ENABLED config)
    if cfg.Config.MOCK_DATA_ENABLED:
        try:
            from mock_data import start_mock_data; start_mock_data(app)
        except Exception as e: print(f'[DEV] Mock data: {e}')
    print(); print('='*60)
    print('  Smart Home IoT (Dev Mode)'); print(f'  URL: http://{cfg.Config.HOST}:{cfg.Config.PORT}')
    print('  Login: admin / admin123'); print(f'  Mock data: {"ON" if cfg.Config.MOCK_DATA_ENABLED else "OFF"}')
    print('  MQTT: active (real hardware data)'); print('='*60); print()
    app.run(host=cfg.Config.HOST, port=cfg.Config.PORT, debug=True, use_reloader=False)
