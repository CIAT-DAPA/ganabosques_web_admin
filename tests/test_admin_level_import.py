"""Pruebas de la importación de niveles administrativos desde CSV.

La misma lógica existe duplicada en dos módulos del proyecto
(``src/routes/adm_import.py`` y ``src/routes/adminlevel_data_management.py``),
por lo que las pruebas comunes se parametrizan sobre ambos y las diferencias
de comportamiento se prueban aparte.
"""

import math

import pytest

import src.routes.adm_import as adm_import_module
import src.routes.adminlevel_data_management as adminlevel_module
from helpers import FakeObjectsManager, FakeQuerySet, make_document_stub

MODULOS = [adm_import_module, adminlevel_module]
IDS_MODULOS = ["adm_import", "adminlevel_data_management"]


@pytest.fixture(params=MODULOS, ids=IDS_MODULOS)
def modulo_import(request):
    """Cada prueba parametrizada se ejecuta contra las dos copias del código."""
    return request.param


def _stub_documentos(monkeypatch, modulo, adm1=(), adm2=(), adm3=()):
    """Sustituye Adm1/Adm2/Adm3 del módulo por dobles sin conexión a Mongo."""
    stubs = {}
    for nombre, existentes in (("Adm1", adm1), ("Adm2", adm2), ("Adm3", adm3)):
        stub = make_document_stub(existentes)
        monkeypatch.setattr(modulo, nombre, stub)
        stubs[nombre] = stub
    return stubs


class _DocumentoExistente:
    def __init__(self, ext_id):
        self.ext_id = ext_id


# ---------------------------------------------------------------------------
# convert_id
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "entrada, esperado",
    [
        (5, "5"),
        (5.0, "5"),
        ("05", "5"),
        ("05001", "5001"),
        (" 12 ", "12"),
        (1234.0, "1234"),
    ],
)
def test_convert_id_normaliza_valores_numericos(modulo_import, entrada, esperado):
    assert modulo_import.convert_id(entrada) == esperado


@pytest.mark.parametrize(
    "entrada",
    [None, "", "abc", float("nan"), math.nan, [], {}],
)
def test_convert_id_devuelve_none_para_valores_invalidos(modulo_import, entrada):
    assert modulo_import.convert_id(entrada) is None


# ---------------------------------------------------------------------------
# get_log
# ---------------------------------------------------------------------------

def test_get_log_marca_habilitado_y_fechas(modulo_import):
    log = modulo_import.get_log()

    assert log.enable is True
    assert log.created is not None
    assert log.updated is not None


# ---------------------------------------------------------------------------
# procesar_fila_departamento
# ---------------------------------------------------------------------------

def test_procesar_fila_departamento_crea_registro(modulo_import, monkeypatch):
    stubs = _stub_documentos(monkeypatch, modulo_import)
    cache = {}

    modulo_import.procesar_fila_departamento(
        {"COD_DEPARTAMENTO": "05", "NOMBRE_DEPARTAMENTO": "ANTIOQUIA"}, cache
    )

    assert len(stubs["Adm1"].created) == 1
    creado = stubs["Adm1"].created[0]
    assert creado.kwargs["ext_id"] == "5"
    assert creado.kwargs["name"] == "ANTIOQUIA"
    assert creado.saved is True
    assert cache["5"] is creado


def test_procesar_fila_departamento_no_duplica_existente(modulo_import, monkeypatch):
    stubs = _stub_documentos(monkeypatch, modulo_import)
    existente = _DocumentoExistente("5")
    cache = {"5": existente}

    modulo_import.procesar_fila_departamento(
        {"COD_DEPARTAMENTO": "05", "NOMBRE_DEPARTAMENTO": "ANTIOQUIA"}, cache
    )

    assert stubs["Adm1"].created == []
    assert cache["5"] is existente


@pytest.mark.parametrize(
    "fila",
    [
        {"COD_DEPARTAMENTO": None, "NOMBRE_DEPARTAMENTO": "ANTIOQUIA"},
        {"COD_DEPARTAMENTO": "abc", "NOMBRE_DEPARTAMENTO": "ANTIOQUIA"},
        {"COD_DEPARTAMENTO": "05", "NOMBRE_DEPARTAMENTO": ""},
        {"COD_DEPARTAMENTO": "05", "NOMBRE_DEPARTAMENTO": None},
    ],
)
def test_procesar_fila_departamento_descarta_filas_incompletas(modulo_import, monkeypatch, fila):
    stubs = _stub_documentos(monkeypatch, modulo_import)
    cache = {}

    modulo_import.procesar_fila_departamento(fila, cache)

    assert stubs["Adm1"].created == []
    assert cache == {}


# ---------------------------------------------------------------------------
# procesar_fila_municipio
# ---------------------------------------------------------------------------

def test_procesar_fila_municipio_crea_con_referencia_al_departamento(modulo_import, monkeypatch):
    stubs = _stub_documentos(monkeypatch, modulo_import)
    departamento = _DocumentoExistente("5")
    cache_adm1 = {"5": departamento}
    cache_adm2 = {}

    modulo_import.procesar_fila_municipio(
        {
            "COD_DEPARTAMENTO": "05",
            "COD_MUNICIPIO": "05001",
            "NOMBRE_MUNICIPIO": "MEDELLIN",
        },
        cache_adm1,
        cache_adm2,
    )

    assert len(stubs["Adm2"].created) == 1
    creado = stubs["Adm2"].created[0]
    assert creado.kwargs["ext_id"] == "5001"
    assert creado.kwargs["adm1_id"] is departamento
    assert cache_adm2["5001"] is creado


def test_procesar_fila_municipio_omite_si_no_existe_departamento(modulo_import, monkeypatch):
    stubs = _stub_documentos(monkeypatch, modulo_import)
    cache_adm2 = {}

    modulo_import.procesar_fila_municipio(
        {
            "COD_DEPARTAMENTO": "99",
            "COD_MUNICIPIO": "99001",
            "NOMBRE_MUNICIPIO": "HUERFANO",
        },
        {},
        cache_adm2,
    )

    assert stubs["Adm2"].created == []
    assert cache_adm2 == {}


def test_procesar_fila_municipio_no_duplica_existente(modulo_import, monkeypatch):
    stubs = _stub_documentos(monkeypatch, modulo_import)
    cache_adm1 = {"5": _DocumentoExistente("5")}
    cache_adm2 = {"5001": _DocumentoExistente("5001")}

    modulo_import.procesar_fila_municipio(
        {
            "COD_DEPARTAMENTO": "05",
            "COD_MUNICIPIO": "05001",
            "NOMBRE_MUNICIPIO": "MEDELLIN",
        },
        cache_adm1,
        cache_adm2,
    )

    assert stubs["Adm2"].created == []


@pytest.mark.parametrize(
    "fila",
    [
        {"COD_DEPARTAMENTO": None, "COD_MUNICIPIO": "05001", "NOMBRE_MUNICIPIO": "MEDELLIN"},
        {"COD_DEPARTAMENTO": "05", "COD_MUNICIPIO": None, "NOMBRE_MUNICIPIO": "MEDELLIN"},
        {"COD_DEPARTAMENTO": "05", "COD_MUNICIPIO": "05001", "NOMBRE_MUNICIPIO": ""},
    ],
)
def test_procesar_fila_municipio_descarta_filas_incompletas(modulo_import, monkeypatch, fila):
    stubs = _stub_documentos(monkeypatch, modulo_import)

    modulo_import.procesar_fila_municipio(fila, {"5": _DocumentoExistente("5")}, {})

    assert stubs["Adm2"].created == []


# ---------------------------------------------------------------------------
# procesar_fila_vereda
# ---------------------------------------------------------------------------

def test_procesar_fila_vereda_crea_con_referencia_al_municipio(modulo_import, monkeypatch):
    stubs = _stub_documentos(monkeypatch, modulo_import)
    municipio = _DocumentoExistente("5001")
    cache_adm3 = {}

    modulo_import.procesar_fila_vereda(
        {
            "COD_MUNICIPIO": "05001",
            "COD_VEREDA": "05001001",
            "NOMBRE_VEREDA": "EL PORVENIR",
        },
        {"5001": municipio},
        cache_adm3,
    )

    assert len(stubs["Adm3"].created) == 1
    creado = stubs["Adm3"].created[0]
    assert creado.kwargs["ext_id"] == "5001001"
    assert creado.kwargs["adm2_id"] is municipio
    assert cache_adm3["5001001"] is creado


def test_procesar_fila_vereda_omite_si_no_existe_municipio(modulo_import, monkeypatch):
    stubs = _stub_documentos(monkeypatch, modulo_import)

    modulo_import.procesar_fila_vereda(
        {
            "COD_MUNICIPIO": "99001",
            "COD_VEREDA": "99001001",
            "NOMBRE_VEREDA": "HUERFANA",
        },
        {},
        {},
    )

    assert stubs["Adm3"].created == []


def test_procesar_fila_vereda_no_duplica_existente(modulo_import, monkeypatch):
    stubs = _stub_documentos(monkeypatch, modulo_import)

    modulo_import.procesar_fila_vereda(
        {
            "COD_MUNICIPIO": "05001",
            "COD_VEREDA": "05001001",
            "NOMBRE_VEREDA": "EL PORVENIR",
        },
        {"5001": _DocumentoExistente("5001")},
        {"5001001": _DocumentoExistente("5001001")},
    )

    assert stubs["Adm3"].created == []


# ---------------------------------------------------------------------------
# importar_desde_csv
# ---------------------------------------------------------------------------

CSV_COMPLETO = (
    "COD_DEPARTAMENTO,NOMBRE_DEPARTAMENTO,COD_MUNICIPIO,NOMBRE_MUNICIPIO,COD_VEREDA,NOMBRE_VEREDA\n"
    "05,ANTIOQUIA,05001,MEDELLIN,05001001,EL PORVENIR\n"
    "05,ANTIOQUIA,05002,ABEJORRAL,05002001,LA UNION\n"
)


def _escribir_csv(tmp_path, contenido, encoding="utf-8", nombre="niveles.csv"):
    ruta = tmp_path / nombre
    ruta.write_text(contenido, encoding=encoding)
    return str(ruta)


def test_importar_desde_csv_nivel_departamento(modulo_import, monkeypatch, tmp_path, flask_app):
    stubs = _stub_documentos(monkeypatch, modulo_import)
    ruta = _escribir_csv(tmp_path, CSV_COMPLETO)

    with flask_app.test_request_context("/"):
        modulo_import.importar_desde_csv(ruta, nivel="departamento")

    # Las dos filas comparten departamento: solo debe crearse una vez.
    assert len(stubs["Adm1"].created) == 1
    assert stubs["Adm2"].created == []
    assert stubs["Adm3"].created == []


def test_importar_desde_csv_nivel_todo_crea_los_tres_niveles(
    modulo_import, monkeypatch, tmp_path, flask_app
):
    stubs = _stub_documentos(monkeypatch, modulo_import)
    ruta = _escribir_csv(tmp_path, CSV_COMPLETO)

    with flask_app.test_request_context("/"):
        modulo_import.importar_desde_csv(ruta, nivel="todo")

    assert len(stubs["Adm1"].created) == 1
    assert len(stubs["Adm2"].created) == 2
    assert len(stubs["Adm3"].created) == 2


def test_importar_desde_csv_acepta_nivel_en_mayusculas(
    modulo_import, monkeypatch, tmp_path, flask_app
):
    stubs = _stub_documentos(monkeypatch, modulo_import)
    ruta = _escribir_csv(tmp_path, CSV_COMPLETO)

    with flask_app.test_request_context("/"):
        modulo_import.importar_desde_csv(ruta, nivel="DEPARTAMENTO")

    assert len(stubs["Adm1"].created) == 1


def test_importar_desde_csv_lanza_error_si_faltan_columnas(
    modulo_import, monkeypatch, tmp_path, flask_app
):
    _stub_documentos(monkeypatch, modulo_import)
    ruta = _escribir_csv(tmp_path, "COD_DEPARTAMENTO\n05\n")

    with flask_app.test_request_context("/"):
        with pytest.raises(ValueError, match="Faltan columnas"):
            modulo_import.importar_desde_csv(ruta, nivel="departamento")


def test_importar_desde_csv_reintenta_con_latin1(
    modulo_import, monkeypatch, tmp_path, flask_app
):
    """Un CSV en latin-1 con tildes debe leerse tras fallar la lectura UTF-8."""
    stubs = _stub_documentos(monkeypatch, modulo_import)
    contenido = "COD_DEPARTAMENTO,NOMBRE_DEPARTAMENTO\n05,ANTIOQUÍA\n"
    ruta = _escribir_csv(tmp_path, contenido, encoding="latin1")

    with flask_app.test_request_context("/"):
        modulo_import.importar_desde_csv(ruta, nivel="departamento")

    assert len(stubs["Adm1"].created) == 1
    assert "ANTIOQU" in stubs["Adm1"].created[0].kwargs["name"]


def test_importar_desde_csv_reutiliza_documentos_ya_almacenados(
    modulo_import, monkeypatch, tmp_path, flask_app
):
    """Los ext_id que ya existen en Mongo no se vuelven a crear."""
    stubs = _stub_documentos(monkeypatch, modulo_import, adm1=[_DocumentoExistente("5")])
    ruta = _escribir_csv(tmp_path, CSV_COMPLETO)

    with flask_app.test_request_context("/"):
        modulo_import.importar_desde_csv(ruta, nivel="departamento")

    assert stubs["Adm1"].created == []


def test_importar_desde_csv_nivel_municipio_precarga_departamentos(
    modulo_import, monkeypatch, tmp_path, flask_app
):
    """Al importar solo municipios se debe consultar también Adm1 para resolver la referencia."""
    stubs = _stub_documentos(monkeypatch, modulo_import, adm1=[_DocumentoExistente("5")])
    ruta = _escribir_csv(tmp_path, CSV_COMPLETO)

    with flask_app.test_request_context("/"):
        modulo_import.importar_desde_csv(ruta, nivel="municipio")

    assert len(stubs["Adm2"].created) == 2
    assert stubs["Adm2"].created[0].kwargs["adm1_id"].ext_id == "5"


# ---------------------------------------------------------------------------
# Diferencia de comportamiento entre las dos copias
# ---------------------------------------------------------------------------

def test_adminlevel_notifica_por_flash_al_terminar(monkeypatch, tmp_path, flask_app):
    """La copia de ``adminlevel_data_management`` avisa por flash; la de ``adm_import`` no."""
    _stub_documentos(monkeypatch, adminlevel_module)
    mensajes = []
    monkeypatch.setattr(
        adminlevel_module, "flash", lambda mensaje, categoria=None: mensajes.append((mensaje, categoria))
    )
    ruta = _escribir_csv(tmp_path, CSV_COMPLETO)

    with flask_app.test_request_context("/"):
        adminlevel_module.importar_desde_csv(ruta, nivel="departamento")

    assert mensajes == [("Niveles administrativos creados con éxito", "success")]


def test_adm_import_no_usa_flash_en_la_funcion_de_importacion(monkeypatch, tmp_path, flask_app):
    _stub_documentos(monkeypatch, adm_import_module)
    ruta = _escribir_csv(tmp_path, CSV_COMPLETO)

    with flask_app.test_request_context("/"):
        resultado = adm_import_module.importar_desde_csv(ruta, nivel="departamento")

    assert resultado is None


# ---------------------------------------------------------------------------
# Ruta /importar-administrativos
# ---------------------------------------------------------------------------

def test_ruta_importar_administrativos_get_renderiza_formulario(
    make_app, capture_render, monkeypatch
):
    capturado = capture_render(adm_import_module)
    app = make_app(adm_import_module.adm_bp)

    respuesta = app.test_client().get("/importar-administrativos")

    assert respuesta.status_code == 200
    assert capturado["template"] == "importar_administrativos.html"
    assert "form" in capturado["context"]


def test_ruta_importar_administrativos_guarda_y_procesa_el_csv(
    make_app, monkeypatch, tmp_path
):
    import io

    llamadas = {}

    def fake_importar(ruta, nivel="todo"):
        llamadas["ruta"] = ruta
        llamadas["nivel"] = nivel

    monkeypatch.setattr(adm_import_module, "importar_desde_csv", fake_importar)
    monkeypatch.setattr(adm_import_module, "UPLOAD_FOLDER", str(tmp_path))

    app = make_app(adm_import_module.adm_bp)
    datos = {
        "nivel": "departamento",
        "archivo": (io.BytesIO(b"COD_DEPARTAMENTO,NOMBRE_DEPARTAMENTO\n05,ANTIOQUIA\n"), "niveles.csv"),
    }

    respuesta = app.test_client().post(
        "/importar-administrativos", data=datos, content_type="multipart/form-data"
    )

    assert respuesta.status_code == 302
    assert llamadas["nivel"] == "departamento"
    assert llamadas["ruta"].endswith("niveles.csv")


def test_ruta_importar_administrativos_informa_errores_de_importacion(
    make_app, monkeypatch, tmp_path
):
    import io

    def fake_importar(ruta, nivel="todo"):
        raise ValueError("Faltan columnas: ['COD_VEREDA']")

    monkeypatch.setattr(adm_import_module, "importar_desde_csv", fake_importar)
    monkeypatch.setattr(adm_import_module, "UPLOAD_FOLDER", str(tmp_path))

    app = make_app(adm_import_module.adm_bp)
    datos = {
        "nivel": "vereda",
        "archivo": (io.BytesIO(b"COD_MUNICIPIO\n05001\n"), "niveles.csv"),
    }

    with app.test_client() as cliente:
        respuesta = cliente.post(
            "/importar-administrativos", data=datos, content_type="multipart/form-data"
        )
        with cliente.session_transaction() as sesion:
            categorias = [categoria for categoria, _ in sesion.get("_flashes", [])]
            mensajes = [mensaje for _, mensaje in sesion.get("_flashes", [])]

    assert respuesta.status_code == 302
    assert "danger" in categorias
    assert any("Error durante la importación" in mensaje for mensaje in mensajes)


def test_ruta_importar_administrativos_rechaza_archivo_no_csv(make_app, capture_render):
    import io

    capturado = capture_render(adm_import_module)
    app = make_app(adm_import_module.adm_bp)
    datos = {
        "nivel": "departamento",
        "archivo": (io.BytesIO(b"no soy un csv"), "archivo.txt"),
    }

    respuesta = app.test_client().post(
        "/importar-administrativos", data=datos, content_type="multipart/form-data"
    )

    assert respuesta.status_code == 200
    assert capturado["template"] == "importar_administrativos.html"
    assert capturado["context"]["form"].archivo.errors
