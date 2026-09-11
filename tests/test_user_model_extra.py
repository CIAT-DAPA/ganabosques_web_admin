"""Pruebas complementarias del modelo de usuario y su extracción de roles."""

import pytest
from flask import session

from src.models.User import User


# ---------------------------------------------------------------------------
# Construcción del usuario
# ---------------------------------------------------------------------------

def test_identificador_cae_en_cascada_hasta_el_username():
    usuario = User({"username": "ana"})

    assert usuario.id == "ana"
    assert usuario.get_id() == "ana"


def test_identificador_prefiere_sub():
    usuario = User({"sub": "kc-1", "id": "otro", "preferred_username": "ana"})

    assert usuario.id == "kc-1"


def test_username_se_deduce_del_correo():
    usuario = User({"sub": "kc-1", "email": "ana.ruiz@example.com"})

    assert usuario.username == "ana.ruiz"


def test_nombre_completo_se_arma_con_nombre_y_apellido():
    usuario = User({"sub": "kc-1", "given_name": "Ana", "family_name": "Ruiz"})

    assert usuario.name == "Ana Ruiz"
    assert usuario.first_name == "Ana"
    assert usuario.last_name == "Ruiz"


def test_nombre_explicito_tiene_prioridad():
    usuario = User(
        {"sub": "kc-1", "name": "Ana R.", "given_name": "Ana", "family_name": "Ruiz"}
    )

    assert usuario.name == "Ana R."


def test_campos_opcionales_quedan_vacios():
    usuario = User({"sub": "kc-1"})

    assert usuario.email == ""
    assert usuario.first_name == ""
    assert usuario.last_name == ""
    assert usuario.name == ""


# ---------------------------------------------------------------------------
# Extracción de roles
# ---------------------------------------------------------------------------

def test_extrae_roles_de_client_roles_como_diccionarios():
    usuario = User(
        {
            "sub": "kc-1",
            "client_roles": [{"name": "editor"}, {"name": "revisor"}],
        }
    )

    assert set(usuario.roles) == {"editor", "revisor"}


def test_extrae_roles_de_client_roles_como_cadenas():
    usuario = User({"sub": "kc-1", "client_roles": ["editor", "revisor"]})

    assert set(usuario.roles) == {"editor", "revisor"}


def test_ignora_client_roles_con_formato_inesperado():
    usuario = User({"sub": "kc-1", "client_roles": "no-es-una-lista"})

    assert usuario.roles == []


def test_extrae_role_name_suelto():
    usuario = User({"sub": "kc-1", "role_name": "coordinador"})

    assert usuario.roles == ["coordinador"]


def test_extrae_roles_de_grupos():
    usuario = User({"sub": "kc-1", "groups": ["equipo-adm"]})

    assert usuario.roles == ["equipo-adm"]


def test_extrae_roles_de_varios_clientes_de_resource_access():
    usuario = User(
        {
            "sub": "kc-1",
            "resource_access": {
                "account": {"roles": ["view-profile"]},
                "realm-management": {"roles": ["manage-users"]},
                "aclimate_admin": {"roles": ["editor"]},
                "cliente-no-listado": {"roles": ["invisible"]},
            },
        }
    )

    assert {"view-profile", "manage-users", "editor"}.issubset(set(usuario.roles))
    assert "invisible" not in usuario.roles


@pytest.mark.parametrize(
    "rol_de_sistema",
    [
        "offline_access",
        "uma_authorization",
        "default-roles-aclimate",
        "account-manage-account",
        "account-view-profile",
        "web-origins",
    ],
)
def test_filtra_los_roles_internos_de_keycloak(rol_de_sistema):
    usuario = User({"sub": "kc-1", "roles": [rol_de_sistema, "admin"]})

    assert rol_de_sistema not in usuario.roles
    assert "admin" in usuario.roles


def test_elimina_roles_duplicados():
    usuario = User(
        {
            "sub": "kc-1",
            "roles": ["admin"],
            "realm_access": {"roles": ["admin"]},
            "client_roles": ["admin"],
        }
    )

    assert usuario.roles == ["admin"]


def test_usuario_sin_roles():
    usuario = User({"sub": "kc-1"})

    assert usuario.roles == []


# ---------------------------------------------------------------------------
# Comprobaciones de privilegio
# ---------------------------------------------------------------------------

def test_is_admin_acepta_admin_y_adminsuper():
    assert User({"sub": "1", "roles": ["admin"]}).is_admin() is True
    assert User({"sub": "1", "roles": ["adminsuper"]}).is_admin() is True


def test_is_admin_es_false_para_otros_roles():
    assert User({"sub": "1", "roles": ["analista"]}).is_admin() is False


def test_is_super_admin_solo_con_adminsuper():
    assert User({"sub": "1", "roles": ["adminsuper"]}).is_super_admin() is True
    assert User({"sub": "1", "roles": ["admin"]}).is_super_admin() is False


# ---------------------------------------------------------------------------
# Compatibilidad con el modelo anterior
# ---------------------------------------------------------------------------

def test_property_role_devuelve_el_primero():
    usuario = User({"sub": "1", "roles": ["analista"]})

    assert usuario.role == "analista"


def test_property_role_cae_en_guest_sin_roles():
    assert User({"sub": "1"}).role == "guest"


def test_check_password_siempre_es_false():
    assert User({"sub": "1"}).check_password("lo-que-sea") is False


# ---------------------------------------------------------------------------
# authenticate_oauth
# ---------------------------------------------------------------------------

def test_authenticate_oauth_devuelve_none_sin_token(flask_app):
    with flask_app.test_request_context("/"):
        assert User.authenticate_oauth(None, {"sub": "1"}) is None


def test_authenticate_oauth_devuelve_none_sin_user_info(flask_app):
    with flask_app.test_request_context("/"):
        assert User.authenticate_oauth({"access_token": "abc"}, None) is None


def test_authenticate_oauth_guarda_tokens_ausentes_como_none(flask_app):
    with flask_app.test_request_context("/"):
        User.authenticate_oauth({"access_token": "abc"}, {"sub": "1", "preferred_username": "ana"})

        assert session["access_token"] == "abc"
        assert session["refresh_token"] is None
        assert session["id_token"] is None


# ---------------------------------------------------------------------------
# get y validate_token
# ---------------------------------------------------------------------------

def test_get_devuelve_none_sin_datos_en_sesion(flask_app):
    with flask_app.test_request_context("/"):
        assert User.get("kc-1") is None


def test_validate_token_es_false_si_no_hay_servicio_oauth(flask_app):
    with flask_app.test_request_context("/"):
        session["access_token"] = "abc"
        flask_app.extensions = {}

        assert User({"sub": "1"}).validate_token() is False


def test_validate_token_es_false_si_el_servicio_lanza(flask_app):
    with flask_app.test_request_context("/"):
        session["access_token"] = "abc"

        class ServicioQueFalla:
            def validate_token(self, token):
                raise RuntimeError("sin red")

        flask_app.extensions = {"oauth_service": ServicioQueFalla()}

        assert User({"sub": "1"}).validate_token() is False


def test_validate_token_propaga_el_rechazo_del_servicio(flask_app):
    with flask_app.test_request_context("/"):
        session["access_token"] = "expirado"

        class Servicio:
            def validate_token(self, token):
                return False

        flask_app.extensions = {"oauth_service": Servicio()}

        assert User({"sub": "1"}).validate_token() is False
