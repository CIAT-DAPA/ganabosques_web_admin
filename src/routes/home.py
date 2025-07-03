from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from flask_login import login_user, logout_user, login_required, current_user
from src.forms.login_form import LoginForm
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

    """Redirigir a Keycloak para autenticación"""
    if current_user.is_authenticated:
        return redirect(url_for('home_bp.home'))
    
    try:
        # Obtener servicio OAuth desde la app
        oauth_service = current_app.extensions.get('oauth_service')
        
        if not oauth_service:
            logger.error("OAuth service not found in app extensions")
            flash(('Authentication service not available'), 'error')
            return render_template('login.html', form=None)
        
        # Redirigir a Keycloak
        redirect_uri = url_for('home_bp.auth_callback', _external=True)
        logger.info(f"Initiating OAuth flow with redirect URI: {redirect_uri}")
        
        return oauth_service.get_authorization_url(redirect_uri)
        
    except Exception as e:
        logger.error(f"Error in login route: {e}")
        flash(('Error initiating authentication'), 'error')
        return render_template('login.html', form=None)

@bp.route('/auth/callback')
def auth_callback():
    """Callback de Keycloak después de autenticación"""
    try:
        # Obtener servicio OAuth
        oauth_service = current_app.extensions.get('oauth_service')
        
        if not oauth_service:
            logger.error("OAuth service not found in app extensions")
            flash(('Authentication service not available'), 'error')
            return redirect(url_for('home_bp.login'))
        
        # Intercambiar código por token
        token_data = oauth_service.exchange_code_for_token()
        
        if not token_data:
            logger.error("Failed to exchange code for token")
            flash(('Authentication failed'), 'error')
            return redirect(url_for('home_bp.login'))
        
        # Obtener información del usuario
        user_info = oauth_service.get_user_info(token_data)
        
        if not user_info:
            logger.error("Failed to get user information")
            flash(('Failed to get user information'), 'error')
            return redirect(url_for('home_bp.login'))
        
        # Enriquecer información del usuario con roles desde la API
        # user_info_enriched = enrich_user_with_roles(token_data, user_info)
        
        # Autenticar usuario con información enriquecida
        user = User.authenticate_oauth(token_data, user_info)
        
        if user:
            login_user(user)
            logger.info(f"User {user.username} logged in successfully with roles: {user.roles}")
            flash(('Login successful!'), 'success')
            return redirect(url_for('home_bp.home'))
        else:
            logger.error("Failed to authenticate user")
            flash(('Authentication failed'), 'error')
            return redirect(url_for('home_bp.login'))
            
    except Exception as e:
        logger.error(f"Auth callback error: {e}")
        flash(('Authentication error occurred'), 'error')
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