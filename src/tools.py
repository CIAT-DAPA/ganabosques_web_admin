import os
import sys
import shutil
import glob
from zipfile import ZipFile
from geoserver.catalog import Catalog
from geoserver.resource import Coverage
from geoserver.support import DimensionInfo

class GeoserverClient:
    """
    Cliente para conectarse y manipular datos en GeoServer.
    Soporta carga de mosaicos (tiff) y shapefiles comprimidos (.zip).
    """

    def __init__(self, url, user, pwd):
        self.url = url
        self.user = user
        self.pwd = pwd
        self.catalog = None
        self.workspace = None
        self.workspace_name = ''

    def connect(self):
        """Establece conexión con el GeoServer."""
        try:
            self.catalog = Catalog(self.url, username=self.user, password=self.pwd)
            print("Connected to GeoServer")
        except Exception as err:
            print("Error connecting to GeoServer:", err)

    def get_workspace(self, name):
        """Selecciona y guarda el workspace actual."""
        if self.catalog:
            self.workspace = self.catalog.get_workspace(name)
            self.workspace_name = name
            print("Workspace found")
        else:
            print("Workspace not available")
            sys.exit()

    def get_store(self, store_name):
        """Obtiene un store dentro del workspace actual."""
        if self.workspace:
            try:
                return self.catalog.get_store(store_name, self.workspace)
            except Exception as err:
                print("Store not found:", store_name)
                return None
        else:
            print("Workspace not found")
            return None

    # ------------- MOSAICOS (GeoTIFF) ------------- #

    def zip_files(self, file, folder_properties, folder_tmp):
        """Empaqueta un archivo TIFF con sus propiedades como ZIP para mosaico."""
        if os.path.exists(file) and os.path.exists(folder_properties):
            if os.path.exists(folder_tmp):
                shutil.rmtree(folder_tmp)
            os.mkdir(folder_tmp)

            props = glob.glob(os.path.join(folder_properties, '*.properties'))
            if len(props) != 2:
                print("Check the properties file")
                sys.exit()
            for p in props:
                shutil.copy(p, os.path.join(folder_tmp, os.path.basename(p)))

            shutil.copy(file, os.path.join(folder_tmp, os.path.basename(file)))

            zip_name = "mosaic.zip"
            with ZipFile(zip_name, mode="w") as zipf:
                for f in glob.glob(os.path.join(folder_tmp, "*.*")):
                    zipf.write(f, os.path.basename(f))

            return os.path.join(os.getcwd(), zip_name)
        else:
            print("ZIP not created - file or properties missing")
            return None

    def create_mosaic(self, store_name, file, folder_properties, folder_tmp):
        """Crea un mosaico (TIFF) en el store y workspace definidos."""
        output = self.zip_files(file, folder_properties, folder_tmp)
        self.catalog.create_imagemosaic(store_name, output, workspace=self.workspace)
        print(f"Mosaic store: {store_name} created")

        store = self.catalog.get_store(store_name, workspace=self.workspace)
        url = f"{self.url}workspaces/{self.workspace_name}/coveragestores/{store_name}/coverages/{store_name}.xml"
        xml = self.catalog.get_xml(url)
        name = xml.find("name").text

        coverage = Coverage(self.catalog, store=store, name=name, href=url, workspace=self.workspace)
        coverage.supported_formats = ["GEOTIFF"]
        coverage.metadata = {
            "dirName": f"{store_name}_{store_name}",
            "time": DimensionInfo(name="time", enabled="true", presentation="LIST", resolution=None, units="ISO8601", unit_symbol=None)
        }
        self.catalog.save(coverage)
        print("Time dimension enabled")

    def update_mosaic(self, store, file, folder_properties, folder_tmp):
        """Agrega nuevas imágenes TIFF a un mosaico existente."""
        output = self.zip_files(file, folder_properties, folder_tmp)
        self.catalog.harvest_uploadgranule(output, store)
        print("Mosaic updated")

    # ------------- SHAPEFILES (ZIP) ------------- #

    def create_shp_datastore(self, path, store_name, workspace, layer_name=None):
        """
        Crea un store de shapefile, renombrando los archivos internos del ZIP
        para garantizar que la capa se registre con el nombre deseado.
        """
        if not self.catalog:
            self.connect()

        if not os.path.exists(path):
            raise FileNotFoundError(f"Archivo no encontrado: {path}")

        import tempfile
        import uuid

        with tempfile.TemporaryDirectory() as tmpdir:
            # Descomprimir ZIP original
            with ZipFile(path, 'r') as zip_ref:
                zip_ref.extractall(tmpdir)

            # Encontrar archivo .shp principal
            shp_files = [f for f in os.listdir(tmpdir) if f.endswith('.shp')]
            if not shp_files:
                raise Exception("No se encontró ningún archivo .shp en el ZIP")
            base_name = os.path.splitext(shp_files[0])[0]

            # Renombrar todos los archivos relacionados
            new_base = layer_name if layer_name else base_name
            for ext in ['shp', 'shx', 'dbf', 'prj', 'cpg']:  # posibles extensiones
                old_file = os.path.join(tmpdir, f"{base_name}.{ext}")
                if os.path.exists(old_file):
                    new_file = os.path.join(tmpdir, f"{new_base}.{ext}")
                    os.rename(old_file, new_file)

            # Reempaquetar ZIP
            new_zip_path = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4().hex}.zip")
            with ZipFile(new_zip_path, 'w') as zipf:
                for file in os.listdir(tmpdir):
                    full_path = os.path.join(tmpdir, file)
                    zipf.write(full_path, file)

            # Crear featurestore en GeoServer
            self.catalog.create_featurestore(store_name, data=new_zip_path, workspace=workspace)
            print(f"Shapefile store '{store_name}' creado en workspace '{workspace}' con capa '{new_base}'")
