from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from ganabosques_orm.collections.adm3 import Adm3
from ganabosques_orm.collections.adm2 import Adm2
from ganabosques_orm.collections.adm1 import Adm1
from ganabosques_orm.auxiliaries.log import Log
from src.forms.adm3_form import Adm3Form

adm3_bp = Blueprint('adm3', __name__)

@adm3_bp.route('/api/adm2-by-adm1/<string:adm1_id>')
def get_adm2_by_adm1(adm1_id):
    """API JSON que devuelve los municipios (ADM2) de un departamento (ADM1)."""
    adm2_list = Adm2.objects(adm1_id=adm1_id).order_by('name')
    result = [{"id": str(adm.id), "name": adm.name} for adm in adm2_list]
    return jsonify(result)

@adm3_bp.route('/adm3', methods=['GET', 'POST'])
def list_adm3():
    form = Adm3Form()
    form.load_adm2_choices()

    if form.validate_on_submit():
        existing_adm3 = Adm3.objects(ext_id=form.ext_id.data).first()
        if existing_adm3:
            flash('Ya existe una vereda con ese Ext ID.', 'danger')
        else:
            adm2_ref = Adm2.objects(id=form.adm2_id.data).first()
            
            # Generar label automáticamente: DEPARTAMENTO,MUNICIPIO,VEREDA
            vereda_name = form.name.data.upper()
            municipio_name = adm2_ref.name.upper() if adm2_ref else ''
            depto_name = ''
            if adm2_ref and adm2_ref.adm1_id:
                adm1_ref = adm2_ref.adm1_id
                if hasattr(adm1_ref, 'name'):
                    depto_name = adm1_ref.name.upper()
                else:
                    adm1_doc = Adm1.objects(id=adm1_ref.id).first()
                    depto_name = adm1_doc.name.upper() if adm1_doc else ''
            generated_label = f"{depto_name},{municipio_name},{vereda_name}"
            
            new_adm3 = Adm3(
                name=form.name.data,
                ext_id=form.ext_id.data,
                adm2_id=adm2_ref,
                label=generated_label,
                log=Log(enable=form.enable.data)
            )
            new_adm3.save()
            flash('Vereda creada correctamente.', 'success')
            return redirect(url_for('adm3.list_adm3'))

    # Paginación y búsqueda para evitar carga infinita de miles de registros
    page = request.args.get('page', 1, type=int)
    search = request.args.get('q', '').strip()
    per_page = 50
    offset = (page - 1) * per_page
    
    query = Adm3.objects()
    if search:
        query = query.filter(name__icontains=search)
        
    total = query.count()
    # skip y limit deben llamarse ANTES de select_related, ya que select_related devuelve una lista evaluada
    adm3_list = query.skip(offset).limit(per_page).select_related()
    
    total_pages = (total + per_page - 1) // per_page
    
    return render_template('adm3/list.html', 
                          adm3=adm3_list, form=form,
                          adm1_list=Adm1.objects().order_by('name'),
                          page=page, total_pages=total_pages, search=search, total=total)


@adm3_bp.route('/adm3/edit/<string:id>', methods=['GET', 'POST'])
def edit_adm3(id):
    adm = Adm3.objects(id=id).first()
    if not adm:
        flash('Vereda no encontrada.', 'danger')
        return redirect(url_for('adm3.list_adm3'))

    form = Adm3Form()
    form.load_adm2_choices()

    if request.method == 'GET':
        form.name.data = adm.name
        form.ext_id.data = adm.ext_id
        form.adm2_id.data = str(adm.adm2_id.id) if adm.adm2_id else None
        form.enable.data = adm.log.enable if adm.log else True

    if form.validate_on_submit():
        adm2_ref = Adm2.objects(id=form.adm2_id.data).first()
        if not adm2_ref:
            flash('Municipio seleccionado no válido.', 'danger')
            return redirect(url_for('adm3.edit_adm3', id=id))

        adm.name = form.name.data
        adm.ext_id = form.ext_id.data
        adm.adm2_id = adm2_ref
        
        # Regenerar label automáticamente: DEPARTAMENTO,MUNICIPIO,VEREDA
        vereda_name = form.name.data.upper()
        municipio_name = adm2_ref.name.upper() if adm2_ref else ''
        depto_name = ''
        if adm2_ref and adm2_ref.adm1_id:
            adm1_ref = adm2_ref.adm1_id
            if hasattr(adm1_ref, 'name'):
                depto_name = adm1_ref.name.upper()
            else:
                adm1_doc = Adm1.objects(id=adm1_ref.id).first()
                depto_name = adm1_doc.name.upper() if adm1_doc else ''
        adm.label = f"{depto_name},{municipio_name},{vereda_name}"
        
        if not adm.log:
            adm.log = Log(enable=True)
        adm.log.enable = form.enable.data
        adm.save()
        flash('Vereda actualizada.', 'success')
        return redirect(url_for('adm3.list_adm3'))
    else:
        if form.errors:
            print("Errores de validación:", form.errors)

    # Determinar el ADM1 seleccionado para el cascading dropdown
    selected_adm2_id = str(adm.adm2_id.id) if adm.adm2_id else ''
    selected_adm1_id = ''
    if adm.adm2_id and adm.adm2_id.adm1_id:
        try:
            selected_adm1_id = str(adm.adm2_id.adm1_id.id)
        except Exception:
            selected_adm1_id = ''

    return render_template('adm3/edit.html', form=form, adm=adm,
                          adm1_list=Adm1.objects().order_by('name'),
                          selected_adm1_id=selected_adm1_id,
                          selected_adm2_id=selected_adm2_id)

@adm3_bp.route('/adm3/delete/<string:id>')
def delete_adm3(id):
    adm = Adm3.objects(id=id).first()
    if not adm:
        flash('Vereda no encontrada.', 'danger')
    else:
        if not adm.log:
            adm.log = Log(enable=False)
        else:
            adm.log.enable = False
        adm.save()
        flash('Vereda deshabilitada.', 'warning')
    return redirect(url_for('adm3.list_adm3'))

@adm3_bp.route('/adm3/reset/<string:id>')
def reset_adm3(id):
    adm = Adm3.objects(id=id).first()
    if not adm:
        flash('Vereda no encontrada.', 'danger')
    else:
        if not adm.log:
            adm.log = Log(enable=True)
        else:
            adm.log.enable = True
        adm.save()
        flash('Vereda reactivada.', 'success')
    return redirect(url_for('adm3.list_adm3'))
