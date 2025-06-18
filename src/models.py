from flask_login import UserMixin
import requests
from flask import current_app, session
from config import config

class User(UserMixin):
    def __init__(self, id, username, email=None, token=None, user_data=None):
        self.id = id
        self.username = username
        self.email = email
        self.token = token
        self.user_data = user_data or {}
    
    @staticmethod
    def authenticate(username, password):
        """Autentica al usuario contra la API de Keycloak"""
        try:
            response = requests.post(
                f"{config['API_BASE_URL']}/auth/login",
                json={
                    'username': username,
                    'password': password
                },
                timeout=10
            )
            print(f"{config['API_BASE_URL']}/auth/login") 
            print(f"Response status code: {response.status_code}")
            print(f"Response content: {response.content}")
            if response.status_code == 200:
                data = response.json()
                token = data.get('access_token') or data.get('token')
                user_info = data.get('user', {})
                
                if token:
                    # Crear usuario con el token
                    user = User(
                        id=user_info.get('id', username),
                        username=username,
                        email=user_info.get('email'),
                        token=token,
                        user_data=user_info
                    )
                    
                    # Guardar token en sesión para uso posterior
                    session['access_token'] = token
                    session['user_data'] = user_info
                    
                    return user
            
            return None
            
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"Error connecting to auth API: {e}")
            return None
        except Exception as e:
            current_app.logger.error(f"Authentication error: {e}")
            return None

    @staticmethod
    def get(user_id):
        """Recupera usuario desde la sesión"""
        if 'access_token' in session and 'user_data' in session:
            user_data = session['user_data']
            return User(
                id=user_data.get('id', user_id),
                username=user_data.get('username', user_id),
                email=user_data.get('email'),
                token=session['access_token'],
                user_data=user_data
            )
        return None
    
    def validate_token(self):
        """Valida que el token siga siendo válido"""
        try:
            if not self.token:
                return False
            
            response = requests.get(
                f"{config['API_BASE_URL']}/auth/token/validate",
                headers={'Authorization': f'Bearer {self.token}'},
                timeout=10
            )
            
            return response.status_code == 200
            
        except requests.exceptions.RequestException:
            return False
    
    @property
    def role(self):
        """Obtiene el rol del usuario desde user_data"""
        return self.user_data.get('role', 'user')
    
    def get_auth_headers(self):
        """Retorna headers de autenticación para peticiones a la API"""
        if self.token:
            return {'Authorization': f'Bearer {self.token}'}
        return {}