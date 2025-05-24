from flask import Blueprint, request, render_template, redirect, flash
from datetime import datetime
from ganabosques_orm.collections.enterprise import Enterprise
from ganabosques_orm.collections.farm import Farm
from ganabosques_orm.collections.suppliers import Suppliers
from ganabosques_orm.auxiliaries.years import Years
from ganabosques_orm.auxiliaries.log import Log
from config import config

suppliers_bp = Blueprint('suppliers', __name__)

# Función auxiliar para extraer códigos desde el archivo CSV
def extract_codigos_from_csv(file_stream):
    lines = file_stream.read().decode('utf-8').splitlines()
    codigos = [line.strip() for line in lines if line.strip()]
    if not codigos:
        raise ValueError("El archivo está vacío o no contiene códigos válidos.")
    return codigos

# Ruta para importar proveedores
@suppliers_bp.route('/importar_proveedores', methods=['GET', 'POST'])
def importar_proveedores():
    empresas = Enterprise.objects.only('id', 'name')
    anios = list(range(2013, datetime.now().year + 1))
    encontrados, no_encontrados = [], []

    if request.method == 'POST':
        empresa_id = request.form.get('empresa_id')
        anios_seleccionados = request.form.getlist('anios')
        archivo = request.files.get('archivo')

        # Validación básica de entrada
        if not empresa_id or not archivo:
            flash("Debes seleccionar una empresa y subir un archivo CSV", 'danger')
            return redirect(request.url)

        try:
            codigos = extract_codigos_from_csv(archivo)
        except ValueError as e:
            flash(str(e), 'danger')
            return redirect(request.url)

        # Buscar fincas cuyo ext_code coincida con algún código importado
        farms = Farm.objects(ext_id__ext_code__in=codigos)
        encontrados = [ext.ext_code for farm in farms for ext in farm.ext_id if ext.ext_code in codigos]
        no_encontrados = list(set(codigos) - set(encontrados))

        # Obtener la empresa seleccionada
        enterprise = Enterprise.objects.get(id=empresa_id)
        nuevos, actualizados = 0, 0

        for farm in farms:
            # Buscar si ya existe un documento Supplier para esta empresa y finca
            supplier = Suppliers.objects(enterprise_id=enterprise.id, farm_id=farm.id).first()

            # Crear lista de nuevos años como documentos embebidos correctamente
            nuevos_anios = []
            for a in anios_seleccionados:
                y = Years()
                y.years = str(a)
                nuevos_anios.append(y)

            if not supplier:
                Suppliers(
                    enterprise_id=enterprise.id,
                    farm_id=farm.id,
                    years=nuevos_anios,
                    log=Log(enable=True)
                ).save()
                nuevos += 1
            else:
                existentes = set(y.years for y in supplier.years)
                nuevos_uniq = []
                for a in anios_seleccionados:
                    if str(a) not in existentes:
                        y = Years()
                        y.years = str(a)
                        nuevos_uniq.append(y)
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
