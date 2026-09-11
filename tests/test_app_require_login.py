"""Pruebas del guardián global de sesión declarado en ``src/app.py``.

``require_login`` corre antes de cada petición y es la única barrera que
protege a todas las vistas del panel, así que se comprueba tanto la lista de
endpoints exentos como el rechazo del resto.
"""

from types import SimpleNamespace

import pytest

import src.app as app_module


@pytest.fixture()
def app_real(monkeypatch):
    aplicacion = app_module.app
    # La clave real sale del entorno; la prueba no debe depender del .env.
    monkeypatch.setattr(aplicacion, "secret_key", "test-secret")
    monkeypatch.setitem(aplicacion.config, "TESTING", True)
    monkeypatch.setitem(aplicacion.config, "SERVER_NAME", "localhost")
    return aplicacion


def _sin_sesion(monkeypatch):
    monkeypatch.setattr(app_module, "current_user", SimpleNamespace(is_authenticated=False))


def _con_sesion(monkeypatch):
    monkeypatch.setattr(app_module, "current_user", SimpleNamespace(is_authenticated=True))


@pytest.mark.parametrize(
    "ruta",
    ["/login", "/login/keycloak", "/auth/callback"],
)
def test_require_login_deja_pasar_los_endpoints_de_autenticacion(app_real, monkeypatch, ruta):
    _sin_sesion(monkeypatch)

    with app_real.test_request_context(ruta):
        assert app_module.require_login() is None


def test_require_login_deja_pasar_los_archivos_estaticos(app_real, monkeypatch):
    _sin_sesion(monkeypatch)

    with app_real.test_request_context("/static/css/estilos.css"):
        assert app_module.require_login() is None


def test_require_login_ignora_rutas_sin_endpoint(app_real, monkeypatch):
    _sin_sesion(monkeypatch)

    with app_real.test_request_context("/ruta-que-no-existe"):
        assert app_module.require_login() is None


@pytest.mark.parametrize(
    "ruta",
    ["/home", "/adm1", "/farm", "/enterprise", "/users", "/roles/", "/importar", "/logout"],
)
def test_require_login_redirige_al_login_sin_sesion(app_real, monkeypatch, ruta):
    _sin_sesion(monkeypatch)

    with app_real.test_request_context(ruta):
        respuesta = app_module.require_login()

        assert respuesta is not None
        assert respuesta.status_code == 302
        assert respuesta.headers["Location"].endswith("/login")


def test_require_login_deja_pasar_con_sesion_activa(app_real, monkeypatch):
    _con_sesion(monkeypatch)

    with app_real.test_request_context("/home"):
        assert app_module.require_login() is None


def test_require_login_avisa_al_usuario(app_real, monkeypatch):
    _sin_sesion(monkeypatch)

    with app_real.test_request_context("/adm1"):
        from flask import get_flashed_messages

        app_module.require_login()
        mensajes = get_flashed_messages()

    assert "Debes iniciar sesión para acceder al panel." in mensajes


# ---------------------------------------------------------------------------
# Registro de la aplicación
# ---------------------------------------------------------------------------

def test_la_app_registra_todos_los_blueprints(app_real):
    esperados = {
        "home_bp",
        "spatial",
        "suppliers",
        "adm1",
        "adm2",
        "adm3",
        "datamanagement",
        "farm",
        "enterprise",
        "configuration",
        "admin_import",
        "user",
        "role",
    }

    assert esperados.issubset(set(app_real.blueprints))


def test_la_app_expone_el_servicio_oauth(app_real):
    assert "oauth_service" in app_real.extensions
    assert hasattr(app_real.extensions["oauth_service"], "get_authorization_url")


def test_la_app_tiene_el_login_manager_inicializado(app_real):
    assert app_real.login_manager is not None


def test_las_carpetas_de_carga_existen(app_real):
    import os

    assert os.path.isdir(app_real.config["UPLOAD_FOLDER"])
    assert os.path.isdir(app_real.config["CSV_FOLDER"])
