from flask import Flask
from mongoengine import connect
from dotenv import load_dotenv
import os
import sys
import logging
from services.oauth_service import OAuthService
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Importar configuraciones y rutas
from config import config
from extensions import login_manager 
from routes.home import bp as home_bp
from routes.spatial_data_management import spatial_bp
from routes.suppliers_data_management import suppliers_bp
from routes.adm1_routes import adm1_bp 
from routes.adm2_routes import adm2_bp
from routes.adm3_routes import adm3_bp
from routes.data_management import datamanagement_bp
from routes.farm_routes import farm_bp
from routes.enterprise_routes import enterprise_bp
from routes.configuration_routes import configuration_bp
from routes.adm_import import adm_bp

oauth_service = OAuthService()

# Inicializar Flask
load_dotenv()
app = Flask(__name__)
app.secret_key = config['SECRET_KEY']

logging.basicConfig(level=logging.INFO)

# Configuración de carpetas de subida de archivos desde config
os.makedirs(config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(config['CSV_FOLDER'], exist_ok=True)

app.config['UPLOAD_FOLDER'] = config['UPLOAD_FOLDER']
app.config['CSV_FOLDER'] = config['CSV_FOLDER']
app.config['ALLOWED_EXTENSIONS'] = config['ALLOWED_EXTENSIONS']
app.config['KEYCLOAK_SERVER_URL'] = os.environ.get('KEYCLOAK_SERVER_URL')
app.config['KEYCLOAK_REALM'] = os.environ.get('KEYCLOAK_REALM')
app.config['KEYCLOAK_CLIENT_ID'] = os.environ.get('KEYCLOAK_CLIENT_ID')
app.config['KEYCLOAK_CLIENT_SECRET'] = os.environ.get('KEYCLOAK_CLIENT_SECRET')


# Inicializar el gestor de login
login_manager.init_app(app)

oauth_service.init_app(app)

app.extensions['oauth_service'] = oauth_service

# Registrar rutas
app.register_blueprint(home_bp)
app.register_blueprint(spatial_bp)
app.register_blueprint(suppliers_bp)
app.register_blueprint(adm1_bp)
app.register_blueprint(adm2_bp)
app.register_blueprint(adm3_bp)
app.register_blueprint(datamanagement_bp)
app.register_blueprint(farm_bp)
app.register_blueprint(enterprise_bp)
app.register_blueprint(configuration_bp)
app.register_blueprint(adm_bp)

# Ejecutar aplicación
if __name__ == '__main__':
    connect(
        db=config['MONGO_DB_NAME'],
        host=config['MONGO_URI']
    )
    app.run(host=config['HOST'], port=config['PORT'], debug=config['DEBUG'])
