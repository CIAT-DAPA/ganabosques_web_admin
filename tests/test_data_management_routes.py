"""Pruebas de la descarga y verificación de fuentes externas de datos."""

from types import SimpleNamespace

import pytest

import src.routes.data_management as data_management_module
from helpers import FakeObjectsManager, FakeQuerySet

OBJECT_ID_VALIDO = "507f1f77bcf86cd799439011"


def _configuracion(url="https://datos.example.com/", extension=".tiff", nombre="SMBYC"):
    parametros = [
        SimpleNamespace(key="url", value=url),
        SimpleNamespace(key="extension", value=extension),
    ]
    return SimpleNamespace(id=OBJECT_ID_VALIDO, name=nombre, parameters=parametros)


class _RespuestaFalsa:
    def __init__(self, text="", status_code=200, chunks=None):
        self.text = text
        self.status_code = status_code
        self._chunks = chunks or []

    def iter_content(self, chunk_size):
        return iter(self._chunks)


# ---------------------------------------------------------------------------
# get_parameters
# ---------------------------------------------------------------------------

def test_get_parameters_extrae_url_y_extension():
    url, extension = data_management_module.get_parameters(_configuracion())

    assert url == "https://datos.example.com/"
    assert extension == ".tiff"


def test_get_parameters_devuelve_none_cuando_faltan_claves():
    config = SimpleNamespace(parameters=[SimpleNamespace(key="otro", value="x")])

    url, extension = data_management_module.get_parameters(config)

    assert url is None
    assert extension is None


def test_get_parameters_con_lista_vacia():
    url, extension = data_management_module.get_parameters(SimpleNamespace(parameters=[]))

    assert (url, extension) == (None, None)


# ---------------------------------------------------------------------------
# get_latest_file
# ---------------------------------------------------------------------------

HTML_LISTADO = """
<html><body>
  <a href="datos_2022.tiff">2022</a>
  <a href="datos_2024.tiff">2024</a>
  <a href="datos_2023.tiff">2023</a>
  <a href="leeme.txt">texto</a>
</body></html>
"""


def test_get_latest_file_devuelve_el_mayor_por_orden_descendente(monkeypatch):
    monkeypatch.setattr(
        data_management_module.requests,
        "get",
        lambda url, verify: _RespuestaFalsa(text=HTML_LISTADO),
    )

    assert data_management_module.get_latest_file("https://x/", ".tiff") == "datos_2024.tiff"


def test_get_latest_file_devuelve_none_si_no_hay_coincidencias(monkeypatch):
    monkeypatch.setattr(
        data_management_module.requests,
        "get",
        lambda url, verify: _RespuestaFalsa(text="<html><a href='a.txt'>a</a></html>"),
    )

    assert data_management_module.get_latest_file("https://x/", ".tiff") is None


def test_get_latest_file_devuelve_none_ante_error_de_red(monkeypatch):
    def explota(url, verify):
        raise ConnectionError("sin red")

    monkeypatch.setattr(data_management_module.requests, "get", explota)

    assert data_management_module.get_latest_file("https://x/", ".tiff") is None


def test_get_latest_file_ignora_enlaces_sin_href(monkeypatch):
    html = "<html><a>sin href</a><a href='b_2020.tiff'>b</a></html>"
    monkeypatch.setattr(
        data_management_module.requests, "get", lambda url, verify: _RespuestaFalsa(text=html)
    )

    assert data_management_module.get_latest_file("https://x/", ".tiff") == "b_2020.tiff"


# ---------------------------------------------------------------------------
# download_file
# ---------------------------------------------------------------------------

def test_download_file_escribe_el_contenido_en_temporal(monkeypatch, tmp_path):
    monkeypatch.setattr(data_management_module.tempfile, "gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr(
        data_management_module.requests,
        "get",
        lambda url, stream, verify, timeout: _RespuestaFalsa(chunks=[b"abc", b"def"]),
    )

    ruta = data_management_module.download_file("https://x/", "archivo.tiff")

    assert ruta == str(tmp_path / "archivo.tiff")
    assert (tmp_path / "archivo.tiff").read_bytes() == b"abcdef"


def test_download_file_falla_si_el_servidor_no_devuelve_200(monkeypatch, tmp_path):
    monkeypatch.setattr(data_management_module.tempfile, "gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr(
        data_management_module.requests,
        "get",
        lambda url, stream, verify, timeout: _RespuestaFalsa(status_code=404),
    )

    with pytest.raises(Exception, match="No se pudo descargar"):
        data_management_module.download_file("https://x/", "archivo.tiff")


def test_download_file_traduce_el_timeout(monkeypatch, tmp_path):
    def explota(url, stream, verify, timeout):
        raise data_management_module.requests.exceptions.Timeout()

    monkeypatch.setattr(data_management_module.requests, "get", explota)

    with pytest.raises(Exception, match="tiempo de espera"):
        data_management_module.download_file("https://x/", "archivo.tiff")


def test_download_file_traduce_errores_de_peticion(monkeypatch, tmp_path):
    def explota(url, stream, verify, timeout):
        raise data_management_module.requests.exceptions.RequestException("fallo DNS")

    monkeypatch.setattr(data_management_module.requests, "get", explota)

    with pytest.raises(Exception, match="Error durante la descarga"):
        data_management_module.download_file("https://x/", "archivo.tiff")


# ---------------------------------------------------------------------------
# convert_to_tiff
# ---------------------------------------------------------------------------

def test_convert_to_tiff_copia_con_perfil_gtiff(monkeypatch):
    llamadas = {}

    class FuenteFalsa:
        profile = {"driver": "HFA", "width": 10}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(data_management_module.rasterio, "open", lambda ruta: FuenteFalsa())

    def fake_copy(src, destino, **profile):
        llamadas["destino"] = destino
        llamadas["profile"] = profile

    monkeypatch.setattr(data_management_module, "rio_copy", fake_copy)

    salida = data_management_module.convert_to_tiff("/tmp/datos.img")

    assert salida == "/tmp/datos.tiff"
    assert llamadas["profile"]["driver"] == "GTiff"
    assert llamadas["profile"]["compress"] == "lzw"


# ---------------------------------------------------------------------------
# Ruta /data_management/data
# ---------------------------------------------------------------------------

def test_data_management_lista_solo_configuraciones_habilitadas(
    make_app, capture_render, monkeypatch
):
    capturado = capture_render(data_management_module)
    queryset = FakeQuerySet([_configuracion()])
    manager = FakeObjectsManager(queryset)
    monkeypatch.setattr(
        data_management_module, "Configuration", type("ConfigStub", (), {"objects": manager})
    )

    app = make_app(data_management_module.datamanagement_bp)
    respuesta = app.test_client().get("/data_management/data")

    assert respuesta.status_code == 200
    assert capturado["template"] == "data_management.html"
    assert capturado["context"]["active_page"] == "data_management"
    assert manager.calls[0][1] == {"log__enable": True}


# ---------------------------------------------------------------------------
# Ruta /data_management/check
# ---------------------------------------------------------------------------

def _stub_configuration(monkeypatch, items):
    manager = FakeObjectsManager(FakeQuerySet(items))
    monkeypatch.setattr(
        data_management_module, "Configuration", type("ConfigStub", (), {"objects": manager})
    )
    return manager


def test_check_new_data_sin_config_id_responde_400(make_app):
    app = make_app(data_management_module.datamanagement_bp)

    respuesta = app.test_client().get("/data_management/check")

    assert respuesta.status_code == 400
    assert respuesta.get_json()["success"] is False


def test_check_new_data_con_config_inexistente_responde_404(make_app, monkeypatch):
    _stub_configuration(monkeypatch, [])
    app = make_app(data_management_module.datamanagement_bp)

    respuesta = app.test_client().get(f"/data_management/check?config_id={OBJECT_ID_VALIDO}")

    assert respuesta.status_code == 404
    assert "inválida o deshabilitada" in respuesta.get_json()["message"]


def test_check_new_data_con_parametros_incompletos_responde_400(make_app, monkeypatch):
    config_sin_parametros = SimpleNamespace(parameters=[])
    _stub_configuration(monkeypatch, [config_sin_parametros])
    app = make_app(data_management_module.datamanagement_bp)

    respuesta = app.test_client().get(f"/data_management/check?config_id={OBJECT_ID_VALIDO}")

    assert respuesta.status_code == 400
    assert "Faltan parámetros" in respuesta.get_json()["message"]


def test_check_new_data_devuelve_el_archivo_mas_reciente(make_app, monkeypatch):
    _stub_configuration(monkeypatch, [_configuracion()])
    monkeypatch.setattr(
        data_management_module, "get_latest_file", lambda url, ext: "datos_2024.tiff"
    )
    app = make_app(data_management_module.datamanagement_bp)

    respuesta = app.test_client().get(f"/data_management/check?config_id={OBJECT_ID_VALIDO}")

    assert respuesta.status_code == 200
    assert respuesta.get_json() == {"success": True, "latest_file": "datos_2024.tiff"}


def test_check_new_data_responde_404_si_no_hay_archivo(make_app, monkeypatch):
    _stub_configuration(monkeypatch, [_configuracion()])
    monkeypatch.setattr(data_management_module, "get_latest_file", lambda url, ext: None)
    app = make_app(data_management_module.datamanagement_bp)

    respuesta = app.test_client().get(f"/data_management/check?config_id={OBJECT_ID_VALIDO}")

    assert respuesta.status_code == 404
    assert ".tiff" in respuesta.get_json()["message"]


# ---------------------------------------------------------------------------
# Ruta /data_management/download
# ---------------------------------------------------------------------------

def test_download_sin_config_id_responde_400(make_app):
    app = make_app(data_management_module.datamanagement_bp)

    respuesta = app.test_client().post("/data_management/download", data={})

    assert respuesta.status_code == 400


def test_download_responde_404_si_no_hay_archivo_reciente(make_app, monkeypatch):
    _stub_configuration(monkeypatch, [_configuracion()])
    monkeypatch.setattr(data_management_module, "get_latest_file", lambda url, ext: None)
    app = make_app(data_management_module.datamanagement_bp)

    respuesta = app.test_client().post(
        "/data_management/download", data={"config_id": OBJECT_ID_VALIDO}
    )

    assert respuesta.status_code == 404


def test_download_envia_el_archivo_y_marca_la_cabecera_de_exito(make_app, monkeypatch, tmp_path):
    archivo = tmp_path / "datos_2024.tiff"
    archivo.write_bytes(b"contenido raster")

    _stub_configuration(monkeypatch, [_configuracion()])
    monkeypatch.setattr(
        data_management_module, "get_latest_file", lambda url, ext: "datos_2024.tiff"
    )
    monkeypatch.setattr(
        data_management_module, "download_file", lambda url, nombre: str(archivo)
    )

    app = make_app(data_management_module.datamanagement_bp)
    respuesta = app.test_client().post(
        "/data_management/download", data={"config_id": OBJECT_ID_VALIDO}
    )

    assert respuesta.status_code == 200
    assert respuesta.headers["X-Import-Success"] == "true"
    assert "datos_2024.tiff" in respuesta.headers["Content-Disposition"]


def test_download_convierte_img_a_tiff_antes_de_enviar(make_app, monkeypatch, tmp_path):
    origen = tmp_path / "datos.img"
    origen.write_bytes(b"img")
    convertido = tmp_path / "datos.tiff"
    convertido.write_bytes(b"tiff")

    _stub_configuration(monkeypatch, [_configuracion(extension=".img")])
    monkeypatch.setattr(data_management_module, "get_latest_file", lambda url, ext: "datos.img")
    monkeypatch.setattr(data_management_module, "download_file", lambda url, nombre: str(origen))

    conversiones = []

    def fake_convert(ruta):
        conversiones.append(ruta)
        return str(convertido)

    monkeypatch.setattr(data_management_module, "convert_to_tiff", fake_convert)

    app = make_app(data_management_module.datamanagement_bp)
    respuesta = app.test_client().post(
        "/data_management/download", data={"config_id": OBJECT_ID_VALIDO}
    )

    assert respuesta.status_code == 200
    assert conversiones == [str(origen)]
    assert "datos.tiff" in respuesta.headers["Content-Disposition"]


def test_download_responde_500_si_la_descarga_falla(make_app, monkeypatch):
    _stub_configuration(monkeypatch, [_configuracion()])
    monkeypatch.setattr(data_management_module, "get_latest_file", lambda url, ext: "datos.tiff")

    def explota(url, nombre):
        raise Exception("servidor caído")

    monkeypatch.setattr(data_management_module, "download_file", explota)

    app = make_app(data_management_module.datamanagement_bp)
    respuesta = app.test_client().post(
        "/data_management/download", data={"config_id": OBJECT_ID_VALIDO}
    )

    assert respuesta.status_code == 500
