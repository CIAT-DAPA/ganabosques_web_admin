"""Pruebas de la carga de archivos espaciales y su publicación en GeoServer."""

import io
import os
import zipfile

import pytest

import src.routes.spatial_data_management as spatial_module


# ---------------------------------------------------------------------------
# allowed_file
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "nombre",
    ["datos.zip", "raster.tif", "raster.TIF", "tabla.csv", "hoja.xlsx", "capa.shp", "raster.tiff"],
)
def test_allowed_file_acepta_extensiones_permitidas(nombre):
    assert spatial_module.allowed_file(nombre) is True


@pytest.mark.parametrize(
    "nombre",
    ["script.exe", "notas.txt", "sin_extension", "imagen.png", "archivo."],
)
def test_allowed_file_rechaza_extensiones_no_permitidas(nombre):
    assert spatial_module.allowed_file(nombre) is False


def test_allowed_file_usa_la_ultima_extension():
    assert spatial_module.allowed_file("respaldo.zip.txt") is False
    assert spatial_module.allowed_file("respaldo.txt.zip") is True


def test_allowed_file_acepta_nombres_sin_base():
    """Un nombre como '.zip' pasa la validación: solo se mira lo que sigue al último punto."""
    assert spatial_module.allowed_file(".zip") is True


# ---------------------------------------------------------------------------
# Mapeo de tipos de deforestación
# ---------------------------------------------------------------------------

def test_mapa_de_deforestacion_cubre_las_tres_fuentes():
    assert spatial_module.DEFORESTATION_TYPE_MAP == {
        "deforestation_smbyc": ("smbyc", "smbyc"),
        "deforestation_nad": ("nad", "nad"),
        "deforestation_atd": ("atd", "atd"),
    }


# ---------------------------------------------------------------------------
# Ruta /importar
# ---------------------------------------------------------------------------

def _zip_en_memoria(nombres):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archivo:
        for nombre in nombres:
            archivo.writestr(nombre, b"contenido raster")
    buffer.seek(0)
    return buffer


def _mensajes_flash(cliente):
    with cliente.session_transaction() as sesion:
        return [mensaje for _, mensaje in sesion.get("_flashes", [])]


def test_importar_get_renderiza_el_formulario(make_app, capture_render):
    capturado = capture_render(spatial_module)
    app = make_app(spatial_module.spatial_bp)

    respuesta = app.test_client().get("/importar")

    assert respuesta.status_code == 200
    assert capturado["template"] == "upload.html"
    assert capturado["context"]["active_page"] == "importar"
    assert isinstance(capturado["context"]["current_year"], int)


def test_importar_niveles_administrativos_procesa_el_csv(make_app, monkeypatch, tmp_path):
    llamadas = {}

    def fake_importar(ruta, nivel):
        llamadas["ruta"] = ruta
        llamadas["nivel"] = nivel

    monkeypatch.setattr(spatial_module, "importar_desde_csv", fake_importar)
    monkeypatch.setattr(spatial_module, "UPLOAD_FOLDER", str(tmp_path))
    monkeypatch.setattr(spatial_module, "render_template", lambda *a, **kw: "ok")

    app = make_app(spatial_module.spatial_bp)
    datos = {
        "file_type": "levels_adm",
        "level": "departamento",
        "file": (io.BytesIO(b"COD_DEPARTAMENTO\n05\n"), "niveles.csv"),
    }

    respuesta = app.test_client().post("/importar", data=datos, content_type="multipart/form-data")

    assert respuesta.status_code == 200
    assert llamadas["nivel"] == "departamento"
    assert llamadas["ruta"].endswith("niveles.csv")
    # El archivo temporal se elimina tras la importación
    assert not os.path.exists(llamadas["ruta"])


def test_importar_niveles_administrativos_rechaza_archivo_no_csv(make_app, monkeypatch, tmp_path):
    monkeypatch.setattr(spatial_module, "UPLOAD_FOLDER", str(tmp_path))
    app = make_app(spatial_module.spatial_bp)
    datos = {
        "file_type": "levels_adm",
        "level": "departamento",
        "file": (io.BytesIO(b"x"), "niveles.txt"),
    }

    with app.test_client() as cliente:
        respuesta = cliente.post("/importar", data=datos, content_type="multipart/form-data")
        mensajes = _mensajes_flash(cliente)

    assert respuesta.status_code == 302
    assert "El archivo debe ser un CSV." in mensajes


def test_importar_niveles_administrativos_informa_error_de_importacion(
    make_app, monkeypatch, tmp_path
):
    def explota(ruta, nivel):
        raise ValueError("Faltan columnas")

    monkeypatch.setattr(spatial_module, "importar_desde_csv", explota)
    monkeypatch.setattr(spatial_module, "UPLOAD_FOLDER", str(tmp_path))
    monkeypatch.setattr(spatial_module, "render_template", lambda *a, **kw: "ok")

    app = make_app(spatial_module.spatial_bp)
    datos = {
        "file_type": "levels_adm",
        "level": "departamento",
        "file": (io.BytesIO(b"COD\n1\n"), "niveles.csv"),
    }

    with app.test_client() as cliente:
        respuesta = cliente.post("/importar", data=datos, content_type="multipart/form-data")
        mensajes = _mensajes_flash(cliente)

    assert respuesta.status_code == 200
    assert any("Error durante la importacion" in mensaje for mensaje in mensajes)


@pytest.mark.parametrize(
    "file_type, store_esperado",
    [
        ("deforestation_smbyc", "smbyc"),
        ("deforestation_nad", "nad"),
        ("deforestation_atd", "atd"),
    ],
)
def test_importar_deforestacion_extrae_tifs_y_publica(
    make_app, monkeypatch, tmp_path, file_type, store_esperado
):
    llamadas = {}

    def fake_process(output_dir, store_name, source):
        llamadas["output_dir"] = output_dir
        llamadas["store_name"] = store_name
        llamadas["source"] = source
        llamadas["tifs"] = sorted(os.listdir(output_dir))

    monkeypatch.setattr(spatial_module, "process_geoserver_mosaics", fake_process)
    monkeypatch.setattr(spatial_module, "UPLOAD_FOLDER", str(tmp_path))

    app = make_app(spatial_module.spatial_bp)
    datos = {
        "file_type": file_type,
        "file": (_zip_en_memoria(["a_2020.tif", "b_2021.tif"]), "rasters.zip"),
    }

    with app.test_client() as cliente:
        respuesta = cliente.post("/importar", data=datos, content_type="multipart/form-data")
        mensajes = _mensajes_flash(cliente)

    assert respuesta.status_code == 302
    assert llamadas["store_name"] == store_esperado
    assert llamadas["source"] == store_esperado
    assert llamadas["tifs"] == ["a_2020.tif", "b_2021.tif"]
    assert any("2 archivo(s) TIFF" in mensaje for mensaje in mensajes)


def test_importar_deforestacion_ignora_entradas_macosx(make_app, monkeypatch, tmp_path):
    extraidos = {}

    def fake_process(output_dir, store_name, source):
        extraidos["tifs"] = sorted(os.listdir(output_dir))

    monkeypatch.setattr(spatial_module, "process_geoserver_mosaics", fake_process)
    monkeypatch.setattr(spatial_module, "UPLOAD_FOLDER", str(tmp_path))

    app = make_app(spatial_module.spatial_bp)
    datos = {
        "file_type": "deforestation_nad",
        "file": (_zip_en_memoria(["__MACOSX/._a.tif", "real_2020.tif"]), "rasters.zip"),
    }

    app.test_client().post("/importar", data=datos, content_type="multipart/form-data")

    assert extraidos["tifs"] == ["real_2020.tif"]


def test_importar_deforestacion_avisa_si_el_zip_no_trae_tifs(make_app, monkeypatch, tmp_path):
    llamado = []
    monkeypatch.setattr(
        spatial_module, "process_geoserver_mosaics", lambda *a, **kw: llamado.append(a)
    )
    monkeypatch.setattr(spatial_module, "UPLOAD_FOLDER", str(tmp_path))

    app = make_app(spatial_module.spatial_bp)
    datos = {
        "file_type": "deforestation_smbyc",
        "file": (_zip_en_memoria(["leeme.txt"]), "rasters.zip"),
    }

    with app.test_client() as cliente:
        respuesta = cliente.post("/importar", data=datos, content_type="multipart/form-data")
        mensajes = _mensajes_flash(cliente)

    assert respuesta.status_code == 302
    assert llamado == []
    assert any("No se encontraron archivos .tif/.tiff" in mensaje for mensaje in mensajes)


def test_importar_deforestacion_exige_zip(make_app, monkeypatch, tmp_path):
    monkeypatch.setattr(spatial_module, "UPLOAD_FOLDER", str(tmp_path))
    app = make_app(spatial_module.spatial_bp)
    datos = {
        "file_type": "deforestation_nad",
        "file": (io.BytesIO(b"no soy zip"), "raster.tif"),
    }

    with app.test_client() as cliente:
        respuesta = cliente.post("/importar", data=datos, content_type="multipart/form-data")
        mensajes = _mensajes_flash(cliente)

    assert respuesta.status_code == 302
    assert any(".zip que contenga los archivos TIFF" in mensaje for mensaje in mensajes)


def test_importar_deforestacion_exige_archivo(make_app, monkeypatch, tmp_path):
    monkeypatch.setattr(spatial_module, "UPLOAD_FOLDER", str(tmp_path))
    app = make_app(spatial_module.spatial_bp)

    with app.test_client() as cliente:
        respuesta = cliente.post(
            "/importar",
            data={"file_type": "deforestation_nad"},
            content_type="multipart/form-data",
        )
        mensajes = _mensajes_flash(cliente)

    assert respuesta.status_code == 302
    assert "No se seleccionó ningún archivo." in mensajes


def test_importar_deforestacion_informa_error_de_geoserver(make_app, monkeypatch, tmp_path):
    def explota(output_dir, store_name, source):
        raise RuntimeError("GeoServer no responde")

    monkeypatch.setattr(spatial_module, "process_geoserver_mosaics", explota)
    monkeypatch.setattr(spatial_module, "UPLOAD_FOLDER", str(tmp_path))

    app = make_app(spatial_module.spatial_bp)
    datos = {
        "file_type": "deforestation_atd",
        "file": (_zip_en_memoria(["a_2020.tif"]), "rasters.zip"),
    }

    with app.test_client() as cliente:
        respuesta = cliente.post("/importar", data=datos, content_type="multipart/form-data")
        mensajes = _mensajes_flash(cliente)

    assert respuesta.status_code == 302
    assert any("Error al procesar deforestación" in mensaje for mensaje in mensajes)


@pytest.mark.parametrize(
    "file_type, store_esperado, capa_esperada",
    [
        ("veredas", "adm3", "admin_3"),
        ("adm1", "adm1", "admin_1"),
        ("adm2", "adm2", "admin_2"),
        ("upra", "upra", "upra_boundaries"),
        ("protected_areas", "protected_areas", "pnn_areas"),
    ],
)
def test_importar_shapefile_publica_con_el_store_y_capa_correctos(
    make_app, monkeypatch, tmp_path, file_type, store_esperado, capa_esperada
):
    llamadas = {}

    class GeoserverClientFalso:
        def __init__(self, url, user, pwd):
            llamadas["credenciales"] = (url, user, pwd)

        def connect(self):
            llamadas["conectado"] = True

        def create_shp_datastore(self, path, store_name, workspace, layer_name):
            llamadas["store_name"] = store_name
            llamadas["layer_name"] = layer_name
            llamadas["workspace"] = workspace

    monkeypatch.setattr(spatial_module, "GeoserverClient", GeoserverClientFalso)
    monkeypatch.setattr(spatial_module, "UPLOAD_FOLDER", str(tmp_path))

    app = make_app(spatial_module.spatial_bp)
    datos = {
        "file_type": file_type,
        "file": (_zip_en_memoria(["capa.shp"]), "capa.zip"),
    }

    with app.test_client() as cliente:
        respuesta = cliente.post("/importar", data=datos, content_type="multipart/form-data")
        mensajes = _mensajes_flash(cliente)

    assert respuesta.status_code == 302
    assert llamadas["conectado"] is True
    assert llamadas["store_name"] == store_esperado
    assert llamadas["layer_name"] == capa_esperada
    assert llamadas["workspace"] == "administrative"
    assert "Archivo subido correctamente al GeoServer." in mensajes


def test_importar_shapefile_exige_zip(make_app, monkeypatch, tmp_path):
    monkeypatch.setattr(spatial_module, "UPLOAD_FOLDER", str(tmp_path))
    app = make_app(spatial_module.spatial_bp)
    datos = {
        "file_type": "veredas",
        "file": (io.BytesIO(b"x"), "capa.shp"),
    }

    with app.test_client() as cliente:
        respuesta = cliente.post("/importar", data=datos, content_type="multipart/form-data")
        mensajes = _mensajes_flash(cliente)

    assert respuesta.status_code == 302
    assert any(".zip que contenga el shapefile" in mensaje for mensaje in mensajes)


def test_importar_shapefile_informa_error_de_geoserver(make_app, monkeypatch, tmp_path):
    class GeoserverClientFalso:
        def __init__(self, *args):
            pass

        def connect(self):
            raise ConnectionError("GeoServer inaccesible")

    monkeypatch.setattr(spatial_module, "GeoserverClient", GeoserverClientFalso)
    monkeypatch.setattr(spatial_module, "UPLOAD_FOLDER", str(tmp_path))

    app = make_app(spatial_module.spatial_bp)
    datos = {
        "file_type": "adm1",
        "file": (_zip_en_memoria(["capa.shp"]), "capa.zip"),
    }

    with app.test_client() as cliente:
        respuesta = cliente.post("/importar", data=datos, content_type="multipart/form-data")
        mensajes = _mensajes_flash(cliente)

    assert respuesta.status_code == 302
    assert any("Error al subir a GeoServer" in mensaje for mensaje in mensajes)


def test_importar_sin_archivo_en_rama_generica(make_app, monkeypatch, tmp_path):
    monkeypatch.setattr(spatial_module, "UPLOAD_FOLDER", str(tmp_path))
    app = make_app(spatial_module.spatial_bp)

    with app.test_client() as cliente:
        respuesta = cliente.post(
            "/importar", data={"file_type": "otro"}, content_type="multipart/form-data"
        )
        mensajes = _mensajes_flash(cliente)

    assert respuesta.status_code == 302
    assert "No se seleccionó ningún archivo." in mensajes
