from flask import Flask
from mongoengine import connect
from dotenv import load_dotenv
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Importar configuraciones y rutas
from config import config
from routes.home import home_bp
from routes.spatial_data_management import spatial_bp
from routes.suppliers_data_management import suppliers_bp
from routes.adm1_routes import adm1_bp 

# Inicializar Flask
load_dotenv()
app = Flask(__name__)
app.secret_key = config['SECRET_KEY']

# Configuración de carpetas de subida de archivos desde config
os.makedirs(config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(config['CSV_FOLDER'], exist_ok=True)

app.config['UPLOAD_FOLDER'] = config['UPLOAD_FOLDER']
app.config['CSV_FOLDER'] = config['CSV_FOLDER']
app.config['ALLOWED_EXTENSIONS'] = config['ALLOWED_EXTENSIONS']

# Registrar rutas
app.register_blueprint(home_bp)
app.register_blueprint(spatial_bp)
app.register_blueprint(suppliers_bp)
app.register_blueprint(adm1_bp)

# Ejecutar aplicación
if __name__ == '__main__':
    connect(
        db=config['MONGO_DB_NAME'],
        host=config['MONGO_URI']
    )
    app.run(host=config['HOST'], port=config['PORT'], debug=config['DEBUG'])
