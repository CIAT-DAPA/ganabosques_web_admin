import os
import sys

import pytest
from flask import Blueprint, Flask

from helpers import FakeObjectsManager, FakeQuerySet, make_document_stub  # noqa: F401


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


@pytest.fixture()
def make_app():
    """Construye una app Flask mínima que registra los blueprints indicados."""

    def _factory(*blueprints, **config):
        app = Flask(__name__)
        app.config.update(
            SECRET_KEY="test-secret",
            TESTING=True,
            WTF_CSRF_ENABLED=False,
            SERVER_NAME="localhost",
        )
        app.config.update(config)

        for blueprint in blueprints:
            app.register_blueprint(blueprint)

        return app

    return _factory


@pytest.fixture()
def capture_render(monkeypatch):
    """Sustituye ``render_template`` en un módulo y captura su contexto.

    Evita depender del HTML real: el test comprueba qué plantilla se eligió y
    qué variables se le pasaron.
    """

    captured = {}

    def _patch(module):
        def fake_render_template(template_name, **context):
            captured["template"] = template_name
            captured["context"] = context
            return f"rendered:{template_name}"

        monkeypatch.setattr(module, "render_template", fake_render_template)
        return captured

    _patch.captured = captured
    return _patch
