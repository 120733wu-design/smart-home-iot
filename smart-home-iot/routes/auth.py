from flask import Blueprint, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
from models.user import UserModel
auth_bp = Blueprint('auth', __name__)
@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json(); username = data.get('username','').strip(); password = data.get('password','')
    if not username or not password: return jsonify({'success':False,'message':'用户名和密码不能为空'}),400
    if len(username)<3 or len(username)>50: return jsonify({'success':False,'message':'用户名长度需在3-50之间'}),400
    if len(password)<6: return jsonify({'success':False,'message':'密码长度不能少于6位'}),400
    if UserModel.find_by_username(username): return jsonify({'success':False,'message':'用户名已存在'}),409
    user_id = UserModel.create(username, generate_password_hash(password))
    session['user_id'] = user_id; session['username'] = username
    return jsonify({'success':True,'message':'注册成功','user':{'id':user_id,'username':username}})
@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json(); username = data.get('username','').strip(); password = data.get('password','')
    user = UserModel.find_by_username(username)
    if not user or not check_password_hash(user['password_hash'], password):
        return jsonify({'success':False,'message':'用户名或密码错误'}),401
    session['user_id'] = user['id']; session['username'] = user['username']
    return jsonify({'success':True,'message':'登录成功','user':{'id':user['id'],'username':user['username'],'role':user['role']}})
@auth_bp.route('/logout', methods=['POST'])
def logout(): session.clear(); return jsonify({'success':True,'message':'已退出登录'})
@auth_bp.route('/session', methods=['GET'])
def check_session():
    if session.get('user_id'): return jsonify({'authenticated':True,'user':{'id':session['user_id'],'username':session.get('username')}})
    return jsonify({'authenticated':False}),401
