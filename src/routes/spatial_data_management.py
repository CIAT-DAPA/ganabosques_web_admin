from flask import Blueprint, request, render_template, redirect, url_for, flash
import os
import traceback
import tempfile
from datetime import datetime
from geoserver_import import upload_to_geoserver
from tools import GeoserverClient
from config import config
from ganabosques_orm.auxiliaries.log import Log
from .adminlevel_data_management import importar_desde_csv

# Configuración
ALLOWED_EXTENSIONS = config['ALLOWED_EXTENSIONS']
UPLOAD_FOLDER = config['UPLOAD_FOLDER']
GEOSERVER_URL = config['GEOSERVER_URL']
GEOSERVER_USER = config['GEOSERVER_USER']
GEOSERVER_PWD = config['GEOSERVER_PWD']

# Blueprint
spatial_bp = Blueprint('spatial', __name__)

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
            
            if file.filename.lower().endswith('.csv'):
                flash('El archivo debe ser un CSV.')
                return redirect(request.url)

            if file and allowed_file(file.filename):
                try:
                    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
                    file.save(filepath)
                    try: 
                        importar_desde_csv(filepath, level)
                        os.remove(filepath)
                    except Exception as e:
                        traceback.print_exc()
                        flash(f'Error durante la importacion de datos: {e}')
                        os.remove(filepath)
                except Exception as e:
                    traceback.print_exc()
                    flash(f'Error al subir al importar datos: {e}')
                    os.remove(filepath)

        else:
            file = request.files.get('file')

            source = request.form.get('source')
            year_start = request.form.get('year_start')
            year_end = request.form.get('year_end')

            if not file or file.filename == '':
                flash('No se seleccionó ningún archivo.')
                return redirect(request.url)

            if file and allowed_file(file.filename):
                try:
                    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

                    # Caso 1: Deforestación anual (TIFF)
                    if file_type == 'deforestation':
                        if not source or not year_start or not year_end:
                            flash("Debes seleccionar fuente, año inicio y año fin para deforestación.", "danger")
                            return redirect(request.url)

                        filename = f"{source}_{year_start}-{year_end}.tiff"
                        filepath = os.path.join(UPLOAD_FOLDER, filename)
                        file.save(filepath)
                        upload_to_geoserver(filepath, file_type)

                    # Caso 2: Archivos ZIP con shapefiles
                    elif file_type in ['veredas', 'adm1', 'adm2', 'upra', 'protected_areas']:
                        if not file.filename.endswith('.zip'):
                            flash('El archivo debe ser un .zip que contenga el shapefile.', 'danger')
                            return redirect(request.url)

                        zip_path = os.path.join(tempfile.gettempdir(), file.filename)
                        file.save(zip_path)

                        # Determinar el store y nombre de capa según el tipo
                        store_layer_mapping = {
                            'veredas': ('adm3', 'admin_3'),
                            'adm1': ('adm1', 'admin_1'),
                            'adm2': ('adm2', 'admin_2'),
                            'upra': ('upra', 'upra_boundaries'),
                            'protected_areas': ('protected_areas', 'pnn_areas')
                        }
                        store_name, layer_name = store_layer_mapping[file_type]

                        # Subida a GeoServer
                        geo = GeoserverClient(GEOSERVER_URL, GEOSERVER_USER, GEOSERVER_PWD)
                        geo.connect()
                        geo.create_shp_datastore(
                            path=zip_path,
                            store_name=store_name,
                            workspace='administrative',
                            layer_name=layer_name
                        )

                    # Caso 3: Otros tipos
                    else:
                        filepath = os.path.join(UPLOAD_FOLDER, file.filename)
                        file.save(filepath)
                        upload_to_geoserver(filepath, file_type)

                    flash('Archivo subido correctamente al GeoServer.')

                except Exception as e:
                    traceback.print_exc()
                    flash(f'Error al subir a GeoServer: {e}')

                return redirect(url_for('spatial.upload_file'))

    return render_template('upload.html', active_page='importar', current_year=datetime.now().year)