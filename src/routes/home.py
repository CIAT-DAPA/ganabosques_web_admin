from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from flask_login import login_user, logout_user, login_required, current_user
from src.models.User import User
from extensions import login_manager
from src.decorators import token_required
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('home_bp', __name__)

@login_manager.user_loader
def load_user(user_id):
    """Carga el usuario desde la sesión"""
    return User.get(user_id)

@bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('home_bp.home'))
    return redirect(url_for('home_bp.login'))

@bp.route('/login')
def login():
    """Mostrar página de login"""
    if current_user.is_authenticated:
        return redirect(url_for('home_bp.home'))
    return render_template('login.html')

@bp.route('/login/keycloak')
def login_keycloak():
    """Redirigir a Keycloak para autenticación"""
    if current_user.is_authenticated:
        return redirect(url_for('home_bp.home'))
    
    try:
        oauth_service = current_app.extensions.get('oauth_service')
        
        if not oauth_service:
            logger.error("OAuth service not found in app extensions")
            flash('El servicio de autenticación no está disponible', 'error')
            return redirect(url_for('home_bp.login'))
        
        redirect_uri = url_for('home_bp.auth_callback', _external=True)
        logger.info(f"Initiating OAuth flow with redirect URI: {redirect_uri}")
        
        return oauth_service.get_authorization_url(redirect_uri)
        
    except Exception as e:
        logger.error(f"Error in login route: {e}")
        flash('Error al iniciar la autenticación con Keycloak', 'error')
        return redirect(url_for('home_bp.login'))

@bp.route('/auth/callback')
def auth_callback():
    """Callback de Keycloak después de autenticación"""
    try:
        # Obtener servicio OAuth
        oauth_service = current_app.extensions.get('oauth_service')
        
        if not oauth_service:
            logger.error("OAuth service not found in app extensions")
            flash('El servicio de autenticación no está disponible', 'error')
            return redirect(url_for('home_bp.login'))
        
        # Intercambiar código por token
        token_data = oauth_service.exchange_code_for_token()
        
        if not token_data:
            logger.error("Failed to exchange code for token")
            flash('Error en la autenticación', 'error')
            return redirect(url_for('home_bp.login'))
        
        # Validar token contra la API de GanaBosques
        access_token = token_data.get('access_token')
        if not access_token:
            logger.error("No access token in token data")
            flash('No se obtuvo token de acceso', 'error')
            return redirect(url_for('home_bp.login'))
        
        validation_result = oauth_service.validate_token_with_api(access_token)
        
        if not validation_result or not validation_result.get('valid'):
            logger.error(f"Token validation failed: {validation_result}")
            flash('Token inválido. No se pudo verificar tu identidad.', 'error')
            return redirect(url_for('home_bp.login'))
        
        # Verificar si el usuario es admin
        payload = validation_result.get('payload', {})
        user_db = payload.get('user_db', {})
        is_admin = user_db.get('admin', False)
        
        if not is_admin:
            logger.warning(f"User {payload.get('preferred_username', 'unknown')} is not admin, access denied")
            flash('No tienes permisos de administrador para acceder a este sistema.', 'warning')
            return redirect(url_for('home_bp.login'))
        
        # Obtener información del usuario desde el payload de la API
        user_info = {
            'sub': payload.get('sub'),
            'preferred_username': payload.get('preferred_username'),
            'email': payload.get('email'),
            'name': payload.get('name'),
            'given_name': payload.get('given_name'),
            'family_name': payload.get('family_name'),
            'email_verified': payload.get('email_verified'),
            'realm_access': payload.get('realm_access', {}),
            'resource_access': payload.get('resource_access', {}),
            'user_db': user_db,
        }
        
        logger.info(f"Admin user validated: {user_info.get('preferred_username')} (admin={is_admin})")
        
        # Autenticar usuario
        user = User.authenticate_oauth(token_data, user_info)
        
        if user:
            login_user(user)
            logger.info(f"User {user.username} logged in successfully")
            flash('¡Inicio de sesión exitoso!', 'success')
            return redirect(url_for('home_bp.home'))
        else:
            logger.error("Failed to authenticate user")
            flash('Error en la autenticación', 'error')
            return redirect(url_for('home_bp.login'))
            
    except Exception as e:
        logger.error(f"Auth callback error: {e}")
        flash('Ocurrió un error durante la autenticación', 'error')
        return redirect(url_for('home_bp.login'))

@bp.route('/logout')
@token_required
def logout():
    """Logout del usuario y redirigir a Keycloak logout"""
    try:
        # Obtener servicio OAuth
        oauth_service = current_app.extensions.get('oauth_service')

        # Obtener id_token de la sesión antes de limpiarla
        id_token = session.get('id_token')
        
        # Limpiar sesión local
        session.clear()
        logout_user()
        
        if oauth_service:
            # Redirigir a logout de Keycloak
            post_logout_redirect = url_for('home_bp.index', _external=True)
            keycloak_logout_url = oauth_service.logout_url(
                redirect_uri=post_logout_redirect,
                id_token=id_token
            )
            return redirect(keycloak_logout_url)
        else:
            flash(('Logged out successfully'), 'info')
            return redirect(url_for('home_bp.index'))
            
    except Exception as e:
        logger.error(f"Logout error: {e}")
        flash(('Logout completed'), 'info')
        return redirect(url_for('home_bp.index'))

@bp.route('/home')
@token_required
def home():
    return render_template('home.html')