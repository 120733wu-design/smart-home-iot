from flask import Blueprint, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
from models.user import UserModel
from functools import wraps
import base64, io, os, json, numpy as np
from PIL import Image

# ===== 人脸检测模型（延迟加载）=====
_face_model = None
_FACE_SIMILARITY_THRESHOLD = 0.65

def _get_face_model():
    global _face_model
    if _face_model is None:
        from ultralytics import YOLO
        model_path = os.path.join(os.path.dirname(__file__), '..', 'yolo11n.pt')
        if not os.path.exists(model_path):
            model_path = 'yolo11n.pt'
        _face_model = YOLO(model_path)
        print(f"[FACE] Model loaded: {model_path}")
    return _face_model

def _extract_face_embedding(pil_img):
    """从PIL图像中提取人脸特征向量，返回 256 维归一化 list"""
    model = _get_face_model()
    results = model(pil_img, verbose=False)
    for r in results:
        boxes = r.boxes
        if boxes is not None and len(boxes) > 0:
            box = boxes.xyxy[0].cpu().numpy()
            x1, y1, x2, y2 = map(int, box)
            face = pil_img.crop((x1, y1, x2, y2)).resize((112, 112)).convert('L')
            face_small = face.resize((16, 16))
            pixels = np.array(face_small, dtype=np.float32).flatten()
            norm = np.linalg.norm(pixels)
            if norm > 0:
                pixels = pixels / norm
            return pixels.tolist(), (x1, y1, x2, y2)
    return None, None

def _cosine_similarity(a, b):
    a, b = np.array(a), np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))

# ===== 登录鉴权装饰器 — 返回 JSON 不跳转 =====
def login_required_json(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get('user_id'):
            return jsonify({"success": False, "message": "请先登录后再操作"}), 401
        return f(*args, **kwargs)
    return wrapper

# ===== Blueprint =====
auth_bp = Blueprint('auth', __name__)

# ── 账号注册 ──
@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '')
    if not username or not password:
        return jsonify({'success': False, 'message': '用户名和密码不能为空'}), 400
    if len(username) < 3 or len(username) > 50:
        return jsonify({'success': False, 'message': '用户名长度需在3-50之间'}), 400
    if len(password) < 6:
        return jsonify({'success': False, 'message': '密码长度不能少于6位'}), 400
    if UserModel.find_by_username(username):
        return jsonify({'success': False, 'message': '用户名已存在'}), 409
    user_id = UserModel.create(username, generate_password_hash(password))
    session['user_id'] = user_id
    session['username'] = username
    return jsonify({'success': True, 'message': '注册成功', 'user': {'id': user_id, 'username': username}})

# ── 账号密码登录 ──
@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '')
    user = UserModel.find_by_username(username)
    if not user or not check_password_hash(user['password_hash'], password):
        return jsonify({'success': False, 'message': '用户名或密码错误'}), 401
    session['user_id'] = user['id']
    session['username'] = user['username']
    return jsonify({'success': True, 'message': '登录成功', 'user': {'id': user['id'], 'username': user['username'], 'role': user.get('role', 'user')}})

# ── 退出 ──
@auth_bp.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True, 'message': '已退出登录'})

# ── Session 检查 ──
@auth_bp.route('/session', methods=['GET'])
def check_session():
    if session.get('user_id'):
        return jsonify({'authenticated': True, 'user': {'id': session['user_id'], 'username': session.get('username')}})
    return jsonify({'authenticated': False}), 401

# ==================== 人脸接口 ====================

def _decode_frame(data):
    """从请求体中解码 base64 帧为 PIL.Image"""
    if not data or "frame" not in data:
        return None, "未收到图片数据"
    frame_str = data["frame"]
    if "," in frame_str:
        frame_str = frame_str.split(",", 1)[1]
    try:
        img_bytes = base64.b64decode(frame_str)
        return Image.open(io.BytesIO(img_bytes)).convert("RGB"), None
    except Exception as e:
        return None, f"图片解码失败: {str(e)}"

# ── 人脸登录（无需登录）──
@auth_bp.route('/face-login', methods=['POST'])
def face_login():
    data = request.get_json()
    pil_img, err = _decode_frame(data)
    if err:
        return jsonify({"success": False, "message": err}), 400

    try:
        embedding, bbox = _extract_face_embedding(pil_img)
    except Exception as e:
        return jsonify({"success": False, "message": f"人脸检测异常: {str(e)}"}), 500

    if embedding is None:
        return jsonify({"success": False, "message": "未检测到人脸，请正对摄像头并确保光线充足"})

    face_users = UserModel.get_all_face_users()
    if not face_users:
        return jsonify({"success": False, "message": "系统中暂无已录入人脸的用户，请先用密码登录后录入人脸"})

    best_match, best_score = None, 0
    for fu in face_users:
        score = _cosine_similarity(embedding, fu["embedding"])
        if score > best_score:
            best_score = score
            best_match = fu

    if best_match and best_score >= _FACE_SIMILARITY_THRESHOLD:
        session["user_id"] = best_match["id"]
        session["username"] = best_match["username"]
        return jsonify({
            "success": True,
            "message": "人脸登录成功",
            "user": {"id": best_match["id"], "username": best_match["username"]},
            "similarity": round(best_score, 4)
        })

    return jsonify({"success": False, "message": f"人脸不匹配（相似度 {best_score:.2%}，需 ≥ {_FACE_SIMILARITY_THRESHOLD:.0%}）"})

# ── 人脸保存（需要登录）──
@auth_bp.route('/face-save', methods=['POST'])
@login_required_json
def face_save():
    """登录用户上传人脸截帧，提取特征覆盖存入 face_feature"""
    data = request.get_json()
    pil_img, err = _decode_frame(data)
    if err:
        return jsonify({"success": False, "message": err}), 400

    try:
        embedding, bbox = _extract_face_embedding(pil_img)
    except Exception as e:
        return jsonify({"success": False, "message": f"人脸检测异常: {str(e)}"}), 500

    if embedding is None:
        return jsonify({"success": False, "message": "未检测到人脸，请正对摄像头并保持光线充足"})

    UserModel.save_face_feature(session["user_id"], embedding)
    return jsonify({"success": True, "message": "人脸特征已保存（已有特征已覆盖）"})

# ── 人脸状态查询（需要登录）──
@auth_bp.route('/face-status', methods=['GET'])
@login_required_json
def face_status():
    has = UserModel.has_face(session["user_id"])
    return jsonify({"success": True, "has_face": has})
