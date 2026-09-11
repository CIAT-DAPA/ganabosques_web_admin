"""Pruebas de las vistas CRUD de los tres niveles administrativos."""

from types import SimpleNamespace

import pytest

import src.forms.adm2_form as adm2_form_module
import src.forms.adm3_form as adm3_form_module
import src.routes.adm1_routes as adm1_module
import src.routes.adm2_routes as adm2_module
import src.routes.adm3_routes as adm3_module
from helpers import FakeQuerySet


class _Manager:
    """Manager de MongoEngine que responde distinto según cómo se le consulte.

    ``Adm1.objects()`` devuelve el listado completo mientras que
    ``Adm1.objects(ext_id=...)`` o ``Adm1.objects(id=...)`` resuelven una
    búsqueda puntual, que es justo la distinción que hacen las vistas.
    """

    def __init__(self, listado=(), por_clave=None, claves_listado=()):
        self.queryset = FakeQuerySet(listado)
        self.por_clave = por_clave or {}
        self.claves_listado = set(claves_listado)
        self.consultas = []

    def __call__(self, **kwargs):
        self.consultas.append(kwargs)
        if not kwargs or self.claves_listado & set(kwargs):
            return self.queryset
        for clave, valor in kwargs.items():
            encontrado = self.por_clave.get((clave, valor))
            if encontrado is not None:
                return FakeQuerySet([encontrado])
        return FakeQuerySet([])

    def order_by(self, *args):
        return self.queryset.order_by(*args)


class _Documento:
    def __init__(self, doc_id="d1", name="ANTIOQUIA", ext_id="5", log=None, **extra):
        self.id = doc_id
        self.name = name
        self.ext_id = ext_id
        self.log = log
        self.saved = False
        for clave, valor in extra.items():
            setattr(self, clave, valor)

    def save(self):
        self.saved = True
        return self


class _Log:
    def __init__(self, enable=True):
        self.enable = enable
        self.updated = None


def _stub_documento(monkeypatch, modulo, nombre, manager):
    creados = []

    class DocStub:
        objects = manager

        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.saved = False
            for clave, valor in kwargs.items():
                setattr(self, clave, valor)
            creados.append(self)

        def save(self):
            self.saved = True
            return self

    DocStub.creados = creados
    monkeypatch.setattr(modulo, nombre, DocStub)
    return DocStub


def _mensajes_flash(cliente):
    with cliente.session_transaction() as sesion:
        return [mensaje for _, mensaje in sesion.get("_flashes", [])]


# ---------------------------------------------------------------------------
# ADM1 - Departamentos
# ---------------------------------------------------------------------------

def test_adm1_list_renderiza_con_paginacion(make_app, capture_render, monkeypatch):
    capturado = capture_render(adm1_module)
    manager = _Manager(listado=[_Documento() for _ in range(120)])
    _stub_documento(monkeypatch, adm1_module, "Adm1", manager)

    app = make_app(adm1_module.adm1_bp)
    respuesta = app.test_client().get("/adm1?page=2")

    assert respuesta.status_code == 200
    assert capturado["template"] == "adm1/list.html"
    assert capturado["context"]["page"] == 2
    assert capturado["context"]["total"] == 120
    assert capturado["context"]["total_pages"] == 3
    assert manager.queryset.skip_calls == [50]
    assert manager.queryset.limit_calls == [50]


def test_adm1_list_aplica_el_filtro_de_busqueda(make_app, capture_render, monkeypatch):
    capturado = capture_render(adm1_module)
    manager = _Manager(listado=[_Documento()])
    _stub_documento(monkeypatch, adm1_module, "Adm1", manager)

    app = make_app(adm1_module.adm1_bp)
    app.test_client().get("/adm1?q=ANTIO")

    assert capturado["context"]["search"] == "ANTIO"
    filtro = manager.queryset.filter_calls[0][1]["__raw__"]
    assert filtro["$or"][0]["name"]["$regex"] == "ANTIO"
    assert filtro["$or"][1]["ext_id"]["$regex"] == "ANTIO"


def test_adm1_list_crea_un_departamento(make_app, capture_render, monkeypatch):
    capture_render(adm1_module)
    manager = _Manager()
    stub = _stub_documento(monkeypatch, adm1_module, "Adm1", manager)

    app = make_app(adm1_module.adm1_bp)
    with app.test_client() as cliente:
        respuesta = cliente.post(
            "/adm1", data={"name": "ANTIOQUIA", "ext_id": "5", "ugg_size": "1.5", "enable": "y"}
        )
        mensajes = _mensajes_flash(cliente)

    assert respuesta.status_code == 302
    assert len(stub.creados) == 1
    assert stub.creados[0].kwargs["name"] == "ANTIOQUIA"
    assert stub.creados[0].kwargs["ugg_size"] == pytest.approx(1.5)
    assert stub.creados[0].saved is True
    assert "Departamento creado correctamente." in mensajes


def test_adm1_list_rechaza_ext_id_duplicado(make_app, capture_render, monkeypatch):
    capture_render(adm1_module)
    existente = _Documento()
    manager = _Manager(por_clave={("ext_id", "5"): existente})
    stub = _stub_documento(monkeypatch, adm1_module, "Adm1", manager)

    app = make_app(adm1_module.adm1_bp)
    with app.test_client() as cliente:
        respuesta = cliente.post("/adm1", data={"name": "ANTIOQUIA", "ext_id": "5"})
        mensajes = _mensajes_flash(cliente)

    assert respuesta.status_code == 200
    assert stub.creados == []
    assert "Ya existe un departamento con ese Ext ID." in mensajes


def test_adm1_list_no_crea_si_falta_el_nombre(make_app, capture_render, monkeypatch):
    capturado = capture_render(adm1_module)
    manager = _Manager()
    stub = _stub_documento(monkeypatch, adm1_module, "Adm1", manager)

    app = make_app(adm1_module.adm1_bp)
    respuesta = app.test_client().post("/adm1", data={"name": "", "ext_id": "5"})

    assert respuesta.status_code == 200
    assert stub.creados == []
    assert capturado["context"]["form"].name.errors


def test_adm1_edit_muestra_los_datos_actuales(make_app, capture_render, monkeypatch):
    capturado = capture_render(adm1_module)
    documento = _Documento(doc_id="d1", name="CALDAS", ext_id="17", log=_Log(enable=False))
    documento.ugg_size = 2.0
    manager = _Manager(por_clave={("id", "d1"): documento})
    _stub_documento(monkeypatch, adm1_module, "Adm1", manager)

    app = make_app(adm1_module.adm1_bp)
    respuesta = app.test_client().get("/adm1/edit/d1")

    assert respuesta.status_code == 200
    assert capturado["template"] == "adm1/edit.html"
    formulario = capturado["context"]["form"]
    assert formulario.name.data == "CALDAS"
    assert formulario.ext_id.data == "17"
    assert formulario.enable.data is False


def test_adm1_edit_redirige_si_no_existe(make_app, monkeypatch):
    manager = _Manager()
    _stub_documento(monkeypatch, adm1_module, "Adm1", manager)

    app = make_app(adm1_module.adm1_bp)
    with app.test_client() as cliente:
        respuesta = cliente.get("/adm1/edit/inexistente")
        mensajes = _mensajes_flash(cliente)

    assert respuesta.status_code == 302
    assert "Departamento no encontrado." in mensajes


def test_adm1_edit_guarda_los_cambios(make_app, capture_render, monkeypatch):
    capture_render(adm1_module)
    documento = _Documento(doc_id="d1", log=_Log(enable=True))
    manager = _Manager(por_clave={("id", "d1"): documento})
    _stub_documento(monkeypatch, adm1_module, "Adm1", manager)

    app = make_app(adm1_module.adm1_bp)
    with app.test_client() as cliente:
        respuesta = cliente.post(
            "/adm1/edit/d1", data={"name": "NUEVO NOMBRE", "ext_id": "99", "enable": ""}
        )
        mensajes = _mensajes_flash(cliente)

    assert respuesta.status_code == 302
    assert documento.name == "NUEVO NOMBRE"
    assert documento.ext_id == "99"
    assert documento.log.enable is False
    assert documento.saved is True
    assert "Departamento actualizado." in mensajes


def test_adm1_edit_crea_el_log_si_no_existe(make_app, capture_render, monkeypatch):
    capture_render(adm1_module)
    documento = _Documento(doc_id="d1", log=None)
    manager = _Manager(por_clave={("id", "d1"): documento})
    _stub_documento(monkeypatch, adm1_module, "Adm1", manager)

    app = make_app(adm1_module.adm1_bp)
    app.test_client().post("/adm1/edit/d1", data={"name": "X", "ext_id": "1", "enable": "y"})

    assert documento.log is not None
    assert documento.log.enable is True


def test_adm1_delete_deshabilita_sin_borrar(make_app, monkeypatch):
    documento = _Documento(doc_id="d1", log=_Log(enable=True))
    manager = _Manager(por_clave={("id", "d1"): documento})
    _stub_documento(monkeypatch, adm1_module, "Adm1", manager)

    app = make_app(adm1_module.adm1_bp)
    with app.test_client() as cliente:
        respuesta = cliente.get("/adm1/delete/d1")
        mensajes = _mensajes_flash(cliente)

    assert respuesta.status_code == 302
    assert documento.log.enable is False
    assert documento.saved is True
    assert "Departamento deshabilitado." in mensajes


def test_adm1_delete_avisa_si_no_existe(make_app, monkeypatch):
    _stub_documento(monkeypatch, adm1_module, "Adm1", _Manager())

    app = make_app(adm1_module.adm1_bp)
    with app.test_client() as cliente:
        respuesta = cliente.get("/adm1/delete/inexistente")
        mensajes = _mensajes_flash(cliente)

    assert respuesta.status_code == 302
    assert "Departamento no encontrado." in mensajes


def test_adm1_reset_vuelve_a_habilitar(make_app, monkeypatch):
    documento = _Documento(doc_id="d1", log=_Log(enable=False))
    manager = _Manager(por_clave={("id", "d1"): documento})
    _stub_documento(monkeypatch, adm1_module, "Adm1", manager)

    app = make_app(adm1_module.adm1_bp)
    with app.test_client() as cliente:
        respuesta = cliente.get("/adm1/reset/d1")
        mensajes = _mensajes_flash(cliente)

    assert respuesta.status_code == 302
    assert documento.log.enable is True
    assert "Departamento reactivado." in mensajes


# ---------------------------------------------------------------------------
# ADM2 - Municipios
# ---------------------------------------------------------------------------

def _preparar_adm2(monkeypatch, manager_adm2, departamentos=()):
    stub_adm2 = _stub_documento(monkeypatch, adm2_module, "Adm2", manager_adm2)
    manager_adm1 = _Manager(
        listado=departamentos,
        por_clave={("id", d.id): d for d in departamentos},
        claves_listado={"log__enable"},
    )
    _stub_documento(monkeypatch, adm2_module, "Adm1", manager_adm1)
    # El formulario resuelve sus opciones contra su propio módulo.
    _stub_documento(monkeypatch, adm2_form_module, "Adm1", manager_adm1)
    return stub_adm2


def test_adm2_list_crea_con_referencia_al_departamento(make_app, capture_render, monkeypatch):
    capture_render(adm2_module)
    departamento = _Documento(doc_id="a1", name="ANTIOQUIA")
    stub = _preparar_adm2(monkeypatch, _Manager(), [departamento])

    app = make_app(adm2_module.adm2_bp)
    with app.test_client() as cliente:
        respuesta = cliente.post(
            "/adm2", data={"name": "MEDELLIN", "ext_id": "5001", "adm1_id": "a1", "enable": "y"}
        )
        mensajes = _mensajes_flash(cliente)

    assert respuesta.status_code == 302
    assert len(stub.creados) == 1
    assert stub.creados[0].kwargs["adm1_id"] is departamento
    assert "Municipio creado correctamente." in mensajes


def test_adm2_list_rechaza_ext_id_duplicado(make_app, capture_render, monkeypatch):
    capture_render(adm2_module)
    departamento = _Documento(doc_id="a1")
    existente = _Documento(doc_id="m1", ext_id="5001")
    stub = _preparar_adm2(
        monkeypatch, _Manager(por_clave={("ext_id", "5001"): existente}), [departamento]
    )

    app = make_app(adm2_module.adm2_bp)
    with app.test_client() as cliente:
        respuesta = cliente.post(
            "/adm2", data={"name": "MEDELLIN", "ext_id": "5001", "adm1_id": "a1"}
        )
        mensajes = _mensajes_flash(cliente)

    assert respuesta.status_code == 200
    assert stub.creados == []
    assert "Ya existe un municipio con ese Ext ID." in mensajes


def test_adm2_edit_actualiza_el_departamento_asociado(make_app, capture_render, monkeypatch):
    capture_render(adm2_module)
    nuevo_departamento = _Documento(doc_id="a2", name="CALDAS")
    municipio = _Documento(
        doc_id="m1", name="MEDELLIN", ext_id="5001", log=_Log(), adm1_id=_Documento(doc_id="a1")
    )
    _preparar_adm2(
        monkeypatch,
        _Manager(por_clave={("id", "m1"): municipio}),
        [nuevo_departamento],
    )

    app = make_app(adm2_module.adm2_bp)
    respuesta = app.test_client().post(
        "/adm2/edit/m1", data={"name": "MANIZALES", "ext_id": "17001", "adm1_id": "a2", "enable": "y"}
    )

    assert respuesta.status_code == 302
    assert municipio.name == "MANIZALES"
    assert municipio.adm1_id is nuevo_departamento
    assert municipio.saved is True


def test_adm2_edit_redirige_si_no_existe(make_app, monkeypatch):
    _preparar_adm2(monkeypatch, _Manager())

    app = make_app(adm2_module.adm2_bp)
    with app.test_client() as cliente:
        respuesta = cliente.get("/adm2/edit/inexistente")
        mensajes = _mensajes_flash(cliente)

    assert respuesta.status_code == 302
    assert "Municipio no encontrado." in mensajes


def test_adm2_delete_y_reset(make_app, monkeypatch):
    municipio = _Documento(doc_id="m1", log=_Log(enable=True))
    _preparar_adm2(monkeypatch, _Manager(por_clave={("id", "m1"): municipio}))

    app = make_app(adm2_module.adm2_bp)
    cliente = app.test_client()

    cliente.get("/adm2/delete/m1")
    assert municipio.log.enable is False

    cliente.get("/adm2/reset/m1")
    assert municipio.log.enable is True


# ---------------------------------------------------------------------------
# ADM3 - Veredas
# ---------------------------------------------------------------------------

def _preparar_adm3(monkeypatch, manager_adm3, municipios=(), departamentos=()):
    stub_adm3 = _stub_documento(monkeypatch, adm3_module, "Adm3", manager_adm3)
    manager_adm2 = _Manager(
        listado=municipios,
        por_clave={("id", m.id): m for m in municipios},
        claves_listado={"log__enable", "adm1_id"},
    )
    _stub_documento(monkeypatch, adm3_module, "Adm2", manager_adm2)
    _stub_documento(monkeypatch, adm3_form_module, "Adm2", manager_adm2)
    manager_adm1 = _Manager(
        listado=departamentos, por_clave={("id", d.id): d for d in departamentos}
    )
    _stub_documento(monkeypatch, adm3_module, "Adm1", manager_adm1)
    return stub_adm3


def test_adm3_api_devuelve_municipios_del_departamento(make_app, monkeypatch):
    municipios = [_Documento(doc_id="m1", name="BELLO"), _Documento(doc_id="m2", name="ITAGUI")]
    _preparar_adm3(monkeypatch, _Manager(), municipios)

    app = make_app(adm3_module.adm3_bp)
    respuesta = app.test_client().get("/api/adm2-by-adm1/a1")

    assert respuesta.status_code == 200
    assert respuesta.get_json() == [
        {"id": "m1", "name": "BELLO"},
        {"id": "m2", "name": "ITAGUI"},
    ]


def test_adm3_list_genera_el_label_jerarquico(make_app, capture_render, monkeypatch):
    capture_render(adm3_module)
    departamento = _Documento(doc_id="a1", name="Antioquia")
    municipio = _Documento(doc_id="m1", name="Medellin", adm1_id=departamento)
    stub = _preparar_adm3(monkeypatch, _Manager(), [municipio], [departamento])

    app = make_app(adm3_module.adm3_bp)
    respuesta = app.test_client().post(
        "/adm3",
        data={"name": "El Porvenir", "ext_id": "5001001", "adm2_id": "m1", "enable": "y"},
    )

    assert respuesta.status_code == 302
    assert len(stub.creados) == 1
    assert stub.creados[0].kwargs["label"] == "ANTIOQUIA,MEDELLIN,EL PORVENIR"


def test_adm3_list_genera_label_sin_departamento(make_app, capture_render, monkeypatch):
    capture_render(adm3_module)
    municipio = _Documento(doc_id="m1", name="Medellin", adm1_id=None)
    stub = _preparar_adm3(monkeypatch, _Manager(), [municipio])

    app = make_app(adm3_module.adm3_bp)
    app.test_client().post(
        "/adm3", data={"name": "El Porvenir", "ext_id": "5001001", "adm2_id": "m1"}
    )

    assert stub.creados[0].kwargs["label"] == ",MEDELLIN,EL PORVENIR"


def test_adm3_list_rechaza_ext_id_duplicado(make_app, capture_render, monkeypatch):
    capture_render(adm3_module)
    existente = _Documento(doc_id="v1", ext_id="5001001")
    municipio = _Documento(doc_id="m1", name="Medellin")
    stub = _preparar_adm3(
        monkeypatch, _Manager(por_clave={("ext_id", "5001001"): existente}), [municipio]
    )

    app = make_app(adm3_module.adm3_bp)
    with app.test_client() as cliente:
        respuesta = cliente.post(
            "/adm3", data={"name": "El Porvenir", "ext_id": "5001001", "adm2_id": "m1"}
        )
        mensajes = _mensajes_flash(cliente)

    assert respuesta.status_code == 200
    assert stub.creados == []
    assert "Ya existe una vereda con ese Ext ID." in mensajes


def test_adm3_list_busca_por_nombre(make_app, capture_render, monkeypatch):
    capturado = capture_render(adm3_module)
    manager = _Manager(listado=[_Documento()])
    _preparar_adm3(monkeypatch, manager)

    app = make_app(adm3_module.adm3_bp)
    app.test_client().get("/adm3?q=PORVENIR")

    assert capturado["context"]["search"] == "PORVENIR"
    assert manager.queryset.filter_calls[0][1] == {"name__icontains": "PORVENIR"}


def test_adm3_edit_regenera_el_label(make_app, capture_render, monkeypatch):
    capture_render(adm3_module)
    departamento = _Documento(doc_id="a1", name="Caldas")
    municipio = _Documento(doc_id="m2", name="Manizales", adm1_id=departamento)
    vereda = _Documento(doc_id="v1", name="Vieja", ext_id="1", log=_Log(), adm2_id=municipio)
    _preparar_adm3(
        monkeypatch, _Manager(por_clave={("id", "v1"): vereda}), [municipio], [departamento]
    )

    app = make_app(adm3_module.adm3_bp)
    respuesta = app.test_client().post(
        "/adm3/edit/v1",
        data={"name": "Nueva Vereda", "ext_id": "17001001", "adm2_id": "m2", "enable": "y"},
    )

    assert respuesta.status_code == 302
    assert vereda.label == "CALDAS,MANIZALES,NUEVA VEREDA"
    assert vereda.saved is True


def test_adm3_edit_rechaza_municipio_invalido(make_app, capture_render, monkeypatch):
    capture_render(adm3_module)
    vereda = _Documento(doc_id="v1", log=_Log(), adm2_id=_Documento(doc_id="m1"))
    _preparar_adm3(monkeypatch, _Manager(por_clave={("id", "v1"): vereda}))

    app = make_app(adm3_module.adm3_bp)
    with app.test_client() as cliente:
        respuesta = cliente.post(
            "/adm3/edit/v1",
            data={"name": "Nueva", "ext_id": "1", "adm2_id": "no-existe", "enable": "y"},
        )
        mensajes = _mensajes_flash(cliente)

    assert respuesta.status_code == 302
    assert "Municipio seleccionado no válido." in mensajes
    assert vereda.saved is False


def test_adm3_edit_redirige_si_no_existe(make_app, monkeypatch):
    _preparar_adm3(monkeypatch, _Manager())

    app = make_app(adm3_module.adm3_bp)
    with app.test_client() as cliente:
        respuesta = cliente.get("/adm3/edit/inexistente")
        mensajes = _mensajes_flash(cliente)

    assert respuesta.status_code == 302
    assert "Vereda no encontrada." in mensajes


def test_adm3_delete_y_reset(make_app, monkeypatch):
    vereda = _Documento(doc_id="v1", log=_Log(enable=True))
    _preparar_adm3(monkeypatch, _Manager(por_clave={("id", "v1"): vereda}))

    app = make_app(adm3_module.adm3_bp)
    cliente = app.test_client()

    cliente.get("/adm3/delete/v1")
    assert vereda.log.enable is False

    cliente.get("/adm3/reset/v1")
    assert vereda.log.enable is True
