from flask_login import UserMixin
from flask import session
import logging

logger = logging.getLogger(__name__)

class User(UserMixin):
    def __init__(self, user_data):
        # Log completo de los datos para debug
        logger.info(f"Raw user data from Keycloak: {user_data}")
        
        # Keycloak puede devolver diferentes campos según la configuración
        self.id = (user_data.get('sub') or 
                  user_data.get('id') or 
                  user_data.get('preferred_username') or 
                  user_data.get('username'))
        self.username = (user_data.get('preferred_username') or 
                         user_data.get('username') or 
                         user_data.get('email', '').split('@')[0])
        self.email = user_data.get('email', '')
        self.first_name = user_data.get('given_name', '')
        self.last_name = user_data.get('family_name', '')
        self.name = user_data.get('name', f"{self.first_name} {self.last_name}".strip())
        
        # Debug detallado de extracción de roles
        self.roles = self._extract_roles(user_data)
        
        logger.info(f"Created user: {self.username} (ID: {self.id}) with roles: {self.roles}")
        
    def _extract_roles(self, user_data):
        """Extrae roles de diferentes ubicaciones en los datos de Keycloak"""
        logger.info("Starting role extraction...")
        
        # Debug: mostrar todas las claves disponibles
        logger.info(f"Available keys in user_data: {list(user_data.keys())}")
        
        roles = []
        
        # Intentar obtener roles de diferentes ubicaciones
        possible_sources = [
            ('roles', user_data.get('roles', [])),
            ('realm_access.roles', user_data.get('realm_access', {}).get('roles', [])),
            ('resource_access', self._extract_from_resource_access(user_data)),
            ('groups', user_data.get('groups', [])),
            ('client_roles', self._extract_from_client_roles(user_data)),
            ('role_name', [user_data.get('role_name')] if user_data.get('role_name') else []),
        ]
        
        for source_name, role_source in possible_sources:
            logger.info(f"Checking {source_name}: {role_source}")
            if role_source:
                if isinstance(role_source, list):
                    for role in role_source:
                        if role and role not in roles:
                            roles.append(role)
                    logger.info(f"Found roles in {source_name}: {role_source}")
        
        # Filtrar roles del sistema de Keycloak que no nos interesan
        system_roles = {
            'offline_access', 
            'uma_authorization', 
            'default-roles-aclimate',
            'account-manage-account',
            'account-view-profile',
            'web-origins'
        }
        
        filtered_roles = [role for role in roles if role not in system_roles]
        unique_roles = list(set(filtered_roles))  # Eliminar duplicados
        
        logger.info(f"Final filtered roles: {unique_roles}")
        return unique_roles
    
    def _extract_from_resource_access(self, user_data):
        """Extrae roles específicos de resource_access"""
        resource_access = user_data.get('resource_access', {})
        logger.info(f"Resource access data: {resource_access}")
        
        roles = []
        
        # Buscar en diferentes recursos/clientes
        possible_clients = ['account', 'realm-management', 'aclimate_admin', 'admin-cli']
        
        for client in possible_clients:
            client_data = resource_access.get(client, {})
            client_roles = client_data.get('roles', [])
            if client_roles:
                logger.info(f"Found roles in {client}: {client_roles}")
                roles.extend(client_roles)
        
        return roles
    
    def _extract_from_client_roles(self, user_data):
        """Extrae roles de la estructura client_roles de la API"""
        client_roles = user_data.get('client_roles', [])
        logger.info(f"Client roles data: {client_roles}")
        
        roles = []
        
        if isinstance(client_roles, list):
            for role_data in client_roles:
                if isinstance(role_data, dict):
                    role_name = role_data.get('name')
                    if role_name:
                        roles.append(role_name)
                        logger.info(f"Found role from client_roles: {role_name}")
                elif isinstance(role_data, str):
                    roles.append(role_data)
                    logger.info(f"Found role from client_roles: {role_data}")
        
        return roles
        
    def get_id(self):
        return str(self.id)
    
    # def has_module_access(self, module):
    #     """Verifica si el usuario tiene acceso a un módulo"""
    #     from app.config.permissions import RolePermissionMapper
    #     return RolePermissionMapper.user_has_module_access(self.roles, module)
    
    # def get_accessible_modules(self):
    #     """Obtiene lista de módulos accesibles para el usuario"""
    #     from app.config.permissions import RolePermissionMapper
    #     return list(RolePermissionMapper.get_user_modules(self.roles))
    
    def is_super_admin(self):
        """Verifica si el usuario es super administrador"""
        return 'adminsuper' in self.roles
    
    def is_admin(self):
        """Verifica si el usuario es administrador (cualquier tipo)"""
        admin_roles = {'adminsuper', 'admin'}
        return any(role in admin_roles for role in self.roles)
    
    @staticmethod
    def get(user_id):
        """Cargar usuario desde la sesión"""
        user_data = session.get('user_data')
        if user_data:
            user = User(user_data)
            if str(user.id) == str(user_id):
                return user
        return None
    
    @staticmethod
    def authenticate_oauth(token_data, user_info):
        """Autenticar usuario con datos OAuth"""
        if token_data and user_info:
            # Log detallado de tokens
            logger.info(f"Token data keys: {list(token_data.keys()) if token_data else 'None'}")
            logger.info(f"User info keys: {list(user_info.keys()) if user_info else 'None'}")
            
            # Guardar datos en sesión incluyendo el id_token
            session['access_token'] = token_data.get('access_token')
            session['refresh_token'] = token_data.get('refresh_token')
            session['id_token'] = token_data.get('id_token')
            session['user_data'] = user_info
            
            logger.info(f"Authenticated user via OAuth: {user_info.get('preferred_username', 'unknown')}")
            logger.debug(f"Stored tokens: access_token={bool(token_data.get('access_token'))}, id_token={bool(token_data.get('id_token'))}")
            
            # Crear usuario con información enriquecida
            user = User(user_info)
            logger.info(f"User created with roles: {user.roles}")
            
            return user
        return None
    
    def validate_token(self):
        """Validar que el token del usuario siga siendo válido"""
        access_token = session.get('access_token')
        if not access_token:
            logger.warning("No access token found in session")
            return False
        
        from src.services.oauth_service import OAuthService
        oauth_service = OAuthService()
        is_valid = oauth_service.validate_token(access_token)
        
        if not is_valid:
            logger.warning(f"Token validation failed for user: {self.username}")
        
        return is_valid

    # Métodos de compatibilidad para el modelo anterior
    @property
    def role(self):
        """Compatibilidad: devuelve el primer rol o 'guest'"""
        return self.roles[0] if self.roles else 'guest'
    
    def check_password(self, password):
        """Compatibilidad: OAuth no usa contraseñas locales"""
        return False
    
    # def refresh_roles(self):
    #     """Actualiza los roles del usuario desde la API"""
    #     try:
    #         from src.services.user_service import UserService
            
    #         # Solo refrescar si hay un token válido
    #         if not self.validate_token():
    #             logger.warning("Cannot refresh roles: invalid token")
    #             return False
            
    #         logger.info(f"Refreshing roles for user: {self.id}")
            
    #         user_service = UserService()
    #         complete_user_data = user_service.get_by_id(self.id)
            
    #         logger.info(f"Retrieved complete user data for refresh: {complete_user_data}")
            
    #         # Extraer roles usando la misma lógica que en el enriquecimiento
    #         api_roles = []
            
    #         # 1. Extraer del campo 'role_name' directo
    #         role_name = complete_user_data.get('role_name')
    #         if role_name:
    #             api_roles.append(role_name)
    #             logger.info(f"Found role from 'role_name': {role_name}")
            
    #         # 2. Extraer de 'client_roles' array
    #         client_roles = complete_user_data.get('client_roles', [])
    #         if client_roles:
    #             logger.info(f"Processing client_roles for refresh: {client_roles}")
    #             for role in client_roles:
    #                 if isinstance(role, dict):
    #                     role_name = role.get('name')
    #                     if role_name and role_name not in api_roles:
    #                         api_roles.append(role_name)
    #                         logger.info(f"Found role from 'client_roles': {role_name}")
    #                 elif isinstance(role, str):
    #                     if role not in api_roles:
    #                         api_roles.append(role)
    #                         logger.info(f"Found role from 'client_roles' (string): {role}")
            
    #         # 3. Extraer de cualquier otro campo 'roles' si existe
    #         roles_array = complete_user_data.get('roles', [])
    #         if roles_array:
    #             logger.info(f"Processing roles array for refresh: {roles_array}")
    #             for role in roles_array:
    #                 if isinstance(role, str) and role not in api_roles:
    #                     api_roles.append(role)
    #                     logger.info(f"Found role from 'roles' array: {role}")
            
    #         logger.info(f"Final extracted roles for refresh: {api_roles}")
            
    #         # Actualizar roles en el objeto usuario
    #         self.roles = api_roles
            
    #         # Actualizar roles en la sesión
    #         user_data = session.get('user_data', {})
    #         user_data['roles'] = api_roles
    #         user_data['client_roles'] = client_roles
    #         user_data['role_name'] = complete_user_data.get('role_name')
    #         user_data['role_id'] = complete_user_data.get('role_id')
            
    #         if 'realm_access' not in user_data:
    #             user_data['realm_access'] = {}
    #         user_data['realm_access']['roles'] = api_roles
            
    #         session['user_data'] = user_data
            
    #         logger.info(f"Successfully refreshed roles for user {self.username}: {api_roles}")
    #         return True
            
        # except Exception as e:
        #     logger.error(f"Error refreshing roles for user {self.username}: {e}")
        #     return False