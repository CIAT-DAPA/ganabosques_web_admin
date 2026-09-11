"""Pruebas complementarias del servicio OAuth: rutas alternativas y fallos."""

from types import SimpleNamespace

import pytest

import src.services.oauth_service as oauth_module
from src.services.oauth_service import OAuthService

CONFIG = {
    "KEYCLOAK_SERVER_URL": "https://kc.example.com",
    "KEYCLOAK_REALM": "ganabosques",
    "KEYCLOAK_CLIENT_ID": "admin-panel",
    "KEYCLOAK_CLIENT_SECRET": "secreto",
}


class RespuestaFalsa:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.text = text

    def json(self):
        return self._payload


@pytest.fixture()
def app_oauth(flask_app):
    flask_app.config.update(CONFIG)
    return flask_app


# ---------------------------------------------------------------------------
# init_app
# ---------------------------------------------------------------------------

def test_init_app_deja_el_cliente_en_none_si_falla(app_oauth):
    servicio = OAuthService()

    class MotorQueFalla:
        def init_app(self, app):
            raise RuntimeError("Authlib roto")

    servicio.oauth = MotorQueFalla()
    servicio.init_app(app_oauth)

    assert servicio.keycloak is None


def test_init_app_configura_scope_y_metodo_de_autenticacion(app_oauth):
    servicio = OAuthService()
    registrados = {}

    class Motor:
        def init_app(self, app):
            pass

        def register(self, **kwargs):
            registrados.update(kwargs)
            return object()

    servicio.oauth = Motor()
    servicio.init_app(app_oauth)

    assert registrados["client_kwargs"]["scope"] == "openid email profile"
    assert registrados["client_kwargs"]["token_endpoint_auth_method"] == "client_secret_post"
    assert registrados["jwks_uri"].endswith("/protocol/openid-connect/certs")
    assert registrados["issuer"] == "https://kc.example.com/realms/ganabosques"


# ---------------------------------------------------------------------------
# exchange_code_for_token y get_authorization_url
# ---------------------------------------------------------------------------

def test_exchange_code_for_token_sin_cliente_devuelve_none():
    assert OAuthService().exchange_code_for_token() is None


def test_exchange_code_for_token_devuelve_el_token():
    servicio = OAuthService()
    servicio.keycloak = SimpleNamespace(
        authorize_access_token=lambda: {"access_token": "abc", "id_token": "xyz"}
    )

    assert servicio.exchange_code_for_token() == {"access_token": "abc", "id_token": "xyz"}


def test_get_authorization_url_propaga_errores_del_cliente():
    servicio = OAuthService()

    def explota(redirect_uri):
        raise RuntimeError("proveedor caído")

    servicio.keycloak = SimpleNamespace(authorize_redirect=explota)

    with pytest.raises(RuntimeError, match="proveedor caído"):
        servicio.get_authorization_url("https://app/callback")


# ---------------------------------------------------------------------------
# get_user_info: los tres métodos
# ---------------------------------------------------------------------------

def test_get_user_info_sin_cliente_devuelve_none():
    assert OAuthService().get_user_info({"access_token": "abc"}) is None


def test_get_user_info_usa_el_endpoint_http_si_authlib_falla(app_oauth, monkeypatch):
    """Segundo método: petición directa al userinfo endpoint."""
    servicio = OAuthService()

    def userinfo_roto(token):
        raise RuntimeError("authlib no disponible")

    servicio.keycloak = SimpleNamespace(userinfo=userinfo_roto)
    monkeypatch.setattr(servicio, "_enrich_user_info", lambda info, token: info)

    capturado = {}

    def fake_get(url, headers, timeout):
        capturado["url"] = url
        capturado["headers"] = headers
        return RespuestaFalsa(payload={"preferred_username": "ana"})

    monkeypatch.setattr(oauth_module.requests, "get", fake_get)

    with app_oauth.app_context():
        info = servicio.get_user_info({"access_token": "abc"})

    assert info["preferred_username"] == "ana"
    assert capturado["url"].endswith("/protocol/openid-connect/userinfo")
    assert capturado["headers"]["Authorization"] == "Bearer abc"


def test_get_user_info_cae_al_id_token_si_el_endpoint_falla(app_oauth, monkeypatch):
    """Tercer método: parsear el id_token cuando no hay userinfo utilizable."""
    servicio = OAuthService()

    def userinfo_roto(token):
        raise RuntimeError("no disponible")

    servicio.keycloak = SimpleNamespace(
        userinfo=userinfo_roto,
        parse_id_token=lambda token: {"preferred_username": "desde-id-token"},
    )
    monkeypatch.setattr(servicio, "_enrich_user_info", lambda info, token: info)
    monkeypatch.setattr(
        oauth_module.requests,
        "get",
        lambda url, headers, timeout: RespuestaFalsa(status_code=401, text="no autorizado"),
    )

    with app_oauth.app_context():
        info = servicio.get_user_info({"access_token": "abc", "id_token": "xyz"})

    assert info["preferred_username"] == "desde-id-token"


def test_get_user_info_devuelve_none_si_fallan_los_tres_metodos(app_oauth, monkeypatch):
    servicio = OAuthService()

    def falla(*args, **kwargs):
        raise RuntimeError("no disponible")

    servicio.keycloak = SimpleNamespace(userinfo=falla, parse_id_token=falla)
    monkeypatch.setattr(
        oauth_module.requests,
        "get",
        lambda url, headers, timeout: RespuestaFalsa(status_code=500, text="error"),
    )

    with app_oauth.app_context():
        assert servicio.get_user_info({"access_token": "abc", "id_token": "xyz"}) is None


# ---------------------------------------------------------------------------
# _enrich_user_info
# ---------------------------------------------------------------------------

def test_enrich_user_info_agrega_los_roles_del_realm(app_oauth, monkeypatch):
    servicio = OAuthService()
    monkeypatch.setattr(
        oauth_module.requests,
        "get",
        lambda url, headers, timeout: RespuestaFalsa(
            payload={"realmMappings": [{"name": "admin"}, {"name": "analista"}]}
        ),
    )

    with app_oauth.app_context():
        info = servicio._enrich_user_info({"sub": "kc-1"}, "token")

    assert info["realm_access"]["roles"] == ["admin", "analista"]


def test_enrich_user_info_conserva_la_info_si_la_consulta_falla(app_oauth, monkeypatch):
    servicio = OAuthService()

    def explota(url, headers, timeout):
        raise ConnectionError("sin red")

    monkeypatch.setattr(oauth_module.requests, "get", explota)

    with app_oauth.app_context():
        info = servicio._enrich_user_info({"sub": "kc-1", "preferred_username": "ana"}, "token")

    assert info == {"sub": "kc-1", "preferred_username": "ana"}


def test_enrich_user_info_ignora_respuestas_no_exitosas(app_oauth, monkeypatch):
    servicio = OAuthService()
    monkeypatch.setattr(
        oauth_module.requests,
        "get",
        lambda url, headers, timeout: RespuestaFalsa(status_code=403),
    )

    with app_oauth.app_context():
        info = servicio._enrich_user_info({"sub": "kc-1"}, "token")

    assert "realm_access" not in info


# ---------------------------------------------------------------------------
# validate_token
# ---------------------------------------------------------------------------

def test_validate_token_es_true_con_respuesta_200(app_oauth, monkeypatch):
    monkeypatch.setattr(
        oauth_module.requests, "get", lambda url, headers, timeout: RespuestaFalsa(200)
    )

    with app_oauth.app_context():
        assert OAuthService().validate_token("abc") is True


def test_validate_token_es_false_con_token_expirado(app_oauth, monkeypatch):
    monkeypatch.setattr(
        oauth_module.requests, "get", lambda url, headers, timeout: RespuestaFalsa(401)
    )

    with app_oauth.app_context():
        assert OAuthService().validate_token("abc") is False


def test_validate_token_es_false_ante_error_de_red(app_oauth, monkeypatch):
    def explota(url, headers, timeout):
        raise ConnectionError("sin red")

    monkeypatch.setattr(oauth_module.requests, "get", explota)

    with app_oauth.app_context():
        assert OAuthService().validate_token("abc") is False


# ---------------------------------------------------------------------------
# validate_token_with_api
# ---------------------------------------------------------------------------

def test_validate_token_with_api_usa_la_url_configurada(app_oauth, monkeypatch):
    app_oauth.config["API_BASE_URL"] = "https://api.example.com/"
    capturado = {}

    def fake_get(url, headers, timeout):
        capturado["url"] = url
        return RespuestaFalsa(payload={"valid": True, "payload": {"sub": "kc-1"}})

    monkeypatch.setattr(oauth_module.requests, "get", fake_get)

    with app_oauth.app_context():
        resultado = OAuthService().validate_token_with_api("abc")

    assert resultado["valid"] is True
    assert capturado["url"] == "https://api.example.com/auth/token/validate"


def test_validate_token_with_api_devuelve_none_si_la_api_rechaza(app_oauth, monkeypatch):
    app_oauth.config["API_BASE_URL"] = "https://api.example.com"
    monkeypatch.setattr(
        oauth_module.requests,
        "get",
        lambda url, headers, timeout: RespuestaFalsa(status_code=401, text="no autorizado"),
    )

    with app_oauth.app_context():
        assert OAuthService().validate_token_with_api("abc") is None


def test_validate_token_with_api_devuelve_none_ante_excepcion(app_oauth, monkeypatch):
    app_oauth.config["API_BASE_URL"] = "https://api.example.com"

    def explota(url, headers, timeout):
        raise TimeoutError("timeout")

    monkeypatch.setattr(oauth_module.requests, "get", explota)

    with app_oauth.app_context():
        assert OAuthService().validate_token_with_api("abc") is None


# ---------------------------------------------------------------------------
# logout_url y get_auth_headers
# ---------------------------------------------------------------------------

def test_logout_url_sin_parametros(app_oauth):
    with app_oauth.app_context():
        url = OAuthService().logout_url()

    assert url.endswith("/protocol/openid-connect/logout")
    assert "?" not in url


def test_logout_url_solo_con_redirect(app_oauth):
    with app_oauth.app_context():
        url = OAuthService().logout_url(redirect_uri="https://app/bye")

    assert url.endswith("?post_logout_redirect_uri=https://app/bye")
    assert "id_token_hint" not in url


def test_logout_url_ordena_los_parametros(app_oauth):
    with app_oauth.app_context():
        url = OAuthService().logout_url(redirect_uri="https://app/bye", id_token="tok")

    assert url.endswith("?id_token_hint=tok&post_logout_redirect_uri=https://app/bye")


def test_get_auth_headers_vacio_sin_token(flask_app):
    with flask_app.test_request_context("/"):
        assert OAuthService.get_auth_headers() == {}


def test_get_auth_headers_prefiere_el_token_explicito(flask_app):
    with flask_app.test_request_context("/"):
        from flask import session

        session["access_token"] = "de-sesion"

        assert OAuthService.get_auth_headers("explicito") == {
            "Authorization": "Bearer explicito"
        }
