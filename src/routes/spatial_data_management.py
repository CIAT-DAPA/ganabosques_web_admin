from flask import Blueprint, request, render_template, redirect, url_for, flash
import os
import traceback
from geoserver_import import upload_to_geoserver

ALLOWED_EXTENSIONS = {'shp', 'tif', 'tiff', 'csv', 'xls', 'xlsx'}
spatial_bp = Blueprint('spatial', __name__)

# Check if the file has an allowed extension
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@spatial_bp.route('/importar', methods=['GET', 'POST'])
def upload_file():
    from app import app  # import local app context to access config

    if request.method == 'POST':
        file_type = request.form.get('file_type')
        file = request.files.get('file')

        if not file or file.filename == '':
            flash('No se seleccionó ningún archivo.')
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filename = file.filename
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

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

    return render_template('upload.html', active_page='importar')
