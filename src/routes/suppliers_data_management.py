from flask import Blueprint, request, render_template, redirect, flash
from datetime import datetime
from ganabosques_orm.collections.enterprise import Enterprise
from ganabosques_orm.collections.farm import Farm
from ganabosques_orm.collections.suppliers import Suppliers
from ganabosques_orm.auxiliaries.years import Years
from config import config

suppliers_bp = Blueprint('suppliers', __name__)

# Extract codes from CSV line-by-line
def extract_codigos_from_csv(file_stream):
    lines = file_stream.read().decode('utf-8').splitlines()
    codigos = [line.strip() for line in lines if line.strip()]
    if not codigos:
        raise ValueError("El archivo está vacío o no contiene códigos válidos.")
    return codigos

# Route to import suppliers
@suppliers_bp.route('/importar_proveedores', methods=['GET', 'POST'])
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

        try:
            codigos = extract_codigos_from_csv(archivo)
        except ValueError as e:
            flash(str(e), 'danger')
            return redirect(request.url)

        codigos_encontrados = Farm.objects(ext_id__ext_code__in=codigos).distinct('ext_id.ext_code')
        encontrados = list(set(codigos_encontrados))
        no_encontrados = list(set(codigos) - set(encontrados))

        enterprise = Enterprise.objects.get(id=empresa_id)
        farms = Farm.objects(ext_id__ext_code__in=encontrados)
        nuevos, actualizados = 0, 0

        for farm in farms:
            supplier = Suppliers.objects(enterprise_id=enterprise.id, farm_id=farm.id).first()
            nuevos_anios = [Years(years=a) for a in anios_seleccionados]

            if not supplier:
                Suppliers(
                    enterprise_id=enterprise.id,
                    farm_id=farm.id,
                    years=nuevos_anios
                ).save()
                nuevos += 1
            else:
                existentes = set(y.years for y in supplier.years)
                nuevos_uniq = [Years(years=a) for a in anios_seleccionados if a not in existentes]
                if nuevos_uniq:
                    supplier.years.extend(nuevos_uniq)
                    supplier.save()
                    actualizados += 1

        flash(f"Proveedores guardados: {nuevos} nuevos, {actualizados} actualizados.", 'success')

        return render_template('import_suppliers.html', empresas=empresas, anios=anios,
                               encontrados=encontrados, no_encontrados=no_encontrados,
                               selected_empresa=empresa_id, selected_anios=anios_seleccionados,
                               active_page='import_suppliers')

    return render_template('import_suppliers.html', empresas=empresas, anios=anios, active_page='import_suppliers')
