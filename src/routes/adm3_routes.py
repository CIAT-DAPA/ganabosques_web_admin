from flask import Blueprint, render_template, redirect, url_for, flash, request
from ganabosques_orm.collections.adm3 import Adm3
from ganabosques_orm.collections.adm2 import Adm2
from ganabosques_orm.auxiliaries.log import Log
from src.forms.adm3_form import Adm3Form

adm3_bp = Blueprint('adm3', __name__)

@adm3_bp.route('/adm3', methods=['GET', 'POST'])
def list_adm3():
    form = Adm3Form()
    form.load_adm2_choices()

    if form.validate_on_submit():
        adm2_ref = Adm2.objects(id=form.adm2_id.data).first()
        new_adm3 = Adm3(
            name=form.name.data,
            ext_id=form.ext_id.data,
            adm2_id=adm2_ref,
            log=Log(enable=form.enable.data)
        )
        new_adm3.save()
        flash('Vereda creada correctamente.', 'success')
        return redirect(url_for('adm3.list_adm3'))

    adm3_list = Adm3.objects()
    return render_template('adm3/list.html', adm3=adm3_list, form=form)

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
        if not adm.log:
            adm.log = Log(enable=True)
        adm.log.enable = form.enable.data
        adm.save()
        flash('Vereda actualizada.', 'success')
        return redirect(url_for('adm3.list_adm3'))
    else:
        if form.errors:
            print("Errores de validación:", form.errors)

    return render_template('adm3/edit.html', form=form, adm=adm)

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
