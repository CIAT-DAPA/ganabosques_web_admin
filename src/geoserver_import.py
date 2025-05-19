import os
from tools import GeoserverClient

geo_url = "http://localhost:8080/geoserver/rest/"
geo_user = os.getenv("GEOSERVER_USER")
geo_pwd = os.getenv("GEOSERVER_PWD")
path_file = os.path.abspath(__file__)
path_file = os.path.dirname(path_file)
folder_properties = os.path.join(path_file, "data", "layers", "mosaic_properties")
folder_tmp = "C:/temp/ganabosques_tmp"
os.makedirs(folder_tmp, exist_ok=True)

WORKSPACE_STORE_CONFIG = {
    "deforestation": {"workspace": "deforestation", "store": "smbyc"},
    "administrative_risk": {"workspace": "administrative_risk", "store": "administrative_risk_annual"},
}

geoclient = GeoserverClient(geo_url, geo_user, geo_pwd)

def upload_to_geoserver(filepath, file_type):
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

        mosaic_zip = "D:/OneDrive - CGIAR/Desktop/GanaBosques_WebAdmin/mosaic.zip"
        if os.path.exists(mosaic_zip):
            os.remove(mosaic_zip)

    except Exception as e:
        print(f"Error al subir archivo a GeoServer: {e}")
        raise
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)
