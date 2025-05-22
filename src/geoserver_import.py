import os
import tempfile
from tools import GeoserverClient
from config import config

# Leer credenciales desde variables de entorno
geo_url = config['GEOSERVER_URL']
geo_user = config['GEOSERVER_USER']
geo_pwd = config['GEOSERVER_PWD']

# Validación de credenciales
if not geo_user or not geo_pwd:
    raise EnvironmentError("Faltan las variables de entorno GEOSERVER_USER o GEOSERVER_PWD")

# Rutas de carpetas
path_file = os.path.abspath(os.path.dirname(__file__))
folder_properties = os.path.join(path_file, "data", "layers", "mosaic_properties")

# Validación de la carpeta de propiedades
if not os.path.isdir(folder_properties):
    raise FileNotFoundError(f"No se encontró la carpeta de propiedades: {folder_properties}")

# Carpeta temporal portable
folder_tmp = os.path.join(tempfile.gettempdir(), "ganabosques_tmp")
os.makedirs(folder_tmp, exist_ok=True)

# Configuración de workspaces y stores
WORKSPACE_STORE_CONFIG = {
    "deforestation": {
        "workspace": "deforestation",
        "store": "smbyc"
    },
    "administrative_risk": {
        "workspace": "administrative_risk",
        "store": "administrative_risk_annual"
    },
}

# Cliente GeoServer
geoclient = GeoserverClient(geo_url, geo_user, geo_pwd)

def upload_to_geoserver(filepath, file_type):
    """
    Sube un archivo TIFF como mosaico a GeoServer. Crea o actualiza el store según corresponda.
    """
    if file_type not in WORKSPACE_STORE_CONFIG:
        raise ValueError("Tipo de archivo inválido.")

    workspace_name = WORKSPACE_STORE_CONFIG[file_type]['workspace']
    store_name = WORKSPACE_STORE_CONFIG[file_type]['store']

    try:
        geoclient.connect()
        geoclient.get_workspace(workspace_name)

        store = geoclient.get_store(store_name)

        if not store:
            geoclient.create_mosaic(store_name, filepath, folder_properties, folder_tmp)
            print(f"Mosaico creado en workspace '{workspace_name}' con store '{store_name}'.")
        else:
            geoclient.update_mosaic(store, filepath, folder_properties, folder_tmp)
            print(f"Mosaico actualizado en workspace '{workspace_name}' con store '{store_name}'.")

        # Eliminar el ZIP si fue generado
        mosaic_zip = os.path.join(folder_tmp, "mosaic.zip")
        if os.path.exists(mosaic_zip):
            os.remove(mosaic_zip)

    except Exception as e:
        print(f"Error al subir archivo a GeoServer: {e}")
        raise
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)
