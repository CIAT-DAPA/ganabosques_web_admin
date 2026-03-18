from flask import Blueprint, render_template, redirect, url_for, flash, request
from ganabosques_orm.collections.adm2 import Adm2
from ganabosques_orm.collections.adm1 import Adm1
from ganabosques_orm.auxiliaries.log import Log
from src.forms.adm2_form import Adm2Form

adm2_bp = Blueprint('adm2', __name__)

@adm2_bp.route('/adm2', methods=['GET', 'POST'])
def list_adm2():
    form = Adm2Form()
    form.load_adm1_choices()

    if form.validate_on_submit():
        existing_adm2 = Adm2.objects(ext_id=form.ext_id.data).first()
        if existing_adm2:
            flash('Ya existe un municipio con ese Ext ID.', 'danger')
        else:
            new_adm2 = Adm2(
                name=form.name.data,
                ext_id=form.ext_id.data,
                adm1_id=Adm1.objects(id=form.adm1_id.data).first(),  # Asignar documento, no string
                log=Log(enable=form.enable.data)
            )
            new_adm2.save()
            flash('Municipio creado correctamente.', 'success')
            return redirect(url_for('adm2.list_adm2'))

    query_str = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 50
    offset = (page - 1) * per_page
    
    query = Adm2.objects()

    if query_str:
        query = query.filter(__raw__={
            "$or": [
                {"name": {"$regex": query_str, "$options": "i"}},
                {"ext_id": {"$regex": query_str, "$options": "i"}}
            ]
        })

    total = query.count()
    adm2_list = query.order_by('-id').skip(offset).limit(per_page).select_related()
    total_pages = (total + per_page - 1) // per_page

    return render_template(
        'adm2/list.html', 
        adm2=adm2_list, 
        form=form,
        page=page,
        total_pages=total_pages,
        search=query_str,
        total=total
    )

@adm2_bp.route('/adm2/edit/<string:id>', methods=['GET', 'POST'])
def edit_adm2(id):
    adm = Adm2.objects(id=id).first()
    if not adm:
        flash('Municipio no encontrado.', 'danger')
        return redirect(url_for('adm2.list_adm2'))

    form = Adm2Form(obj=adm)
    form.load_adm1_choices()

    if request.method == 'GET':
        form.name.data = adm.name
        form.ext_id.data = adm.ext_id
        form.adm1_id.data = str(adm.adm1_id.id) if adm.adm1_id else None
        form.enable.data = adm.log.enable if adm.log else True

    if form.validate_on_submit():
        adm.name = form.name.data
        adm.ext_id = form.ext_id.data
        adm.adm1_id = Adm1.objects(id=form.adm1_id.data).first()  # Corregido aquí
        if not adm.log:
            adm.log = Log(enable=True)
        adm.log.enable = form.enable.data
        adm.save()
        flash('Municipio actualizado.', 'success')
        return redirect(url_for('adm2.list_adm2'))

    return render_template('adm2/edit.html', form=form, adm=adm)


@adm2_bp.route('/adm2/delete/<string:id>')
def delete_adm2(id):
    adm = Adm2.objects(id=id).first()
    if not adm:
        flash('Municipio no encontrado.', 'danger')
    else:
        if not adm.log:
            adm.log = Log(enable=False)
        else:
            adm.log.enable = False
        adm.save()
        flash('Municipio deshabilitado.', 'warning')
    return redirect(url_for('adm2.list_adm2'))


@adm2_bp.route('/adm2/reset/<string:id>')
def reset_adm2(id):
    adm = Adm2.objects(id=id).first()
    if not adm:
        flash('Municipio no encontrado.', 'danger')
    else:
        if not adm.log:
            adm.log = Log(enable=True)
        else:
            adm.log.enable = True
        adm.save()
        flash('Municipio reactivado.', 'success')
    return redirect(url_for('adm2.list_adm2'))
