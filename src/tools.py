import os
import sys
import shutil
import glob
import uuid
import tempfile
from zipfile import ZipFile
from urllib.parse import urljoin
from geoserver.catalog import Catalog
from geoserver.resource import Coverage
from geoserver.support import DimensionInfo

class GeoserverClient:
    def __init__(self, url, user, pwd):
        self.url = url if url.endswith("/") else url + "/"
        self.user = user
        self.pwd = pwd
        self.catalog = None
        self.workspace = None
        self.workspace_name = ''

    def connect(self):
        try:
            self.catalog = Catalog(self.url, username=self.user, password=self.pwd)
            print("✅ Conectado a GeoServer")
        except Exception as err:
            raise ConnectionError(f"❌ Error de conexión a GeoServer: {err}")

    def get_workspace(self, name):
        if not self.catalog:
            raise RuntimeError("❌ Catalog no inicializado. Llama a connect() primero.")
        self.workspace = self.catalog.get_workspace(name)
        if not self.workspace:
            raise ValueError(f"❌ Workspace '{name}' no encontrado.")
        self.workspace_name = name
        print(f"🎯 Workspace '{name}' seleccionado")

    def get_store(self, store_name):
        if not self.workspace:
            raise RuntimeError("❌ Workspace no inicializado")
        try:
            return self.catalog.get_store(store_name, self.workspace)
        except Exception as err:
            print(f"⚠️ Store '{store_name}' no encontrado:", err)
            return None

    # -------- MOSAICOS (GeoTIFF) -------- #

    def zip_mosaic_files(self, file_or_folder, folder_properties, folder_tmp, zip_output_dir):
        if not os.path.exists(file_or_folder) or not os.path.exists(folder_properties):
            print(f"❌ No se encontraron TIFF o propiedades: {file_or_folder}, {folder_properties}")
            return None

        if os.path.exists(folder_tmp):
            shutil.rmtree(folder_tmp)
        os.makedirs(folder_tmp)

        props = glob.glob(os.path.join(folder_properties, '*.properties'))
        if len(props) != 2:
            raise ValueError("❌ Deben existir exactamente 2 archivos '.properties' en la carpeta")

        for p in props:
            shutil.copy(p, os.path.join(folder_tmp, os.path.basename(p)))

        if os.path.isdir(file_or_folder):
            rasters = glob.glob(os.path.join(file_or_folder, "*.*"))
        else:
            rasters = [file_or_folder]

        for file in rasters:
            shutil.copy(file, os.path.join(folder_tmp, os.path.basename(file)))

        zip_name = "mosaic.zip"
        zip_path = os.path.join(zip_output_dir, zip_name)
        with ZipFile(zip_path, mode="w") as zipf:
            for f in glob.glob(os.path.join(folder_tmp, "*.*")):
                zipf.write(f, os.path.basename(f))

        print(f"🗜️ ZIP generado: {zip_path}")
        return zip_path

    def create_mosaic(self, store_name, file_or_folder, folder_properties, folder_tmp, zip_output_dir):
        output = self.zip_mosaic_files(file_or_folder, folder_properties, folder_tmp, zip_output_dir)
        if not output:
            raise RuntimeError("❌ No se pudo crear el archivo ZIP para mosaico.")

        self.catalog.create_imagemosaic(store_name, output, workspace=self.workspace)
        print(f"🟢 Mosaic store '{store_name}' creado.")

        store = self.get_store(store_name)
        url = urljoin(self.url, f"workspaces/{self.workspace_name}/coveragestores/{store_name}/coverages/{store_name}.xml")
        xml = self.catalog.get_xml(url)
        name = xml.find("name").text

        coverage = Coverage(self.catalog, store=store, name=name, href=url, workspace=self.workspace)

        coverage.supported_formats = ["GEOTIFF", "GEOTIF"]

        # ✅ Activar dimensión temporal correctamente
        coverage.metadata_dimensions = {
            "time": DimensionInfo(
                name="time",
                enabled=True,
                presentation="LIST",
                resolution=None,
                units="ISO8601",
                unit_symbol=None
            )
        }

        # ✅ Especificar el subdirectorio del mosaico
        coverage.metadata = {
            "dirName": f"{store_name}_{store_name}"
        }

        self.catalog.save(coverage)
        print("⏱️ Dimensión temporal habilitada correctamente")

    def update_mosaic(self, store, file_or_folder, folder_properties, folder_tmp, zip_output_dir):
        output = self.zip_mosaic_files(file_or_folder, folder_properties, folder_tmp, zip_output_dir)
        if output:
            self.catalog.harvest_uploadgranule(output, store)
            print("🔄 Mosaico actualizado")

    # -------- SHAPEFILES (ZIP) -------- #

    def create_shp_datastore(self, path, store_name, workspace=None, layer_name=None):
        if not self.catalog:
            self.connect()
        if not os.path.exists(path):
            raise FileNotFoundError(f"Archivo no encontrado: {path}")

        workspace = workspace or self.workspace
        if not workspace:
            raise ValueError("❌ Workspace no definido")

        with tempfile.TemporaryDirectory() as tmpdir:
            with ZipFile(path, 'r') as zip_ref:
                zip_ref.extractall(tmpdir)

            shp_files = [f for f in os.listdir(tmpdir) if f.endswith('.shp')]
            if not shp_files:
                raise Exception("No se encontró ningún archivo .shp")

            base_name = os.path.splitext(shp_files[0])[0]
            new_base = layer_name if layer_name else base_name

            for ext in ['shp', 'shx', 'dbf', 'prj', 'cpg']:
                old = os.path.join(tmpdir, f"{base_name}.{ext}")
                if os.path.exists(old):
                    os.rename(old, os.path.join(tmpdir, f"{new_base}.{ext}"))

            new_zip_path = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4().hex}.zip")
            with ZipFile(new_zip_path, 'w') as zipf:
                for f in os.listdir(tmpdir):
                    full = os.path.join(tmpdir, f)
                    zipf.write(full, f)

            self.catalog.create_featurestore(store_name, data=new_zip_path, workspace=workspace)
            print(f"🟢 Shapefile store '{store_name}' creado con capa '{new_base}'")

    # -------- UTILIDAD -------- #

    def delete_folder_content(self, folder_path):
        for item in os.listdir(folder_path):
            path = os.path.join(folder_path, item)
            if os.path.isfile(path) or os.path.islink(path):
                os.unlink(path)
                print(f"🗑️ Archivo eliminado: {path}")
            elif os.path.isdir(path):
                shutil.rmtree(path)
                print(f"🗑️ Carpeta eliminada: {path}")