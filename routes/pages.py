from flask import Blueprint, render_template, session, redirect, url_for
pages_bp = Blueprint('pages', __name__)

def _auth(): return session.get('user_id') is not None

@pages_bp.route('/')
def index():
    if not _auth(): return redirect(url_for('pages.login_page'))
    return redirect(url_for('pages.dashboard'))

@pages_bp.route('/login')
def login_page():
    if _auth(): return redirect(url_for('pages.dashboard'))
    return render_template('login.html')

@pages_bp.route('/register')
def register_page():
    if _auth(): return redirect(url_for('pages.dashboard'))
    return render_template('register.html')

@pages_bp.route('/dashboard')
def dashboard():
    if not _auth(): return redirect(url_for('pages.login_page'))
    return render_template('dashboard.html')

@pages_bp.route('/devices')
def devices():
    if not _auth(): return redirect(url_for('pages.login_page'))
    return render_template('devices.html')

@pages_bp.route('/monitor')
def monitor():
    if not _auth(): return redirect(url_for('pages.login_page'))
    return render_template('monitor.html')

@pages_bp.route('/history')
def history():
    if not _auth(): return redirect(url_for('pages.login_page'))
    return render_template('history.html')

@pages_bp.route('/alerts')
def alerts():
    if not _auth(): return redirect(url_for('pages.login_page'))
    return render_template('alerts.html')

@pages_bp.route('/prediction')
def prediction():
    if not _auth(): return redirect(url_for('pages.login_page'))
    return render_template('prediction.html')

@pages_bp.route('/face-setup')
def face_setup():
    if not _auth(): return redirect(url_for('pages.login_page'))
    return render_template('face_setup.html')

@pages_bp.route('/control')
def control():
    if not _auth(): return redirect(url_for('pages.login_page'))
    return render_template('control.html')

@pages_bp.route('/buzzer')
def buzzer():
    if not _auth(): return redirect(url_for('pages.login_page'))
    return render_template('buzzer.html')

@pages_bp.route('/admin/users')
def admin_users():
    if not _auth(): return redirect(url_for('pages.login_page'))
    return render_template('admin_users.html')
