"""Pruebas de las vistas de gestión de usuarios (Keycloak + MongoDB)."""

import json
from types import SimpleNamespace

import pytest

import src.routes.user_routes as user_routes_module

CONFIG_KEYCLOAK = {
    "KEYCLOAK_SERVER_URL": "https://kc.example.com",
    "KEYCLOAK_REALM": "ganabosques",
    "KEYCLOAK_CLIENT_ID": "admin-panel",
    "KEYCLOAK_CLIENT_SECRET": "secreto",
}


@pytest.fixture()
def app_usuarios(make_app):
    return make_app(user_routes_module.user_bp, **CONFIG_KEYCLOAK)


class _RolFalso:
    """Doble de un documento Role con acciones ya resueltas."""

    def __init__(self, role_id="r1", name="Analista", actions=None):
        self.id = role_id
        self.name = name
        self.actions = actions if actions is not None else [_permiso("FRONT_ADM", ["READ"])]
        self.saved = False
        self.deleted = False

    def save(self):
        self.saved = True
        return self


def _permiso(action_name, option_names):
    from ganabosques_orm.enums.actions import Actions
    from ganabosques_orm.enums.options import Options

    return SimpleNamespace(
        action=Actions[action_name],
        options=[Options[nombre] for nombre in option_names],
    )


class _UsuarioDB:
    def __init__(self, ext_id="kc-1", admin=False, role=None):
        self.ext_id = ext_id
        self.admin = admin
        self.role = role or []
        self.saved = False
        self.deleted = False

    def save(self):
        self.saved = True
        return self

    def delete(self):
        self.deleted = True
        return self


class _ManagerUsuarios:
    """Manager que distingue entre listar todos y buscar por ext_id."""

    def __init__(self, usuarios):
        self.usuarios = list(usuarios)
        self.creados = []

    def __call__(self, **kwargs):
        if "ext_id" in kwargs:
            coincidencias = [u for u in self.usuarios if u.ext_id == kwargs["ext_id"]]
            return SimpleNamespace(first=lambda: coincidencias[0] if coincidencias else None)
        return self

    def __iter__(self):
        return iter(self.usuarios)


def _stub_user_orm(monkeypatch, usuarios):
    manager = _ManagerUsuarios(usuarios)
    creados = []

    class UserORMStub:
        objects = manager

        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.saved = False
            creados.append(self)

        def save(self):
            self.saved = True
            return self

    UserORMStub.creados = creados
    monkeypatch.setattr(user_routes_module, "UserORM", UserORMStub)
    return UserORMStub


def _stub_role(monkeypatch, roles=()):
    creados = []
    eliminados = []

    class RoleStub:
        def __init__(self, name=None, actions=None):
            self.name = name
            self.actions = actions or []
            self.id = f"nuevo-{len(creados)}"
            self.saved = False
            creados.append(self)

        def save(self):
            self.saved = True
            return self

        @staticmethod
        def objects(**kwargs):
            if "id" in kwargs:
                coincidencias = [r for r in roles if str(r.id) == str(kwargs["id"])]
                return SimpleNamespace(
                    first=lambda: coincidencias[0] if coincidencias else None,
                    delete=lambda: eliminados.append(kwargs["id"]),
                )
            return list(roles)

    RoleStub.creados = creados
    RoleStub.eliminados = eliminados
    monkeypatch.setattr(user_routes_module, "Role", RoleStub)
    return RoleStub


def _mensajes_flash(cliente):
    with cliente.session_transaction() as sesion:
        return [mensaje for _, mensaje in sesion.get("_flashes", [])]


# ---------------------------------------------------------------------------
# list_users
# ---------------------------------------------------------------------------

def test_list_users_combina_datos_de_keycloak_y_mongo(
    app_usuarios, capture_render, monkeypatch
):
    capturado = capture_render(user_routes_module)
    rol = _RolFalso()
    _stub_user_orm(monkeypatch, [_UsuarioDB(ext_id="kc-1", admin=True, role=[rol])])
    _stub_role(monkeypatch, [rol])
    monkeypatch.setattr(user_routes_module, "get_keycloak_admin_token", lambda: "token")
    monkeypatch.setattr(
        user_routes_module,
        "get_keycloak_user_by_id",
        lambda token, ext_id: {
            "id": ext_id,
            "username": "ana",
            "email": "ana@example.com",
            "firstName": "Ana",
            "lastName": "Ruiz",
            "enabled": True,
        },
    )

    respuesta = app_usuarios.test_client().get("/users")

    assert respuesta.status_code == 200
    assert capturado["template"] == "user/list.html"
    usuarios = capturado["context"]["users"]
    assert len(usuarios) == 1
    assert usuarios[0]["username"] == "ana"
    assert usuarios[0]["admin"] is True
    assert usuarios[0]["roles"][0]["name"] == "Analista"
    assert usuarios[0]["roles"][0]["actions"][0]["options"] == ["read"]


def test_list_users_sin_token_devuelve_lista_vacia(app_usuarios, capture_render, monkeypatch):
    capturado = capture_render(user_routes_module)
    _stub_user_orm(monkeypatch, [_UsuarioDB(ext_id="kc-1")])
    _stub_role(monkeypatch)
    monkeypatch.setattr(user_routes_module, "get_keycloak_admin_token", lambda: None)

    respuesta = app_usuarios.test_client().get("/users")

    assert respuesta.status_code == 200
    assert capturado["context"]["users"] == []
    assert capturado["context"]["total"] == 0


def test_list_users_omite_usuarios_ausentes_en_keycloak(
    app_usuarios, capture_render, monkeypatch
):
    capturado = capture_render(user_routes_module)
    _stub_user_orm(monkeypatch, [_UsuarioDB(ext_id="kc-1"), _UsuarioDB(ext_id="kc-2")])
    _stub_role(monkeypatch)
    monkeypatch.setattr(user_routes_module, "get_keycloak_admin_token", lambda: "token")
    monkeypatch.setattr(
        user_routes_module,
        "get_keycloak_user_by_id",
        lambda token, ext_id: {"id": ext_id, "username": "ana"} if ext_id == "kc-1" else None,
    )

    app_usuarios.test_client().get("/users")

    assert len(capturado["context"]["users"]) == 1


def test_list_users_filtra_por_busqueda(app_usuarios, capture_render, monkeypatch):
    capturado = capture_render(user_routes_module)
    _stub_user_orm(monkeypatch, [_UsuarioDB(ext_id="kc-1"), _UsuarioDB(ext_id="kc-2")])
    _stub_role(monkeypatch)
    monkeypatch.setattr(user_routes_module, "get_keycloak_admin_token", lambda: "token")

    perfiles = {
        "kc-1": {"id": "kc-1", "username": "ana", "email": "ana@example.com",
                 "firstName": "Ana", "lastName": "Ruiz"},
        "kc-2": {"id": "kc-2", "username": "beto", "email": "beto@example.com",
                 "firstName": "Beto", "lastName": "Gil"},
    }
    monkeypatch.setattr(
        user_routes_module, "get_keycloak_user_by_id", lambda token, ext_id: perfiles[ext_id]
    )

    app_usuarios.test_client().get("/users?q=BETO")

    usuarios = capturado["context"]["users"]
    assert len(usuarios) == 1
    assert usuarios[0]["username"] == "beto"
    assert capturado["context"]["search"] == "BETO"


def test_list_users_pagina_los_resultados(app_usuarios, capture_render, monkeypatch):
    capturado = capture_render(user_routes_module)
    usuarios_db = [_UsuarioDB(ext_id=f"kc-{i}") for i in range(60)]
    _stub_user_orm(monkeypatch, usuarios_db)
    _stub_role(monkeypatch)
    monkeypatch.setattr(user_routes_module, "get_keycloak_admin_token", lambda: "token")
    monkeypatch.setattr(
        user_routes_module,
        "get_keycloak_user_by_id",
        lambda token, ext_id: {"id": ext_id, "username": ext_id, "email": "", "firstName": "", "lastName": ""},
    )

    app_usuarios.test_client().get("/users?page=2")

    assert capturado["context"]["total"] == 60
    assert capturado["context"]["total_pages"] == 2
    assert len(capturado["context"]["users"]) == 10


# ---------------------------------------------------------------------------
# create_user
# ---------------------------------------------------------------------------

def test_create_user_get_expone_enums_y_roles(app_usuarios, capture_render, monkeypatch):
    capturado = capture_render(user_routes_module)
    _stub_role(monkeypatch, [_RolFalso()])

    respuesta = app_usuarios.test_client().get("/users/create")

    assert respuesta.status_code == 200
    assert capturado["template"] == "user/create.html"
    assert any(a["name"] == "FRONT_ADM" for a in capturado["context"]["actions_enum"])
    assert any(o["name"] == "READ" for o in capturado["context"]["options_enum"])
    roles = json.loads(capturado["context"]["available_roles_json"])
    assert roles[0]["name"] == "Analista"


def test_create_user_exige_campos_obligatorios(app_usuarios, capture_render, monkeypatch):
    capture_render(user_routes_module)
    _stub_role(monkeypatch)
    _stub_user_orm(monkeypatch, [])

    with app_usuarios.test_client() as cliente:
        respuesta = cliente.post("/users/create", data={"username": "ana"})
        mensajes = _mensajes_flash(cliente)

    assert respuesta.status_code == 200
    assert any("obligatorios" in mensaje for mensaje in mensajes)


def test_create_user_avisa_si_keycloak_no_responde(app_usuarios, capture_render, monkeypatch):
    capture_render(user_routes_module)
    _stub_role(monkeypatch)
    _stub_user_orm(monkeypatch, [])
    monkeypatch.setattr(user_routes_module, "get_keycloak_admin_token", lambda: None)

    datos = {"username": "ana", "email": "ana@example.com", "password": "Clave1"}
    with app_usuarios.test_client() as cliente:
        respuesta = cliente.post("/users/create", data=datos)
        mensajes = _mensajes_flash(cliente)

    assert respuesta.status_code == 200
    assert any("No se pudo conectar con Keycloak" in mensaje for mensaje in mensajes)


def test_create_user_informa_error_de_creacion_en_keycloak(
    app_usuarios, capture_render, monkeypatch
):
    capture_render(user_routes_module)
    _stub_role(monkeypatch)
    usuario_stub = _stub_user_orm(monkeypatch, [])
    monkeypatch.setattr(user_routes_module, "get_keycloak_admin_token", lambda: "token")
    monkeypatch.setattr(
        user_routes_module,
        "create_keycloak_user",
        lambda token, datos: (None, "User exists with same username"),
    )

    datos = {"username": "ana", "email": "ana@example.com", "password": "Clave1"}
    with app_usuarios.test_client() as cliente:
        respuesta = cliente.post("/users/create", data=datos)
        mensajes = _mensajes_flash(cliente)

    assert respuesta.status_code == 200
    assert any("User exists with same username" in mensaje for mensaje in mensajes)
    assert usuario_stub.creados == []


def test_create_user_crea_roles_y_usuario_en_mongo(app_usuarios, capture_render, monkeypatch):
    capture_render(user_routes_module)
    role_stub = _stub_role(monkeypatch)
    usuario_stub = _stub_user_orm(monkeypatch, [])
    monkeypatch.setattr(user_routes_module, "get_keycloak_admin_token", lambda: "token")
    monkeypatch.setattr(
        user_routes_module, "create_keycloak_user", lambda token, datos: ("kc-nuevo", None)
    )

    roles_data = json.dumps(
        [{"name": "Analista", "actions": [{"name": "FRONT_ADM", "options": ["READ", "UPDATE"]}]}]
    )
    datos = {
        "username": "ana",
        "email": "ana@example.com",
        "password": "Clave1",
        "admin": "on",
        "roles_data": roles_data,
    }

    respuesta = app_usuarios.test_client().post("/users/create", data=datos)

    assert respuesta.status_code == 302
    assert len(role_stub.creados) == 1
    assert role_stub.creados[0].name == "Analista"
    assert len(role_stub.creados[0].actions) == 1
    assert len(usuario_stub.creados) == 1
    creado = usuario_stub.creados[0]
    assert creado.kwargs["ext_id"] == "kc-nuevo"
    assert creado.kwargs["admin"] is True
    assert creado.kwargs["role"] == role_stub.creados


def test_create_user_ignora_roles_con_json_invalido(app_usuarios, capture_render, monkeypatch):
    capture_render(user_routes_module)
    role_stub = _stub_role(monkeypatch)
    usuario_stub = _stub_user_orm(monkeypatch, [])
    monkeypatch.setattr(user_routes_module, "get_keycloak_admin_token", lambda: "token")
    monkeypatch.setattr(
        user_routes_module, "create_keycloak_user", lambda token, datos: ("kc-nuevo", None)
    )

    datos = {
        "username": "ana",
        "email": "ana@example.com",
        "password": "Clave1",
        "roles_data": "esto no es json",
    }

    respuesta = app_usuarios.test_client().post("/users/create", data=datos)

    assert respuesta.status_code == 302
    assert role_stub.creados == []
    assert usuario_stub.creados[0].kwargs["role"] == []


def test_create_user_descarta_acciones_desconocidas(app_usuarios, capture_render, monkeypatch):
    capture_render(user_routes_module)
    role_stub = _stub_role(monkeypatch)
    _stub_user_orm(monkeypatch, [])
    monkeypatch.setattr(user_routes_module, "get_keycloak_admin_token", lambda: "token")
    monkeypatch.setattr(
        user_routes_module, "create_keycloak_user", lambda token, datos: ("kc-nuevo", None)
    )

    roles_data = json.dumps(
        [
            {
                "name": "Analista",
                "actions": [
                    {"name": "ACCION_QUE_NO_EXISTE", "options": ["READ"]},
                    {"name": "FRONT_ADM", "options": ["READ", "OPCION_INVALIDA"]},
                ],
            }
        ]
    )
    datos = {
        "username": "ana",
        "email": "ana@example.com",
        "password": "Clave1",
        "roles_data": roles_data,
    }

    app_usuarios.test_client().post("/users/create", data=datos)

    assert len(role_stub.creados) == 1
    acciones = role_stub.creados[0].actions
    assert len(acciones) == 1
    assert len(acciones[0].options) == 1


def test_create_user_omite_roles_sin_nombre(app_usuarios, capture_render, monkeypatch):
    capture_render(user_routes_module)
    role_stub = _stub_role(monkeypatch)
    _stub_user_orm(monkeypatch, [])
    monkeypatch.setattr(user_routes_module, "get_keycloak_admin_token", lambda: "token")
    monkeypatch.setattr(
        user_routes_module, "create_keycloak_user", lambda token, datos: ("kc-nuevo", None)
    )

    datos = {
        "username": "ana",
        "email": "ana@example.com",
        "password": "Clave1",
        "roles_data": json.dumps([{"name": "   ", "actions": []}]),
    }

    app_usuarios.test_client().post("/users/create", data=datos)

    assert role_stub.creados == []


# ---------------------------------------------------------------------------
# edit_user
# ---------------------------------------------------------------------------

def test_edit_user_redirige_si_keycloak_no_responde(app_usuarios, monkeypatch):
    monkeypatch.setattr(user_routes_module, "get_keycloak_admin_token", lambda: None)

    with app_usuarios.test_client() as cliente:
        respuesta = cliente.get("/users/edit/kc-1")
        mensajes = _mensajes_flash(cliente)

    assert respuesta.status_code == 302
    assert "No se pudo conectar con Keycloak." in mensajes


def test_edit_user_redirige_si_el_usuario_no_existe_en_keycloak(app_usuarios, monkeypatch):
    monkeypatch.setattr(user_routes_module, "get_keycloak_admin_token", lambda: "token")
    monkeypatch.setattr(user_routes_module, "get_keycloak_user_by_id", lambda t, i: None)

    with app_usuarios.test_client() as cliente:
        respuesta = cliente.get("/users/edit/kc-1")
        mensajes = _mensajes_flash(cliente)

    assert respuesta.status_code == 302
    assert "Usuario no encontrado en Keycloak." in mensajes


def test_edit_user_redirige_si_no_esta_en_mongo(app_usuarios, monkeypatch):
    monkeypatch.setattr(user_routes_module, "get_keycloak_admin_token", lambda: "token")
    monkeypatch.setattr(
        user_routes_module, "get_keycloak_user_by_id", lambda t, i: {"id": i, "username": "ana"}
    )
    _stub_user_orm(monkeypatch, [])
    _stub_role(monkeypatch)

    with app_usuarios.test_client() as cliente:
        respuesta = cliente.get("/users/edit/kc-1")
        mensajes = _mensajes_flash(cliente)

    assert respuesta.status_code == 302
    assert any("no está registrado en la base de datos" in mensaje for mensaje in mensajes)


def test_edit_user_get_prepara_roles_existentes(app_usuarios, capture_render, monkeypatch):
    capturado = capture_render(user_routes_module)
    rol = _RolFalso()
    monkeypatch.setattr(user_routes_module, "get_keycloak_admin_token", lambda: "token")
    monkeypatch.setattr(
        user_routes_module, "get_keycloak_user_by_id", lambda t, i: {"id": i, "username": "ana"}
    )
    _stub_user_orm(monkeypatch, [_UsuarioDB(ext_id="kc-1", admin=True, role=[rol])])
    _stub_role(monkeypatch, [rol])

    respuesta = app_usuarios.test_client().get("/users/edit/kc-1")

    assert respuesta.status_code == 200
    assert capturado["template"] == "user/edit.html"
    existentes = json.loads(capturado["context"]["existing_roles_json"])
    assert existentes[0]["name"] == "Analista"
    assert existentes[0]["actions"][0]["name"] == "FRONT_ADM"


def test_edit_user_post_actualiza_keycloak_y_mongo(app_usuarios, monkeypatch):
    rol_viejo = _RolFalso(role_id="r-viejo")
    usuario = _UsuarioDB(ext_id="kc-1", admin=False, role=[rol_viejo])
    monkeypatch.setattr(user_routes_module, "get_keycloak_admin_token", lambda: "token")
    monkeypatch.setattr(
        user_routes_module, "get_keycloak_user_by_id", lambda t, i: {"id": i, "username": "ana"}
    )
    _stub_user_orm(monkeypatch, [usuario])
    role_stub = _stub_role(monkeypatch, [rol_viejo])

    actualizaciones = {}

    def fake_update(token, user_id, datos):
        actualizaciones["datos"] = datos
        return True, None

    monkeypatch.setattr(user_routes_module, "update_keycloak_user", fake_update)

    datos = {
        "email": "nueva@example.com",
        "firstName": "Ana",
        "lastName": "Ruiz",
        "admin": "on",
        "roles_data": json.dumps(
            [{"name": "Editor", "actions": [{"name": "FRONT_FARMS", "options": ["UPDATE"]}]}]
        ),
    }

    respuesta = app_usuarios.test_client().post("/users/edit/kc-1", data=datos)

    assert respuesta.status_code == 302
    assert actualizaciones["datos"]["email"] == "nueva@example.com"
    assert usuario.admin is True
    assert usuario.saved is True
    assert role_stub.eliminados == ["r-viejo"]
    assert [r.name for r in role_stub.creados] == ["Editor"]
    assert usuario.role == role_stub.creados


def test_edit_user_post_informa_error_de_keycloak(app_usuarios, monkeypatch):
    usuario = _UsuarioDB(ext_id="kc-1")
    monkeypatch.setattr(user_routes_module, "get_keycloak_admin_token", lambda: "token")
    monkeypatch.setattr(
        user_routes_module, "get_keycloak_user_by_id", lambda t, i: {"id": i, "username": "ana"}
    )
    _stub_user_orm(monkeypatch, [usuario])
    _stub_role(monkeypatch)
    monkeypatch.setattr(
        user_routes_module, "update_keycloak_user", lambda t, i, d: (False, "correo inválido")
    )

    with app_usuarios.test_client() as cliente:
        respuesta = cliente.post("/users/edit/kc-1", data={"email": "mal"})
        mensajes = _mensajes_flash(cliente)

    assert respuesta.status_code == 302
    assert any("correo inválido" in mensaje for mensaje in mensajes)
    assert usuario.saved is False


# ---------------------------------------------------------------------------
# update_password
# ---------------------------------------------------------------------------

def test_update_password_rechaza_contrasenas_que_no_coinciden(app_usuarios):
    with app_usuarios.test_client() as cliente:
        respuesta = cliente.post(
            "/users/password/kc-1",
            data={"new_password": "Clave1", "confirm_password": "Clave2"},
        )
        mensajes = _mensajes_flash(cliente)

    assert respuesta.status_code == 302
    assert any("no coinciden" in mensaje for mensaje in mensajes)


def test_update_password_rechaza_contrasena_vacia(app_usuarios):
    with app_usuarios.test_client() as cliente:
        respuesta = cliente.post(
            "/users/password/kc-1", data={"new_password": "", "confirm_password": ""}
        )
        mensajes = _mensajes_flash(cliente)

    assert respuesta.status_code == 302
    assert any("no coinciden" in mensaje for mensaje in mensajes)


def test_update_password_actualiza_correctamente(app_usuarios, monkeypatch):
    llamadas = {}
    monkeypatch.setattr(user_routes_module, "get_keycloak_admin_token", lambda: "token")

    def fake_update(token, user_id, password):
        llamadas["password"] = password
        return True, None

    monkeypatch.setattr(user_routes_module, "update_keycloak_password", fake_update)

    with app_usuarios.test_client() as cliente:
        respuesta = cliente.post(
            "/users/password/kc-1",
            data={"new_password": "Clave1", "confirm_password": "Clave1"},
        )
        mensajes = _mensajes_flash(cliente)

    assert respuesta.status_code == 302
    assert llamadas["password"] == "Clave1"
    assert "Contraseña actualizada exitosamente." in mensajes


def test_update_password_informa_error(app_usuarios, monkeypatch):
    monkeypatch.setattr(user_routes_module, "get_keycloak_admin_token", lambda: "token")
    monkeypatch.setattr(
        user_routes_module, "update_keycloak_password", lambda t, i, p: (False, "muy corta")
    )

    with app_usuarios.test_client() as cliente:
        respuesta = cliente.post(
            "/users/password/kc-1",
            data={"new_password": "1", "confirm_password": "1"},
        )
        mensajes = _mensajes_flash(cliente)

    assert respuesta.status_code == 302
    assert any("muy corta" in mensaje for mensaje in mensajes)


# ---------------------------------------------------------------------------
# delete_user
# ---------------------------------------------------------------------------

def test_delete_user_elimina_en_keycloak_y_mongo(app_usuarios, monkeypatch):
    rol = _RolFalso(role_id="r1")
    usuario = _UsuarioDB(ext_id="kc-1", role=[rol])
    monkeypatch.setattr(user_routes_module, "get_keycloak_admin_token", lambda: "token")
    monkeypatch.setattr(user_routes_module, "delete_keycloak_user", lambda t, i: (True, None))
    _stub_user_orm(monkeypatch, [usuario])
    role_stub = _stub_role(monkeypatch, [rol])

    with app_usuarios.test_client() as cliente:
        respuesta = cliente.post("/users/delete/kc-1")
        mensajes = _mensajes_flash(cliente)

    assert respuesta.status_code == 302
    assert usuario.deleted is True
    assert role_stub.eliminados == ["r1"]
    assert "Usuario eliminado exitosamente." in mensajes


def test_delete_user_no_borra_en_mongo_si_falla_keycloak(app_usuarios, monkeypatch):
    usuario = _UsuarioDB(ext_id="kc-1")
    monkeypatch.setattr(user_routes_module, "get_keycloak_admin_token", lambda: "token")
    monkeypatch.setattr(
        user_routes_module, "delete_keycloak_user", lambda t, i: (False, "prohibido")
    )
    _stub_user_orm(monkeypatch, [usuario])
    _stub_role(monkeypatch)

    with app_usuarios.test_client() as cliente:
        respuesta = cliente.post("/users/delete/kc-1")
        mensajes = _mensajes_flash(cliente)

    assert respuesta.status_code == 302
    assert usuario.deleted is False
    assert any("prohibido" in mensaje for mensaje in mensajes)


def test_delete_user_sin_token_no_elimina(app_usuarios, monkeypatch):
    usuario = _UsuarioDB(ext_id="kc-1")
    monkeypatch.setattr(user_routes_module, "get_keycloak_admin_token", lambda: None)
    _stub_user_orm(monkeypatch, [usuario])

    with app_usuarios.test_client() as cliente:
        respuesta = cliente.post("/users/delete/kc-1")
        mensajes = _mensajes_flash(cliente)

    assert respuesta.status_code == 302
    assert usuario.deleted is False
    assert "No se pudo conectar con Keycloak." in mensajes
