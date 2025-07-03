import os

config = {}

# Detecta si estamos en modo desarrollo o producción
if os.getenv('DEBUG', 'true').lower() == 'true':
    config['DEBUG'] = True
    config['PORT'] = 5000
    config['HOST'] = 'localhost'
    config['SECRET_KEY'] = 'dev_secret_key'

    # Parámetros de desarrollo
    config['MONGO_URI'] = 'mongodb://localhost:27017'
    config['MONGO_DB_NAME'] = 'ganabosques'
    config['GEOSERVER_USER'] = 'admin'
    config['GEOSERVER_PWD'] = 'geoserver'
    config['GEOSERVER_URL'] = 'http://localhost:8600/geoserver/rest/'
    config['API_BASE_URL'] = 'http://127.0.0.1:8000'

    # Keycloak desarrollo
    config['KEYCLOAK_SERVER_URL'] = 'http://localhost:8080'
    config['KEYCLOAK_REALM'] = 'GanaBosques'
    config['KEYCLOAK_CLIENT_ID'] = 'GanaBosques'
    config['KEYCLOAK_CLIENT_SECRET'] = 'your-client-secret'

else:
    # Parámetros de producción
    config['DEBUG'] = False
    config['PORT'] = int(os.getenv('PORT', 5000))
    config['HOST'] = os.getenv('HOST', '0.0.0.0')
    config['SECRET_KEY'] = os.getenv('SECRET_KEY')

    config['MONGO_URI'] = os.getenv('MONGO_URI')
    config['MONGO_DB_NAME'] = os.getenv('MONGO_DB_NAME')
    config['GEOSERVER_USER'] = os.getenv('GEOSERVER_USER')
    config['GEOSERVER_PWD'] = os.getenv('GEOSERVER_PWD')
    config['GEOSERVER_URL'] = os.getenv('GEOSERVER_URL')
    config['API_BASE_URL'] = os.getenv('API_BASE_URL')

    # Keycloak producción
    config['KEYCLOAK_SERVER_URL'] = os.getenv('KEYCLOAK_SERVER_URL')
    config['KEYCLOAK_REALM'] = os.getenv('KEYCLOAK_REALM')
    config['KEYCLOAK_CLIENT_ID'] = os.getenv('KEYCLOAK_CLIENT_ID')
    config['KEYCLOAK_CLIENT_SECRET'] = os.getenv('KEYCLOAK_CLIENT_SECRET')

# URLs derivadas de Keycloak
config['KEYCLOAK_AUTHORIZATION_URL'] = f"{config['KEYCLOAK_SERVER_URL']}/realms/{config['KEYCLOAK_REALM']}/protocol/openid-connect/auth"
config['KEYCLOAK_TOKEN_URL'] = f"{config['KEYCLOAK_SERVER_URL']}/realms/{config['KEYCLOAK_REALM']}/protocol/openid-connect/token"
config['KEYCLOAK_USERINFO_URL'] = f"{config['KEYCLOAK_SERVER_URL']}/realms/{config['KEYCLOAK_REALM']}/protocol/openid-connect/userinfo"
config['KEYCLOAK_LOGOUT_URL'] = f"{config['KEYCLOAK_SERVER_URL']}/realms/{config['KEYCLOAK_REALM']}/protocol/openid-connect/logout"

# Rutas de carpetas usadas en la app
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'uploaded_files')
config['CSV_FOLDER'] = os.path.join(BASE_DIR, 'uploaded_codes')

# Extensiones permitidas para archivos cargados
config['ALLOWED_EXTENSIONS'] = {'shp', 'tif', 'tiff', 'csv', 'xls', 'xlsx', 'zip'}

# Crear carpetas necesarias si no existen
for folder in [config['UPLOAD_FOLDER'], config['CSV_FOLDER']]:
    os.makedirs(folder, exist_ok=True)
