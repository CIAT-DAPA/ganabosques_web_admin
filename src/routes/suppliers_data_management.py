from flask import Blueprint, request, render_template, redirect, flash, make_response
from datetime import datetime
from ganabosques_orm.collections.enterprise import Enterprise
from ganabosques_orm.collections.farm import Farm
from ganabosques_orm.collections.suppliers import Suppliers
from ganabosques_orm.auxiliaries.years import Years
from ganabosques_orm.auxiliaries.log import Log
from ganabosques_orm.enums.label import Label
from config import config
import csv
import io

suppliers_bp = Blueprint('suppliers', __name__)

def extract_data_from_csv(file_stream):
    lines = file_stream.read().decode('utf-8').splitlines()
    reader = csv.reader(lines)
    data = [(row[0].strip(), row[1].strip()) for row in reader if row and len(row) >= 2]
    if not data:
        raise ValueError("El archivo CSV debe tener al menos dos columnas con datos válidos.")
    return data

def generate_csv_response(filename, rows, headers):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    for row in rows:
        writer.writerow(row)
    output.seek(0)

    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    response.headers['Content-Type'] = 'text/csv'
    return response

@suppliers_bp.route('/descargar_encontrados', methods=['POST'])
def descargar_encontrados():
    encontrados = request.form.getlist('encontrados[]')
    encontrados = [row.split('|') for row in encontrados]
    return generate_csv_response('encontrados.csv', encontrados, ['codigo_empresa', 'codigo_finca'])

@suppliers_bp.route('/descargar_no_encontrados', methods=['POST'])
def descargar_no_encontrados():
    no_encontrados = request.form.getlist('no_encontrados[]')
    no_encontrados = [row.split('|') for row in no_encontrados]
    return generate_csv_response('no_encontrados.csv', no_encontrados, ['codigo_empresa', 'codigo_finca'])

@suppliers_bp.route('/importar_proveedores', methods=['GET', 'POST'])
def importar_proveedores():
    labels = list(Label)
    anios = list(range(2013, datetime.now().year + 1))
    encontrados, no_encontrados = [], []

    if request.method == 'POST':
        label_value = request.form.get('label')
        anios_seleccionados = request.form.getlist('anios')
        archivo = request.files.get('archivo')

        if not label_value or not archivo:
            flash("Debes seleccionar un tipo de código y subir un archivo CSV", 'danger')
            return redirect(request.url)

        try:
            label_enum = Label[label_value]
        except KeyError:
            flash("Tipo de código no válido", 'danger')
            return redirect(request.url)

        try:
            datos_csv = extract_data_from_csv(archivo)
        except ValueError as e:
            flash(str(e), 'danger')
            return redirect(request.url)

        nuevos, actualizados = 0, 0

        for codigo_empresa, codigo_finca in datos_csv:
            empresa = Enterprise.objects(ext_id__match={"label": label_enum, "ext_code": codigo_empresa}).first()
            finca = Farm.objects(ext_id__ext_code=codigo_finca).first()

            if not empresa or not finca:
                no_encontrados.append((codigo_empresa, codigo_finca))
                continue

            existentes = Suppliers.objects(enterprise_id=empresa.id, farm_id=finca.id).first()
            nuevos_anios = [Years(years=str(a)) for a in anios_seleccionados]

            if not existentes:
                Suppliers(
                    enterprise_id=empresa.id,
                    farm_id=finca.id,
                    years=nuevos_anios,
                    log=Log(enable=True)
                ).save()
                nuevos += 1
            else:
                ya_guardados = set(y.years for y in existentes.years)
                nuevos_unicos = [Years(years=str(a)) for a in anios_seleccionados if str(a) not in ya_guardados]
                if nuevos_unicos:
                    existentes.years.extend(nuevos_unicos)
                    existentes.save()
                    actualizados += 1

            encontrados.append((codigo_empresa, codigo_finca))

        flash(f"Proveedores guardados: {nuevos} nuevos, {actualizados} actualizados.", 'success')

        return render_template('import_suppliers.html', labels=labels, anios=anios,
                               encontrados=encontrados, no_encontrados=no_encontrados,
                               selected_label=label_value, selected_anios=anios_seleccionados,
                               active_page='import_suppliers')

    return render_template('import_suppliers.html', labels=labels, anios=anios, active_page='import_suppliers')
