from functools import wraps
from flask import g, jsonify, redirect, url_for, request
from app.models import Permission, RolePermission, UserRole, SessionLocal
from app.logger import log


def load_user_permissions(user_id):
    """Loads all permissions for a user as a set of strings."""
    session = SessionLocal()
    try:
        permissions = (
            session.query(Permission.permissionName)
            .join(RolePermission, RolePermission.permissionID == Permission.id)
            .join(UserRole, UserRole.roleID == RolePermission.roleID)
            .filter(UserRole.userID == user_id)
            .distinct()
            .all()
        )
        return {p[0] for p in permissions}
    except Exception as e:
        log('error', f'Error loading permissions for user {user_id}: {e}')
        return set()
    finally:
        session.close()


def require_permission(permission_name):
    """Decorator: checks if user has the required permission."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(g, 'user_permissions') or permission_name not in g.user_permissions:
                from app.translation import _
                user_name = getattr(g, 'user_name', 'unknown')
                log('warning', f'Permission denied: {user_name} tried to access {request.path} (requires "{permission_name}")')
                if request.is_json or request.path.startswith('/api/'):
                    return jsonify({
                        'status': 'error',
                        'message': _('Insufficient permissions'),
                        'data': {'error_code': 403, 'error_message': _('Insufficient permissions')}
                    }), 403
                return redirect(url_for('pages.home'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def has_permission(permission_name):
    """For Jinja templates: {% if has_permission('Create User') %}"""
    return hasattr(g, 'user_permissions') and permission_name in g.user_permissions


def has_list_permission(action, list_type_title):
    """For Jinja templates: {% if has_list_permission('Create', 'Home') %}"""
    permission_name = f'{action} {list_type_title}'
    return hasattr(g, 'user_permissions') and permission_name in g.user_permissions


def require_list_permission(action, list_type_id):
    """For API endpoints: returns None if allowed, or a 403 response tuple."""
    from app.models import ListType
    session = SessionLocal()
    try:
        lt = session.query(ListType).filter(ListType.id == list_type_id).first()
        if not lt:
            from app.translation import _
            return jsonify({
                'status': 'error',
                'message': _('List type not found'),
                'data': {'error_code': 404}
            }), 404
        permission_name = f'{action} {lt.title}'
    finally:
        session.close()

    if not hasattr(g, 'user_permissions') or permission_name not in g.user_permissions:
        from app.translation import _
        user_name = getattr(g, 'user_name', 'unknown')
        log('warning', f'Permission denied: {user_name} tried to access {request.path} (requires "{permission_name}")')
        return jsonify({
            'status': 'error',
            'message': _('Insufficient permissions'),
            'data': {'error_code': 403, 'error_message': _('Insufficient permissions')}
        }), 403

    return None
