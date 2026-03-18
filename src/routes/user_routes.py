from flask import Blueprint, render_template, request, current_app, redirect, url_for, flash, jsonify
from ganabosques_orm.collections.user import User as UserORM
from ganabosques_orm.collections.role import Role, ActionPermission
from ganabosques_orm.enums.actions import Actions
from ganabosques_orm.enums.options import Options
import requests
import logging
import json

logger = logging.getLogger(__name__)

user_bp = Blueprint('user', __name__)


def get_keycloak_admin_token():
    """Obtiene un token de admin usando client credentials para la API de Keycloak."""
    server_url = current_app.config.get('KEYCLOAK_SERVER_URL')
    realm = current_app.config.get('KEYCLOAK_REALM')
    client_id = current_app.config.get('KEYCLOAK_CLIENT_ID')
    client_secret = current_app.config.get('KEYCLOAK_CLIENT_SECRET')
    
    token_url = f"{server_url}/realms/{realm}/protocol/openid-connect/token"
    
    try:
        resp = requests.post(token_url, data={
            'grant_type': 'client_credentials',
            'client_id': client_id,
            'client_secret': client_secret
        })
        resp.raise_for_status()
        return resp.json().get('access_token')
    except Exception as e:
        logger.error(f"Error obteniendo token admin de Keycloak: {e}")
        return None


def get_keycloak_user_by_id(token, user_id):
    """Obtiene un usuario de Keycloak por su ID."""
    server_url = current_app.config.get('KEYCLOAK_SERVER_URL')
    realm = current_app.config.get('KEYCLOAK_REALM')
    
    url = f"{server_url}/admin/realms/{realm}/users/{user_id}"
    
    try:
        resp = requests.get(url, headers={
            'Authorization': f'Bearer {token}'
        })
        if resp.status_code == 200:
            return resp.json()
        else:
            logger.warning(f"No se pudo obtener usuario {user_id}: HTTP {resp.status_code}")
            return None
    except Exception as e:
        logger.error(f"Error obteniendo usuario {user_id} de Keycloak: {e}")
        return None


@user_bp.route('/users')
def list_users():
    """Lista los usuarios de Keycloak que están registrados en la colección de MongoDB."""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('q', '').strip()
    per_page = 50
    
    # 1. Obtener todos los ext_id de la colección user de MongoDB
    db_users = UserORM.objects()
    ext_ids = [u.ext_id for u in db_users if u.ext_id]
    
    # 2. Obtener token de admin de Keycloak
    token = get_keycloak_admin_token()
    
    keycloak_users = []
    if token:
        for ext_id in ext_ids:
            kc_user = get_keycloak_user_by_id(token, ext_id)
            if kc_user:
                # Buscar el documento MongoDB correspondiente para obtener el admin flag y roles
                db_user = UserORM.objects(ext_id=ext_id).first()
                
                # Extraer roles con acciones y opciones
                roles_data = []
                if db_user and db_user.role:
                    for role_ref in db_user.role:
                        try:
                            role = role_ref
                            if not hasattr(role, 'name'):
                                from ganabosques_orm.collections.role import Role
                                role = Role.objects(id=role_ref.id).first()
                            if role:
                                role_info = {
                                    'name': role.name or 'Sin nombre',
                                    'actions': []
                                }
                                if role.actions:
                                    for ap in role.actions:
                                        action_info = {
                                            'name': ap.action.value if ap.action else '',
                                            'options': [o.value for o in ap.options] if ap.options else []
                                        }
                                        role_info['actions'].append(action_info)
                                roles_data.append(role_info)
                        except Exception as e:
                            logger.warning(f"Error cargando rol para usuario {ext_id}: {e}")
                
                keycloak_users.append({
                    'id': kc_user.get('id', ''),
                    'username': kc_user.get('username', ''),
                    'email': kc_user.get('email', 'Sin correo'),
                    'firstName': kc_user.get('firstName', ''),
                    'lastName': kc_user.get('lastName', ''),
                    'enabled': kc_user.get('enabled', False),
                    'admin': db_user.admin if db_user else False,
                    'roles': roles_data
                })
    else:
        logger.error("No se pudo obtener token admin de Keycloak para listar usuarios")
    
    # 3. Filtrar por búsqueda si hay query
    if search:
        search_lower = search.lower()
        keycloak_users = [
            u for u in keycloak_users
            if search_lower in u['username'].lower()
            or search_lower in u['email'].lower()
            or search_lower in u['firstName'].lower()
            or search_lower in u['lastName'].lower()
        ]
    
    # 4. Paginación
    total = len(keycloak_users)
    offset = (page - 1) * per_page
    paginated_users = keycloak_users[offset:offset + per_page]
    total_pages = (total + per_page - 1) // per_page
    
    return render_template(
        'user/list.html',
        users=paginated_users,
        page=page,
        total_pages=total_pages,
        search=search,
        total=total
    )


def create_keycloak_user(token, user_data):
    """Crea un usuario en Keycloak y devuelve su ID."""
    server_url = current_app.config.get('KEYCLOAK_SERVER_URL')
    realm = current_app.config.get('KEYCLOAK_REALM')
    
    url = f"{server_url}/admin/realms/{realm}/users"
    
    payload = {
        "username": user_data['username'],
        "email": user_data['email'],
        "firstName": user_data.get('firstName', ''),
        "lastName": user_data.get('lastName', ''),
        "enabled": True,
        "emailVerified": False,
        "credentials": [{
            "type": "password",
            "value": user_data['password'],
            "temporary": False
        }]
    }
    
    try:
        resp = requests.post(url, json=payload, headers={
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        })
        
        if resp.status_code == 201:
            # El ID viene en el header Location
            location = resp.headers.get('Location', '')
            keycloak_id = location.split('/')[-1] if location else None
            logger.info(f"Usuario creado en Keycloak con ID: {keycloak_id}")
            return keycloak_id, None
        else:
            error_msg = resp.json().get('errorMessage', resp.text) if resp.text else f'HTTP {resp.status_code}'
            logger.error(f"Error creando usuario en Keycloak: {error_msg}")
            return None, error_msg
    except Exception as e:
        logger.error(f"Error creando usuario en Keycloak: {e}")
        return None, str(e)


@user_bp.route('/users/create', methods=['GET', 'POST'])
def create_user():
    """Crear un usuario nuevo en Keycloak y MongoDB."""
    
    # Datos para el template
    actions_enum = [{'name': a.name, 'value': a.value} for a in Actions]
    options_enum = [{'name': o.name, 'value': o.value} for o in Options]
    
    # Obtener roles genéricos existentes (únicos por nombre)
    all_roles = Role.objects()
    unique_roles = {}
    for r in all_roles:
        if r.name not in unique_roles:
            actions_list = []
            for a in r.actions:
                actions_list.append({
                    'name': a.action.name,
                    'label': a.action.value,
                    'options': [o.name for o in a.options]
                })
            unique_roles[r.name] = {
                'id': str(r.id),
                'name': r.name,
                'actions': actions_list
            }
    available_roles_json = json.dumps(list(unique_roles.values()))
    
    if request.method == 'POST':
        # Obtener datos del formulario
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        first_name = request.form.get('firstName', '').strip()
        last_name = request.form.get('lastName', '').strip()
        password = request.form.get('password', '').strip()
        is_admin = request.form.get('admin') == 'on'
        roles_json = request.form.get('roles_data', '[]')
        
        # Validaciones básicas
        if not username or not email or not password:
            flash('Username, correo y contraseña son obligatorios.', 'danger')
            return render_template('user/create.html', 
                                 actions_enum=actions_enum, options_enum=options_enum,
                                 available_roles_json=available_roles_json)
        
        # 1. Crear usuario en Keycloak
        token = get_keycloak_admin_token()
        if not token:
            flash('No se pudo conectar con Keycloak. Verifica la configuración.', 'danger')
            return render_template('user/create.html',
                                 actions_enum=actions_enum, options_enum=options_enum,
                                 available_roles_json=available_roles_json)
        
        keycloak_id, error = create_keycloak_user(token, {
            'username': username,
            'email': email,
            'firstName': first_name,
            'lastName': last_name,
            'password': password
        })
        
        if not keycloak_id:
            flash(f'Error al crear usuario en Keycloak: {error}', 'danger')
            return render_template('user/create.html',
                                 actions_enum=actions_enum, options_enum=options_enum,
                                 available_roles_json=available_roles_json)
        
        # 2. Crear roles en MongoDB
        try:
            roles_data = json.loads(roles_json)
        except Exception:
            roles_data = []
        
        role_refs = []
        for role_data in roles_data:
            role_name = role_data.get('name', '').strip()
            if not role_name:
                continue
            
            action_permissions = []
            for action_data in role_data.get('actions', []):
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
                    logger.warning(f"Acción u opción inválida: {e}")
            
            new_role = Role(name=role_name, actions=action_permissions)
            new_role.save()
            role_refs.append(new_role)
        
        # 3. Crear usuario en MongoDB
        new_user = UserORM(
            ext_id=keycloak_id,
            admin=is_admin,
            role=role_refs
        )
        new_user.save()
        
        flash(f'Usuario "{username}" creado exitosamente.', 'success')
        return redirect(url_for('user.list_users'))
    
    return render_template('user/create.html',
                         actions_enum=actions_enum, options_enum=options_enum,
                         available_roles_json=available_roles_json)


def update_keycloak_user(token, user_id, user_data):
    """Actualiza la información básica de un usuario en Keycloak."""
    server_url = current_app.config.get('KEYCLOAK_SERVER_URL')
    realm = current_app.config.get('KEYCLOAK_REALM')
    url = f"{server_url}/admin/realms/{realm}/users/{user_id}"
    
    payload = {
        "email": user_data['email'],
        "firstName": user_data.get('firstName', ''),
        "lastName": user_data.get('lastName', '')
    }
    
    try:
        resp = requests.put(url, json=payload, headers={
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        })
        if resp.status_code == 204:
            return True, None
        else:
            error_msg = resp.json().get('errorMessage', resp.text) if resp.text else f'HTTP {resp.status_code}'
            return False, error_msg
    except Exception as e:
        logger.error(f"Error actualizando usuario {user_id} en Keycloak: {e}")
        return False, str(e)


def update_keycloak_password(token, user_id, new_password):
    """Actualiza la contraseña de un usuario en Keycloak."""
    server_url = current_app.config.get('KEYCLOAK_SERVER_URL')
    realm = current_app.config.get('KEYCLOAK_REALM')
    url = f"{server_url}/admin/realms/{realm}/users/{user_id}/reset-password"
    
    payload = {
        "type": "password",
        "value": new_password,
        "temporary": False
    }
    
    try:
        resp = requests.put(url, json=payload, headers={
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        })
        if resp.status_code == 204:
            return True, None
        else:
            error_msg = resp.json().get('errorMessage', resp.text) if resp.text else f'HTTP {resp.status_code}'
            return False, error_msg
    except Exception as e:
        logger.error(f"Error actualizando contraseña para {user_id}: {e}")
        return False, str(e)


@user_bp.route('/users/edit/<keycloak_id>', methods=['GET', 'POST'])
def edit_user(keycloak_id):
    """Editar un usuario existente."""
    token = get_keycloak_admin_token()
    if not token:
        flash('No se pudo conectar con Keycloak.', 'danger')
        return redirect(url_for('user.list_users'))
    
    kc_user = get_keycloak_user_by_id(token, keycloak_id)
    if not kc_user:
        flash('Usuario no encontrado en Keycloak.', 'danger')
        return redirect(url_for('user.list_users'))
    
    db_user = UserORM.objects(ext_id=keycloak_id).first()
    if not db_user:
        flash('El usuario no está registrado en la base de datos de MongoDB.', 'danger')
        return redirect(url_for('user.list_users'))

    actions_enum = [{'name': a.name, 'value': a.value} for a in Actions]
    options_enum = [{'name': o.name, 'value': o.value} for o in Options]
    
    if request.method == 'POST':
        # 1. Actualizar Keycloak
        email = request.form.get('email', '').strip()
        first_name = request.form.get('firstName', '').strip()
        last_name = request.form.get('lastName', '').strip()
        is_admin = request.form.get('admin') == 'on'
        roles_json = request.form.get('roles_data', '[]')
        
        success, error = update_keycloak_user(token, keycloak_id, {
            'email': email,
            'firstName': first_name,
            'lastName': last_name
        })
        
        if not success:
            flash(f'Error actualizando en Keycloak: {error}', 'danger')
            return redirect(url_for('user.edit_user', keycloak_id=keycloak_id))
        
        # 2. Actualizar MongoDB (borrar roles viejos y recrear nuevos para simplificar)
        try:
            roles_data = json.loads(roles_json)
        except:
            roles_data = []
            
        # Limpiar roles anteriores si existen referenciados
        if db_user.role:
            for old_r in db_user.role:
                try:
                    Role.objects(id=old_r.id).delete()
                except:
                    pass
        
        role_refs = []
        for role_data in roles_data:
            role_name = role_data.get('name', '').strip()
            if not role_name: continue
            
            action_permissions = []
            for action_data in role_data.get('actions', []):
                action_name = action_data.get('name', '')
                try:
                    action_enum = Actions[action_name]
                    opts = [Options[o] for o in action_data.get('options', []) if o in Options.__members__]
                    action_permissions.append(ActionPermission(action=action_enum, options=opts))
                except:
                    pass
            new_role = Role(name=role_name, actions=action_permissions)
            new_role.save()
            role_refs.append(new_role)
            
        db_user.admin = is_admin
        db_user.role = role_refs
        db_user.save()
        
        flash('Usuario actualizado correctamente.', 'success')
        return redirect(url_for('user.list_users'))

    # GET request: Preparar datos para el frontend
    existing_roles = []
    if db_user.role:
        for r_ref in db_user.role:
            try:
                r_obj = Role.objects(id=r_ref.id).first()
                if not r_obj: continue
                
                actions_list = []
                for a in r_obj.actions:
                    actions_list.append({
                        'name': a.action.name,
                        'label': a.action.value,
                        'options': [o.name for o in a.options]
                    })
                existing_roles.append({
                    'name': r_obj.name,
                    'actions': actions_list
                })
            except:
                pass

    # Obtener roles creados previamente
    all_roles = Role.objects()
    unique_roles = {}
    for r in all_roles:
        if r.name not in unique_roles:
            a_list = []
            for a in r.actions:
                a_list.append({
                    'name': a.action.name,
                    'label': a.action.value,
                    'options': [o.name for o in a.options]
                })
            unique_roles[r.name] = {
                'id': str(r.id),
                'name': r.name,
                'actions': a_list
            }
    available_roles_json = json.dumps(list(unique_roles.values()))

    return render_template('user/edit.html',
                         user=kc_user,
                         db_user=db_user,
                         existing_roles_json=json.dumps(existing_roles),
                         available_roles_json=available_roles_json,
                         actions_enum=actions_enum,
                         options_enum=options_enum)


@user_bp.route('/users/password/<keycloak_id>', methods=['POST'])
def update_password(keycloak_id):
    """Actualiza la contraseña del usuario."""
    password = request.form.get('new_password')
    confirm = request.form.get('confirm_password')
    
    if not password or password != confirm:
        flash('Las contraseñas no coinciden o están vacías.', 'danger')
        return redirect(url_for('user.edit_user', keycloak_id=keycloak_id))
        
    token = get_keycloak_admin_token()
    if not token:
        flash('No se pudo conectar con Keycloak.', 'danger')
        return redirect(url_for('user.edit_user', keycloak_id=keycloak_id))
        
    success, error = update_keycloak_password(token, keycloak_id, password)
    if success:
        flash('Contraseña actualizada exitosamente.', 'success')
    else:
        flash(f'Error al cambiar contraseña: {error}', 'danger')
        
    return redirect(url_for('user.edit_user', keycloak_id=keycloak_id))


def delete_keycloak_user(token, user_id):
    """Elimina un usuario de Keycloak."""
    server_url = current_app.config.get('KEYCLOAK_SERVER_URL')
    realm = current_app.config.get('KEYCLOAK_REALM')
    url = f"{server_url}/admin/realms/{realm}/users/{user_id}"
    
    try:
        resp = requests.delete(url, headers={
            'Authorization': f'Bearer {token}'
        })
        if resp.status_code == 204:
            return True, None
        else:
            error_msg = resp.json().get('errorMessage', resp.text) if resp.text else f'HTTP {resp.status_code}'
            return False, error_msg
    except Exception as e:
        logger.error(f"Error eliminando usuario {user_id} de Keycloak: {e}")
        return False, str(e)


@user_bp.route('/users/delete/<keycloak_id>', methods=['POST'])
def delete_user(keycloak_id):
    """Elimina un usuario de Keycloak y MongoDB."""
    token = get_keycloak_admin_token()
    if not token:
        flash('No se pudo conectar con Keycloak.', 'danger')
        return redirect(url_for('user.list_users'))
    
    # 1. Eliminar de Keycloak
    success, error = delete_keycloak_user(token, keycloak_id)
    if not success:
        flash(f'Error al eliminar usuario en Keycloak: {error}', 'danger')
        return redirect(url_for('user.list_users'))
        
    # 2. Eliminar de MongoDB
    db_user = UserORM.objects(ext_id=keycloak_id).first()
    if db_user:
        # Limpiar roles huérfanos
        if db_user.role:
            for r_ref in db_user.role:
                try:
                    Role.objects(id=r_ref.id).delete()
                except:
                    pass
        db_user.delete()
        
    flash('Usuario eliminado exitosamente.', 'success')
    return redirect(url_for('user.list_users'))
