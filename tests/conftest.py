import os
import sys

import pytest
from flask import Blueprint, Flask


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC_DIR = os.path.join(ROOT_DIR, "src")

for path in (ROOT_DIR, SRC_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)


@pytest.fixture()
def flask_app():
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY="test-secret",
        TESTING=True,
        WTF_CSRF_ENABLED=False,
        SERVER_NAME="localhost",
    )

    home_bp = Blueprint("home_bp", __name__)

    @home_bp.route("/login")
    def login():
        return "login"

    app.register_blueprint(home_bp)
    return app
