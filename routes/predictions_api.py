from flask import Blueprint, request, jsonify
from models.prediction import PredictionModel; from models.device import DeviceModel
from models.sensor_data import SensorDataModel
predictions_api_bp = Blueprint('predictions_api', __name__)
@predictions_api_bp.route('/predictions', methods=['GET'])
def get_predictions():
    did=request.args.get('device_id',type=int) or (DeviceModel.list_all() or [{}])[0].get('id')
    st=request.args.get('type','temperature'); h=int(request.args.get('hours',6))
    p=PredictionModel.get_predictions(did,st,h)
    for i in p:
        if i.get('predicted_at'): i['predicted_at']=i['predicted_at'].strftime('%Y-%m-%d %H:%M:%S')
        if i.get('created_at'): i['created_at']=i['created_at'].strftime('%Y-%m-%d %H:%M:%S')
    return jsonify({'success':True,'data':p})
@predictions_api_bp.route('/predictions/generate', methods=['POST'])
def generate_predictions():
    from ml.predictor import Predictor
    data=request.get_json() or {}; did=data.get('device_id') or (DeviceModel.list_all() or [{}])[0].get('id')
    st=data.get('type'); p=Predictor()
    types=[st] if st else ['temperature','humidity']
    results=[r for t in types if (r:=p.predict(did,t))]
    if not results: return jsonify({'success':False,'message':'预测失败：数据不足'}),400
    return jsonify({'success':True,'message':'预测完成','data':results})
@predictions_api_bp.route('/predictions/latest', methods=['GET'])
def get_latest_predictions():
    did=request.args.get('device_id',type=int) or (DeviceModel.list_all() or [{}])[0].get('id')
    st=request.args.get('type','temperature'); hh=int(request.args.get('history_hours',3)); ph=int(request.args.get('predict_hours',6))
    hist=SensorDataModel.get_latest_value(did,st,hh)
    preds=PredictionModel.get_predictions(did,st,ph)
    # hist 中的 recorded_at 已由 get_latest_value 格式化为字符串，无需重复 strftime
    # (历史数据由 get_latest_value 统一格式化)
    for i in preds:
        if i.get('predicted_at'): i['predicted_at']=i['predicted_at'].strftime('%Y-%m-%d %H:%M:%S')
    return jsonify({'success':True,'data':{'history':hist,'predictions':preds,'sensor_type':st,'device_id':did}})

@predictions_api_bp.route('/predictions/accuracy', methods=['GET'])
def get_accuracy():
    did = request.args.get('device_id', type=int)
    if not did:
        devs = DeviceModel.list_all()
        if not devs: return jsonify({'success': False, 'message': '没有可用设备'}), 404
        did = devs[0]['id']
    from ml.predictor import get_predictor
    predictor = get_predictor()
    accuracy = predictor.get_accuracy_metrics(did)
    return jsonify({'success': True, 'data': accuracy})
