import os
import tempfile
from tools import GeoserverClient
from config import config

# Leer credenciales desde archivo de configuración
geo_url = config['GEOSERVER_URL']
geo_user = config['GEOSERVER_USER']
geo_pwd = config['GEOSERVER_PWD']

# Validación de credenciales
if not geo_user or not geo_pwd:
    raise EnvironmentError("❌ Faltan las variables de entorno GEOSERVER_USER o GEOSERVER_PWD")

# Carpeta de propiedades de mosaico (TIFF)
path_file = os.path.abspath(os.path.dirname(__file__))
folder_properties = os.path.join(path_file, "data", "layers", "mosaic_properties")

if not os.path.isdir(folder_properties):
    raise FileNotFoundError(f"❌ No se encontró la carpeta de propiedades: {folder_properties}")

# Carpeta temporal para preparar mosaico y ZIP
folder_tmp = os.path.join(tempfile.gettempdir(), "ganabosques_tmp")
os.makedirs(folder_tmp, exist_ok=True)

# Puedes usar esta carpeta también para guardar temporalmente el ZIP generado
zip_output_dir = folder_tmp

# Configuración centralizada de tipos y workspaces
WORKSPACE_STORE_CONFIG = {
    "deforestation": {
        "workspace": "deforestation",
        "store": "smbyc"
    },
    "administrative_risk": {
        "workspace": "administrative_risk",
        "store": "administrative_risk_annual"
    }
}

# Instancia global del cliente GeoServer
geoclient = GeoserverClient(geo_url, geo_user, geo_pwd)

def upload_to_geoserver(filepath, file_type):
    """
    Sube un archivo TIFF como mosaico a GeoServer.
    Crea el store si no existe, o actualiza si ya está presente.
    También elimina el archivo generado temporalmente.
    """
    if file_type not in WORKSPACE_STORE_CONFIG:
        raise ValueError(f"Tipo de archivo inválido: {file_type}")

    workspace_name = WORKSPACE_STORE_CONFIG[file_type]['workspace']
    store_name = WORKSPACE_STORE_CONFIG[file_type]['store']

    try:
        # Conexión y selección de workspace
        geoclient.connect()
        geoclient.get_workspace(workspace_name)

        # Verifica si el store ya existe
        store = geoclient.get_store(store_name)

        if not store:
            # Crear mosaico por primera vez
            geoclient.create_mosaic(
                store_name=store_name,
                file_or_folder=filepath,
                folder_properties=folder_properties,
                folder_tmp=folder_tmp,
                zip_output_dir=zip_output_dir
            )
            print(f"🟢 Mosaico creado en workspace '{workspace_name}' con store '{store_name}'")
        else:
            # Actualizar mosaico existente
            geoclient.update_mosaic(
                store=store,
                file_or_folder=filepath,
                folder_properties=folder_properties,
                folder_tmp=folder_tmp,
                zip_output_dir=zip_output_dir
            )
            print(f"🔄 Mosaico actualizado en workspace '{workspace_name}' con store '{store_name}'")

        # Limpieza del ZIP generado
        mosaic_zip = os.path.join(zip_output_dir, "mosaic.zip")
        if os.path.exists(mosaic_zip):
            os.remove(mosaic_zip)
            print(f"🗑️ ZIP temporal eliminado: {mosaic_zip}")

    except Exception as e:
        print(f"❌ Error al subir archivo a GeoServer: {e}")
        raise
    finally:
        # Limpieza del archivo original subido
        if os.path.exists(filepath):
            os.remove(filepath)
            print(f"🗑️ TIFF original eliminado: {filepath}")