from flask import Blueprint, render_template, redirect, url_for, request, flash
from bson import ObjectId
from ganabosques_orm.collections.enterprise import Enterprise
from ganabosques_orm.collections.adm2 import Adm2
from ganabosques_orm.auxiliaries.extidenterprise import ExtIdEnterprise
from ganabosques_orm.auxiliaries.log import Log
from ganabosques_orm.enums.label import Label
from ganabosques_orm.enums.typeenterprise import TypeEnterprise
from forms.enterprise_form import EnterpriseForm

enterprise_bp = Blueprint('enterprise', __name__)

@enterprise_bp.route('/enterprise', methods=['GET', 'POST'])
def list_enterprise():
    form = EnterpriseForm()
    form.load_adm2_choices()
    form.load_label_choices()
    form.load_type_enterprise_choices()

    # Manejo de creación de empresa (POST)
    if form.validate_on_submit():
        try:
            adm2_ref = Adm2.objects.get(id=ObjectId(form.adm2_id.data))
            new_enterprise = Enterprise(
                name=form.name.data,
                adm2_id=adm2_ref,
                type_enterprise=TypeEnterprise[form.type_enterprise.data],
                latitude=form.latitude.data,
                longitud=form.longitud.data,
                ext_id=[ExtIdEnterprise(label=Label[form.label.data], ext_code=form.ext_code.data)],
                log=Log(enable=form.enable.data)
            )
            new_enterprise.save()
            flash('Empresa creada exitosamente.', 'success')
            return redirect(url_for('enterprise.list_enterprise'))
        except Exception as e:
            flash(f'Error al crear la empresa: {e}', 'danger')

    # Buscador funcional (GET con query param)
    query = request.args.get('q', '').strip()
    if query:
        enterprises = Enterprise.objects(
            __raw__={
                "$or": [
                    {"name": {"$regex": query, "$options": "i"}},
                    {"ext_id.ext_code": {"$regex": query, "$options": "i"}},
                    {"adm2_id.name": {"$regex": query, "$options": "i"}}
                ]
            }
        )
    else:
        enterprises = Enterprise.objects()

    return render_template('enterprise/list.html', enterprises=enterprises, form=form)

@enterprise_bp.route('/enterprise/edit/<string:id>', methods=['GET', 'POST'])
def edit_enterprise(id):
    enterprise = Enterprise.objects.get(id=ObjectId(id))
    form = EnterpriseForm()
    form.load_adm2_choices()
    form.load_label_choices()
    form.load_type_enterprise_choices()

    if request.method == 'GET':
        form.name.data = enterprise.name
        form.adm2_id.data = str(enterprise.adm2_id.id) if enterprise.adm2_id else None
        form.type_enterprise.data = enterprise.type_enterprise.name if enterprise.type_enterprise else None
        form.latitude.data = enterprise.latitude
        form.longitud.data = enterprise.longitud
        form.enable.data = enterprise.log.enable if enterprise.log else True

        if enterprise.ext_id:
            form.label.data = enterprise.ext_id[0].label.name
            form.ext_code.data = enterprise.ext_id[0].ext_code

    if form.validate_on_submit():
        try:
            adm2_ref = Adm2.objects.get(id=ObjectId(form.adm2_id.data))
            enterprise.name = form.name.data
            enterprise.adm2_id = adm2_ref
            enterprise.type_enterprise = TypeEnterprise[form.type_enterprise.data]
            enterprise.latitude = form.latitude.data
            enterprise.longitud = form.longitud.data
            enterprise.ext_id = [ExtIdEnterprise(label=Label[form.label.data], ext_code=form.ext_code.data)]

            if not enterprise.log:
                enterprise.log = Log(enable=True)
            enterprise.log.enable = form.enable.data

            enterprise.save()
            flash('Empresa actualizada correctamente.', 'success')
            return redirect(url_for('enterprise.list_enterprise'))
        except Exception as e:
            flash(f'Error al actualizar la empresa: {e}', 'danger')

    return render_template('enterprise/edit.html', form=form, enterprise=enterprise)

@enterprise_bp.route('/enterprise/delete/<string:id>', methods=['POST'])
def delete_enterprise(id):
    enterprise = Enterprise.objects.get(id=ObjectId(id))
    if not enterprise.log:
        enterprise.log = Log(enable=False)
    else:
        enterprise.log.enable = False
    enterprise.save()
    flash('Empresa deshabilitada.', 'warning')
    return redirect(url_for('enterprise.list_enterprise'))

@enterprise_bp.route('/enterprise/reset/<string:id>', methods=['POST'])
def reset_enterprise(id):
    enterprise = Enterprise.objects.get(id=ObjectId(id))
    if not enterprise.log:
        enterprise.log = Log(enable=True)
    else:
        enterprise.log.enable = True
    enterprise.save()
    flash('Empresa reactivada.', 'success')
    return redirect(url_for('enterprise.list_enterprise'))

@enterprise_bp.route('/enterprise/delete/permanent/<string:id>', methods=['POST'])
def permanent_delete_enterprise(id):
    try:
        enterprise = Enterprise.objects.get(id=ObjectId(id))
        enterprise.delete()  # Elimina completamente el documento de la base de datos
        flash('Empresa eliminada definitivamente.', 'danger')
    except Exception as e:
        flash(f'Error al eliminar permanentemente: {e}', 'danger')
    return redirect(url_for('enterprise.list_enterprise'))

