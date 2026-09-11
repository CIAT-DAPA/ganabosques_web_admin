"""Pruebas de las vistas de configuración de fuentes de datos."""

from types import SimpleNamespace

import pytest

import src.routes.configuration_routes as configuration_module
from helpers import FakeQuerySet

OBJECT_ID_VALIDO = "507f1f77bcf86cd799439011"


class _Log:
    def __init__(self, enable=True):
        self.enable = enable


class _Configuracion:
    def __init__(self, name="SMBYC", url="https://datos.example.com", extension=".tiff", log=None):
        self.id = OBJECT_ID_VALIDO
        self.name = name
        self.parameters = [
            SimpleNamespace(key="url", value=url),
            SimpleNamespace(key="extension", value=extension),
        ]
        self.log = log
        self.saved = False
        self.deleted = False

    def save(self):
        self.saved = True
        return self

    def delete(self):
        self.deleted = True
        return self


def _stub_configuration(monkeypatch, existentes=(), get_falla=False, save_falla=None):
    creados = []
    existentes = list(existentes)

    queryset = FakeQuerySet(existentes)

    class Manager:
        def __call__(self, **kwargs):
            return queryset

        @staticmethod
        def get(**kwargs):
            if get_falla or not existentes:
                raise LookupError("no encontrado")
            return existentes[0]

    class ConfigurationStub:
        objects = Manager()

        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.saved = False
            for clave, valor in kwargs.items():
                setattr(self, clave, valor)
            creados.append(self)

        def save(self):
            if save_falla is not None:
                raise save_falla
            self.saved = True
            return self

    ConfigurationStub.creados = creados
    monkeypatch.setattr(configuration_module, "Configuration", ConfigurationStub)
    return ConfigurationStub


def _mensajes_flash(cliente):
    with cliente.session_transaction() as sesion:
        return [mensaje for _, mensaje in sesion.get("_flashes", [])]


@pytest.fixture()
def app_configuracion(make_app):
    return make_app(configuration_module.configuration_bp)


# ---------------------------------------------------------------------------
# list_configuration
# ---------------------------------------------------------------------------

def test_list_configuration_renderiza(app_configuracion, capture_render, monkeypatch):
    capturado = capture_render(configuration_module)
    _stub_configuration(monkeypatch, [_Configuracion()])

    respuesta = app_configuracion.test_client().get("/configuration/")

    assert respuesta.status_code == 200
    assert capturado["template"] == "configuration/list.html"
    assert "form" in capturado["context"]
    assert len(list(capturado["context"]["configurations"])) == 1


def test_list_configuration_filtra_por_busqueda(app_configuracion, capture_render, monkeypatch):
    capture_render(configuration_module)
    stub = _stub_configuration(monkeypatch, [_Configuracion()])

    app_configuracion.test_client().get("/configuration/?q=SMBYC")

    queryset = stub.objects()
    assert queryset.filter_calls
    filtro = queryset.filter_calls[0][1]["__raw__"]
    assert filtro["$or"][0]["name"]["$regex"] == "SMBYC"


def test_list_configuration_crea_con_dos_parametros(app_configuracion, capture_render, monkeypatch):
    capture_render(configuration_module)
    stub = _stub_configuration(monkeypatch)

    datos = {
        "name": "NAD",
        "url": "https://nad.example.com/datos",
        "extension": ".img",
        "enable": "y",
    }
    with app_configuracion.test_client() as cliente:
        respuesta = cliente.post("/configuration/", data=datos)
        mensajes = _mensajes_flash(cliente)

    assert respuesta.status_code == 302
    assert len(stub.creados) == 1
    creado = stub.creados[0]
    assert creado.kwargs["name"] == "NAD"
    parametros = {p.key: p.value for p in creado.kwargs["parameters"]}
    assert parametros == {"url": "https://nad.example.com/datos", "extension": ".img"}
    assert "Configuración agregada correctamente." in mensajes


def test_list_configuration_rechaza_url_invalida(app_configuracion, capture_render, monkeypatch):
    capturado = capture_render(configuration_module)
    stub = _stub_configuration(monkeypatch)

    respuesta = app_configuracion.test_client().post(
        "/configuration/", data={"name": "NAD", "url": "no-es-url", "extension": ".img"}
    )

    assert respuesta.status_code == 200
    assert stub.creados == []
    assert capturado["context"]["form"].url.errors


def test_list_configuration_informa_error_al_guardar(app_configuracion, capture_render, monkeypatch):
    capture_render(configuration_module)
    _stub_configuration(monkeypatch, save_falla=RuntimeError("Mongo caído"))

    datos = {"name": "NAD", "url": "https://nad.example.com", "extension": ".img"}
    with app_configuracion.test_client() as cliente:
        respuesta = cliente.post("/configuration/", data=datos)
        mensajes = _mensajes_flash(cliente)

    assert respuesta.status_code == 200
    assert any("Error al guardar la configuración" in mensaje for mensaje in mensajes)


# ---------------------------------------------------------------------------
# edit_configuration
# ---------------------------------------------------------------------------

def test_edit_configuration_precarga_los_parametros(app_configuracion, capture_render, monkeypatch):
    capturado = capture_render(configuration_module)
    configuracion = _Configuracion(
        name="SMBYC", url="https://smbyc.example.com", extension=".tiff", log=_Log(enable=False)
    )
    _stub_configuration(monkeypatch, [configuracion])

    respuesta = app_configuracion.test_client().get(f"/configuration/edit/{OBJECT_ID_VALIDO}")

    assert respuesta.status_code == 200
    assert capturado["template"] == "configuration/edit.html"
    formulario = capturado["context"]["form"]
    assert formulario.name.data == "SMBYC"
    assert formulario.url.data == "https://smbyc.example.com"
    assert formulario.extension.data == ".tiff"
    assert formulario.enable.data is False


def test_edit_configuration_guarda_los_cambios(app_configuracion, capture_render, monkeypatch):
    capture_render(configuration_module)
    configuracion = _Configuracion(log=_Log(enable=True))
    _stub_configuration(monkeypatch, [configuracion])

    datos = {
        "name": "SMBYC v2",
        "url": "https://nuevo.example.com",
        "extension": ".img",
        "enable": "",
    }
    with app_configuracion.test_client() as cliente:
        respuesta = cliente.post(f"/configuration/edit/{OBJECT_ID_VALIDO}", data=datos)
        mensajes = _mensajes_flash(cliente)

    assert respuesta.status_code == 302
    assert configuracion.name == "SMBYC v2"
    assert {p.key: p.value for p in configuracion.parameters} == {
        "url": "https://nuevo.example.com",
        "extension": ".img",
    }
    assert configuracion.log.enable is False
    assert configuracion.saved is True
    assert "Configuración actualizada correctamente." in mensajes


def test_edit_configuration_crea_el_log_si_falta(app_configuracion, capture_render, monkeypatch):
    capture_render(configuration_module)
    configuracion = _Configuracion(log=None)
    _stub_configuration(monkeypatch, [configuracion])

    datos = {
        "name": "SMBYC",
        "url": "https://nuevo.example.com",
        "extension": ".img",
        "enable": "y",
    }
    app_configuracion.test_client().post(f"/configuration/edit/{OBJECT_ID_VALIDO}", data=datos)

    assert configuracion.log is not None
    assert configuracion.log.enable is True


# ---------------------------------------------------------------------------
# delete y reset
# ---------------------------------------------------------------------------

def test_delete_configuration_borra_definitivamente(app_configuracion, monkeypatch):
    configuracion = _Configuracion()
    _stub_configuration(monkeypatch, [configuracion])

    with app_configuracion.test_client() as cliente:
        respuesta = cliente.post(f"/configuration/delete/{OBJECT_ID_VALIDO}")
        mensajes = _mensajes_flash(cliente)

    assert respuesta.status_code == 302
    assert configuracion.deleted is True
    assert "Configuración eliminada permanentemente." in mensajes


def test_reset_configuration_rehabilita(app_configuracion, monkeypatch):
    configuracion = _Configuracion(log=_Log(enable=False))
    _stub_configuration(monkeypatch, [configuracion])

    with app_configuracion.test_client() as cliente:
        respuesta = cliente.post(f"/configuration/reset/{OBJECT_ID_VALIDO}")
        mensajes = _mensajes_flash(cliente)

    assert respuesta.status_code == 302
    assert configuracion.log.enable is True
    assert configuracion.saved is True
    assert "Configuración reactivada." in mensajes


def test_reset_configuration_crea_el_log_si_falta(app_configuracion, monkeypatch):
    configuracion = _Configuracion(log=None)
    _stub_configuration(monkeypatch, [configuracion])

    app_configuracion.test_client().post(f"/configuration/reset/{OBJECT_ID_VALIDO}")

    assert configuracion.log is not None
    assert configuracion.log.enable is True
