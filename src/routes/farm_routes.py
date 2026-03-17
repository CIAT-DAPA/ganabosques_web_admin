from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from ganabosques_orm.collections.farm import Farm
from ganabosques_orm.collections.adm3 import Adm3
from ganabosques_orm.collections.adm2 import Adm2
from ganabosques_orm.collections.adm1 import Adm1
from ganabosques_orm.auxiliaries.log import Log
from ganabosques_orm.auxiliaries.extidfarm import ExtIdFarm
from ganabosques_orm.enums.farmsource import FarmSource
from ganabosques_orm.enums.source import Source
from ganabosques_orm.enums.valuechain import ValueChain
from src.forms.farm_form import FarmForm
from bson import ObjectId

farm_bp = Blueprint('farm', __name__)

@farm_bp.route('/api/adm3-by-adm2/<string:adm2_id>')
def get_adm3_by_adm2(adm2_id):
    """API JSON que devuelve las veredas (ADM3) de un municipio (ADM2)."""
    adm3_list = Adm3.objects(adm2_id=adm2_id).order_by('name')
    result = [{"id": str(adm.id), "name": adm.name} for adm in adm3_list]
    return jsonify(result)


@farm_bp.route('/farm', methods=['GET', 'POST'])
def list_farms():
    form = FarmForm()
    form.load_adm3_choices()

    if form.validate_on_submit():
        adm3_ref = Adm3.objects(id=form.adm3_id.data).first()

        ext_ids = [
            ExtIdFarm(
                source=Source[entry.form.source.data],
                ext_code=entry.form.ext_code.data
            )
            for entry in form.ext_id.entries
        ]

        new_farm = Farm(
            adm3_id=adm3_ref,
            ext_id=ext_ids,
            farm_source=FarmSource[form.farm_source.data],
            value_chain=ValueChain[form.value_chain.data] if form.value_chain.data else None,
            log=Log(enable=form.enable.data)
        )
        new_farm.save()
        flash('Finca creada correctamente.', 'success')
        return redirect(url_for('farm.list_farms'))

    search = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 50
    offset = (page - 1) * per_page
    
    query = Farm.objects()
    if search:
        query = query.filter(__raw__={
            "$or": [
                {"ext_id.ext_code": {"$regex": search, "$options": "i"}},
                {"adm3_id.name": {"$regex": search, "$options": "i"}}
            ]
        })

    total = query.count()
    farms = query.order_by('-id').skip(offset).limit(per_page).select_related()
    total_pages = (total + per_page - 1) // per_page

    return render_template(
        'farm/list.html',
        farms=farms,
        form=form,
        adm1_list=Adm1.objects().order_by('name'),
        farm_sources=FarmSource,
        source_enum=[{"name": s.name, "value": s.value} for s in Source],
        page=page,
        total_pages=total_pages,
        search=search,
        total=total
    )


@farm_bp.route('/farm/edit/<string:id>', methods=['GET', 'POST'])
def edit_farm(id):
    farm = Farm.objects(id=ObjectId(id)).first()
    if not farm:
        flash('Finca no encontrada.', 'danger')
        return redirect(url_for('farm.list_farms'))

    form = FarmForm()
    form.load_adm3_choices()

    if request.method == 'GET':
        form.adm3_id.data = str(farm.adm3_id.id) if farm.adm3_id else None
        form.farm_source.data = farm.farm_source.name
        form.value_chain.data = farm.value_chain.name if farm.value_chain else ''
        form.enable.data = farm.log.enable if farm.log else True
        form.ext_id.pop_entry()  # Quitar el inicial vacío
        for ext in farm.ext_id:
            form.ext_id.append_entry({
                'source': ext.source.name,
                'ext_code': ext.ext_code
            })

    if form.validate_on_submit():
        try:
            adm3_ref = Adm3.objects(id=form.adm3_id.data).first()
            farm.adm3_id = adm3_ref
            farm.farm_source = FarmSource[form.farm_source.data]
            farm.value_chain = ValueChain[form.value_chain.data] if form.value_chain.data else None
            farm.ext_id = [
                ExtIdFarm(
                    source=Source[entry.form.source.data],
                    ext_code=entry.form.ext_code.data
                ) for entry in form.ext_id.entries
            ]
            if not farm.log:
                farm.log = Log(enable=True)
            farm.log.enable = form.enable.data
            farm.save()
            flash('Finca actualizada correctamente.', 'success')
            return redirect(url_for('farm.list_farms'))
        except Exception as e:
            flash(f'Error al actualizar: {str(e)}', 'danger')

    # Determinar los IDs seleccionados para el cascading dropdown
    selected_adm3_id = str(farm.adm3_id.id) if farm.adm3_id else ''
    selected_adm2_id = ''
    selected_adm1_id = ''
    if farm.adm3_id and farm.adm3_id.adm2_id:
        try:
            selected_adm2_id = str(farm.adm3_id.adm2_id.id)
            if farm.adm3_id.adm2_id.adm1_id:
                selected_adm1_id = str(farm.adm3_id.adm2_id.adm1_id.id)
        except Exception:
            pass

    return render_template(
        'farm/edit.html',
        form=form,
        farm=farm,
        adm1_list=Adm1.objects().order_by('name'),
        selected_adm1_id=selected_adm1_id,
        selected_adm2_id=selected_adm2_id,
        selected_adm3_id=selected_adm3_id
    )


@farm_bp.route('/farm/delete/<string:id>')
def delete_farm(id):
    farm = Farm.objects(id=ObjectId(id)).first()
    if not farm:
        flash('Finca no encontrada.', 'danger')
    else:
        if not farm.log:
            farm.log = Log(enable=False)
        else:
            farm.log.enable = False
        farm.save()
        flash('Finca deshabilitada.', 'warning')
    return redirect(url_for('farm.list_farms'))


@farm_bp.route('/farm/reset/<string:id>')
def reset_farm(id):
    farm = Farm.objects(id=ObjectId(id)).first()
    if not farm:
        flash('Finca no encontrada.', 'danger')
    else:
        if not farm.log:
            farm.log = Log(enable=True)
        else:
            farm.log.enable = True
        farm.save()
        flash('Finca reactivada.', 'success')
    return redirect(url_for('farm.list_farms'))
