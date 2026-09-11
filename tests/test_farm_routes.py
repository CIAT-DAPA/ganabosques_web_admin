"""Pruebas de las vistas CRUD de fincas y su API de veredas."""

import sys
from types import SimpleNamespace

import pytest

import src.forms.farm_form as farm_form_module
import src.routes.farm_routes as farm_module
from helpers import FakeQuerySet

OBJECT_ID_VALIDO = "507f1f77bcf86cd799439011"
OTRO_OBJECT_ID = "507f1f77bcf86cd799439022"

GEOJSON = (
    '{"type": "FeatureCollection", "features": [{"type": "Feature", '
    '"geometry": {"type": "Polygon", "coordinates": '
    '[[[-74.0,4.0],[-74.0,4.01],[-73.99,4.01],[-73.99,4.0],[-74.0,4.0]]]}, '
    '"properties": {}}]}'
)


class _Log:
    def __init__(self, enable=True):
        self.enable = enable
        self.updated = None


class _Adm1:
    def __init__(self, doc_id=OBJECT_ID_VALIDO, name="ANTIOQUIA"):
        self.id = doc_id
        self.name = name


class _Adm2:
    def __init__(self, doc_id=OBJECT_ID_VALIDO, name="MEDELLIN", adm1_id=None):
        self.id = doc_id
        self.name = name
        self.adm1_id = adm1_id


class _Adm3:
    def __init__(self, doc_id=OBJECT_ID_VALIDO, name="EL PORVENIR", adm2_id=None):
        self.id = doc_id
        self.name = name
        self.adm2_id = adm2_id


class _Finca:
    def __init__(self, adm3_id=None, log=None, ext_id=None):
        from ganabosques_orm.enums.farmsource import FarmSource
        from ganabosques_orm.enums.source import Source
        from ganabosques_orm.enums.valuechain import ValueChain

        self.id = OBJECT_ID_VALIDO
        self.adm3_id = adm3_id
        self.farm_source = FarmSource.GEOFARMER
        self.value_chain = ValueChain.LIVESTOCK
        self.ext_id = ext_id if ext_id is not None else [
            SimpleNamespace(source=Source.SIT_CODE, ext_code="ABC123")
        ]
        self.log = log
        self.saved = False

    def save(self):
        self.saved = True
        return self


def _stub_farm(monkeypatch, existentes=(), get_falla=False):
    creados = []
    existentes = list(existentes)
    queryset = FakeQuerySet(existentes)

    class Manager:
        def __call__(self, **kwargs):
            return queryset

        @staticmethod
        def get(**kwargs):
            if get_falla or not existentes:
                raise LookupError("no encontrada")
            return existentes[0]

    class FarmStub:
        objects = Manager()

        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.saved = False
            creados.append(self)

        def save(self):
            self.saved = True
            return self

    FarmStub.creados = creados
    FarmStub.queryset = queryset
    monkeypatch.setattr(farm_module, "Farm", FarmStub)
    return FarmStub


def _stub_adm(monkeypatch, veredas=(), municipios=(), departamentos=()):
    veredas = list(veredas)

    class ManagerAdm3:
        def __call__(self, **kwargs):
            return FakeQuerySet(veredas)

        def order_by(self, *args):
            return FakeQuerySet(veredas)

    class Adm3Stub:
        objects = ManagerAdm3()

    class ManagerAdm2:
        def __call__(self, **kwargs):
            return FakeQuerySet(list(municipios))

    class Adm2Stub:
        objects = ManagerAdm2()

    class ManagerAdm1:
        def __call__(self, **kwargs):
            return FakeQuerySet(list(departamentos))

        def order_by(self, *args):
            return FakeQuerySet(list(departamentos))

    class Adm1Stub:
        objects = ManagerAdm1()

    monkeypatch.setattr(farm_module, "Adm3", Adm3Stub)
    monkeypatch.setattr(farm_module, "Adm2", Adm2Stub)
    monkeypatch.setattr(farm_module, "Adm1", Adm1Stub)
    monkeypatch.setattr(farm_form_module, "Adm3", Adm3Stub)
    return Adm3Stub


def _stub_polygons(monkeypatch, poligono_actual=None):
    class ManagerPoly:
        def __call__(self, **kwargs):
            return FakeQuerySet([poligono_actual] if poligono_actual else [])

    class FarmPolygonsStub:
        objects = ManagerPoly()

    monkeypatch.setattr(farm_module, "FarmPolygons", FarmPolygonsStub)

    llamadas = []

    class ServicioFalso:
        @staticmethod
        def save_new_version(farm, geojson_text, current):
            llamadas.append({"farm": farm, "geojson": geojson_text, "current": current})

    monkeypatch.setattr(farm_module, "FarmPolygonService", ServicioFalso)
    return llamadas


def _mensajes_flash(cliente):
    with cliente.session_transaction() as sesion:
        return [mensaje for _, mensaje in sesion.get("_flashes", [])]


def _payload(**overrides):
    from ganabosques_orm.enums.farmsource import FarmSource
    from ganabosques_orm.enums.source import Source
    from ganabosques_orm.enums.valuechain import ValueChain

    datos = {
        "adm3_id": OBJECT_ID_VALIDO,
        "ext_id-0-source": Source.SIT_CODE.name,
        "ext_id-0-ext_code": "ABC123",
        "farm_source": FarmSource.GEOFARMER.name,
        "value_chain": ValueChain.LIVESTOCK.name,
        "geojson": GEOJSON,
        "enable": "y",
    }
    datos.update(overrides)
    return datos


@pytest.fixture()
def app_fincas(make_app):
    return make_app(farm_module.farm_bp)


# ---------------------------------------------------------------------------
# API de veredas por municipio
# ---------------------------------------------------------------------------

def test_api_adm3_by_adm2_devuelve_json(app_fincas, monkeypatch):
    _stub_adm(monkeypatch, [_Adm3(doc_id="v1", name="EL PORVENIR"), _Adm3(doc_id="v2", name="LA UNION")])

    respuesta = app_fincas.test_client().get(f"/api/adm3-by-adm2/{OBJECT_ID_VALIDO}")

    assert respuesta.status_code == 200
    assert respuesta.get_json() == [
        {"id": "v1", "name": "EL PORVENIR"},
        {"id": "v2", "name": "LA UNION"},
    ]


def test_api_adm3_by_adm2_sin_resultados(app_fincas, monkeypatch):
    _stub_adm(monkeypatch, [])

    respuesta = app_fincas.test_client().get(f"/api/adm3-by-adm2/{OBJECT_ID_VALIDO}")

    assert respuesta.get_json() == []


# ---------------------------------------------------------------------------
# list_farms
# ---------------------------------------------------------------------------

def test_list_farms_renderiza_con_paginacion(app_fincas, capture_render, monkeypatch):
    capturado = capture_render(farm_module)
    stub = _stub_farm(monkeypatch, [_Finca() for _ in range(60)])
    _stub_adm(monkeypatch, [_Adm3()], departamentos=[_Adm1()])

    respuesta = app_fincas.test_client().get("/farm?page=2")

    assert respuesta.status_code == 200
    assert capturado["template"] == "farm/list.html"
    assert capturado["context"]["total"] == 60
    assert capturado["context"]["total_pages"] == 2
    assert stub.queryset.skip_calls == [50]


def test_list_farms_filtra_por_codigo_y_vereda(app_fincas, capture_render, monkeypatch):
    capture_render(farm_module)
    stub = _stub_farm(monkeypatch, [_Finca()])
    _stub_adm(monkeypatch, [_Adm3()], departamentos=[_Adm1()])

    app_fincas.test_client().get("/farm?q=ABC")

    filtro = stub.queryset.filter_calls[0][1]["__raw__"]
    campos = [list(condicion.keys())[0] for condicion in filtro["$or"]]
    assert campos == ["ext_id.ext_code", "adm3_id.name"]


def test_list_farms_crea_una_finca(app_fincas, capture_render, monkeypatch):
    capture_render(farm_module)
    stub = _stub_farm(monkeypatch)
    vereda = _Adm3()
    _stub_adm(monkeypatch, [vereda], departamentos=[_Adm1()])

    with app_fincas.test_client() as cliente:
        respuesta = cliente.post("/farm", data=_payload())
        mensajes = _mensajes_flash(cliente)

    assert respuesta.status_code == 302
    assert len(stub.creados) == 1
    creado = stub.creados[0]
    assert creado.kwargs["adm3_id"] is vereda
    assert creado.kwargs["ext_id"][0].ext_code == "ABC123"
    assert "Finca creada correctamente." in mensajes


def test_list_farms_no_crea_sin_geojson(app_fincas, capture_render, monkeypatch):
    capturado = capture_render(farm_module)
    stub = _stub_farm(monkeypatch)
    _stub_adm(monkeypatch, [_Adm3()], departamentos=[_Adm1()])

    respuesta = app_fincas.test_client().post("/farm", data=_payload(geojson=""))

    assert respuesta.status_code == 200
    assert stub.creados == []
    assert capturado["context"]["form"].geojson.errors


def test_list_farms_expone_los_enums_al_template(app_fincas, capture_render, monkeypatch):
    capturado = capture_render(farm_module)
    _stub_farm(monkeypatch, [_Finca()])
    _stub_adm(monkeypatch, [_Adm3()], departamentos=[_Adm1()])

    app_fincas.test_client().get("/farm")

    nombres = [s["name"] for s in capturado["context"]["source_enum"]]
    assert "SIT_CODE" in nombres
    assert capturado["context"]["farm_sources"] is not None


# ---------------------------------------------------------------------------
# edit_farm
# ---------------------------------------------------------------------------

def test_edit_farm_redirige_si_no_existe(app_fincas, monkeypatch):
    _stub_farm(monkeypatch, [])
    _stub_adm(monkeypatch, [_Adm3()], departamentos=[_Adm1()])

    with app_fincas.test_client() as cliente:
        respuesta = cliente.get(f"/farm/edit/{OBJECT_ID_VALIDO}")
        mensajes = _mensajes_flash(cliente)

    assert respuesta.status_code == 302
    assert "Finca no encontrada." in mensajes


def test_edit_farm_precarga_datos_y_geojson(app_fincas, capture_render, monkeypatch):
    capturado = capture_render(farm_module)
    departamento = _Adm1(doc_id=OTRO_OBJECT_ID)
    municipio = _Adm2(doc_id=OTRO_OBJECT_ID, adm1_id=departamento)
    vereda = _Adm3(adm2_id=municipio)
    finca = _Finca(adm3_id=vereda, log=_Log(enable=False))
    _stub_farm(monkeypatch, [finca])
    _stub_adm(monkeypatch, [vereda], departamentos=[departamento])
    _stub_polygons(monkeypatch, SimpleNamespace(geojson=GEOJSON))

    respuesta = app_fincas.test_client().get(f"/farm/edit/{OBJECT_ID_VALIDO}")

    assert respuesta.status_code == 200
    assert capturado["template"] == "farm/edit.html"
    formulario = capturado["context"]["form"]
    assert formulario.geojson.data == GEOJSON
    assert formulario.enable.data is False
    assert len(formulario.ext_id.entries) == 1
    assert formulario.ext_id.entries[0].form.ext_code.data == "ABC123"
    assert capturado["context"]["selected_adm1_id"] == OTRO_OBJECT_ID
    assert capturado["context"]["selected_adm2_id"] == OTRO_OBJECT_ID


def test_edit_farm_guarda_y_versiona_el_poligono(app_fincas, capture_render, monkeypatch):
    capture_render(farm_module)
    vereda = _Adm3()
    finca = _Finca(adm3_id=vereda, log=_Log(enable=True))
    _stub_farm(monkeypatch, [finca])
    _stub_adm(monkeypatch, [vereda], departamentos=[_Adm1()])
    poligono_actual = SimpleNamespace(geojson=GEOJSON)
    llamadas = _stub_polygons(monkeypatch, poligono_actual)

    with app_fincas.test_client() as cliente:
        respuesta = cliente.post(
            f"/farm/edit/{OBJECT_ID_VALIDO}", data=_payload(**{"ext_id-0-ext_code": "NUEVO"})
        )
        mensajes = _mensajes_flash(cliente)

    assert respuesta.status_code == 302
    assert finca.saved is True
    assert finca.ext_id[0].ext_code == "NUEVO"
    assert finca.log.updated is not None
    assert len(llamadas) == 1
    assert llamadas[0]["current"] is poligono_actual
    assert "Finca actualizada correctamente." in mensajes


def test_edit_farm_informa_error_del_servicio_de_poligonos(
    app_fincas, capture_render, monkeypatch
):
    capture_render(farm_module)
    vereda = _Adm3()
    finca = _Finca(adm3_id=vereda, log=_Log())
    _stub_farm(monkeypatch, [finca])
    _stub_adm(monkeypatch, [vereda], departamentos=[_Adm1()])
    _stub_polygons(monkeypatch)

    class ServicioQueFalla:
        @staticmethod
        def save_new_version(farm, geojson_text, current):
            raise ValueError("Solo se permiten Polygon o MultiPolygon.")

    monkeypatch.setattr(farm_module, "FarmPolygonService", ServicioQueFalla)

    with app_fincas.test_client() as cliente:
        respuesta = cliente.post(f"/farm/edit/{OBJECT_ID_VALIDO}", data=_payload())
        mensajes = _mensajes_flash(cliente)

    assert respuesta.status_code == 200
    assert finca.saved is False
    assert any("Solo se permiten Polygon" in mensaje for mensaje in mensajes)


def test_edit_farm_crea_el_log_si_falta(app_fincas, capture_render, monkeypatch):
    capture_render(farm_module)
    vereda = _Adm3()
    finca = _Finca(adm3_id=vereda, log=None)
    _stub_farm(monkeypatch, [finca])
    _stub_adm(monkeypatch, [vereda], departamentos=[_Adm1()])
    _stub_polygons(monkeypatch)

    app_fincas.test_client().post(f"/farm/edit/{OBJECT_ID_VALIDO}", data=_payload())

    assert finca.log is not None
    assert finca.log.enable is True


def test_edit_farm_sin_vereda_asociada(app_fincas, capture_render, monkeypatch):
    capturado = capture_render(farm_module)
    finca = _Finca(adm3_id=None, log=_Log())
    _stub_farm(monkeypatch, [finca])
    _stub_adm(monkeypatch, [_Adm3()], departamentos=[_Adm1()])
    _stub_polygons(monkeypatch)

    app_fincas.test_client().get(f"/farm/edit/{OBJECT_ID_VALIDO}")

    assert capturado["context"]["selected_adm3_id"] == ""
    assert capturado["context"]["selected_adm1_id"] == ""


# ---------------------------------------------------------------------------
# delete y reset
# ---------------------------------------------------------------------------

def test_delete_farm_deshabilita(app_fincas, monkeypatch):
    finca = _Finca(log=_Log(enable=True))
    _stub_farm(monkeypatch, [finca])

    with app_fincas.test_client() as cliente:
        respuesta = cliente.get(f"/farm/delete/{OBJECT_ID_VALIDO}")
        mensajes = _mensajes_flash(cliente)

    assert respuesta.status_code == 302
    assert finca.log.enable is False
    assert finca.saved is True
    assert "Finca deshabilitada." in mensajes


def test_delete_farm_avisa_si_no_existe(app_fincas, monkeypatch):
    _stub_farm(monkeypatch, [])

    with app_fincas.test_client() as cliente:
        respuesta = cliente.get(f"/farm/delete/{OBJECT_ID_VALIDO}")
        mensajes = _mensajes_flash(cliente)

    assert respuesta.status_code == 302
    assert "Finca no encontrada." in mensajes


def test_reset_farm_rehabilita(app_fincas, monkeypatch):
    finca = _Finca(log=_Log(enable=False))
    _stub_farm(monkeypatch, [finca])

    with app_fincas.test_client() as cliente:
        respuesta = cliente.get(f"/farm/reset/{OBJECT_ID_VALIDO}")
        mensajes = _mensajes_flash(cliente)

    assert respuesta.status_code == 302
    assert finca.log.enable is True
    assert "Finca reactivada." in mensajes


def test_reset_farm_crea_el_log_si_falta(app_fincas, monkeypatch):
    finca = _Finca(log=None)
    _stub_farm(monkeypatch, [finca])

    app_fincas.test_client().get(f"/farm/reset/{OBJECT_ID_VALIDO}")

    assert finca.log is not None
    assert finca.log.enable is True
