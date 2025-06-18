from flask import Blueprint, render_template, redirect, url_for, flash, request
from ganabosques_orm.collections.farm import Farm
from ganabosques_orm.collections.adm3 import Adm3
from ganabosques_orm.auxiliaries.log import Log
from ganabosques_orm.auxiliaries.extidfarm import ExtIdFarm
from ganabosques_orm.enums.farmsource import FarmSource
from ganabosques_orm.enums.source import Source
from src.forms.farm_form import FarmForm
from bson import ObjectId

farm_bp = Blueprint('farm', __name__)


@farm_bp.route('/farm', methods=['GET', 'POST'])
def list_farms():
    form = FarmForm()
    form.load_adm3_choices()

    if form.validate_on_submit():
        print("Formulario válido")

        adm3_ref = Adm3.objects(id=form.adm3_id.data).first()

        ext_ids = []
        for entry in form.ext_id.entries:
            ext_ids.append(ExtIdFarm(
                source=Source[entry.form.source.data],
                ext_code=entry.form.ext_code.data
            ))

        new_farm = Farm(
            adm3_id=adm3_ref,
            ext_id=ext_ids,
            farm_source=FarmSource[form.farm_source.data],
            log=Log(enable=form.enable.data)
        )
        new_farm.save()
        flash('Finca creada correctamente.', 'success')
        return redirect(url_for('farm.list_farms'))
    else:
        print("Errores en el formulario:")
        print(form.errors)

    query = Farm.objects()
    search = request.args.get('search', '').strip()

    if search:
        query = query.filter(__raw__={
            "$or": [
                {"ext_id.ext_code": {"$regex": search, "$options": "i"}},
                {"adm3_id.name": {"$regex": search, "$options": "i"}}
            ]
        })

    farms = query.order_by('-id')

    return render_template(
        'farm/list.html',
        farms=farms,
        form=form,
        search=search,
        adm3_list=Adm3.objects(log__enable=True),
        farm_sources=FarmSource,
        source_enum=[{"name": s.name, "value": s.value} for s in Source]  # ← clave correcta
    )


@farm_bp.route('/farm/edit/<string:id>', methods=['GET', 'POST'])
def edit_farm(id):
    farm = Farm.objects(id=ObjectId(id)).first()
    if not farm:
        flash('Finca no encontrada.', 'danger')
        return redirect(url_for('farm.list_farms'))

    if request.method == 'POST':
        adm3_id = request.form.get('adm3_id')
        farm_source = request.form.get('farm_source')
        ext_sources = request.form.getlist('ext_id_source[]')
        ext_codes = request.form.getlist('ext_id_code[]')

        if not adm3_id or not farm_source or not ext_sources or not ext_codes:
            flash("Todos los campos son obligatorios.", "danger")
            return redirect(url_for('farm.list_farms'))

        if len(ext_sources) != len(ext_codes):
            flash("Los códigos externos no coinciden.", "danger")
            return redirect(url_for('farm.list_farms'))

        try:
            ext_ids = []
            for source, code in zip(ext_sources, ext_codes):
                ext_ids.append(ExtIdFarm(
                    source=Source[source],
                    ext_code=code
                ))

            farm.adm3_id = Adm3.objects(id=adm3_id).first()
            farm.farm_source = FarmSource[farm_source]
            farm.ext_id = ext_ids

            if not farm.log:
                farm.log = Log(enable=True)
            else:
                farm.log.enable = True

            farm.save()
            flash('Finca actualizada correctamente.', 'success')
        except Exception as e:
            flash(f'Ocurrió un error al actualizar: {str(e)}', 'danger')

        return redirect(url_for('farm.list_farms'))

    # Si es GET, solo carga los datos (modal se llena en el template)
    return render_template('farm/edit.html', farm=farm)


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
