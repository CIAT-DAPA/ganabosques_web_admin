from flask import Flask
import os
from dotenv import load_dotenv
from mongoengine import connect

from routes.home import home_bp
from routes.spatial_data_management import spatial_bp
from routes.suppliers_data_management import suppliers_bp

# Cargar variables de entorno
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev_default")

# Configuración de carpetas de subida
ALLOWED_EXTENSIONS = {'shp', 'tif', 'tiff', 'csv', 'xls', 'xlsx'}
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploaded_files')
CSV_FOLDER = os.path.join(BASE_DIR, 'uploaded_codes')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CSV_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['CSV_FOLDER'] = CSV_FOLDER
app.config['ALLOWED_EXTENSIONS'] = ALLOWED_EXTENSIONS

# Registrar Blueprints
app.register_blueprint(home_bp)
app.register_blueprint(spatial_bp)
app.register_blueprint(suppliers_bp)

# Conexión a MongoDB
if __name__ == '__main__':
    connect(
        db=os.getenv("MONGO_DB_NAME", "ganabosques"),
        host=os.getenv("MONGO_URI", "mongodb://localhost:27017")
    )
    app.run(debug=True, host='0.0.0.0')