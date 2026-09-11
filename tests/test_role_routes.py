"""Pruebas de la gestión de roles y permisos."""

import json
from types import SimpleNamespace

import pytest

import src.routes.role_routes as role_module

OBJECT_ID_VALIDO = "507f1f77bcf86cd799439011"


def _permiso(action_name, option_names):
    from ganabosques_orm.enums.actions import Actions
    from ganabosques_orm.enums.options import Options

    return SimpleNamespace(
        action=Actions[action_name],
        options=[Options[nombre] for nombre in option_names],
    )


class _Rol:
    def __init__(self, role_id=OBJECT_ID_VALIDO, name="Analista", actions=None):
        self.id = role_id
        self.name = name
        self.actions = actions if actions is not None else [_permiso("FRONT_ADM", ["READ"])]
        self.saved = False
        self.deleted = False

    def save(self):
        self.saved = True
        return self

    def delete(self):
        self.deleted = True
        return self


def _stub_role(monkeypatch, roles=(), get_falla=False):
    creados = []
    roles = list(roles)

    class Manager:
        def __call__(self, **kwargs):
            return roles

        def __iter__(self):
            return iter(roles)

        @staticmethod
        def get(**kwargs):
            if get_falla or not roles:
                raise LookupError("Rol no encontrado")
            return roles[0]

    class RoleStub:
        objects = Manager()

        def __init__(self, name=None, actions=None):
            self.name = name
            self.actions = actions or []
            self.id = f"nuevo-{len(creados)}"
            self.saved = False
            creados.append(self)

        def save(self):
            self.saved = True
            return self

    RoleStub.creados = creados
    monkeypatch.setattr(role_module, "Role", RoleStub)
    return RoleStub


def _mensajes_flash(cliente):
    with cliente.session_transaction() as sesion:
        return [mensaje for _, mensaje in sesion.get("_flashes", [])]


@pytest.fixture()
def app_roles(make_app):
    return make_app(role_module.role_bp)


# ---------------------------------------------------------------------------
# list_roles
# ---------------------------------------------------------------------------

def test_list_roles_expone_roles_y_enums(app_roles, capture_render, monkeypatch):
    capturado = capture_render(role_module)
    _stub_role(monkeypatch, [_Rol()])

    respuesta = app_roles.test_client().get("/roles/")

    assert respuesta.status_code == 200
    assert capturado["template"] == "role/list.html"
    assert capturado["context"]["active_page"] == "roles"
    roles = capturado["context"]["roles"]
    assert roles[0]["name"] == "Analista"
    assert roles[0]["actions"][0]["name"] == "FRONT_ADM"
    assert roles[0]["actions"][0]["label"] == "front_adm"
    assert roles[0]["actions"][0]["options"] == ["read"]
    assert any(a["name"] == "API_FARMS" for a in capturado["context"]["actions_enum"])


def test_list_roles_usa_un_nombre_por_defecto(app_roles, capture_render, monkeypatch):
    capturado = capture_render(role_module)
    _stub_role(monkeypatch, [_Rol(name=None, actions=[])])

    app_roles.test_client().get("/roles/")

    assert capturado["context"]["roles"][0]["name"] == "Sin nombre"
    assert capturado["context"]["roles"][0]["actions"] == []


def test_list_roles_con_coleccion_vacia(app_roles, capture_render, monkeypatch):
    capturado = capture_render(role_module)
    _stub_role(monkeypatch, [])

    app_roles.test_client().get("/roles/")

    assert capturado["context"]["roles"] == []


# ---------------------------------------------------------------------------
# create_role
# ---------------------------------------------------------------------------

def test_create_role_guarda_nombre_y_permisos(app_roles, monkeypatch):
    stub = _stub_role(monkeypatch)
    acciones = json.dumps([{"name": "FRONT_FARMS", "options": ["CREATE", "READ"]}])

    with app_roles.test_client() as cliente:
        respuesta = cliente.post(
            "/roles/create", data={"name": "Editor", "actions_data": acciones}
        )
        mensajes = _mensajes_flash(cliente)

    assert respuesta.status_code == 302
    assert len(stub.creados) == 1
    creado = stub.creados[0]
    assert creado.name == "Editor"
    assert creado.saved is True
    assert len(creado.actions) == 1
    assert len(creado.actions[0].options) == 2
    assert any('Rol "Editor" creado' in mensaje for mensaje in mensajes)


def test_create_role_exige_nombre(app_roles, monkeypatch):
    stub = _stub_role(monkeypatch)

    with app_roles.test_client() as cliente:
        respuesta = cliente.post("/roles/create", data={"name": "   "})
        mensajes = _mensajes_flash(cliente)

    assert respuesta.status_code == 302
    assert stub.creados == []
    assert "El nombre del rol es obligatorio." in mensajes


def test_create_role_tolera_json_invalido(app_roles, monkeypatch):
    stub = _stub_role(monkeypatch)

    respuesta = app_roles.test_client().post(
        "/roles/create", data={"name": "Editor", "actions_data": "{no es json"}
    )

    assert respuesta.status_code == 302
    assert stub.creados[0].actions == []


def test_create_role_descarta_acciones_y_opciones_desconocidas(app_roles, monkeypatch):
    stub = _stub_role(monkeypatch)
    acciones = json.dumps(
        [
            {"name": "NO_EXISTE", "options": ["READ"]},
            {"name": "API_ADM", "options": ["READ", "NO_EXISTE"]},
        ]
    )

    app_roles.test_client().post("/roles/create", data={"name": "Editor", "actions_data": acciones})

    creado = stub.creados[0]
    assert len(creado.actions) == 1
    assert len(creado.actions[0].options) == 1


def test_create_role_sin_acciones(app_roles, monkeypatch):
    stub = _stub_role(monkeypatch)

    app_roles.test_client().post("/roles/create", data={"name": "Solo lectura"})

    assert stub.creados[0].actions == []


# ---------------------------------------------------------------------------
# get_role
# ---------------------------------------------------------------------------

def test_get_role_devuelve_json(app_roles, monkeypatch):
    _stub_role(monkeypatch, [_Rol()])

    respuesta = app_roles.test_client().get(f"/roles/get/{OBJECT_ID_VALIDO}")

    assert respuesta.status_code == 200
    datos = respuesta.get_json()
    assert datos["name"] == "Analista"
    assert datos["actions"][0]["name"] == "FRONT_ADM"
    assert datos["actions"][0]["options"] == ["READ"]


def test_get_role_responde_404_si_no_existe(app_roles, monkeypatch):
    _stub_role(monkeypatch, [], get_falla=True)

    respuesta = app_roles.test_client().get(f"/roles/get/{OBJECT_ID_VALIDO}")

    assert respuesta.status_code == 404
    assert respuesta.get_json() == {"error": "Rol no encontrado"}


def test_get_role_responde_404_con_identificador_invalido(app_roles, monkeypatch):
    _stub_role(monkeypatch, [_Rol()])

    respuesta = app_roles.test_client().get("/roles/get/no-es-un-objectid")

    assert respuesta.status_code == 404


def test_get_role_sin_acciones(app_roles, monkeypatch):
    _stub_role(monkeypatch, [_Rol(actions=[])])

    respuesta = app_roles.test_client().get(f"/roles/get/{OBJECT_ID_VALIDO}")

    assert respuesta.get_json()["actions"] == []


# ---------------------------------------------------------------------------
# edit_role
# ---------------------------------------------------------------------------

def test_edit_role_actualiza_nombre_y_permisos(app_roles, monkeypatch):
    rol = _Rol()
    _stub_role(monkeypatch, [rol])
    acciones = json.dumps([{"name": "API_ENTERPRISE", "options": ["DELETE"]}])

    with app_roles.test_client() as cliente:
        respuesta = cliente.post(
            f"/roles/edit/{OBJECT_ID_VALIDO}",
            data={"name": "Editor senior", "actions_data": acciones},
        )
        mensajes = _mensajes_flash(cliente)

    assert respuesta.status_code == 302
    assert rol.name == "Editor senior"
    assert rol.saved is True
    assert len(rol.actions) == 1
    assert any("actualizado exitosamente" in mensaje for mensaje in mensajes)


def test_edit_role_avisa_si_no_existe(app_roles, monkeypatch):
    _stub_role(monkeypatch, [], get_falla=True)

    with app_roles.test_client() as cliente:
        respuesta = cliente.post(f"/roles/edit/{OBJECT_ID_VALIDO}", data={"name": "X"})
        mensajes = _mensajes_flash(cliente)

    assert respuesta.status_code == 302
    assert "Rol no encontrado." in mensajes


def test_edit_role_exige_nombre(app_roles, monkeypatch):
    rol = _Rol()
    _stub_role(monkeypatch, [rol])

    with app_roles.test_client() as cliente:
        respuesta = cliente.post(f"/roles/edit/{OBJECT_ID_VALIDO}", data={"name": ""})
        mensajes = _mensajes_flash(cliente)

    assert respuesta.status_code == 302
    assert rol.saved is False
    assert "El nombre del rol es obligatorio." in mensajes


def test_edit_role_tolera_json_invalido(app_roles, monkeypatch):
    rol = _Rol()
    _stub_role(monkeypatch, [rol])

    app_roles.test_client().post(
        f"/roles/edit/{OBJECT_ID_VALIDO}", data={"name": "Editor", "actions_data": "[["}
    )

    assert rol.actions == []


# ---------------------------------------------------------------------------
# delete_role
# ---------------------------------------------------------------------------

def test_delete_role_elimina(app_roles, monkeypatch):
    rol = _Rol()
    _stub_role(monkeypatch, [rol])

    with app_roles.test_client() as cliente:
        respuesta = cliente.post(f"/roles/delete/{OBJECT_ID_VALIDO}")
        mensajes = _mensajes_flash(cliente)

    assert respuesta.status_code == 302
    assert rol.deleted is True
    assert any('Rol "Analista" eliminado' in mensaje for mensaje in mensajes)


def test_delete_role_informa_error(app_roles, monkeypatch):
    _stub_role(monkeypatch, [], get_falla=True)

    with app_roles.test_client() as cliente:
        respuesta = cliente.post(f"/roles/delete/{OBJECT_ID_VALIDO}")
        mensajes = _mensajes_flash(cliente)

    assert respuesta.status_code == 302
    assert "Error al eliminar el rol." in mensajes
