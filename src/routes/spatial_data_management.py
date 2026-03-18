from flask import Blueprint, request, render_template, redirect, url_for, flash
import os
import traceback
import tempfile
import shutil
from zipfile import ZipFile
from datetime import datetime
from geoserver_import import process_geoserver_mosaics
from tools import GeoserverClient
from config import config
from ganabosques_orm.auxiliaries.log import Log
from .adminlevel_data_management import importar_desde_csv
import time

# Configuración
ALLOWED_EXTENSIONS = config['ALLOWED_EXTENSIONS']
UPLOAD_FOLDER = config['UPLOAD_FOLDER']
GEOSERVER_URL = config['GEOSERVER_URL']
GEOSERVER_USER = config['GEOSERVER_USER']
GEOSERVER_PWD = config['GEOSERVER_PWD']

# Blueprint
spatial_bp = Blueprint('spatial', __name__)

# Mapeo: file_type del frontend → (store_name, source para properties)
DEFORESTATION_TYPE_MAP = {
    'deforestation_smbyc': ('smbyc', 'smbyc'),
    'deforestation_nad':   ('nad',   'nad'),
    'deforestation_atd':   ('atd',   'atd'),
}

def allowed_file(filename):
    """Valida que el archivo tenga una extensión permitida."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@spatial_bp.route('/importar', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        file_type = request.form.get('file_type')

        if file_type == "levels_adm":
            file = request.files.get('file')
            level = request.form.get('level')
            
            if not file.filename.lower().endswith('.csv'):
                flash('El archivo debe ser un CSV.')
                return redirect(request.url)

            if file and allowed_file(file.filename):
                try:
                    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
                    file.save(filepath)
                    try: 
                        start = time.time()
                        importar_desde_csv(filepath, level)
                        os.remove(filepath)
                        end = time.time()
                        print(f"Tiempo total: {end - start:.2f} segundos")
                    except Exception as e:
                        traceback.print_exc()
                        flash(f'Error durante la importacion de datos: {e}')
                        if os.path.exists(filepath):
                            os.remove(filepath)
                except Exception as e:
                    traceback.print_exc()
                    flash(f'Error al subir al importar datos: {e}')

        elif file_type in DEFORESTATION_TYPE_MAP:
            # ── Deforestación (SMBYC, NAD, ATD) ──
            file = request.files.get('file')
            store_name, source = DEFORESTATION_TYPE_MAP[file_type]

            if not file or file.filename == '':
                flash('No se seleccionó ningún archivo.', 'danger')
                return redirect(request.url)

            if not file.filename.lower().endswith('.zip'):
                flash('El archivo debe ser un .zip que contenga los archivos TIFF.', 'danger')
                return redirect(request.url)

            try:
                os.makedirs(UPLOAD_FOLDER, exist_ok=True)

                # Carpeta de destino para los TIFFs (nombre = store_name)
                output_dir = os.path.join(UPLOAD_FOLDER, store_name)
                os.makedirs(output_dir, exist_ok=True)

                # Guardar y extraer ZIP con TIFFs
                zip_path = os.path.join(tempfile.gettempdir(), file.filename)
                file.save(zip_path)
                print(f"📂 ZIP guardado: {zip_path}")

                extracted_count = 0
                with ZipFile(zip_path, 'r') as zf:
                    all_members = zf.namelist()
                    print(f"📋 Contenido del ZIP ({len(all_members)} entradas):")
                    for m in all_members:
                        info = zf.getinfo(m)
                        print(f"  - {m}  (size: {info.file_size} bytes)")

                    for member in all_members:
                        member_lower = member.lower()
                        # Ignorar carpetas __MACOSX
                        if '__macosx' in member_lower:
                            continue
                        if member_lower.endswith('.tif') or member_lower.endswith('.tiff'):
                            fname = os.path.basename(member)
                            if fname:
                                target_path = os.path.join(output_dir, fname)
                                with zf.open(member) as src_file, open(target_path, 'wb') as dst:
                                    shutil.copyfileobj(src_file, dst)
                                extracted_count += 1
                                print(f"  ✅ Extraído: {fname} → {output_dir}")

                # Limpiar ZIP temporal
                if os.path.exists(zip_path):
                    os.remove(zip_path)

                if extracted_count == 0:
                    all_names_str = ", ".join(all_members)
                    flash(f'No se encontraron archivos .tif/.tiff en el ZIP. Contenido: {all_names_str}', 'warning')
                    return redirect(url_for('spatial.upload_file'))

                print(f"📊 Total TIFFs extraídos: {extracted_count} en {output_dir}")

                # Publicar en GeoServer y guardar en Mongo
                process_geoserver_mosaics(output_dir, store_name, source)

                flash(f'{extracted_count} archivo(s) TIFF subidos y publicados correctamente en GeoServer.', 'success')

            except Exception as e:
                traceback.print_exc()
                flash(f'Error al procesar deforestación: {e}', 'danger')

            return redirect(url_for('spatial.upload_file'))

        else:
            file = request.files.get('file')

            if not file or file.filename == '':
                flash('No se seleccionó ningún archivo.')
                return redirect(request.url)

            if file and allowed_file(file.filename):
                try:
                    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

                    # Archivos ZIP con shapefiles
                    if file_type in ['veredas', 'adm1', 'adm2', 'upra', 'protected_areas']:
                        if not file.filename.endswith('.zip'):
                            flash('El archivo debe ser un .zip que contenga el shapefile.', 'danger')
                            return redirect(request.url)

                        zip_path = os.path.join(tempfile.gettempdir(), file.filename)
                        file.save(zip_path)

                        store_layer_mapping = {
                            'veredas': ('adm3', 'admin_3'),
                            'adm1': ('adm1', 'admin_1'),
                            'adm2': ('adm2', 'admin_2'),
                            'upra': ('upra', 'upra_boundaries'),
                            'protected_areas': ('protected_areas', 'pnn_areas')
                        }
                        store_name, layer_name = store_layer_mapping[file_type]

                        geo = GeoserverClient(GEOSERVER_URL, GEOSERVER_USER, GEOSERVER_PWD)
                        geo.connect()
                        geo.create_shp_datastore(
                            path=zip_path,
                            store_name=store_name,
                            workspace='administrative',
                            layer_name=layer_name
                        )

                    flash('Archivo subido correctamente al GeoServer.')

                except Exception as e:
                    traceback.print_exc()
                    flash(f'Error al subir a GeoServer: {e}')

                return redirect(url_for('spatial.upload_file'))

    return render_template(
        'upload.html',
        active_page='importar',
        current_year=datetime.now().year
    )
