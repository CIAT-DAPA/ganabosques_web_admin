"""Pruebas complementarias de la publicación de mosaicos en GeoServer."""

import logging
import os
import zipfile
from datetime import date, datetime

import pytest

import src.geoserver_import as geoserver_module

INDEXER = "TimeAttribute=time\nSchema=*the_geom:Polygon,location:String,time:java.util.Date\n"
TIMEREGEX_OK = "regex=\\d{8},format=yyyyMMdd\n"
TIMEREGEX_MENSUAL = "regex=\\d{6},format=yyyyMM\n"
# La advertencia de fechas con guiones se dispara al encontrar una fecha
# literal YYYY-MM-DD en el archivo, como la de este comentario de ejemplo.
TIMEREGEX_GUIONES = "# ejemplo: 2010-01-01\nregex=\\d{4}-\\d{2}-\\d{2},format=yyyy-MM-dd\n"


def _crear_properties(carpeta, timeregex=TIMEREGEX_OK, con_indexer=True, con_timeregex=True):
    carpeta.mkdir(parents=True, exist_ok=True)
    if con_indexer:
        (carpeta / "indexer.properties").write_text(INDEXER, encoding="utf-8")
    if con_timeregex:
        (carpeta / "timeregex.properties").write_text(timeregex, encoding="utf-8")
    return str(carpeta)


def _crear_tifs(carpeta, nombres):
    carpeta.mkdir(parents=True, exist_ok=True)
    for nombre in nombres:
        (carpeta / nombre).write_bytes(b"raster")
    return str(carpeta)


# ---------------------------------------------------------------------------
# _ensure_rest_url
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "entrada, esperado",
    [
        ("https://host/geoserver", "https://host/geoserver/rest/"),
        ("https://host/geoserver/", "https://host/geoserver/rest/"),
        ("https://host/geoserver/rest", "https://host/geoserver/rest/"),
        ("https://host/geoserver/rest/", "https://host/geoserver/rest/"),
        ("https://host/rest", "https://host/rest/"),
        ("https://host", "https://host/rest/"),
        ("  https://host/geoserver  ", "https://host/geoserver/rest/"),
        ("", ""),
        (None, ""),
    ],
)
def test_ensure_rest_url(entrada, esperado):
    assert geoserver_module._ensure_rest_url(entrada) == esperado


# ---------------------------------------------------------------------------
# _list_tifs y _create_dirs
# ---------------------------------------------------------------------------

def test_list_tifs_devuelve_lista_ordenada(tmp_path):
    carpeta = _crear_tifs(tmp_path / "rasters", ["c.tif", "a.tif", "b.tif"])
    (tmp_path / "rasters" / "nota.txt").write_text("x", encoding="utf-8")

    resultado = geoserver_module._list_tifs(carpeta)

    assert [os.path.basename(p) for p in resultado] == ["a.tif", "b.tif", "c.tif"]


def test_list_tifs_con_carpeta_inexistente():
    assert geoserver_module._list_tifs("/carpeta/que/no/existe") == []


def test_list_tifs_ignora_extension_tiff(tmp_path):
    """El helper solo recoge '.tif', no '.tiff'."""
    carpeta = _crear_tifs(tmp_path / "rasters", ["a.tif"])
    (tmp_path / "rasters" / "b.tiff").write_bytes(b"x")

    resultado = geoserver_module._list_tifs(carpeta)

    assert len(resultado) == 1


def test_create_dirs_crea_todas_las_rutas(tmp_path):
    uno = tmp_path / "uno"
    dos = tmp_path / "dos" / "anidado"

    geoserver_module._create_dirs(str(uno), str(dos))

    assert uno.is_dir()
    assert dos.is_dir()


def test_create_dirs_es_idempotente(tmp_path):
    ruta = tmp_path / "uno"
    geoserver_module._create_dirs(str(ruta))
    geoserver_module._create_dirs(str(ruta))

    assert ruta.is_dir()


# ---------------------------------------------------------------------------
# _read_text_file
# ---------------------------------------------------------------------------

def test_read_text_file_lee_el_contenido(tmp_path):
    archivo = tmp_path / "datos.txt"
    archivo.write_text("contenido", encoding="utf-8")

    assert geoserver_module._read_text_file(str(archivo)) == "contenido"


def test_read_text_file_devuelve_vacio_si_no_existe():
    assert geoserver_module._read_text_file("/no/existe.txt") == ""


# ---------------------------------------------------------------------------
# _check_external_properties
# ---------------------------------------------------------------------------

def test_check_external_properties_devuelve_las_dos_rutas(tmp_path):
    carpeta = _crear_properties(tmp_path / "props")

    idx, trg = geoserver_module._check_external_properties(carpeta)

    assert idx.endswith("indexer.properties")
    assert trg.endswith("timeregex.properties")


def test_check_external_properties_exige_indexer(tmp_path):
    carpeta = _crear_properties(tmp_path / "props", con_indexer=False)

    with pytest.raises(FileNotFoundError, match="indexer.properties"):
        geoserver_module._check_external_properties(carpeta)


def test_check_external_properties_exige_timeregex(tmp_path):
    carpeta = _crear_properties(tmp_path / "props", con_timeregex=False)

    with pytest.raises(FileNotFoundError, match="timeregex.properties"):
        geoserver_module._check_external_properties(carpeta)


def test_check_external_properties_advierte_por_formato_con_guiones(tmp_path, caplog):
    carpeta = _crear_properties(tmp_path / "props", timeregex=TIMEREGEX_GUIONES)

    geoserver_module._check_external_properties(carpeta)

    assert any("guiones" in registro.message for registro in caplog.records)


def test_check_external_properties_reconoce_el_formato_mensual(tmp_path, caplog):
    caplog.set_level(logging.INFO, logger="src.geoserver_import")
    carpeta = _crear_properties(tmp_path / "props", timeregex=TIMEREGEX_MENSUAL)

    geoserver_module._check_external_properties(carpeta)

    assert any("compatible con YYYYMM" in registro.message for registro in caplog.records)
    assert not any("No pude inferir" in registro.message for registro in caplog.records)


def test_check_external_properties_reconoce_el_formato_diario_sin_advertir(tmp_path, caplog):
    r"""Un timeregex válido para YYYYMMDD no debe disparar ninguna advertencia.

    Antes el ``else`` de "No pude inferir el formato" colgaba de la comprobación
    de ``\d{6}`` en vez de cerrar la cadena completa, así que un archivo correcto
    recibía a la vez el mensaje de compatibilidad y el aviso de formato
    desconocido.
    """
    caplog.set_level(logging.INFO, logger="src.geoserver_import")
    carpeta = _crear_properties(tmp_path / "props", timeregex=TIMEREGEX_OK)

    geoserver_module._check_external_properties(carpeta)

    mensajes = [registro.message for registro in caplog.records]
    assert any("compatible con YYYYMMDD" in mensaje for mensaje in mensajes)
    assert not any("No pude inferir" in mensaje for mensaje in mensajes)


def test_check_external_properties_advierte_si_no_reconoce_el_formato(tmp_path, caplog):
    caplog.set_level(logging.INFO, logger="src.geoserver_import")
    carpeta = _crear_properties(tmp_path / "props", timeregex="regex=cualquier-cosa\n")

    geoserver_module._check_external_properties(carpeta)

    mensajes = [registro.message for registro in caplog.records]
    assert any("No pude inferir" in mensaje for mensaje in mensajes)
    assert not any("parece compatible" in mensaje for mensaje in mensajes)


def test_check_external_properties_prefiere_el_formato_mas_especifico(tmp_path, caplog):
    """Con ambos patrones presentes gana YYYYMMDD y solo se emite un mensaje."""
    caplog.set_level(logging.INFO, logger="src.geoserver_import")
    carpeta = _crear_properties(
        tmp_path / "props", timeregex="regex=\\d{8}\n# alterno: \\d{6}\n"
    )

    geoserver_module._check_external_properties(carpeta)

    mensajes = [registro.message for registro in caplog.records]
    assert any("compatible con YYYYMMDD" in mensaje for mensaje in mensajes)
    assert not any("compatible con YYYYMM." in mensaje for mensaje in mensajes)


# ---------------------------------------------------------------------------
# _parse_period_from_filename
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "nombre, inicio, fin",
    [
        ("nad_deforestation_201701.tif", date(2017, 1, 1), date(2017, 3, 31)),
        ("nad_deforestation_201702.tif", date(2017, 4, 1), date(2017, 6, 30)),
        ("nad_deforestation_201703.tif", date(2017, 7, 1), date(2017, 9, 30)),
        ("atd_deforestation_202004.tif", date(2020, 10, 1), date(2020, 12, 31)),
    ],
)
def test_parse_period_trimestral(nombre, inicio, fin):
    assert geoserver_module._parse_period_from_filename(nombre) == (inicio, fin)


def test_parse_period_anual_simple():
    inicio, fin = geoserver_module._parse_period_from_filename(
        "smbyc_deforestation_annual_2013.tif"
    )

    assert (inicio, fin) == (date(2013, 1, 1), date(2013, 12, 31))


def test_parse_period_rango_de_anios():
    inicio, fin = geoserver_module._parse_period_from_filename(
        "smbyc_deforestation_annual_2010-2012.tif"
    )

    assert (inicio, fin) == (date(2010, 1, 1), date(2012, 12, 31))


def test_parse_period_formato_yyyymmdd():
    inicio, fin = geoserver_module._parse_period_from_filename(
        "smbyc_deforestation_annual_20100101-20120315.tif"
    )

    assert (inicio, fin) == (date(2010, 1, 1), date(2012, 3, 15))


def test_parse_period_formato_legacy_con_guiones():
    inicio, fin = geoserver_module._parse_period_from_filename(
        "smbyc_deforestation_annual_2010-01-01-2012-01-01.tif"
    )

    assert (inicio, fin) == (date(2010, 1, 1), date(2012, 1, 1))


def test_parse_period_usa_solo_el_nombre_del_archivo():
    inicio, _ = geoserver_module._parse_period_from_filename(
        "/datos/2099/smbyc_deforestation_annual_2013.tif"
    )

    assert inicio.year == 2013


@pytest.mark.parametrize(
    "nombre",
    [
        "archivo_sin_fecha.tif",
        "smbyc_deforestation.tif",
        "nad_deforestation_201713.tif",  # trimestre 13 no existe
        "datos_2013.tiff",  # los patrones exigen la extensión .tif
    ],
)
def test_parse_period_rechaza_nombres_no_reconocidos(nombre):
    with pytest.raises(ValueError, match="No se pudo extraer rango de fechas"):
        geoserver_module._parse_period_from_filename(nombre)


# ---------------------------------------------------------------------------
# _zip_tifs_and_props
# ---------------------------------------------------------------------------

def test_zip_tifs_and_props_incluye_rasters_y_properties(tmp_path):
    rasters = _crear_tifs(tmp_path / "rasters", ["a_2020.tif", "b_2021.tif"])
    props = _crear_properties(tmp_path / "props")

    zip_path = geoserver_module._zip_tifs_and_props(
        rasters, props, str(tmp_path / "tmp"), str(tmp_path / "zip"), "mosaic.zip"
    )

    assert zip_path.endswith("mosaic.zip")
    with zipfile.ZipFile(zip_path) as archivo:
        contenido = sorted(archivo.namelist())
    assert contenido == ["a_2020.tif", "b_2021.tif", "indexer.properties", "timeregex.properties"]


def test_zip_tifs_and_props_limpia_la_carpeta_temporal(tmp_path):
    rasters = _crear_tifs(tmp_path / "rasters", ["a_2020.tif"])
    props = _crear_properties(tmp_path / "props")
    tmp_dir = tmp_path / "tmp"

    geoserver_module._zip_tifs_and_props(
        rasters, props, str(tmp_dir), str(tmp_path / "zip"), "mosaic.zip"
    )

    assert not tmp_dir.exists()


def test_zip_tifs_and_props_devuelve_none_sin_rasters(tmp_path):
    vacia = tmp_path / "rasters"
    vacia.mkdir()
    props = _crear_properties(tmp_path / "props")

    resultado = geoserver_module._zip_tifs_and_props(
        str(vacia), props, str(tmp_path / "tmp"), str(tmp_path / "zip"), "mosaic.zip"
    )

    assert resultado is None


def test_zip_tifs_and_props_falla_sin_properties(tmp_path):
    rasters = _crear_tifs(tmp_path / "rasters", ["a_2020.tif"])
    props_vacia = tmp_path / "props"
    props_vacia.mkdir()

    with pytest.raises(FileNotFoundError):
        geoserver_module._zip_tifs_and_props(
            rasters, str(props_vacia), str(tmp_path / "tmp"), str(tmp_path / "zip"), "mosaic.zip"
        )


# ---------------------------------------------------------------------------
# _zip_tifs_only
# ---------------------------------------------------------------------------

def test_zip_tifs_only_incluye_solo_rasters(tmp_path):
    rasters = _crear_tifs(tmp_path / "rasters", ["a_2020.tif", "b_2021.tif"])

    zip_path = geoserver_module._zip_tifs_only(
        rasters, str(tmp_path / "tmp"), str(tmp_path / "zip"), "granules.zip"
    )

    with zipfile.ZipFile(zip_path) as archivo:
        assert sorted(archivo.namelist()) == ["a_2020.tif", "b_2021.tif"]


def test_zip_tifs_only_devuelve_none_sin_rasters(tmp_path):
    vacia = tmp_path / "rasters"
    vacia.mkdir()

    resultado = geoserver_module._zip_tifs_only(
        str(vacia), str(tmp_path / "tmp"), str(tmp_path / "zip"), "granules.zip"
    )

    assert resultado is None


# ---------------------------------------------------------------------------
# GeoserverClient
# ---------------------------------------------------------------------------

class _CatalogoFalso:
    def __init__(self, store=None, recurso=None):
        self.store = store
        self.recurso = recurso
        self.mosaicos_creados = []
        self.harvests = []
        self.guardados = []
        self.workspaces = {"deforestation": object()}

    def get_workspace(self, nombre):
        return self.workspaces.get(nombre)

    def get_store(self, nombre, workspace):
        if self.store is None:
            raise LookupError("no existe")
        return self.store

    def get_resource(self, nombre, workspace=None):
        return self.recurso

    def create_imagemosaic(self, store_name, zip_path, workspace=None):
        self.mosaicos_creados.append((store_name, zip_path))

    def harvest_uploadgranule(self, zip_path, store):
        self.harvests.append((zip_path, store))

    def save(self, recurso):
        self.guardados.append(recurso)


def test_client_connect_asigna_el_catalogo(monkeypatch):
    monkeypatch.setattr(
        geoserver_module, "Catalog", lambda url, username, password: _CatalogoFalso()
    )
    cliente = geoserver_module.GeoserverClient("https://host/rest/", "admin", "clave")

    cliente.connect()

    assert cliente.catalog is not None


def test_client_connect_termina_el_proceso_si_falla(monkeypatch):
    def explota(url, username, password):
        raise ConnectionError("inaccesible")

    monkeypatch.setattr(geoserver_module, "Catalog", explota)
    cliente = geoserver_module.GeoserverClient("https://host/rest/", "admin", "clave")

    with pytest.raises(SystemExit):
        cliente.connect()


def test_client_get_workspace_sin_catalogo_falla():
    cliente = geoserver_module.GeoserverClient("https://host/rest/", "admin", "clave")

    with pytest.raises(RuntimeError, match="no inicializado"):
        cliente.get_workspace("deforestation")


def test_client_get_workspace_encuentra_el_espacio():
    cliente = geoserver_module.GeoserverClient("https://host/rest/", "admin", "clave")
    cliente.catalog = _CatalogoFalso()

    cliente.get_workspace("deforestation")

    assert cliente.workspace_name == "deforestation"
    assert cliente.workspace is not None


def test_client_get_workspace_termina_si_no_existe():
    cliente = geoserver_module.GeoserverClient("https://host/rest/", "admin", "clave")
    cliente.catalog = _CatalogoFalso()

    with pytest.raises(SystemExit):
        cliente.get_workspace("inexistente")


def test_client_get_store_devuelve_none_sin_workspace():
    cliente = geoserver_module.GeoserverClient("https://host/rest/", "admin", "clave")

    assert cliente.get_store("smbyc") is None


def test_client_get_store_devuelve_none_si_el_catalogo_falla():
    cliente = geoserver_module.GeoserverClient("https://host/rest/", "admin", "clave")
    cliente.catalog = _CatalogoFalso(store=None)
    cliente.workspace = object()

    assert cliente.get_store("smbyc") is None


def test_client_get_store_devuelve_el_store():
    marcador = object()
    cliente = geoserver_module.GeoserverClient("https://host/rest/", "admin", "clave")
    cliente.catalog = _CatalogoFalso(store=marcador)
    cliente.workspace = object()

    assert cliente.get_store("smbyc") is marcador


def test_client_habilita_la_dimension_temporal():
    class Recurso:
        def __init__(self):
            self.metadata = {}

    recurso = Recurso()
    catalogo = _CatalogoFalso(recurso=recurso)
    cliente = geoserver_module.GeoserverClient("https://host/rest/", "admin", "clave")
    cliente.catalog = catalogo

    cliente._enable_time_dimension("smbyc")

    assert "time" in recurso.metadata
    assert catalogo.guardados == [recurso]


def test_client_tolera_coverage_ausente():
    catalogo = _CatalogoFalso(recurso=None)
    cliente = geoserver_module.GeoserverClient("https://host/rest/", "admin", "clave")
    cliente.catalog = catalogo

    cliente._enable_time_dimension("smbyc")

    assert catalogo.guardados == []


def test_client_create_mosaic_publica_y_habilita_tiempo(tmp_path):
    rasters = _crear_tifs(tmp_path / "rasters", ["a_2020.tif"])
    props = _crear_properties(tmp_path / "props")

    class Recurso:
        metadata = {}

    catalogo = _CatalogoFalso(recurso=Recurso())
    cliente = geoserver_module.GeoserverClient("https://host/rest/", "admin", "clave")
    cliente.catalog = catalogo

    cliente.create_mosaic("smbyc", rasters, props, str(tmp_path / "tmp"), str(tmp_path / "zip"))

    assert len(catalogo.mosaicos_creados) == 1
    assert catalogo.mosaicos_creados[0][0] == "smbyc"
    assert catalogo.guardados


def test_client_create_mosaic_sin_catalogo_falla(tmp_path):
    cliente = geoserver_module.GeoserverClient("https://host/rest/", "admin", "clave")

    with pytest.raises(RuntimeError, match="no inicializado"):
        cliente.create_mosaic("smbyc", str(tmp_path), str(tmp_path), str(tmp_path), str(tmp_path))


def test_client_create_mosaic_no_publica_sin_rasters(tmp_path):
    vacia = tmp_path / "rasters"
    vacia.mkdir()
    props = _crear_properties(tmp_path / "props")
    catalogo = _CatalogoFalso()
    cliente = geoserver_module.GeoserverClient("https://host/rest/", "admin", "clave")
    cliente.catalog = catalogo

    cliente.create_mosaic(
        "smbyc", str(vacia), props, str(tmp_path / "tmp"), str(tmp_path / "zip")
    )

    assert catalogo.mosaicos_creados == []


def test_client_update_mosaic_hace_harvest(tmp_path):
    rasters = _crear_tifs(tmp_path / "rasters", ["a_2020.tif"])

    class Recurso:
        metadata = {}

    catalogo = _CatalogoFalso(recurso=Recurso())
    cliente = geoserver_module.GeoserverClient("https://host/rest/", "admin", "clave")
    cliente.catalog = catalogo
    store = type("Store", (), {"name": "smbyc"})()

    cliente.update_mosaic(store, rasters, str(tmp_path / "tmp"), str(tmp_path / "zip"))

    assert len(catalogo.harvests) == 1
    assert catalogo.harvests[0][1] is store


def test_client_update_mosaic_no_hace_nada_sin_rasters(tmp_path):
    vacia = tmp_path / "rasters"
    vacia.mkdir()
    catalogo = _CatalogoFalso()
    cliente = geoserver_module.GeoserverClient("https://host/rest/", "admin", "clave")
    cliente.catalog = catalogo
    store = type("Store", (), {"name": "smbyc"})()

    cliente.update_mosaic(store, str(vacia), str(tmp_path / "tmp"), str(tmp_path / "zip"))

    assert catalogo.harvests == []


# ---------------------------------------------------------------------------
# _save_mosaic_records_to_mongo
# ---------------------------------------------------------------------------

class _Deforestacion:
    creados = []
    encontrado = None

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.saved = False
        for clave, valor in kwargs.items():
            setattr(self, clave, valor)
        _Deforestacion.creados.append(self)

    def save(self):
        self.saved = True
        return self

    @staticmethod
    def objects(**kwargs):
        encontrado = _Deforestacion.encontrado
        return type("QS", (), {"first": staticmethod(lambda: encontrado)})()


@pytest.fixture()
def deforestacion_stub(monkeypatch):
    _Deforestacion.creados = []
    _Deforestacion.encontrado = None
    monkeypatch.setattr(geoserver_module, "Deforestation", _Deforestacion)
    monkeypatch.setattr(geoserver_module, "connect", lambda **kwargs: None)
    return _Deforestacion


def test_save_mosaic_records_crea_registros(tmp_path, deforestacion_stub):
    carpeta = _crear_tifs(
        tmp_path / "rasters",
        ["smbyc_deforestation_annual_2013.tif", "smbyc_deforestation_annual_2014.tif"],
    )

    geoserver_module._save_mosaic_records_to_mongo(carpeta, "smbyc_annual", "smbyc")

    assert len(deforestacion_stub.creados) == 2
    creado = deforestacion_stub.creados[0]
    assert creado.kwargs["path"] == "smbyc_annual"
    assert creado.kwargs["period_start"] == date(2013, 1, 1)
    assert creado.saved is True


def test_save_mosaic_records_actualiza_el_existente(tmp_path, deforestacion_stub):
    carpeta = _crear_tifs(tmp_path / "rasters", ["smbyc_deforestation_annual_2013.tif"])

    class Existente:
        def __init__(self):
            self.path = "viejo"
            self.log = type("Log", (), {"updated": None})()
            self.saved = False

        def save(self):
            self.saved = True

    existente = Existente()
    deforestacion_stub.encontrado = existente

    geoserver_module._save_mosaic_records_to_mongo(carpeta, "smbyc_annual", "smbyc")

    assert deforestacion_stub.creados == []
    assert existente.path == "smbyc_annual"
    assert existente.saved is True
    assert existente.log.updated is not None


@pytest.mark.parametrize(
    "store_name, tipo_esperado",
    [
        ("smbyc_annual", "ANNUAL"),
        ("smbyc_cumulative", "CUMULATIVE"),
        ("nad", "NAD"),
        ("atd", "ATD"),
        ("otro_store", "ANNUAL"),
    ],
)
def test_save_mosaic_records_deduce_el_tipo_desde_el_store(
    tmp_path, deforestacion_stub, store_name, tipo_esperado
):
    carpeta = _crear_tifs(tmp_path / store_name, ["smbyc_deforestation_annual_2013.tif"])

    geoserver_module._save_mosaic_records_to_mongo(carpeta, store_name, "smbyc")

    assert deforestacion_stub.creados[0].kwargs["deforestation_type"].name == tipo_esperado


def test_save_mosaic_records_ignora_fuente_desconocida(tmp_path, deforestacion_stub):
    carpeta = _crear_tifs(tmp_path / "rasters", ["smbyc_deforestation_annual_2013.tif"])

    geoserver_module._save_mosaic_records_to_mongo(carpeta, "smbyc", "fuente_inventada")

    assert deforestacion_stub.creados == []


def test_save_mosaic_records_omite_carpeta_inexistente(deforestacion_stub):
    geoserver_module._save_mosaic_records_to_mongo("/no/existe", "smbyc", "smbyc")

    assert deforestacion_stub.creados == []


def test_save_mosaic_records_omite_carpeta_sin_tifs(tmp_path, deforestacion_stub):
    vacia = tmp_path / "rasters"
    vacia.mkdir()

    geoserver_module._save_mosaic_records_to_mongo(str(vacia), "smbyc", "smbyc")

    assert deforestacion_stub.creados == []


def test_save_mosaic_records_salta_los_nombres_sin_fecha(tmp_path, deforestacion_stub):
    carpeta = _crear_tifs(
        tmp_path / "rasters", ["sin_fecha.tif", "smbyc_deforestation_annual_2013.tif"]
    )

    geoserver_module._save_mosaic_records_to_mongo(carpeta, "smbyc", "smbyc")

    assert len(deforestacion_stub.creados) == 1


# ---------------------------------------------------------------------------
# process_geoserver_mosaics
# ---------------------------------------------------------------------------

def test_process_falla_si_faltan_variables_de_configuracion(monkeypatch, tmp_path):
    monkeypatch.setattr(geoserver_module, "config", {"GEOSERVER_URL": "", "GEOSERVER_USER": None})

    with pytest.raises(RuntimeError, match="Faltan variables"):
        geoserver_module.process_geoserver_mosaics(str(tmp_path), "smbyc", "smbyc")


def _config_completa():
    return {
        "GEOSERVER_URL": "https://host/geoserver",
        "GEOSERVER_USER": "admin",
        "GEOSERVER_PWD": "clave",
        "GEO_WORKSPACE": "deforestation",
    }


def test_process_falla_si_no_existe_la_carpeta_de_tifs(monkeypatch):
    monkeypatch.setattr(geoserver_module, "config", _config_completa())

    with pytest.raises(FileNotFoundError, match="Carpeta de TIFFs no encontrada"):
        geoserver_module.process_geoserver_mosaics("/no/existe", "smbyc", "smbyc")


def test_process_falla_si_la_carpeta_esta_vacia(monkeypatch, tmp_path):
    monkeypatch.setattr(geoserver_module, "config", _config_completa())
    vacia = tmp_path / "rasters"
    vacia.mkdir()

    with pytest.raises(FileNotFoundError, match="No hay archivos .tif"):
        geoserver_module.process_geoserver_mosaics(str(vacia), "smbyc", "smbyc")


def test_process_falla_si_no_encuentra_las_properties(monkeypatch, tmp_path):
    monkeypatch.setattr(geoserver_module, "config", _config_completa())
    carpeta = _crear_tifs(tmp_path / "rasters", ["a_2020.tif"])

    with pytest.raises(FileNotFoundError, match="No se encontró carpeta de propiedades"):
        geoserver_module.process_geoserver_mosaics(carpeta, "smbyc", "fuente_sin_carpeta")
