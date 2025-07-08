from flask import Blueprint, render_template, redirect, url_for, flash, request
from ganabosques_orm.collections.adm1 import Adm1
from ganabosques_orm.auxiliaries.log import Log
from src.forms.adm1_form import Adm1Form

adm1_bp = Blueprint('adm1', __name__)

@adm1_bp.route('/adm1', methods=['GET', 'POST'])
def list_adm1():
    form = Adm1Form()

    if form.validate_on_submit():
        existing_adm = Adm1.objects(ext_id=form.ext_id.data).first()
        if existing_adm:
            flash('Ya existe un departamento con ese Ext ID.', 'danger')
        else:
            new_adm1 = Adm1(
                name=form.name.data,
                ext_id=form.ext_id.data,
                ugg_size=form.ugg_size.data,
                log=Log(enable=form.enable.data)
            )
            new_adm1.save()
            flash('Departamento creado correctamente.', 'success')
            return redirect(url_for('adm1.list_adm1'))

    adm1_list = Adm1.objects(log__enable=True)
    return render_template('adm1/list.html', adm1=adm1_list, form=form)


@adm1_bp.route('/adm1/edit/<string:id>', methods=['GET', 'POST'])
def edit_adm1(id):
    adm = Adm1.objects(id=id).first()
    if not adm:
        flash('Departamento no encontrado.', 'danger')
        return redirect(url_for('adm1.list_adm1'))

    form = Adm1Form(obj=adm)

    if request.method == 'GET':
        form.name.data = adm.name
        form.ext_id.data = adm.ext_id
        form.ugg_size.data = adm.ugg_size
        form.enable.data = adm.log.enable if adm.log else True

    if form.validate_on_submit():
        adm.name = form.name.data
        adm.ext_id = form.ext_id.data
        adm.ugg_size = form.ugg_size.data
        if not adm.log:
            adm.log = Log(enable=True)
        adm.log.enable = form.enable.data
        adm.save()
        flash('Departamento actualizado.', 'success')
        return redirect(url_for('adm1.list_adm1'))

    return render_template('adm1/edit.html', form=form, adm=adm)

@adm1_bp.route('/adm1/delete/<string:id>')
def delete_adm1(id):
    adm = Adm1.objects(id=id).first()
    if not adm:
        flash('Departamento no encontrado.', 'danger')
    else:
        if not adm.log:
            adm.log = Log(enable=False)
        else:
            adm.log.enable = False
        adm.save()
        flash('Departamento deshabilitado.', 'warning')
    return redirect(url_for('adm1.list_adm1'))

@adm1_bp.route('/adm1/reset/<string:id>')
def reset_adm1(id):
    adm = Adm1.objects(id=id).first()
    if not adm:
        flash('Departamento no encontrado.', 'danger')
    else:
        if not adm.log:
            adm.log = Log(enable=True)
        else:
            adm.log.enable = True
        adm.save()
        flash('Departamento reactivado.', 'success')
    return redirect(url_for('adm1.list_adm1'))
