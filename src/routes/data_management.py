from flask import Blueprint, render_template, request, send_file, flash, jsonify, make_response
from ganabosques_orm.collections.configuration import Configuration
from bson import ObjectId
import requests, os, tempfile
from bs4 import BeautifulSoup
import rasterio
from rasterio.shutil import copy as rio_copy
import urllib3

# Configuración del Blueprint
datamanagement_bp = Blueprint('datamanagement', __name__, url_prefix='/data_management')
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Obtener parámetros desde la configuración seleccionada
def get_parameters(config):
    url = next((p.value for p in config.parameters if p.key == 'url'), None)
    ext = next((p.value for p in config.parameters if p.key == 'extension'), None)
    return url, ext

# Obtener el archivo más reciente disponible con la extensión indicada
def get_latest_file(url, extension):
    try:
        response = requests.get(url, verify=False)
        soup = BeautifulSoup(response.text, "html.parser")
        files = [a.get('href') for a in soup.find_all('a') if a.get('href', '').endswith(extension)]
        return sorted(files, reverse=True)[0] if files else None
    except Exception as e:
        print("Error:", e)
        return None

# Descargar archivo desde URL
def download_file(url, filename):
    response = requests.get(f"{url}{filename}", stream=True, verify=False)
    if response.status_code != 200:
        raise Exception(f"No se pudo descargar el archivo: {filename}")
    path = os.path.join(tempfile.gettempdir(), filename)
    with open(path, 'wb') as f:
        for chunk in response.iter_content(8192):
            f.write(chunk)
    return path

# Convertir .img a .tiff usando rasterio
def convert_to_tiff(input_path):
    output_path = input_path.replace(".img", ".tiff")
    with rasterio.open(input_path) as src:
        profile = src.profile.copy()
        profile.update(driver="GTiff", compress="lzw")
        rio_copy(src, output_path, **profile)
    return output_path

# Vista principal para gestión de datos
@datamanagement_bp.route('/data', methods=['GET'])
def data_management():
    configs = Configuration.objects(log__enable=True)
    return render_template("data_management.html", configurations=configs, active_page="data_management")

# Nueva ruta para manejar la descarga vía JavaScript
@datamanagement_bp.route('/download', methods=['POST'])
def download_file_route():
    config_id = request.form.get("config_id")
    if not config_id:
        return "Configuración no válida", 400

    try:
        selected_config = Configuration.objects.get(id=ObjectId(config_id))
        url, ext = get_parameters(selected_config)

        latest_file = get_latest_file(url, ext)
        if not latest_file:
            return "No se encontró archivo reciente", 404

        file_path = download_file(url, latest_file)
        if ext == ".img":
            file_path = convert_to_tiff(file_path)

        response = make_response(send_file(file_path, as_attachment=True, download_name=os.path.basename(file_path)))
        response.headers['X-Import-Success'] = 'true'
        return response

    except Exception as e:
        print("Error durante el proceso:", e)
        return "Error en la descarga", 500

# Ruta auxiliar para validación por AJAX
@datamanagement_bp.route('/check', methods=['GET'])
def check_new_data():
    config_id = request.args.get("config_id")
    if not config_id:
        return jsonify({"success": False, "message": "No se proporcionó configuración."}), 400

    config = Configuration.objects(id=ObjectId(config_id), log__enable=True).first()
    if not config:
        return jsonify({"success": False, "message": "Configuración inválida o deshabilitada."}), 404

    url, ext = get_parameters(config)
    if not url or not ext:
        return jsonify({"success": False, "message": "Faltan parámetros en la configuración."}), 400

    latest_file = get_latest_file(url, ext)
    if latest_file:
        return jsonify({"success": True, "latest_file": latest_file})
    else:
        return jsonify({"success": False, "message": f"No se encontró archivo válido con extensión {ext}"}), 404
