"""Pruebas del cliente de GeoServer usado para shapefiles y mosaicos.

Es una clase distinta de la de ``src/geoserver_import.py``; ambas conviven en
el proyecto y esta es la que usan las cargas de shapefiles.
"""

import os
import zipfile

import pytest

import src.tools as tools_module
from src.tools import GeoserverClient


class _CatalogoFalso:
    def __init__(self, workspace=None, store=None):
        self._workspace = workspace
        self._store = store
        self.mosaicos = []
        self.featurestores = []
        self.harvests = []

    def get_workspace(self, nombre):
        return self._workspace

    def get_store(self, nombre, workspace):
        if isinstance(self._store, Exception):
            raise self._store
        return self._store

    def create_imagemosaic(self, store_name, zip_path, workspace=None):
        self.mosaicos.append((store_name, zip_path, workspace))

    def create_featurestore(self, store_name, data=None, workspace=None):
        self.featurestores.append((store_name, data, workspace))

    def harvest_uploadgranule(self, zip_path, store):
        self.harvests.append((zip_path, store))


def _cliente(url="https://host/geoserver/rest"):
    return GeoserverClient(url, "admin", "clave")


# ---------------------------------------------------------------------------
# Construcción y conexión
# ---------------------------------------------------------------------------

def test_la_url_siempre_termina_en_barra():
    assert _cliente("https://host/geoserver/rest").url == "https://host/geoserver/rest/"
    assert _cliente("https://host/geoserver/rest/").url == "https://host/geoserver/rest/"


def test_connect_asigna_el_catalogo(monkeypatch):
    monkeypatch.setattr(
        tools_module, "Catalog", lambda url, username, password: _CatalogoFalso()
    )
    cliente = _cliente()

    cliente.connect()

    assert cliente.catalog is not None


def test_connect_traduce_el_error_en_connection_error(monkeypatch):
    def explota(url, username, password):
        raise OSError("host inaccesible")

    monkeypatch.setattr(tools_module, "Catalog", explota)

    with pytest.raises(ConnectionError, match="Error de conexión a GeoServer"):
        _cliente().connect()


# ---------------------------------------------------------------------------
# Workspaces y stores
# ---------------------------------------------------------------------------

def test_get_workspace_sin_conectar_falla():
    with pytest.raises(RuntimeError, match="Catalog no inicializado"):
        _cliente().get_workspace("administrative")


def test_get_workspace_encuentra_el_espacio():
    cliente = _cliente()
    marcador = object()
    cliente.catalog = _CatalogoFalso(workspace=marcador)

    cliente.get_workspace("administrative")

    assert cliente.workspace is marcador
    assert cliente.workspace_name == "administrative"


def test_get_workspace_falla_si_no_existe():
    cliente = _cliente()
    cliente.catalog = _CatalogoFalso(workspace=None)

    with pytest.raises(ValueError, match="no encontrado"):
        cliente.get_workspace("inexistente")


def test_get_store_sin_workspace_falla():
    cliente = _cliente()
    cliente.catalog = _CatalogoFalso()

    with pytest.raises(RuntimeError, match="Workspace no inicializado"):
        cliente.get_store("adm1")


def test_get_store_devuelve_el_store():
    cliente = _cliente()
    marcador = object()
    cliente.catalog = _CatalogoFalso(store=marcador)
    cliente.workspace = object()

    assert cliente.get_store("adm1") is marcador


def test_get_store_devuelve_none_si_el_catalogo_lanza():
    cliente = _cliente()
    cliente.catalog = _CatalogoFalso(store=LookupError("no existe"))
    cliente.workspace = object()

    assert cliente.get_store("adm1") is None


# ---------------------------------------------------------------------------
# zip_mosaic_files
# ---------------------------------------------------------------------------

def _crear_properties(carpeta, cantidad=2):
    carpeta.mkdir(parents=True, exist_ok=True)
    nombres = ["indexer.properties", "timeregex.properties", "extra.properties"]
    for nombre in nombres[:cantidad]:
        (carpeta / nombre).write_text("clave=valor", encoding="utf-8")
    return str(carpeta)


def _crear_rasters(carpeta, nombres):
    carpeta.mkdir(parents=True, exist_ok=True)
    for nombre in nombres:
        (carpeta / nombre).write_bytes(b"raster")
    return str(carpeta)


def test_zip_mosaic_files_empaqueta_rasters_y_properties(tmp_path):
    rasters = _crear_rasters(tmp_path / "rasters", ["a_2020.tif", "b_2021.tif"])
    props = _crear_properties(tmp_path / "props")
    salida = tmp_path / "salida"
    salida.mkdir()

    zip_path = _cliente().zip_mosaic_files(
        rasters, props, str(tmp_path / "tmp"), str(salida)
    )

    assert zip_path.endswith("mosaic.zip")
    with zipfile.ZipFile(zip_path) as archivo:
        contenido = sorted(archivo.namelist())
    assert contenido == ["a_2020.tif", "b_2021.tif", "indexer.properties", "timeregex.properties"]


def test_zip_mosaic_files_acepta_un_unico_archivo(tmp_path):
    carpeta = _crear_rasters(tmp_path / "rasters", ["solo.tif"])
    props = _crear_properties(tmp_path / "props")
    salida = tmp_path / "salida"
    salida.mkdir()

    zip_path = _cliente().zip_mosaic_files(
        os.path.join(carpeta, "solo.tif"), props, str(tmp_path / "tmp"), str(salida)
    )

    with zipfile.ZipFile(zip_path) as archivo:
        assert "solo.tif" in archivo.namelist()


def test_zip_mosaic_files_exige_exactamente_dos_properties(tmp_path):
    rasters = _crear_rasters(tmp_path / "rasters", ["a.tif"])
    props = _crear_properties(tmp_path / "props", cantidad=3)
    salida = tmp_path / "salida"
    salida.mkdir()

    with pytest.raises(ValueError, match="exactamente 2 archivos"):
        _cliente().zip_mosaic_files(rasters, props, str(tmp_path / "tmp"), str(salida))


def test_zip_mosaic_files_falla_con_una_sola_property(tmp_path):
    rasters = _crear_rasters(tmp_path / "rasters", ["a.tif"])
    props = _crear_properties(tmp_path / "props", cantidad=1)
    salida = tmp_path / "salida"
    salida.mkdir()

    with pytest.raises(ValueError, match="exactamente 2 archivos"):
        _cliente().zip_mosaic_files(rasters, props, str(tmp_path / "tmp"), str(salida))


def test_zip_mosaic_files_devuelve_none_si_falta_la_ruta(tmp_path):
    props = _crear_properties(tmp_path / "props")

    resultado = _cliente().zip_mosaic_files(
        str(tmp_path / "no-existe"), props, str(tmp_path / "tmp"), str(tmp_path)
    )

    assert resultado is None


def test_zip_mosaic_files_devuelve_none_si_faltan_las_properties(tmp_path):
    rasters = _crear_rasters(tmp_path / "rasters", ["a.tif"])

    resultado = _cliente().zip_mosaic_files(
        rasters, str(tmp_path / "no-existe"), str(tmp_path / "tmp"), str(tmp_path)
    )

    assert resultado is None


def test_zip_mosaic_files_reinicia_la_carpeta_temporal(tmp_path):
    rasters = _crear_rasters(tmp_path / "rasters", ["a.tif"])
    props = _crear_properties(tmp_path / "props")
    tmp_dir = tmp_path / "tmp"
    tmp_dir.mkdir()
    (tmp_dir / "residuo.tif").write_bytes(b"viejo")
    salida = tmp_path / "salida"
    salida.mkdir()

    zip_path = _cliente().zip_mosaic_files(rasters, props, str(tmp_dir), str(salida))

    with zipfile.ZipFile(zip_path) as archivo:
        assert "residuo.tif" not in archivo.namelist()


# ---------------------------------------------------------------------------
# update_mosaic
# ---------------------------------------------------------------------------

def test_update_mosaic_llama_a_harvest(tmp_path):
    rasters = _crear_rasters(tmp_path / "rasters", ["a.tif"])
    props = _crear_properties(tmp_path / "props")
    salida = tmp_path / "salida"
    salida.mkdir()

    cliente = _cliente()
    catalogo = _CatalogoFalso()
    cliente.catalog = catalogo
    store = object()

    cliente.update_mosaic(store, rasters, props, str(tmp_path / "tmp"), str(salida))

    assert len(catalogo.harvests) == 1
    assert catalogo.harvests[0][1] is store


def test_update_mosaic_no_hace_nada_sin_zip(tmp_path):
    cliente = _cliente()
    catalogo = _CatalogoFalso()
    cliente.catalog = catalogo

    cliente.update_mosaic(
        object(), str(tmp_path / "no-existe"), str(tmp_path / "tampoco"),
        str(tmp_path / "tmp"), str(tmp_path)
    )

    assert catalogo.harvests == []


# ---------------------------------------------------------------------------
# create_shp_datastore
# ---------------------------------------------------------------------------

def _zip_shapefile(ruta, base="capa", extensiones=("shp", "shx", "dbf", "prj")):
    with zipfile.ZipFile(ruta, "w") as archivo:
        for extension in extensiones:
            archivo.writestr(f"{base}.{extension}", b"contenido")
    return str(ruta)


def test_create_shp_datastore_publica_el_shapefile(tmp_path, monkeypatch):
    zip_path = _zip_shapefile(tmp_path / "capa.zip")
    cliente = _cliente()
    catalogo = _CatalogoFalso()
    cliente.catalog = catalogo
    workspace = object()

    cliente.create_shp_datastore(zip_path, "adm1", workspace=workspace, layer_name="admin_1")

    assert len(catalogo.featurestores) == 1
    nombre, data, ws = catalogo.featurestores[0]
    assert nombre == "adm1"
    assert ws is workspace
    assert data.endswith(".zip")


def test_create_shp_datastore_renombra_los_archivos_a_la_capa(tmp_path):
    zip_path = _zip_shapefile(tmp_path / "capa.zip", base="original")
    cliente = _cliente()
    catalogo = _CatalogoFalso()
    cliente.catalog = catalogo
    cliente.workspace = object()

    cliente.create_shp_datastore(zip_path, "adm1", layer_name="admin_1")

    _, nuevo_zip, _ = catalogo.featurestores[0]
    with zipfile.ZipFile(nuevo_zip) as archivo:
        nombres = sorted(archivo.namelist())
    assert nombres == ["admin_1.dbf", "admin_1.prj", "admin_1.shp", "admin_1.shx"]


def test_create_shp_datastore_conserva_el_nombre_base_sin_layer_name(tmp_path):
    zip_path = _zip_shapefile(tmp_path / "capa.zip", base="veredas")
    cliente = _cliente()
    catalogo = _CatalogoFalso()
    cliente.catalog = catalogo
    cliente.workspace = object()

    cliente.create_shp_datastore(zip_path, "adm3")

    _, nuevo_zip, _ = catalogo.featurestores[0]
    with zipfile.ZipFile(nuevo_zip) as archivo:
        assert "veredas.shp" in archivo.namelist()


def test_create_shp_datastore_falla_si_el_zip_no_existe(tmp_path):
    cliente = _cliente()
    cliente.catalog = _CatalogoFalso()
    cliente.workspace = object()

    with pytest.raises(FileNotFoundError, match="Archivo no encontrado"):
        cliente.create_shp_datastore(str(tmp_path / "no-existe.zip"), "adm1")


def test_create_shp_datastore_falla_sin_workspace(tmp_path):
    zip_path = _zip_shapefile(tmp_path / "capa.zip")
    cliente = _cliente()
    cliente.catalog = _CatalogoFalso()

    with pytest.raises(ValueError, match="Workspace no definido"):
        cliente.create_shp_datastore(zip_path, "adm1")


def test_create_shp_datastore_falla_si_el_zip_no_trae_shp(tmp_path):
    zip_path = tmp_path / "sin_shp.zip"
    with zipfile.ZipFile(zip_path, "w") as archivo:
        archivo.writestr("leeme.txt", b"x")

    cliente = _cliente()
    cliente.catalog = _CatalogoFalso()
    cliente.workspace = object()

    with pytest.raises(Exception, match="No se encontró ningún archivo .shp"):
        cliente.create_shp_datastore(str(zip_path), "adm1")


def test_create_shp_datastore_conecta_si_hace_falta(tmp_path, monkeypatch):
    zip_path = _zip_shapefile(tmp_path / "capa.zip")
    catalogo = _CatalogoFalso()
    monkeypatch.setattr(
        tools_module, "Catalog", lambda url, username, password: catalogo
    )

    cliente = _cliente()
    cliente.create_shp_datastore(zip_path, "adm1", workspace=object())

    assert cliente.catalog is catalogo
    assert len(catalogo.featurestores) == 1


# ---------------------------------------------------------------------------
# delete_folder_content
# ---------------------------------------------------------------------------

def test_delete_folder_content_borra_archivos_y_subcarpetas(tmp_path):
    carpeta = tmp_path / "trabajo"
    carpeta.mkdir()
    (carpeta / "archivo.tif").write_bytes(b"x")
    subcarpeta = carpeta / "sub"
    subcarpeta.mkdir()
    (subcarpeta / "otro.tif").write_bytes(b"y")

    _cliente().delete_folder_content(str(carpeta))

    assert carpeta.is_dir()
    assert list(carpeta.iterdir()) == []


def test_delete_folder_content_con_carpeta_vacia(tmp_path):
    carpeta = tmp_path / "vacia"
    carpeta.mkdir()

    _cliente().delete_folder_content(str(carpeta))

    assert list(carpeta.iterdir()) == []
