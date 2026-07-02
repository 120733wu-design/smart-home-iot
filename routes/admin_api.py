from flask import Blueprint, request, jsonify, session
from models.user import UserModel
from werkzeug.security import generate_password_hash

admin_bp = Blueprint('admin', __name__)


def _is_admin():
    """检查当前登录用户是否为管理员"""
    user_id = session.get('user_id')
    if not user_id:
        return False
    user = UserModel.find_by_id(user_id)
    return user and user.get('role') == 'admin'


# ===== 权限检查装饰器 =====
def require_admin(f):
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not _is_admin():
            return jsonify({'success': False, 'message': '需要管理员权限'}), 403
        return f(*args, **kwargs)
    return wrapper


@admin_bp.route('/admin/users', methods=['GET'])
@require_admin
def list_users():
    """获取所有用户列表"""
    users = UserModel.list_all()
    # 格式化时间
    for u in users:
        if u.get('created_at') and hasattr(u['created_at'], 'strftime'):
            u['created_at_str'] = u['created_at'].strftime('%Y-%m-%d %H:%M:%S')
        else:
            u['created_at_str'] = str(u.get('created_at', ''))
    return jsonify({'success': True, 'data': users, 'total': len(users)})


@admin_bp.route('/admin/users/<int:user_id>/role', methods=['PUT'])
@require_admin
def update_user_role(user_id):
    """修改用户角色"""
    data = request.get_json() or {}
    new_role = data.get('role', '').strip()
    if new_role not in ('admin', 'user'):
        return jsonify({'success': False, 'message': '角色值无效，只能为 admin 或 user'}), 400

    user = UserModel.find_by_id(user_id)
    if not user:
        return jsonify({'success': False, 'message': '用户不存在'}), 404

    # 不允许把自己降级
    if user_id == session.get('user_id') and new_role != 'admin':
        return jsonify({'success': False, 'message': '不能修改自己的管理员权限'}), 400

    UserModel.update_role(user_id, new_role)
    return jsonify({'success': True, 'message': f'用户 {user["username"]} 角色已更新为 {new_role}'})


@admin_bp.route('/admin/users/<int:user_id>/reset-password', methods=['POST'])
@require_admin
def reset_password(user_id):
    """重置用户密码为默认密码 123456"""
    user = UserModel.find_by_id(user_id)
    if not user:
        return jsonify({'success': False, 'message': '用户不存在'}), 404

    new_hash = generate_password_hash('123456')
    UserModel.update_password(user_id, new_hash)
    return jsonify({'success': True, 'message': f'用户 {user["username"]} 密码已重置为 123456'})


@admin_bp.route('/admin/users/<int:user_id>', methods=['DELETE'])
@require_admin
def delete_user(user_id):
    """删除用户"""
    user = UserModel.find_by_id(user_id)
    if not user:
        return jsonify({'success': False, 'message': '用户不存在'}), 404

    # 不能删除自己
    if user_id == session.get('user_id'):
        return jsonify({'success': False, 'message': '不能删除自己的账号'}), 400

    result = UserModel.delete(user_id)
    if result is False:
        return jsonify({'success': False, 'message': '不能删除最后一个管理员账号'}), 400

    return jsonify({'success': True, 'message': f'用户 {user["username"]} 已删除'})


@admin_bp.route('/admin/check', methods=['GET'])
def check_admin():
    """检查当前用户是否为管理员"""
    return jsonify({'success': True, 'is_admin': _is_admin()})
