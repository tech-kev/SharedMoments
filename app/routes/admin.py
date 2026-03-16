from flask import Blueprint, g, render_template, request, jsonify, session
from werkzeug.utils import secure_filename
from app.routes.auth import jwt_required
from app.permissions import require_permission
from app.translation import _
from app.db_queries import (
    get_all_users, get_all_roles, get_all_permissions_list,
    get_role_permissions_map, get_user_roles_map,
    set_role_permissions, set_user_roles,
    get_all_list_types, get_setting_by_name, get_user_setting, get_user_by_id, get_all_settings,
    get_all_active_shares, deactivate_share
)
from app.models import User, Role, Permission, Passkey, RolePermission, UserRole, UserSetting, SessionLocal
from app.logger import log
from app.utils import generate_admin_filename
from app.routes.pages import get_display_title
from datetime import datetime
import os

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/admin')
@jwt_required
@require_permission('Access Admin Panel')
def admin_panel():
    try:
        users = get_all_users()
        roles = get_all_roles()
        permissions = get_all_permissions_list()
        role_permissions_map = get_role_permissions_map()
        user_roles_map = get_user_roles_map()
        list_types = get_all_list_types()
        title = get_display_title()
        darkmode = get_user_setting(g.user_id, 'darkmode')
        user_data = get_user_by_id(g.user_id)
        settings = get_all_settings()
        active_shares = get_all_active_shares()
        sm_edition = get_setting_by_name('sm_edition').value

        return render_template('pages/admin.html',
                               users=users,
                               roles=roles,
                               permissions=permissions,
                               role_permissions_map=role_permissions_map,
                               user_roles_map=user_roles_map,
                               list_types=list_types,
                               title=title,
                               darkmode=darkmode,
                               user_data=user_data,
                               settings=settings,
                               active_shares=active_shares,
                               sm_edition=sm_edition)
    except Exception as e:
        log('error', f'Error while rendering the admin panel: {e}')
        return "An error occurred while rendering the page. Please check the server logs for details.", 500


@admin_bp.route('/api/v2/admin/roles', methods=['POST'])
@jwt_required
@require_permission('Access Admin Panel')
def create_role():
    try:
        role_name = request.form.get('roleName', '').strip()
        if not role_name:
            return jsonify({'status': 'error', 'message': _('Role name is required')}), 400

        session = SessionLocal()
        existing = session.query(Role).filter(Role.roleName == role_name).first()
        if existing:
            session.close()
            return jsonify({'status': 'error', 'message': _('Role already exists')}), 400

        new_role = Role(roleName=role_name)
        session.add(new_role)
        session.commit()
        role_id = new_role.id
        session.close()

        log('info', f'Role created: {role_name} (ID: {role_id})')
        return jsonify({
            'status': 'success',
            'message': _('Role created successfully'),
            'data': {'id': role_id, 'roleName': role_name}
        }), 201

    except Exception as e:
        log('error', f'Error creating role: {e}')
        return jsonify({'status': 'error', 'message': str(e)}), 500


@admin_bp.route('/api/v2/admin/roles/<int:id>', methods=['PUT'])
@jwt_required
@require_permission('Access Admin Panel')
def update_role(id):
    try:
        role_name = request.form.get('roleName', '').strip()
        if not role_name:
            return jsonify({'status': 'error', 'message': _('Role name is required')}), 400

        session = SessionLocal()
        role = session.query(Role).filter(Role.id == id).first()
        if not role:
            session.close()
            return jsonify({'status': 'error', 'message': _('Role not found')}), 404

        role.roleName = role_name
        session.commit()
        session.close()

        log('info', f'Role updated: {role_name} (ID: {id})')
        return jsonify({
            'status': 'success',
            'message': _('Role updated successfully'),
            'data': {'id': id, 'roleName': role_name}
        }), 200

    except Exception as e:
        log('error', f'Error updating role: {e}')
        return jsonify({'status': 'error', 'message': str(e)}), 500


@admin_bp.route('/api/v2/admin/roles/<int:id>', methods=['DELETE'])
@jwt_required
@require_permission('Access Admin Panel')
def delete_role_route(id):
    try:
        if id <= 4:
            return jsonify({'status': 'error', 'message': _('Built-in roles cannot be deleted')}), 400

        session = SessionLocal()
        role = session.query(Role).filter(Role.id == id).first()
        if not role:
            session.close()
            return jsonify({'status': 'error', 'message': _('Role not found')}), 404

        # Delete associated role permissions and user roles
        session.query(RolePermission).filter(RolePermission.roleID == id).delete()
        session.query(UserRole).filter(UserRole.roleID == id).delete()
        session.delete(role)
        session.commit()
        session.close()

        log('info', f'Role deleted: ID {id}')
        return jsonify({
            'status': 'success',
            'message': _('Role deleted successfully')
        }), 200

    except Exception as e:
        log('error', f'Error deleting role: {e}')
        return jsonify({'status': 'error', 'message': str(e)}), 500


@admin_bp.route('/api/v2/admin/roles/<int:id>/permissions', methods=['PUT'])
@jwt_required
@require_permission('Access Admin Panel')
def update_role_permissions(id):
    try:
        import json
        permission_ids = json.loads(request.form.get('permissionIds', '[]'))

        # Prevent removing 'Access Admin Panel' from the Admin role
        admin_role_id = _get_admin_role_id()
        if id == admin_role_id:
            session = SessionLocal()
            access_admin_perm = session.query(Permission).filter(
                Permission.permissionName == 'Access Admin Panel'
            ).first()
            session.close()
            if access_admin_perm and access_admin_perm.id not in permission_ids:
                return jsonify({'status': 'error', 'message': _('Admin role must keep "Access Admin Panel" permission')}), 400

        set_role_permissions(id, permission_ids)

        log('info', f'Role permissions updated for role ID: {id}')
        return jsonify({
            'status': 'success',
            'message': _('Permissions updated successfully')
        }), 200

    except Exception as e:
        log('error', f'Error updating role permissions: {e}')
        return jsonify({'status': 'error', 'message': str(e)}), 500


@admin_bp.route('/api/v2/admin/users/<int:id>/roles', methods=['PUT'])
@jwt_required
@require_permission('Access Admin Panel')
def update_user_roles(id):
    try:
        import json
        role_ids = json.loads(request.form.get('roleIds', '[]'))
        if not role_ids:
            return jsonify({'status': 'error', 'message': _('User must have at least one role')}), 400

        # Prevent removing the last admin
        admin_role_id = _get_admin_role_id()
        if admin_role_id and admin_role_id not in role_ids:
            session = SessionLocal()
            admin_count = session.query(UserRole).filter(
                UserRole.roleID == admin_role_id,
                UserRole.userID != id
            ).count()
            session.close()
            if admin_count == 0:
                return jsonify({'status': 'error', 'message': _('There must be at least one admin')}), 400

        set_user_roles(id, role_ids)

        log('info', f'User roles updated for user ID: {id}')
        return jsonify({
            'status': 'success',
            'message': _('User roles updated successfully')
        }), 200

    except Exception as e:
        log('error', f'Error updating user roles: {e}')
        return jsonify({'status': 'error', 'message': str(e)}), 500


@admin_bp.route('/api/v2/admin/users', methods=['POST'])
@jwt_required
@require_permission('Access Admin Panel')
def create_user_route():
    try:
        db_session = SessionLocal()

        firstName = request.form.get('firstName', '').strip()
        lastName = request.form.get('lastName', '').strip()
        email = request.form.get('email', '').strip()
        birthDate = request.form.get('birthDate', '')
        password = request.form.get('password', '')
        role_id = request.form.get('roleId', '')

        if not firstName or not email or not password:
            return jsonify({'status': 'error', 'message': _('First name, e-mail and password are required')}), 400

        # Check duplicate email
        existing = db_session.query(User).filter(User.email == email).first()
        if existing:
            db_session.close()
            return jsonify({'status': 'error', 'message': _('E-Mail already in use. Please choose a different one.')}), 400

        # Handle profile picture upload
        profilePicture = 'profile-placeholder.jpg'
        if 'profilePicture' in request.files:
            file = request.files['profilePicture']
            if file and file.filename:
                basedir = os.path.abspath(os.path.dirname(__file__))
                profiles_folder = os.path.join(basedir, '..', 'uploads', 'profiles')
                if not os.path.exists(profiles_folder):
                    os.makedirs(profiles_folder)
                identifier = f"{firstName}_{lastName}" if lastName else firstName or 'Unknown'
                ext = file.filename.rsplit('.', 1)[-1] if '.' in file.filename else 'jpg'
                filename = generate_admin_filename('profile', identifier, ext)
                file.save(os.path.join(profiles_folder, filename))
                profilePicture = filename

        new_user = User(
            firstName=firstName,
            lastName=lastName,
            email=email,
            birthDate=datetime.strptime(birthDate, '%Y-%m-%d').date() if birthDate else None,
            profilePicture=profilePicture,
        )
        new_user.hash_password(password)

        db_session.add(new_user)
        db_session.flush()

        user_id = new_user.id

        # Assign role
        if role_id:
            db_session.add(UserRole(userID=user_id, roleID=int(role_id)))
        else:
            # Default: Adult
            adult_role = db_session.query(Role).filter(Role.roleName == 'Adult').first()
            if adult_role:
                db_session.add(UserRole(userID=user_id, roleID=adult_role.id))

        # Create default user settings
        lang = session.get('lang', 'en')
        db_session.add(UserSetting(userID=user_id, name='language', value=lang, icon='language', edition='all', category='about', type='text'))
        db_session.add(UserSetting(userID=user_id, name='darkmode', value='FALSE', icon='dark_mode', edition='all', category='about', type='text'))

        db_session.commit()
        db_session.close()

        log('info', f'User created via admin panel: {firstName} {lastName} (ID: {user_id})')
        return jsonify({
            'status': 'success',
            'message': _('User created successfully'),
            'data': {'id': user_id}
        }), 201

    except Exception as e:
        log('error', f'Error creating user: {e}')
        return jsonify({'status': 'error', 'message': str(e)}), 500


@admin_bp.route('/api/v2/admin/users/<int:id>', methods=['PUT'])
@jwt_required
@require_permission('Access Admin Panel')
def update_user_route(id):
    try:
        db_session = SessionLocal()
        user = db_session.query(User).filter(User.id == id).first()
        if not user:
            db_session.close()
            return jsonify({'status': 'error', 'message': _('User not found')}), 404

        firstName = request.form.get('firstName', '').strip()
        lastName = request.form.get('lastName', '').strip()
        email = request.form.get('email', '').strip()
        birthDate = request.form.get('birthDate', '')
        password = request.form.get('password', '')

        if firstName:
            user.firstName = firstName
        if lastName:
            user.lastName = lastName
        if email:
            # Check duplicate email
            existing = db_session.query(User).filter(User.email == email, User.id != id).first()
            if existing:
                db_session.close()
                return jsonify({'status': 'error', 'message': _('E-Mail already in use. Please choose a different one.')}), 400
            user.email = email
        if birthDate:
            user.birthDate = datetime.strptime(birthDate, '%Y-%m-%d').date()
        if password:
            user.hash_password(password)

        # Handle profile picture upload
        if 'profilePicture' in request.files:
            file = request.files['profilePicture']
            if file and file.filename:
                basedir = os.path.abspath(os.path.dirname(__file__))
                profiles_folder = os.path.join(basedir, '..', 'uploads', 'profiles')
                if not os.path.exists(profiles_folder):
                    os.makedirs(profiles_folder)
                fn = firstName or user.firstName or ''
                ln = lastName or user.lastName or ''
                identifier = f"{fn}_{ln}" if ln else fn or f"User_{id}"
                ext = file.filename.rsplit('.', 1)[-1] if '.' in file.filename else 'jpg'
                filename = generate_admin_filename('profile', identifier, ext)
                file.save(os.path.join(profiles_folder, filename))
                user.profilePicture = filename

        db_session.commit()
        db_session.close()

        log('info', f'User updated via admin panel: ID {id}')
        return jsonify({
            'status': 'success',
            'message': _('User updated successfully')
        }), 200

    except Exception as e:
        log('error', f'Error updating user: {e}')
        return jsonify({'status': 'error', 'message': str(e)}), 500


@admin_bp.route('/api/v2/admin/users/<int:id>', methods=['DELETE'])
@jwt_required
@require_permission('Access Admin Panel')
def delete_user_route(id):
    try:
        # Prevent deleting yourself
        if id == g.user_id:
            return jsonify({'status': 'error', 'message': _('You cannot delete your own account')}), 400

        # Prevent deleting the last admin
        admin_role_id = _get_admin_role_id()
        if admin_role_id:
            db_session = SessionLocal()
            user_is_admin = db_session.query(UserRole).filter(
                UserRole.userID == id, UserRole.roleID == admin_role_id
            ).first()
            if user_is_admin:
                admin_count = db_session.query(UserRole).filter(UserRole.roleID == admin_role_id).count()
                if admin_count <= 1:
                    db_session.close()
                    return jsonify({'status': 'error', 'message': _('There must be at least one admin')}), 400
            db_session.close()

        db_session = SessionLocal()
        user = db_session.query(User).filter(User.id == id).first()
        if not user:
            db_session.close()
            return jsonify({'status': 'error', 'message': _('User not found')}), 404

        # Delete associated data
        db_session.query(UserRole).filter(UserRole.userID == id).delete()
        db_session.query(UserSetting).filter(UserSetting.userID == id).delete()
        db_session.query(Passkey).filter(Passkey.userID == id).delete()
        db_session.delete(user)
        db_session.commit()
        db_session.close()

        log('info', f'User deleted via admin panel: ID {id}')
        return jsonify({
            'status': 'success',
            'message': _('User deleted successfully')
        }), 200

    except Exception as e:
        log('error', f'Error deleting user: {e}')
        return jsonify({'status': 'error', 'message': str(e)}), 500


@admin_bp.route('/api/v2/admin/shares/<int:share_id>', methods=['DELETE'])
@jwt_required
@require_permission('Access Admin Panel')
def delete_share_admin(share_id):
    try:
        deactivate_share(share_id, admin=True)
        log('info', f'Share {share_id} deactivated by admin {g.user_id}')
        return jsonify({
            'status': 'success',
            'message': _('Share link revoked successfully')
        }), 200
    except Exception as e:
        log('error', f'Error revoking share {share_id}: {e}')
        return jsonify({'status': 'error', 'message': str(e)}), 500


def _get_admin_role_id():
    """Returns the ID of the Admin role."""
    session = SessionLocal()
    role = session.query(Role).filter(Role.roleName == 'Admin').first()
    session.close()
    return role.id if role else None
