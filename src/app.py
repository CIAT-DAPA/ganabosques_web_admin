from flask import Flask, request, render_template, redirect, url_for, flash
import os
import traceback
import csv
from datetime import datetime
from geoserver_import import upload_to_geoserver
from mongoengine import connect
from routes.home import home_bp
from ganabosques_orm.collections.enterprise import Enterprise
from ganabosques_orm.collections.farm import Farm

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# Allowed file types
ALLOWED_EXTENSIONS = {'shp', 'tif', 'tiff', 'csv', 'xls', 'xlsx'}
UPLOAD_FOLDER = 'uploaded_files'
CSV_FOLDER = 'uploaded_codes'

# Create upload folders if they don't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CSV_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['CSV_FOLDER'] = CSV_FOLDER

# Check if the file has an allowed extension
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_codigos_from_csv(file_stream):
    reader = csv.DictReader(file_stream.read().decode('utf-8').splitlines())
    return [row['codigo_sit'].strip() for row in reader if row['codigo_sit'].strip()]

@app.route('/importar', methods=['GET', 'POST'])
def upload_file():
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

            return redirect(url_for('upload_file'))
        else:
            flash('Tipo de archivo no permitido.')
            return redirect(request.url)

    return render_template('upload.html', active_page='importar')

@app.route('/importar_proveedores', methods=['GET', 'POST'])
def importar_proveedores():
    empresas = Enterprise.objects.only('id', 'name')
    anios = list(range(2013, datetime.now().year + 1))
    encontrados, no_encontrados = [], []

    if request.method == 'POST':
        empresa_id = request.form.get('empresa_id')
        anios_seleccionados = request.form.getlist('anios')
        archivo = request.files.get('archivo')

        if not empresa_id or not archivo:
            flash("Debes seleccionar una empresa y subir un archivo CSV", 'danger')
            return redirect(request.url)

        codigos = extract_codigos_from_csv(archivo)
        codigos_encontrados = Farm.objects(ext_id__ext_code__in=codigos).distinct('ext_id.ext_code')
        encontrados = list(set(codigos_encontrados))
        no_encontrados = list(set(codigos) - set(encontrados))

        return render_template('import_suppliers.html', empresas=empresas, anios=anios,
                               encontrados=encontrados, no_encontrados=no_encontrados,
                               selected_empresa=empresa_id, selected_anios=anios_seleccionados,
                               active_page='import_suppliers')

    return render_template('import_suppliers.html', empresas=empresas, anios=anios, active_page='import_suppliers')

app.register_blueprint(home_bp)

if __name__ == '__main__':
    connect(host="mongodb://localhost:27017/ganabosques")
    app.run(debug=True, host='0.0.0.0')
