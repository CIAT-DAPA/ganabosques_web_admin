"""Pruebas del flujo de autenticación: login, callback de Keycloak y logout.

El callback es el único punto donde se decide si una persona entra al panel,
por lo que se cubren tanto el camino feliz como cada motivo de rechazo.
"""

from types import SimpleNamespace

import pytest
from flask import Flask

import src.decorators.auth as auth_module
import src.routes.home as home_module
from src.extensions import login_manager


class _ServicioOAuthFalso:
    def __init__(
        self,
        token=None,
        validacion=None,
        url_autorizacion="https://kc.example.com/auth",
        logout="https://kc.example.com/logout",
    ):
        self.token = token
        self.validacion = validacion
        self.url_autorizacion = url_autorizacion
        self.logout = logout
        self.redirect_uri_recibido = None
        self.logout_kwargs = None

    def get_authorization_url(self, redirect_uri):
        from flask import redirect

        self.redirect_uri_recibido = redirect_uri
        return redirect(self.url_autorizacion)

    def exchange_code_for_token(self):
        return self.token

    def validate_token_with_api(self, access_token):
        return self.validacion

    def logout_url(self, redirect_uri=None, id_token=None):
        self.logout_kwargs = {"redirect_uri": redirect_uri, "id_token": id_token}
        return self.logout


def _payload_valido(admin=True, username="ana"):
    return {
        "valid": True,
        "payload": {
            "sub": "kc-1",
            "preferred_username": username,
            "email": f"{username}@example.com",
            "name": "Ana Ruiz",
            "given_name": "Ana",
            "family_name": "Ruiz",
            "email_verified": True,
            "realm_access": {"roles": ["admin"]},
            "resource_access": {},
            "user_db": {"admin": admin},
        },
    }


@pytest.fixture()
def app_home(monkeypatch):
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY="test-secret",
        TESTING=True,
        WTF_CSRF_ENABLED=False,
        SERVER_NAME="localhost",
    )
    login_manager.init_app(app)
    app.register_blueprint(home_module.bp)
    monkeypatch.setattr(home_module, "render_template", lambda nombre, **ctx: f"rendered:{nombre}")
    return app


def _usuario_anonimo(monkeypatch):
    anonimo = SimpleNamespace(is_authenticated=False)
    monkeypatch.setattr(home_module, "current_user", anonimo)
    monkeypatch.setattr(auth_module, "current_user", anonimo)


def _usuario_autenticado(monkeypatch, username="ana"):
    usuario = SimpleNamespace(is_authenticated=True, username=username)
    monkeypatch.setattr(home_module, "current_user", usuario)
    monkeypatch.setattr(auth_module, "current_user", usuario)
    return usuario


def _mensajes_flash(cliente):
    with cliente.session_transaction() as sesion:
        return [mensaje for _, mensaje in sesion.get("_flashes", [])]


# ---------------------------------------------------------------------------
# index y login
# ---------------------------------------------------------------------------

def test_index_redirige_a_login_si_no_hay_sesion(app_home, monkeypatch):
    _usuario_anonimo(monkeypatch)

    respuesta = app_home.test_client().get("/")

    assert respuesta.status_code == 302
    assert respuesta.headers["Location"].endswith("/login")


def test_index_redirige_a_home_si_hay_sesion(app_home, monkeypatch):
    _usuario_autenticado(monkeypatch)

    respuesta = app_home.test_client().get("/")

    assert respuesta.status_code == 302
    assert respuesta.headers["Location"].endswith("/home")


def test_login_muestra_la_pagina(app_home, monkeypatch):
    _usuario_anonimo(monkeypatch)

    respuesta = app_home.test_client().get("/login")

    assert respuesta.status_code == 200
    assert respuesta.get_data(as_text=True) == "rendered:login.html"


def test_login_redirige_si_ya_esta_autenticado(app_home, monkeypatch):
    _usuario_autenticado(monkeypatch)

    respuesta = app_home.test_client().get("/login")

    assert respuesta.status_code == 302
    assert respuesta.headers["Location"].endswith("/home")


# ---------------------------------------------------------------------------
# login/keycloak
# ---------------------------------------------------------------------------

def test_login_keycloak_redirige_al_proveedor(app_home, monkeypatch):
    _usuario_anonimo(monkeypatch)
    servicio = _ServicioOAuthFalso()
    app_home.extensions["oauth_service"] = servicio

    respuesta = app_home.test_client().get("/login/keycloak")

    assert respuesta.status_code == 302
    assert respuesta.headers["Location"] == "https://kc.example.com/auth"
    assert servicio.redirect_uri_recibido.endswith("/auth/callback")


def test_login_keycloak_avisa_si_no_hay_servicio_oauth(app_home, monkeypatch):
    _usuario_anonimo(monkeypatch)
    app_home.extensions.pop("oauth_service", None)

    with app_home.test_client() as cliente:
        respuesta = cliente.get("/login/keycloak")
        mensajes = _mensajes_flash(cliente)

    assert respuesta.status_code == 302
    assert respuesta.headers["Location"].endswith("/login")
    assert "El servicio de autenticación no está disponible" in mensajes


def test_login_keycloak_captura_errores_del_proveedor(app_home, monkeypatch):
    _usuario_anonimo(monkeypatch)

    class ServicioQueFalla:
        def get_authorization_url(self, redirect_uri):
            raise RuntimeError("Keycloak caído")

    app_home.extensions["oauth_service"] = ServicioQueFalla()

    with app_home.test_client() as cliente:
        respuesta = cliente.get("/login/keycloak")
        mensajes = _mensajes_flash(cliente)

    assert respuesta.status_code == 302
    assert "Error al iniciar la autenticación con Keycloak" in mensajes


# ---------------------------------------------------------------------------
# auth/callback
# ---------------------------------------------------------------------------

def test_callback_sin_servicio_oauth(app_home, monkeypatch):
    _usuario_anonimo(monkeypatch)
    app_home.extensions.pop("oauth_service", None)

    with app_home.test_client() as cliente:
        respuesta = cliente.get("/auth/callback")
        mensajes = _mensajes_flash(cliente)

    assert respuesta.status_code == 302
    assert "El servicio de autenticación no está disponible" in mensajes


def test_callback_sin_token_rechaza(app_home, monkeypatch):
    _usuario_anonimo(monkeypatch)
    app_home.extensions["oauth_service"] = _ServicioOAuthFalso(token=None)

    with app_home.test_client() as cliente:
        respuesta = cliente.get("/auth/callback")
        mensajes = _mensajes_flash(cliente)

    assert respuesta.status_code == 302
    assert "Error en la autenticación" in mensajes


def test_callback_sin_access_token_rechaza(app_home, monkeypatch):
    _usuario_anonimo(monkeypatch)
    app_home.extensions["oauth_service"] = _ServicioOAuthFalso(token={"id_token": "x"})

    with app_home.test_client() as cliente:
        respuesta = cliente.get("/auth/callback")
        mensajes = _mensajes_flash(cliente)

    assert respuesta.status_code == 302
    assert "No se obtuvo token de acceso" in mensajes


def test_callback_rechaza_token_no_validado_por_la_api(app_home, monkeypatch):
    _usuario_anonimo(monkeypatch)
    app_home.extensions["oauth_service"] = _ServicioOAuthFalso(
        token={"access_token": "abc"}, validacion=None
    )

    with app_home.test_client() as cliente:
        respuesta = cliente.get("/auth/callback")
        mensajes = _mensajes_flash(cliente)

    assert respuesta.status_code == 302
    assert any("Token inválido" in mensaje for mensaje in mensajes)


def test_callback_rechaza_validacion_con_valid_false(app_home, monkeypatch):
    _usuario_anonimo(monkeypatch)
    app_home.extensions["oauth_service"] = _ServicioOAuthFalso(
        token={"access_token": "abc"}, validacion={"valid": False}
    )

    with app_home.test_client() as cliente:
        respuesta = cliente.get("/auth/callback")
        mensajes = _mensajes_flash(cliente)

    assert respuesta.status_code == 302
    assert any("Token inválido" in mensaje for mensaje in mensajes)


def test_callback_rechaza_usuario_sin_permisos_de_admin(app_home, monkeypatch):
    """Control de acceso principal: solo las cuentas marcadas como admin entran."""
    _usuario_anonimo(monkeypatch)
    app_home.extensions["oauth_service"] = _ServicioOAuthFalso(
        token={"access_token": "abc"}, validacion=_payload_valido(admin=False)
    )

    with app_home.test_client() as cliente:
        respuesta = cliente.get("/auth/callback")
        mensajes = _mensajes_flash(cliente)

    assert respuesta.status_code == 302
    assert respuesta.headers["Location"].endswith("/login")
    assert any("No tienes permisos de administrador" in mensaje for mensaje in mensajes)


def test_callback_rechaza_si_falta_la_clave_user_db(app_home, monkeypatch):
    _usuario_anonimo(monkeypatch)
    validacion = _payload_valido()
    validacion["payload"].pop("user_db")
    app_home.extensions["oauth_service"] = _ServicioOAuthFalso(
        token={"access_token": "abc"}, validacion=validacion
    )

    with app_home.test_client() as cliente:
        respuesta = cliente.get("/auth/callback")
        mensajes = _mensajes_flash(cliente)

    assert respuesta.status_code == 302
    assert any("No tienes permisos de administrador" in mensaje for mensaje in mensajes)


def test_callback_autentica_a_un_administrador(app_home, monkeypatch):
    _usuario_anonimo(monkeypatch)
    app_home.extensions["oauth_service"] = _ServicioOAuthFalso(
        token={"access_token": "abc", "refresh_token": "ref", "id_token": "id"},
        validacion=_payload_valido(admin=True),
    )

    with app_home.test_client() as cliente:
        respuesta = cliente.get("/auth/callback")
        mensajes = _mensajes_flash(cliente)
        with cliente.session_transaction() as sesion:
            datos_sesion = dict(sesion)

    assert respuesta.status_code == 302
    assert respuesta.headers["Location"].endswith("/home")
    assert "¡Inicio de sesión exitoso!" in mensajes
    assert datos_sesion["access_token"] == "abc"
    assert datos_sesion["id_token"] == "id"
    assert datos_sesion["user_data"]["preferred_username"] == "ana"


def test_callback_propaga_los_datos_del_payload_al_usuario(app_home, monkeypatch):
    _usuario_anonimo(monkeypatch)
    capturado = {}

    original = home_module.User.authenticate_oauth

    def espia(token_data, user_info):
        capturado["user_info"] = user_info
        return original(token_data, user_info)

    monkeypatch.setattr(home_module.User, "authenticate_oauth", staticmethod(espia))
    app_home.extensions["oauth_service"] = _ServicioOAuthFalso(
        token={"access_token": "abc"}, validacion=_payload_valido(admin=True)
    )

    app_home.test_client().get("/auth/callback")

    assert capturado["user_info"]["email"] == "ana@example.com"
    assert capturado["user_info"]["given_name"] == "Ana"
    assert capturado["user_info"]["user_db"] == {"admin": True}


def test_callback_informa_si_la_autenticacion_no_devuelve_usuario(app_home, monkeypatch):
    _usuario_anonimo(monkeypatch)
    monkeypatch.setattr(
        home_module.User, "authenticate_oauth", staticmethod(lambda token, info: None)
    )
    app_home.extensions["oauth_service"] = _ServicioOAuthFalso(
        token={"access_token": "abc"}, validacion=_payload_valido(admin=True)
    )

    with app_home.test_client() as cliente:
        respuesta = cliente.get("/auth/callback")
        mensajes = _mensajes_flash(cliente)

    assert respuesta.status_code == 302
    assert "Error en la autenticación" in mensajes


def test_callback_captura_errores_inesperados(app_home, monkeypatch):
    _usuario_anonimo(monkeypatch)

    class ServicioQueFalla:
        def exchange_code_for_token(self):
            raise RuntimeError("boom")

    app_home.extensions["oauth_service"] = ServicioQueFalla()

    with app_home.test_client() as cliente:
        respuesta = cliente.get("/auth/callback")
        mensajes = _mensajes_flash(cliente)

    assert respuesta.status_code == 302
    assert "Ocurrió un error durante la autenticación" in mensajes


# ---------------------------------------------------------------------------
# logout
# ---------------------------------------------------------------------------

def test_logout_limpia_la_sesion_y_va_a_keycloak(app_home, monkeypatch):
    _usuario_autenticado(monkeypatch)
    servicio = _ServicioOAuthFalso()
    app_home.extensions["oauth_service"] = servicio
    monkeypatch.setattr(home_module, "logout_user", lambda: None)

    with app_home.test_client() as cliente:
        with cliente.session_transaction() as sesion:
            sesion["id_token"] = "id-token-guardado"
            sesion["access_token"] = "abc"

        respuesta = cliente.get("/logout")

        with cliente.session_transaction() as sesion:
            assert "access_token" not in sesion

    assert respuesta.status_code == 302
    assert respuesta.headers["Location"] == "https://kc.example.com/logout"
    assert servicio.logout_kwargs["id_token"] == "id-token-guardado"
    assert servicio.logout_kwargs["redirect_uri"].endswith("/")


def test_logout_sin_servicio_oauth_va_al_inicio(app_home, monkeypatch):
    _usuario_autenticado(monkeypatch)
    app_home.extensions.pop("oauth_service", None)
    monkeypatch.setattr(home_module, "logout_user", lambda: None)

    with app_home.test_client() as cliente:
        respuesta = cliente.get("/logout")
        mensajes = _mensajes_flash(cliente)

    assert respuesta.status_code == 302
    assert "Logged out successfully" in mensajes


def test_logout_exige_sesion_activa(app_home, monkeypatch):
    _usuario_anonimo(monkeypatch)

    respuesta = app_home.test_client().get("/logout")

    assert respuesta.status_code == 302
    assert respuesta.headers["Location"].endswith("/login")


# ---------------------------------------------------------------------------
# home y user_loader
# ---------------------------------------------------------------------------

def test_home_exige_sesion_activa(app_home, monkeypatch):
    _usuario_anonimo(monkeypatch)

    respuesta = app_home.test_client().get("/home")

    assert respuesta.status_code == 302
    assert respuesta.headers["Location"].endswith("/login")


def test_home_renderiza_para_usuarios_autenticados(app_home, monkeypatch):
    _usuario_autenticado(monkeypatch)

    respuesta = app_home.test_client().get("/home")

    assert respuesta.status_code == 200
    assert respuesta.get_data(as_text=True) == "rendered:home.html"


def test_load_user_recupera_al_usuario_de_la_sesion(app_home):
    with app_home.test_request_context("/"):
        from flask import session

        session["user_data"] = {"sub": "kc-1", "preferred_username": "ana", "roles": []}

        usuario = home_module.load_user("kc-1")

        assert usuario is not None
        assert usuario.username == "ana"


def test_load_user_devuelve_none_para_otro_identificador(app_home):
    with app_home.test_request_context("/"):
        from flask import session

        session["user_data"] = {"sub": "kc-1", "preferred_username": "ana", "roles": []}

        assert home_module.load_user("kc-2") is None
