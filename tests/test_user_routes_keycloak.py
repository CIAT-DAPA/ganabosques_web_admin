"""Pruebas de las funciones que hablan con la API de administración de Keycloak."""

import pytest

import src.routes.user_routes as user_routes_module

CONFIG_KEYCLOAK = {
    "KEYCLOAK_SERVER_URL": "https://kc.example.com",
    "KEYCLOAK_REALM": "ganabosques",
    "KEYCLOAK_CLIENT_ID": "admin-panel",
    "KEYCLOAK_CLIENT_SECRET": "secreto",
}


class RespuestaFalsa:
    def __init__(self, status_code=200, payload=None, text="", headers=None):
        self.status_code = status_code
        self._payload = payload
        self.text = text
        self.headers = headers or {}
        self.raise_called = False

    def json(self):
        if self._payload is None:
            raise ValueError("sin cuerpo JSON")
        return self._payload

    def raise_for_status(self):
        self.raise_called = True
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")


@pytest.fixture()
def app_keycloak(make_app):
    return make_app(user_routes_module.user_bp, **CONFIG_KEYCLOAK)


# ---------------------------------------------------------------------------
# get_keycloak_admin_token
# ---------------------------------------------------------------------------

def test_get_keycloak_admin_token_devuelve_el_token(app_keycloak, monkeypatch):
    capturado = {}

    def fake_post(url, data):
        capturado["url"] = url
        capturado["data"] = data
        return RespuestaFalsa(payload={"access_token": "token-admin"})

    monkeypatch.setattr(user_routes_module.requests, "post", fake_post)

    with app_keycloak.app_context():
        token = user_routes_module.get_keycloak_admin_token()

    assert token == "token-admin"
    assert capturado["url"] == (
        "https://kc.example.com/realms/ganabosques/protocol/openid-connect/token"
    )
    assert capturado["data"]["grant_type"] == "client_credentials"
    assert capturado["data"]["client_id"] == "admin-panel"
    assert capturado["data"]["client_secret"] == "secreto"


def test_get_keycloak_admin_token_devuelve_none_si_keycloak_falla(app_keycloak, monkeypatch):
    monkeypatch.setattr(
        user_routes_module.requests, "post", lambda url, data: RespuestaFalsa(status_code=401)
    )

    with app_keycloak.app_context():
        assert user_routes_module.get_keycloak_admin_token() is None


def test_get_keycloak_admin_token_devuelve_none_ante_error_de_red(app_keycloak, monkeypatch):
    def explota(url, data):
        raise ConnectionError("sin red")

    monkeypatch.setattr(user_routes_module.requests, "post", explota)

    with app_keycloak.app_context():
        assert user_routes_module.get_keycloak_admin_token() is None


# ---------------------------------------------------------------------------
# get_keycloak_user_by_id
# ---------------------------------------------------------------------------

def test_get_keycloak_user_by_id_devuelve_el_usuario(app_keycloak, monkeypatch):
    capturado = {}

    def fake_get(url, headers):
        capturado["url"] = url
        capturado["headers"] = headers
        return RespuestaFalsa(payload={"id": "u1", "username": "ana"})

    monkeypatch.setattr(user_routes_module.requests, "get", fake_get)

    with app_keycloak.app_context():
        usuario = user_routes_module.get_keycloak_user_by_id("token-admin", "u1")

    assert usuario == {"id": "u1", "username": "ana"}
    assert capturado["url"] == "https://kc.example.com/admin/realms/ganabosques/users/u1"
    assert capturado["headers"]["Authorization"] == "Bearer token-admin"


def test_get_keycloak_user_by_id_devuelve_none_si_no_existe(app_keycloak, monkeypatch):
    monkeypatch.setattr(
        user_routes_module.requests, "get", lambda url, headers: RespuestaFalsa(status_code=404)
    )

    with app_keycloak.app_context():
        assert user_routes_module.get_keycloak_user_by_id("token", "u1") is None


def test_get_keycloak_user_by_id_devuelve_none_ante_excepcion(app_keycloak, monkeypatch):
    def explota(url, headers):
        raise TimeoutError("timeout")

    monkeypatch.setattr(user_routes_module.requests, "get", explota)

    with app_keycloak.app_context():
        assert user_routes_module.get_keycloak_user_by_id("token", "u1") is None


# ---------------------------------------------------------------------------
# create_keycloak_user
# ---------------------------------------------------------------------------

DATOS_USUARIO = {
    "username": "ana",
    "email": "ana@example.com",
    "firstName": "Ana",
    "lastName": "Ruiz",
    "password": "Secreta123",
}


def test_create_keycloak_user_extrae_el_id_de_la_cabecera_location(app_keycloak, monkeypatch):
    capturado = {}

    def fake_post(url, json, headers):
        capturado["url"] = url
        capturado["json"] = json
        return RespuestaFalsa(
            status_code=201,
            headers={"Location": "https://kc.example.com/admin/realms/ganabosques/users/nuevo-id"},
        )

    monkeypatch.setattr(user_routes_module.requests, "post", fake_post)

    with app_keycloak.app_context():
        keycloak_id, error = user_routes_module.create_keycloak_user("token", DATOS_USUARIO)

    assert keycloak_id == "nuevo-id"
    assert error is None
    assert capturado["url"] == "https://kc.example.com/admin/realms/ganabosques/users"
    assert capturado["json"]["username"] == "ana"
    assert capturado["json"]["enabled"] is True
    assert capturado["json"]["credentials"][0]["value"] == "Secreta123"
    assert capturado["json"]["credentials"][0]["temporary"] is False


def test_create_keycloak_user_devuelve_none_si_no_hay_location(app_keycloak, monkeypatch):
    monkeypatch.setattr(
        user_routes_module.requests,
        "post",
        lambda url, json, headers: RespuestaFalsa(status_code=201, headers={}),
    )

    with app_keycloak.app_context():
        keycloak_id, error = user_routes_module.create_keycloak_user("token", DATOS_USUARIO)

    assert keycloak_id is None


def test_create_keycloak_user_propaga_el_mensaje_de_error(app_keycloak, monkeypatch):
    monkeypatch.setattr(
        user_routes_module.requests,
        "post",
        lambda url, json, headers: RespuestaFalsa(
            status_code=409, payload={"errorMessage": "User exists with same username"},
            text='{"errorMessage": "User exists with same username"}',
        ),
    )

    with app_keycloak.app_context():
        keycloak_id, error = user_routes_module.create_keycloak_user("token", DATOS_USUARIO)

    assert keycloak_id is None
    assert error == "User exists with same username"


def test_create_keycloak_user_captura_excepciones(app_keycloak, monkeypatch):
    def explota(url, json, headers):
        raise ConnectionError("sin red")

    monkeypatch.setattr(user_routes_module.requests, "post", explota)

    with app_keycloak.app_context():
        keycloak_id, error = user_routes_module.create_keycloak_user("token", DATOS_USUARIO)

    assert keycloak_id is None
    assert "sin red" in error


# ---------------------------------------------------------------------------
# update_keycloak_user
# ---------------------------------------------------------------------------

def test_update_keycloak_user_envia_solo_los_campos_basicos(app_keycloak, monkeypatch):
    capturado = {}

    def fake_put(url, json, headers):
        capturado["url"] = url
        capturado["json"] = json
        return RespuestaFalsa(status_code=204)

    monkeypatch.setattr(user_routes_module.requests, "put", fake_put)

    with app_keycloak.app_context():
        exito, error = user_routes_module.update_keycloak_user(
            "token", "u1", {"email": "nueva@example.com", "firstName": "Ana", "lastName": "Ruiz"}
        )

    assert exito is True
    assert error is None
    assert capturado["url"] == "https://kc.example.com/admin/realms/ganabosques/users/u1"
    assert capturado["json"] == {
        "email": "nueva@example.com",
        "firstName": "Ana",
        "lastName": "Ruiz",
    }
    assert "username" not in capturado["json"]


def test_update_keycloak_user_reporta_error_http(app_keycloak, monkeypatch):
    monkeypatch.setattr(
        user_routes_module.requests,
        "put",
        lambda url, json, headers: RespuestaFalsa(
            status_code=400, payload={"errorMessage": "correo inválido"}, text="x"
        ),
    )

    with app_keycloak.app_context():
        exito, error = user_routes_module.update_keycloak_user("token", "u1", {"email": "mal"})

    assert exito is False
    assert error == "correo inválido"


def test_update_keycloak_user_captura_excepciones(app_keycloak, monkeypatch):
    def explota(url, json, headers):
        raise ConnectionError("sin red")

    monkeypatch.setattr(user_routes_module.requests, "put", explota)

    with app_keycloak.app_context():
        exito, error = user_routes_module.update_keycloak_user("token", "u1", {"email": "a@b.c"})

    assert exito is False
    assert "sin red" in error


# ---------------------------------------------------------------------------
# update_keycloak_password
# ---------------------------------------------------------------------------

def test_update_keycloak_password_usa_el_endpoint_reset_password(app_keycloak, monkeypatch):
    capturado = {}

    def fake_put(url, json, headers):
        capturado["url"] = url
        capturado["json"] = json
        return RespuestaFalsa(status_code=204)

    monkeypatch.setattr(user_routes_module.requests, "put", fake_put)

    with app_keycloak.app_context():
        exito, error = user_routes_module.update_keycloak_password("token", "u1", "NuevaClave1")

    assert exito is True
    assert error is None
    assert capturado["url"].endswith("/users/u1/reset-password")
    assert capturado["json"] == {"type": "password", "value": "NuevaClave1", "temporary": False}


def test_update_keycloak_password_reporta_error(app_keycloak, monkeypatch):
    monkeypatch.setattr(
        user_routes_module.requests,
        "put",
        lambda url, json, headers: RespuestaFalsa(
            status_code=400, payload={"errorMessage": "contraseña débil"}, text="x"
        ),
    )

    with app_keycloak.app_context():
        exito, error = user_routes_module.update_keycloak_password("token", "u1", "123")

    assert exito is False
    assert error == "contraseña débil"


# ---------------------------------------------------------------------------
# delete_keycloak_user
# ---------------------------------------------------------------------------

def test_delete_keycloak_user_confirma_eliminacion(app_keycloak, monkeypatch):
    capturado = {}

    def fake_delete(url, headers):
        capturado["url"] = url
        capturado["headers"] = headers
        return RespuestaFalsa(status_code=204)

    monkeypatch.setattr(user_routes_module.requests, "delete", fake_delete)

    with app_keycloak.app_context():
        exito, error = user_routes_module.delete_keycloak_user("token", "u1")

    assert exito is True
    assert error is None
    assert capturado["url"] == "https://kc.example.com/admin/realms/ganabosques/users/u1"
    assert capturado["headers"]["Authorization"] == "Bearer token"


def test_delete_keycloak_user_reporta_error(app_keycloak, monkeypatch):
    monkeypatch.setattr(
        user_routes_module.requests,
        "delete",
        lambda url, headers: RespuestaFalsa(
            status_code=403, payload={"errorMessage": "prohibido"}, text="x"
        ),
    )

    with app_keycloak.app_context():
        exito, error = user_routes_module.delete_keycloak_user("token", "u1")

    assert exito is False
    assert error == "prohibido"


def test_delete_keycloak_user_usa_el_texto_crudo_si_no_hay_errormessage(app_keycloak, monkeypatch):
    monkeypatch.setattr(
        user_routes_module.requests,
        "delete",
        lambda url, headers: RespuestaFalsa(status_code=403, payload={"otro": 1}, text="x"),
    )

    with app_keycloak.app_context():
        exito, error = user_routes_module.delete_keycloak_user("token", "u1")

    assert exito is False
    assert error == "x"


def test_delete_keycloak_user_con_cuerpo_no_json_pierde_el_mensaje_del_servidor(
    app_keycloak, monkeypatch
):
    """Documenta un defecto conocido del manejo de errores.

    Cuando Keycloak (o un proxy intermedio) responde un error con cuerpo que no
    es JSON —por ejemplo una página HTML—, ``resp.json()`` lanza y la excepción
    la captura el ``except`` externo, de modo que el mensaje devuelto describe
    el fallo al parsear y no el error real del servidor. El mismo patrón se
    repite en ``create_keycloak_user``, ``update_keycloak_user`` y
    ``update_keycloak_password``.
    """
    monkeypatch.setattr(
        user_routes_module.requests,
        "delete",
        lambda url, headers: RespuestaFalsa(status_code=502, text="<html>Bad Gateway</html>"),
    )

    with app_keycloak.app_context():
        exito, error = user_routes_module.delete_keycloak_user("token", "u1")

    assert exito is False
    assert "Bad Gateway" not in error


def test_delete_keycloak_user_captura_excepciones(app_keycloak, monkeypatch):
    def explota(url, headers):
        raise ConnectionError("sin red")

    monkeypatch.setattr(user_routes_module.requests, "delete", explota)

    with app_keycloak.app_context():
        exito, error = user_routes_module.delete_keycloak_user("token", "u1")

    assert exito is False
    assert "sin red" in error
