from flask import Blueprint, request, jsonify
from models.alert import AlertModel
from models.database import query

alerts_api_bp = Blueprint("alerts_api", __name__)

# 分页告警列表接口
@alerts_api_bp.route("/alerts", methods=["GET"])
def get_all_alerts():
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 10))
    severity = request.args.get("severity")
    is_read = request.args.get("is_read")
    device_id = request.args.get("device_id")
    data_list, total_num = AlertModel.list_all(severity, is_read, device_id, page, per_page)
    return jsonify({
        "success": True,
        "data": data_list,
        "total": total_num
    })

# 告警统计接口（独立SQL，不再调用list_all避免重复报错）
@alerts_api_bp.route("/alerts/stats", methods=["GET"])
def alert_stats():
    total_res = query("SELECT COUNT(*) as cnt FROM alerts")
    total = total_res[0]["cnt"] if total_res else 0
    unread_res = query("SELECT COUNT(*) as cnt FROM alerts WHERE is_read = 0")
    unread_total = unread_res[0]["cnt"] if unread_res else 0
    return jsonify({
        "success": True,
        "total": total,
        "unread": unread_total
    })

# 全部标已读
@alerts_api_bp.route("/alerts/read-all", methods=["POST", "PUT"])
def read_all_alerts():
    AlertModel.mark_all_read()
    return jsonify({"success": True})

# 单条标已读
@alerts_api_bp.route("/alerts/<int:alert_id>/read", methods=["POST", "PUT"])
def read_single_alert(alert_id):
    AlertModel.mark_read(alert_id)
    return jsonify({"success": True})

# 删除告警
@alerts_api_bp.route("/alerts/<int:alert_id>", methods=["DELETE"])
def del_alert(alert_id):
    AlertModel.delete(alert_id)
    return jsonify({
        "success": True,
        "msg": "告警已清除"
    })