from functools import wraps
from flask import session, redirect, url_for, flash
from flask_login import current_user, logout_user

def token_required(f):
    """Decorador que valida autenticación y token válido"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Primero verificar si está autenticado (equivalente a @login_required)
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'info')
            return redirect(url_for('home_bp.login'))
        
        # Luego validar que el token siga siendo válido
        if not current_user.validate_token():
            logout_user()
            session.pop('access_token', None)
            session.pop('user_data', None)
            flash('Session expired. Please login again.', 'warning')
            return redirect(url_for('home_bp.login'))
            
        return f(*args, **kwargs)
    return decorated_function

def login_required_only(f):
    """Decorador solo para verificar login sin validar token (para casos especiales)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'info')
            return redirect(url_for('home_bp.login'))
        return f(*args, **kwargs)
    return decorated_function