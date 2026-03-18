from flask import Blueprint, render_template, request, redirect, url_for, flash
from bson import ObjectId
from ganabosques_orm.collections.configuration import Configuration
from ganabosques_orm.auxiliaries.parameters import Parameters
from ganabosques_orm.auxiliaries.log import Log
from forms.configuration_form import ConfigurationForm

configuration_bp = Blueprint('configuration', __name__, url_prefix='/configuration')

@configuration_bp.route('/', methods=['GET', 'POST'])
def list_configuration():
    form = ConfigurationForm()

    if form.validate_on_submit():
        try:
            new_config = Configuration(
                name=form.name.data,
                parameters=[
                    Parameters(key='url', value=form.url.data),
                    Parameters(key='extension', value=form.extension.data)
                ],
                log=Log(enable=form.enable.data)
            )
            new_config.save()
            flash('Configuración agregada correctamente.', 'success')
            return redirect(url_for('configuration.list_configuration'))
        except Exception as e:
            flash(f'Error al guardar la configuración: {e}', 'danger')

    query = request.args.get('q', '').strip()
    configurations = Configuration.objects()

    if query:
        configurations = configurations.filter(
            __raw__={
                "$or": [
                    {"name": {"$regex": query, "$options": "i"}},
                    {"parameters.value": {"$regex": query, "$options": "i"}}
                ]
            }
        )

    return render_template('configuration/list.html', configurations=configurations, form=form)

@configuration_bp.route('/edit/<string:id>', methods=['GET', 'POST'])
def edit_configuration(id):
    config = Configuration.objects.get(id=ObjectId(id))
    form = ConfigurationForm()

    if request.method == 'GET':
        form.name.data = config.name
        form.enable.data = config.log.enable if config.log else True

        for param in config.parameters:
            if param.key == 'url':
                form.url.data = param.value
            elif param.key == 'extension':
                form.extension.data = param.value

    if form.validate_on_submit():
        try:
            config.name = form.name.data
            config.parameters = [
                Parameters(key='url', value=form.url.data),
                Parameters(key='extension', value=form.extension.data)
            ]

            if not config.log:
                config.log = Log(enable=form.enable.data)
            else:
                config.log.enable = form.enable.data

            config.save()
            flash('Configuración actualizada correctamente.', 'success')
            return redirect(url_for('configuration.list_configuration'))
        except Exception as e:
            flash(f'Error al actualizar la configuración: {e}', 'danger')

    return render_template('configuration/edit.html', form=form, configuration=config)

@configuration_bp.route('/delete/<string:id>', methods=['POST'])
def delete_configuration(id):
    config = Configuration.objects.get(id=ObjectId(id))
    config.delete()  # Borra definitivamente de la base de datos
    flash('Configuración eliminada permanentemente.', 'danger')
    return redirect(url_for('configuration.list_configuration'))

@configuration_bp.route('/reset/<string:id>', methods=['POST'])
def reset_configuration(id):
    config = Configuration.objects.get(id=ObjectId(id))
    if not config.log:
        config.log = Log(enable=True)
    else:
        config.log.enable = True
    config.save()
    flash('Configuración reactivada.', 'success')
    return redirect(url_for('configuration.list_configuration'))
