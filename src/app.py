from dotenv import load_dotenv
load_dotenv()

import logging
import os
import sys

from flask import Flask, request, redirect, url_for, flash
from flask_login import current_user
from mongoengine import connect
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import config
from extensions import login_manager
from services.oauth_service import OAuthService

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
from routes.user_routes import user_bp
from routes.role_routes import role_bp

logging.basicConfig(level=logging.INFO)

oauth_service = OAuthService()

app = Flask(__name__)
app.secret_key = config["SECRET_KEY"]

# Carpetas de carga
os.makedirs(config["UPLOAD_FOLDER"], exist_ok=True)
os.makedirs(config["CSV_FOLDER"], exist_ok=True)

app.config.update(config)

# Inicializar extensiones
login_manager.init_app(app)
oauth_service.init_app(app)

app.extensions["oauth_service"] = oauth_service

# Registrar Blueprints
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
app.register_blueprint(user_bp)
app.register_blueprint(role_bp)

@app.before_request
def require_login():
    """Protege todas las rutas de la aplicación verificando si hay sesión activa."""

    allowed_endpoints = {
        "home_bp.login",
        "home_bp.login_keycloak",
        "home_bp.auth_callback",
        "static",
    }

    if not request.endpoint or request.endpoint in allowed_endpoints:
        return

    if not current_user.is_authenticated:
        flash("Debes iniciar sesión para acceder al panel.", "warning")
        return redirect(url_for("home_bp.login"))


# Conexión Mongo
connect(
    db=config["MONGO_DB_NAME"],
    host=config["MONGO_URI"],
)


if __name__ == "__main__":
    app.run(
        host=config["HOST"],
        port=config["PORT"],
        debug=config["DEBUG"],
    )