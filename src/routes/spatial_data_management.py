from flask import Blueprint, request, render_template, redirect, url_for, flash
import os
import traceback
from datetime import datetime
from geoserver_import import upload_to_geoserver
from config import config

ALLOWED_EXTENSIONS = config['ALLOWED_EXTENSIONS']
UPLOAD_FOLDER = config['UPLOAD_FOLDER']

spatial_bp = Blueprint('spatial', __name__)

# Validar si la extensión es permitida
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@spatial_bp.route('/importar', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        file_type = request.form.get('file_type')
        file = request.files.get('file')

        # Campos adicionales solo para deforestation
        source = request.form.get('source')
        year_start = request.form.get('year_start')
        year_end = request.form.get('year_end')

        if not file or file.filename == '':
            flash('No se seleccionó ningún archivo.')
            return redirect(request.url)

        if file and allowed_file(file.filename):
            # Renombrar si es deforestación anual
            if file_type == 'deforestation':
                if not source or not year_start or not year_end:
                    flash("Debes seleccionar fuente, año inicio y año fin para deforestación.", "danger")
                    return redirect(request.url)
                filename = f"{source}_{year_start}-{year_end}.tiff"
            else:
                filename = file.filename

            filepath = os.path.join(UPLOAD_FOLDER, filename)
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)

            try:
                file.save(filepath)
            except Exception as save_error:
                traceback.print_exc()
                flash(f"Error al guardar el archivo: {save_error}")
                return redirect(request.url)

            try:
                upload_to_geoserver(filepath, file_type)
                flash('Archivo subido correctamente al GeoServer.')
            except Exception as e:
                traceback.print_exc()
                flash(f'Error al subir a GeoServer: {e}')

            return redirect(url_for('spatial.upload_file'))
        else:
            flash('Tipo de archivo no permitido.')
            return redirect(request.url)

    # Render con año actual para desplegables
    return render_template('upload.html', active_page='importar', current_year=datetime.now().year)
