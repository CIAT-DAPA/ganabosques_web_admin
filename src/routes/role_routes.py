from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from ganabosques_orm.collections.role import Role, ActionPermission
from ganabosques_orm.enums.actions import Actions
from ganabosques_orm.enums.options import Options
from bson import ObjectId
import logging
import json

logger = logging.getLogger(__name__)

role_bp = Blueprint('role', __name__, url_prefix='/roles')


@role_bp.route('/')
def list_roles():
    """Lista todos los roles únicos registrados en MongoDB."""
    roles = Role.objects()

    roles_list = []
    for r in roles:
        actions_data = []
        if r.actions:
            for ap in r.actions:
                actions_data.append({
                    'name': ap.action.name if ap.action else '',
                    'label': ap.action.value if ap.action else '',
                    'options': [o.value for o in ap.options] if ap.options else []
                })
        roles_list.append({
            'id': str(r.id),
            'name': r.name or 'Sin nombre',
            'actions': actions_data
        })

    # Datos para los formularios
    actions_enum = [{'name': a.name, 'value': a.value} for a in Actions]
    options_enum = [{'name': o.name, 'value': o.value} for o in Options]

    return render_template(
        'role/list.html',
        roles=roles_list,
        actions_enum=actions_enum,
        options_enum=options_enum,
        active_page='roles'
    )


@role_bp.route('/create', methods=['POST'])
def create_role():
    """Crea un nuevo rol."""
    name = request.form.get('name', '').strip()
    actions_json = request.form.get('actions_data', '[]')

    if not name:
        flash('El nombre del rol es obligatorio.', 'danger')
        return redirect(url_for('role.list_roles'))

    try:
        actions_data = json.loads(actions_json)
    except Exception:
        actions_data = []

    action_permissions = []
    for action_data in actions_data:
        action_name = action_data.get('name', '')
        action_options = action_data.get('options', [])
        try:
            action_enum = Actions[action_name]
            opts = [Options[o] for o in action_options if o in Options.__members__]
            action_permissions.append(ActionPermission(
                action=action_enum,
                options=opts
            ))
        except (KeyError, ValueError) as e:
            logger.warning(f"Acción u opción inválida al crear rol: {e}")

    new_role = Role(name=name, actions=action_permissions)
    new_role.save()

    flash(f'Rol "{name}" creado exitosamente.', 'success')
    return redirect(url_for('role.list_roles'))


@role_bp.route('/get/<role_id>')
def get_role(role_id):
    """Retorna los datos de un rol en formato JSON para edición."""
    try:
        role = Role.objects.get(id=ObjectId(role_id))
        actions_data = []
        if role.actions:
            for ap in role.actions:
                actions_data.append({
                    'name': ap.action.name if ap.action else '',
                    'label': ap.action.value if ap.action else '',
                    'options': [o.name for o in ap.options] if ap.options else []
                })
        return jsonify({
            'id': str(role.id),
            'name': role.name,
            'actions': actions_data
        })
    except Exception as e:
        logger.error(f"Error obteniendo rol {role_id}: {e}")
        return jsonify({'error': 'Rol no encontrado'}), 404


@role_bp.route('/edit/<role_id>', methods=['POST'])
def edit_role(role_id):
    """Actualiza un rol existente."""
    try:
        role = Role.objects.get(id=ObjectId(role_id))
    except Exception:
        flash('Rol no encontrado.', 'danger')
        return redirect(url_for('role.list_roles'))

    name = request.form.get('name', '').strip()
    actions_json = request.form.get('actions_data', '[]')

    if not name:
        flash('El nombre del rol es obligatorio.', 'danger')
        return redirect(url_for('role.list_roles'))

    try:
        actions_data = json.loads(actions_json)
    except Exception:
        actions_data = []

    action_permissions = []
    for action_data in actions_data:
        action_name = action_data.get('name', '')
        action_options = action_data.get('options', [])
        try:
            action_enum = Actions[action_name]
            opts = [Options[o] for o in action_options if o in Options.__members__]
            action_permissions.append(ActionPermission(
                action=action_enum,
                options=opts
            ))
        except (KeyError, ValueError) as e:
            logger.warning(f"Acción u opción inválida al editar rol: {e}")

    role.name = name
    role.actions = action_permissions
    role.save()

    flash(f'Rol "{name}" actualizado exitosamente.', 'success')
    return redirect(url_for('role.list_roles'))


@role_bp.route('/delete/<role_id>', methods=['POST'])
def delete_role(role_id):
    """Elimina un rol."""
    try:
        role = Role.objects.get(id=ObjectId(role_id))
        role_name = role.name
        role.delete()
        flash(f'Rol "{role_name}" eliminado exitosamente.', 'success')
    except Exception as e:
        logger.error(f"Error eliminando rol {role_id}: {e}")
        flash('Error al eliminar el rol.', 'danger')

    return redirect(url_for('role.list_roles'))
