"""Pruebas de las vistas CRUD de empresas."""

import sys
from types import SimpleNamespace

import pytest

import src.routes.enterprise_routes as enterprise_module
from helpers import FakeQuerySet

# La vista importa el formulario como ``forms.enterprise_form`` (sin el prefijo
# ``src.``), de modo que es un módulo distinto en sys.modules: hay que parchear
# ese mismo para que ``load_adm2_choices`` use los dobles.
enterprise_form_module = sys.modules[enterprise_module.EnterpriseForm.__module__]

OBJECT_ID_VALIDO = "507f1f77bcf86cd799439011"
OTRO_OBJECT_ID = "507f1f77bcf86cd799439022"


class _Log:
    def __init__(self, enable=True):
        self.enable = enable


class _Adm1:
    def __init__(self, doc_id=OBJECT_ID_VALIDO, name="ANTIOQUIA"):
        self.id = doc_id
        self.name = name


class _Adm2:
    def __init__(self, doc_id=OBJECT_ID_VALIDO, name="MEDELLIN", adm1_id=None):
        self.id = doc_id
        self.name = name
        self.adm1_id = adm1_id


class _Empresa:
    def __init__(self, name="Frigorífico", adm2_id=None, log=None, ext_id=None):
        from ganabosques_orm.enums.label import Label
        from ganabosques_orm.enums.typeenterprise import TypeEnterprise
        from ganabosques_orm.enums.valuechain import ValueChain

        self.id = OBJECT_ID_VALIDO
        self.name = name
        self.adm2_id = adm2_id
        self.type_enterprise = TypeEnterprise.SLAUGHTERHOUSE
        self.value_chain = ValueChain.LIVESTOCK
        self.latitude = 6.25
        self.longitud = -75.56
        self.ext_id = ext_id if ext_id is not None else [
            SimpleNamespace(label=list(Label)[0], ext_code="900123")
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


def _stub_enterprise(monkeypatch, existentes=(), get_falla=False):
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

    class EnterpriseStub:
        objects = Manager()

        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.saved = False
            creados.append(self)

        def save(self):
            self.saved = True
            return self

    EnterpriseStub.creados = creados
    EnterpriseStub.queryset = queryset
    monkeypatch.setattr(enterprise_module, "Enterprise", EnterpriseStub)
    return EnterpriseStub


def _stub_adm(monkeypatch, municipios=(), departamentos=(), adm2_get_falla=False):
    municipios = list(municipios)

    class ManagerAdm2:
        def __call__(self, **kwargs):
            return FakeQuerySet(municipios)

        @staticmethod
        def get(**kwargs):
            if adm2_get_falla or not municipios:
                raise LookupError("municipio no encontrado")
            return municipios[0]

    class Adm2Stub:
        objects = ManagerAdm2()

    class ManagerAdm1:
        def __call__(self, **kwargs):
            return FakeQuerySet(list(departamentos))

        def order_by(self, *args):
            return FakeQuerySet(list(departamentos))

    class Adm1Stub:
        objects = ManagerAdm1()

    monkeypatch.setattr(enterprise_module, "Adm2", Adm2Stub)
    monkeypatch.setattr(enterprise_module, "Adm1", Adm1Stub)
    monkeypatch.setattr(enterprise_form_module, "Adm2", Adm2Stub)
    return Adm2Stub


def _mensajes_flash(cliente):
    with cliente.session_transaction() as sesion:
        return [mensaje for _, mensaje in sesion.get("_flashes", [])]


def _payload(**overrides):
    from ganabosques_orm.enums.label import Label
    from ganabosques_orm.enums.typeenterprise import TypeEnterprise
    from ganabosques_orm.enums.valuechain import ValueChain

    datos = {
        "name": "Frigorífico del Norte",
        "ext_code": "900123456",
        "label": list(Label)[0].name,
        "adm2_id": OBJECT_ID_VALIDO,
        "type_enterprise": TypeEnterprise.SLAUGHTERHOUSE.name,
        "value_chain": ValueChain.LIVESTOCK.name,
        "latitude": "6.25",
        "longitud": "-75.56",
        "enable": "y",
    }
    datos.update(overrides)
    return datos


@pytest.fixture()
def app_empresas(make_app):
    return make_app(enterprise_module.enterprise_bp)


# ---------------------------------------------------------------------------
# list_enterprise
# ---------------------------------------------------------------------------

def test_list_enterprise_renderiza_con_paginacion(app_empresas, capture_render, monkeypatch):
    capturado = capture_render(enterprise_module)
    stub = _stub_enterprise(monkeypatch, [_Empresa() for _ in range(60)])
    _stub_adm(monkeypatch, [_Adm2()], [_Adm1()])

    respuesta = app_empresas.test_client().get("/enterprise?page=2")

    assert respuesta.status_code == 200
    assert capturado["template"] == "enterprise/list.html"
    assert capturado["context"]["total"] == 60
    assert capturado["context"]["total_pages"] == 2
    assert capturado["context"]["page"] == 2
    assert stub.queryset.skip_calls == [50]


def test_list_enterprise_filtra_por_nombre_codigo_y_municipio(
    app_empresas, capture_render, monkeypatch
):
    capture_render(enterprise_module)
    stub = _stub_enterprise(monkeypatch, [_Empresa()])
    _stub_adm(monkeypatch, [_Adm2()], [_Adm1()])

    app_empresas.test_client().get("/enterprise?q=frigo")

    filtro = stub.queryset.filter_calls[0][1]["__raw__"]
    campos = [list(condicion.keys())[0] for condicion in filtro["$or"]]
    assert campos == ["name", "ext_id.ext_code", "adm2_id.name"]


def test_list_enterprise_crea_una_empresa(app_empresas, capture_render, monkeypatch):
    capture_render(enterprise_module)
    stub = _stub_enterprise(monkeypatch)
    municipio = _Adm2()
    _stub_adm(monkeypatch, [municipio], [_Adm1()])

    with app_empresas.test_client() as cliente:
        respuesta = cliente.post("/enterprise", data=_payload())
        mensajes = _mensajes_flash(cliente)

    assert respuesta.status_code == 302
    assert len(stub.creados) == 1
    creado = stub.creados[0]
    assert creado.kwargs["name"] == "Frigorífico del Norte"
    assert creado.kwargs["adm2_id"] is municipio
    assert creado.kwargs["latitude"] == pytest.approx(6.25)
    assert creado.kwargs["ext_id"][0].ext_code == "900123456"
    assert "Empresa creada exitosamente." in mensajes


def test_list_enterprise_abre_el_modal_si_el_formulario_falla(
    app_empresas, capture_render, monkeypatch
):
    capturado = capture_render(enterprise_module)
    stub = _stub_enterprise(monkeypatch)
    _stub_adm(monkeypatch, [_Adm2()], [_Adm1()])

    respuesta = app_empresas.test_client().post("/enterprise", data=_payload(name=""))

    assert respuesta.status_code == 200
    assert stub.creados == []
    assert capturado["context"]["show_modal"] is True


def test_list_enterprise_informa_error_al_guardar(app_empresas, capture_render, monkeypatch):
    capturado = capture_render(enterprise_module)
    _stub_enterprise(monkeypatch)
    _stub_adm(monkeypatch, [], adm2_get_falla=True)

    with app_empresas.test_client() as cliente:
        respuesta = cliente.post("/enterprise", data=_payload())
        mensajes = _mensajes_flash(cliente)

    assert respuesta.status_code == 200
    assert any("Error al crear la empresa" in mensaje for mensaje in mensajes)
    assert capturado["context"]["show_modal"] is True


# ---------------------------------------------------------------------------
# edit_enterprise
# ---------------------------------------------------------------------------

def test_edit_enterprise_precarga_los_datos(app_empresas, capture_render, monkeypatch):
    capturado = capture_render(enterprise_module)
    departamento = _Adm1(doc_id=OTRO_OBJECT_ID)
    municipio = _Adm2(adm1_id=departamento)
    empresa = _Empresa(adm2_id=municipio, log=_Log(enable=False))
    _stub_enterprise(monkeypatch, [empresa])
    _stub_adm(monkeypatch, [municipio], [departamento])

    respuesta = app_empresas.test_client().get(f"/enterprise/edit/{OBJECT_ID_VALIDO}")

    assert respuesta.status_code == 200
    assert capturado["template"] == "enterprise/edit.html"
    formulario = capturado["context"]["form"]
    assert formulario.name.data == "Frigorífico"
    assert formulario.latitude.data == pytest.approx(6.25)
    assert formulario.enable.data is False
    assert formulario.ext_code.data == "900123"
    assert capturado["context"]["selected_adm1_id"] == OTRO_OBJECT_ID
    assert capturado["context"]["selected_adm2_id"] == OBJECT_ID_VALIDO


def test_edit_enterprise_guarda_los_cambios(app_empresas, capture_render, monkeypatch):
    capture_render(enterprise_module)
    municipio = _Adm2()
    empresa = _Empresa(adm2_id=municipio, log=_Log(enable=True))
    _stub_enterprise(monkeypatch, [empresa])
    _stub_adm(monkeypatch, [municipio], [_Adm1()])

    with app_empresas.test_client() as cliente:
        respuesta = cliente.post(
            f"/enterprise/edit/{OBJECT_ID_VALIDO}",
            data=_payload(name="Nuevo nombre", latitude="4.6", enable=""),
        )
        mensajes = _mensajes_flash(cliente)

    assert respuesta.status_code == 302
    assert empresa.name == "Nuevo nombre"
    assert empresa.latitude == pytest.approx(4.6)
    assert empresa.log.enable is False
    assert empresa.saved is True
    assert "Empresa actualizada correctamente." in mensajes


def test_edit_enterprise_informa_error_al_actualizar(app_empresas, capture_render, monkeypatch):
    capture_render(enterprise_module)
    empresa = _Empresa(adm2_id=_Adm2(), log=_Log())
    _stub_enterprise(monkeypatch, [empresa])
    _stub_adm(monkeypatch, [], adm2_get_falla=True)

    with app_empresas.test_client() as cliente:
        respuesta = cliente.post(f"/enterprise/edit/{OBJECT_ID_VALIDO}", data=_payload())
        mensajes = _mensajes_flash(cliente)

    assert respuesta.status_code == 200
    assert any("Error al actualizar la empresa" in mensaje for mensaje in mensajes)
    assert empresa.saved is False


def test_edit_enterprise_sin_municipio_asociado(app_empresas, capture_render, monkeypatch):
    capturado = capture_render(enterprise_module)
    empresa = _Empresa(adm2_id=None, log=_Log())
    _stub_enterprise(monkeypatch, [empresa])
    _stub_adm(monkeypatch, [_Adm2()], [_Adm1()])

    app_empresas.test_client().get(f"/enterprise/edit/{OBJECT_ID_VALIDO}")

    assert capturado["context"]["selected_adm2_id"] == ""
    assert capturado["context"]["selected_adm1_id"] == ""


# ---------------------------------------------------------------------------
# delete, reset y borrado permanente
# ---------------------------------------------------------------------------

def test_delete_enterprise_deshabilita(app_empresas, monkeypatch):
    empresa = _Empresa(log=_Log(enable=True))
    _stub_enterprise(monkeypatch, [empresa])

    with app_empresas.test_client() as cliente:
        respuesta = cliente.post(f"/enterprise/delete/{OBJECT_ID_VALIDO}")
        mensajes = _mensajes_flash(cliente)

    assert respuesta.status_code == 302
    assert empresa.log.enable is False
    assert empresa.deleted is False
    assert "Empresa deshabilitada." in mensajes


def test_reset_enterprise_rehabilita(app_empresas, monkeypatch):
    empresa = _Empresa(log=_Log(enable=False))
    _stub_enterprise(monkeypatch, [empresa])

    with app_empresas.test_client() as cliente:
        respuesta = cliente.post(f"/enterprise/reset/{OBJECT_ID_VALIDO}")
        mensajes = _mensajes_flash(cliente)

    assert respuesta.status_code == 302
    assert empresa.log.enable is True
    assert "Empresa reactivada." in mensajes


def test_permanent_delete_enterprise_borra_el_documento(app_empresas, monkeypatch):
    empresa = _Empresa()
    _stub_enterprise(monkeypatch, [empresa])

    with app_empresas.test_client() as cliente:
        respuesta = cliente.post(f"/enterprise/delete/permanent/{OBJECT_ID_VALIDO}")
        mensajes = _mensajes_flash(cliente)

    assert respuesta.status_code == 302
    assert empresa.deleted is True
    assert "Empresa eliminada definitivamente." in mensajes


def test_permanent_delete_enterprise_informa_error(app_empresas, monkeypatch):
    _stub_enterprise(monkeypatch, [], get_falla=True)

    with app_empresas.test_client() as cliente:
        respuesta = cliente.post(f"/enterprise/delete/permanent/{OBJECT_ID_VALIDO}")
        mensajes = _mensajes_flash(cliente)

    assert respuesta.status_code == 302
    assert any("Error al eliminar permanentemente" in mensaje for mensaje in mensajes)
