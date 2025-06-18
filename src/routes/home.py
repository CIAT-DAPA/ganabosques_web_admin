from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from src.forms.login_form import LoginForm
from src.models import User
from extensions import login_manager
from src.decorators import token_required

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

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home_bp.home'))
    
    form = LoginForm()
    if request.method == 'POST':
        username = form.username.data.strip() if form.username.data else ''
        password = form.password.data if form.password.data else ''
        
        # Validación manual en el servidor
        errors = {}
        if not username:
            errors['username'] = 'Username is required'
        elif len(username) < 3:
            errors['username'] = 'Username must be at least 3 characters'
        
        if not password:
            errors['password'] = 'Password is required'
        
        # Si no hay errores de validación, verificar credenciales contra la API
        if not errors:
            user = User.authenticate(username, password)
            if user:
                login_user(user)
                flash('Login successful!', 'success')
                return redirect(url_for('home_bp.home'))
            else:
                flash(('Invalid username and/or password'), 'error')
        else:
            # Agregar errores al formulario para mostrar en el template
            if 'username' in errors:
                form.username.errors = [errors['username']]
            if 'password' in errors:
                form.password.errors = [errors['password']]
    
    return render_template('login.html', form=form)

@bp.route('/logout')
@token_required
def logout():
    # Limpiar la sesión
    session.pop('access_token', None)
    session.pop('user_data', None)
    
    logout_user()
    flash('You have logged out successfully', 'info')
    return redirect(url_for('home_bp.login'))

@bp.route('/home')
@token_required
def home():
    return render_template('home.html')