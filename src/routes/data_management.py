import os
import tempfile
import requests
from bs4 import BeautifulSoup
from flask import Blueprint, render_template, request, send_file, flash, jsonify
import rasterio
from rasterio.shutil import copy as rio_copy
import certifi

# Blueprint
datamanagement_bp = Blueprint('datamanagement', __name__, url_prefix='/data_management')

# URL de la fuente
DATA_URL = "https://bart.ideam.gov.co/smbyc/Cambio%20en%20la%20superficie%20cubierta%20por%20bosque%20natural/Capas/"

# Función para obtener el último archivo .img subido
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_latest_img_file():
    try:
        response = requests.get(DATA_URL, verify=False)  # ⚠️ SOLO DESARROLLO
        soup = BeautifulSoup(response.text, "html.parser")

        img_files = [
            link.get('href') for link in soup.find_all('a')
            if link.get('href') and link.get('href').endswith('.img')
        ]

        if not img_files:
            return None

        sorted_files = sorted(img_files, reverse=True)
        return sorted_files[0]
    except Exception as e:
        print("Error al obtener archivos:", e)
        return None

# Función para descargar un archivo
def download_file_from_url(file_name):
    url = f"{DATA_URL}{file_name}"
    response = requests.get(url, stream=True, verify=False) 
    if response.status_code != 200:
        raise Exception(f"No se pudo descargar el archivo: {file_name}")

    tmp_dir = tempfile.gettempdir()
    file_path = os.path.join(tmp_dir, file_name)
    with open(file_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    return file_path

# Función para convertir .img a .tiff usando rasterio
def convert_img_to_tiff_with_rasterio(input_img_path):
    output_path = input_img_path.replace(".img", ".tiff")
    with rasterio.open(input_img_path) as src:
        profile = src.profile.copy()
        profile.update(driver="GTiff", compress="lzw")
        rio_copy(src, output_path, **profile)
    return output_path

# Página principal (GET para mostrar, POST para descargar y convertir)
@datamanagement_bp.route('/data', methods=['GET', 'POST'])
def data_management():
    latest_file = get_latest_img_file()
    if not latest_file:
        flash("No se pudo obtener el archivo más reciente.", "danger")
        return render_template("data_management.html", latest_file=None, active_page='data_management')

    if request.method == 'POST':
        try:
            img_path = download_file_from_url(latest_file)
            tiff_path = convert_img_to_tiff_with_rasterio(img_path)
            return send_file(tiff_path, as_attachment=True, download_name=os.path.basename(tiff_path))
        except Exception as e:
            print("Error durante el proceso:", e)
            flash("Ocurrió un error al descargar o convertir el archivo.", "danger")

    return render_template("data_management.html", latest_file=latest_file, active_page='data_management')

# Ruta para validación desde JS
@datamanagement_bp.route('/check', methods=['GET'])
def check_new_data():
    latest_file = get_latest_img_file()
    if latest_file:
        return jsonify({"success": True, "latest_file": latest_file})
    return jsonify({"success": False, "message": "No se encontró archivo .img válido."}), 404
