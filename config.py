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
    config['API_BASE_URL'] = 'http://localhost:5000/api'

else:
    # Parámetros desde variables de entorno para producción
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

# Rutas de carpetas usadas en la app
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'uploaded_files')
config['CSV_FOLDER'] = os.path.join(BASE_DIR, 'uploaded_codes')

# Extensiones permitidas para archivos cargados
config['ALLOWED_EXTENSIONS'] = {'shp', 'tif', 'tiff', 'csv', 'xls', 'xlsx', 'zip'}

# Crear carpetas necesarias si no existen
for folder in [config['UPLOAD_FOLDER'], config['CSV_FOLDER']]:
    os.makedirs(folder, exist_ok=True)
