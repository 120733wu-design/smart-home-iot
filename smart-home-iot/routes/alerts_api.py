from flask import Blueprint, request, jsonify
from models.alert import AlertModel
alerts_api_bp = Blueprint('alerts_api', __name__)
@alerts_api_bp.route('/alerts', methods=['GET'])
def list_alerts():
    sev=request.args.get('severity'); ir=request.args.get('is_read'); did=request.args.get('device_id')
    p=int(request.args.get('page',1)); pp=int(request.args.get('per_page',50))
    if ir is not None: ir=ir.lower()=='true'
    a=AlertModel.list_all(severity=sev,is_read=ir,device_id=did,page=p,per_page=pp)
    for i in a:
        if i.get('created_at'): i['created_at']=i['created_at'].strftime('%Y-%m-%d %H:%M:%S')
    return jsonify({'success':True,'data':a})
@alerts_api_bp.route('/alerts/<int:alert_id>/read', methods=['PUT'])
def mark_read(alert_id): AlertModel.mark_read(alert_id); return jsonify({'success':True,'message':'已标记为已读'})
@alerts_api_bp.route('/alerts/read-all', methods=['PUT'])
def mark_all_read(): return jsonify({'success':True,'message':f'已标记 {AlertModel.mark_all_read()} 条告警'})
@alerts_api_bp.route('/alerts/<int:alert_id>', methods=['DELETE'])
def delete_alert(alert_id): AlertModel.delete(alert_id); return jsonify({'success':True,'message':'告警已删除'})
@alerts_api_bp.route('/alerts/stats', methods=['GET'])
def alert_stats():
    uc=AlertModel.count_unread(); bs=AlertModel.count_by_severity() if hasattr(AlertModel,'count_by_severity') else []
    sm={i['severity']:i['cnt'] for i in bs} if bs else {'info':0,'warning':0,'critical':0}
    return jsonify({'success':True,'data':{'unread_count':uc,'severity_counts':sm}})
