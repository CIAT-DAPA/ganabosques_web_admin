"""Pruebas de la importación y descarga de proveedores."""

import io

import pytest

import src.routes.suppliers_data_management as suppliers_module
from helpers import FakeObjectsManager, FakeQuerySet, make_document_stub


# ---------------------------------------------------------------------------
# extract_data_from_csv
# ---------------------------------------------------------------------------

def test_extract_data_from_csv_devuelve_pares_limpios():
    stream = io.BytesIO(b"900123, F001 \n900456,F002\n")

    resultado = suppliers_module.extract_data_from_csv(stream)

    assert resultado == [("900123", "F001"), ("900456", "F002")]


def test_extract_data_from_csv_ignora_filas_vacias_o_incompletas():
    stream = io.BytesIO(b"900123,F001\n\n900456\n900789,F003\n")

    resultado = suppliers_module.extract_data_from_csv(stream)

    assert resultado == [("900123", "F001"), ("900789", "F003")]


def test_extract_data_from_csv_conserva_columnas_adicionales_ignoradas():
    stream = io.BytesIO(b"900123,F001,extra,mas\n")

    resultado = suppliers_module.extract_data_from_csv(stream)

    assert resultado == [("900123", "F001")]


def test_extract_data_from_csv_lanza_error_si_no_hay_datos():
    stream = io.BytesIO(b"\n\n")

    with pytest.raises(ValueError, match="al menos dos columnas"):
        suppliers_module.extract_data_from_csv(stream)


# ---------------------------------------------------------------------------
# generate_csv_response
# ---------------------------------------------------------------------------

def test_generate_csv_response_incluye_cabecera_y_filas(flask_app):
    with flask_app.test_request_context("/"):
        respuesta = suppliers_module.generate_csv_response(
            "salida.csv", [("900123", "F001")], ["codigo_empresa", "codigo_finca"]
        )

    cuerpo = respuesta.get_data(as_text=True)
    assert "codigo_empresa,codigo_finca" in cuerpo
    assert "900123,F001" in cuerpo
    assert respuesta.headers["Content-Type"] == "text/csv"
    assert respuesta.headers["Content-Disposition"] == "attachment; filename=salida.csv"


def test_generate_csv_response_admite_lista_vacia(flask_app):
    with flask_app.test_request_context("/"):
        respuesta = suppliers_module.generate_csv_response("vacio.csv", [], ["a", "b"])

    assert "a,b" in respuesta.get_data(as_text=True)


# ---------------------------------------------------------------------------
# Rutas de descarga
# ---------------------------------------------------------------------------

def test_descargar_encontrados_convierte_el_formato_con_pipe(make_app):
    app = make_app(suppliers_module.suppliers_bp)

    respuesta = app.test_client().post(
        "/descargar_encontrados", data={"encontrados[]": ["900123|F001", "900456|F002"]}
    )

    cuerpo = respuesta.get_data(as_text=True)
    assert respuesta.status_code == 200
    assert "900123,F001" in cuerpo
    assert "900456,F002" in cuerpo
    assert "encontrados.csv" in respuesta.headers["Content-Disposition"]


def test_descargar_no_encontrados_usa_su_propio_nombre_de_archivo(make_app):
    app = make_app(suppliers_module.suppliers_bp)

    respuesta = app.test_client().post(
        "/descargar_no_encontrados", data={"no_encontrados[]": ["900999|F999"]}
    )

    assert "no_encontrados.csv" in respuesta.headers["Content-Disposition"]
    assert "900999,F999" in respuesta.get_data(as_text=True)


# ---------------------------------------------------------------------------
# Ruta /importar_proveedores
# ---------------------------------------------------------------------------

class _Documento:
    def __init__(self, doc_id):
        self.id = doc_id


def _preparar_orm(monkeypatch, empresa=None, finca=None, suppliers_existente=None):
    """Sustituye Enterprise/Farm/Suppliers por dobles controlados."""
    empresa_qs = FakeQuerySet([empresa] if empresa else [])
    finca_qs = FakeQuerySet([finca] if finca else [])

    monkeypatch.setattr(
        suppliers_module, "Enterprise", type("EnterpriseStub", (), {"objects": FakeObjectsManager(empresa_qs)})
    )
    monkeypatch.setattr(
        suppliers_module, "Farm", type("FarmStub", (), {"objects": FakeObjectsManager(finca_qs)})
    )

    suppliers_stub = make_document_stub([suppliers_existente] if suppliers_existente else [])
    monkeypatch.setattr(suppliers_module, "Suppliers", suppliers_stub)
    return suppliers_stub


def _etiqueta_valida():
    from ganabosques_orm.enums.label import Label

    return list(Label)[0].name


def test_importar_proveedores_get_renderiza_opciones(make_app, capture_render):
    capturado = capture_render(suppliers_module)
    app = make_app(suppliers_module.suppliers_bp)

    respuesta = app.test_client().get("/importar_proveedores")

    assert respuesta.status_code == 200
    assert capturado["template"] == "import_suppliers.html"
    assert capturado["context"]["active_page"] == "import_suppliers"
    assert 2013 in capturado["context"]["anios"]


def test_importar_proveedores_exige_label_y_archivo(make_app):
    app = make_app(suppliers_module.suppliers_bp)

    with app.test_client() as cliente:
        respuesta = cliente.post("/importar_proveedores", data={})
        with cliente.session_transaction() as sesion:
            mensajes = [mensaje for _, mensaje in sesion.get("_flashes", [])]

    assert respuesta.status_code == 302
    assert any("tipo de código" in mensaje for mensaje in mensajes)


def test_importar_proveedores_rechaza_label_invalido(make_app):
    app = make_app(suppliers_module.suppliers_bp)
    datos = {
        "label": "NO_EXISTE",
        "archivo": (io.BytesIO(b"900123,F001\n"), "proveedores.csv"),
    }

    with app.test_client() as cliente:
        respuesta = cliente.post(
            "/importar_proveedores", data=datos, content_type="multipart/form-data"
        )
        with cliente.session_transaction() as sesion:
            mensajes = [mensaje for _, mensaje in sesion.get("_flashes", [])]

    assert respuesta.status_code == 302
    assert "Tipo de código no válido" in mensajes


def test_importar_proveedores_crea_suppliers_nuevos(make_app, capture_render, monkeypatch):
    capturado = capture_render(suppliers_module)
    suppliers_stub = _preparar_orm(
        monkeypatch, empresa=_Documento("e1"), finca=_Documento("f1")
    )
    app = make_app(suppliers_module.suppliers_bp)

    datos = {
        "label": _etiqueta_valida(),
        "anios": ["2023", "2024"],
        "archivo": (io.BytesIO(b"900123,F001\n"), "proveedores.csv"),
    }

    respuesta = app.test_client().post(
        "/importar_proveedores", data=datos, content_type="multipart/form-data"
    )

    assert respuesta.status_code == 200
    assert len(suppliers_stub.created) == 1
    creado = suppliers_stub.created[0]
    assert creado.kwargs["enterprise_id"] == "e1"
    assert creado.kwargs["farm_id"] == "f1"
    assert [anio.years for anio in creado.kwargs["years"]] == ["2023", "2024"]
    assert capturado["context"]["encontrados"] == [("900123", "F001")]
    assert capturado["context"]["no_encontrados"] == []


def test_importar_proveedores_reporta_codigos_no_encontrados(
    make_app, capture_render, monkeypatch
):
    capturado = capture_render(suppliers_module)
    suppliers_stub = _preparar_orm(monkeypatch, empresa=None, finca=None)
    app = make_app(suppliers_module.suppliers_bp)

    datos = {
        "label": _etiqueta_valida(),
        "anios": ["2024"],
        "archivo": (io.BytesIO(b"900999,F999\n"), "proveedores.csv"),
    }

    app.test_client().post(
        "/importar_proveedores", data=datos, content_type="multipart/form-data"
    )

    assert suppliers_stub.created == []
    assert capturado["context"]["no_encontrados"] == [("900999", "F999")]
    assert capturado["context"]["encontrados"] == []


def test_importar_proveedores_agrega_solo_los_anios_nuevos(
    make_app, capture_render, monkeypatch
):
    capture_render(suppliers_module)

    class SupplierExistente:
        def __init__(self):
            self.years = [type("Y", (), {"years": "2023"})()]
            self.saved = False

        def save(self):
            self.saved = True

    existente = SupplierExistente()
    suppliers_stub = _preparar_orm(
        monkeypatch,
        empresa=_Documento("e1"),
        finca=_Documento("f1"),
        suppliers_existente=existente,
    )
    app = make_app(suppliers_module.suppliers_bp)

    datos = {
        "label": _etiqueta_valida(),
        "anios": ["2023", "2024"],
        "archivo": (io.BytesIO(b"900123,F001\n"), "proveedores.csv"),
    }

    app.test_client().post(
        "/importar_proveedores", data=datos, content_type="multipart/form-data"
    )

    assert suppliers_stub.created == []
    assert existente.saved is True
    assert [anio.years for anio in existente.years] == ["2023", "2024"]


def test_importar_proveedores_no_guarda_si_los_anios_ya_existen(
    make_app, capture_render, monkeypatch
):
    capture_render(suppliers_module)

    class SupplierExistente:
        def __init__(self):
            self.years = [type("Y", (), {"years": "2023"})()]
            self.saved = False

        def save(self):
            self.saved = True

    existente = SupplierExistente()
    _preparar_orm(
        monkeypatch,
        empresa=_Documento("e1"),
        finca=_Documento("f1"),
        suppliers_existente=existente,
    )
    app = make_app(suppliers_module.suppliers_bp)

    datos = {
        "label": _etiqueta_valida(),
        "anios": ["2023"],
        "archivo": (io.BytesIO(b"900123,F001\n"), "proveedores.csv"),
    }

    app.test_client().post(
        "/importar_proveedores", data=datos, content_type="multipart/form-data"
    )

    assert existente.saved is False


def test_importar_proveedores_informa_csv_sin_datos(make_app, monkeypatch):
    _preparar_orm(monkeypatch)
    app = make_app(suppliers_module.suppliers_bp)

    datos = {
        "label": _etiqueta_valida(),
        "archivo": (io.BytesIO(b"\n"), "proveedores.csv"),
    }

    with app.test_client() as cliente:
        respuesta = cliente.post(
            "/importar_proveedores", data=datos, content_type="multipart/form-data"
        )
        with cliente.session_transaction() as sesion:
            mensajes = [mensaje for _, mensaje in sesion.get("_flashes", [])]

    assert respuesta.status_code == 302
    assert any("al menos dos columnas" in mensaje for mensaje in mensajes)
