from flask import Flask, request, render_template, redirect, url_for, flash
import os
import traceback
from geoserver_import import upload_to_geoserver

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# Allowed file types
ALLOWED_EXTENSIONS = {'shp', 'tif', 'tiff', 'csv', 'xls', 'xlsx'}
UPLOAD_FOLDER = 'uploaded_files'

# Create upload folder if it doesn't exist
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Check if the file has an allowed extension
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def home():
    # Render the home page
    return render_template('home.html', active_page='home')


@app.route('/importar', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        # Retrieve file type from form
        file_type = request.form.get('file_type')
        file = request.files.get('file')

        # Check if a file was selected
        if not file or file.filename == '':
            flash('No se seleccionó ningún archivo.')
            return redirect(request.url)

        # Validate and save the file temporarily
        if file and allowed_file(file.filename):
            filename = file.filename
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            # Upload file to GeoServer
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

    # Render the upload page
    return render_template('upload.html', active_page='importar')


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
