from sqlalchemy.exc import IntegrityError
from .models import Passkey, User, Role, Permission, RolePermission, UserRole, Setting, UserSetting, Item, ItemShare, ListType, SessionLocal, RelationshipStatus, Translation
from sqlalchemy.orm import joinedload
from datetime import date
from sqlalchemy import desc, asc, and_, or_
from app.logger import log


# Initial Database Setup
def init_db():
    session = SessionLocal()
    try:
        # Simple guard: if roles exist, DB was already initialized
        if session.query(Role).count() > 0:
            log('debug', 'Database already initialized — skipping')
            return

        log('info', 'Database is empty — creating default data')

        # System user
        system_user = User(firstName='system')
        session.add(system_user)

        # Roles
        roles = {
            'System': Role(roleName='System'),
            'Admin': Role(roleName='Admin'),
            'Adult': Role(roleName='Adult'),
            'Child': Role(roleName='Child'),
        }
        session.add_all(roles.values())

        # List types (English keys — displayed via translation system)
        list_types = {
            'Home': ListType(title='Home', icon='home', contentURL='home', createdByUser=1, navbar=True, navbarOrder=1, routeID='home', mainTitle='Home'),
            'Moments': ListType(title='Moments', icon='', contentURL='', createdByUser=1, navbar=False, navbarOrder=0, routeID='', mainTitle='Moments'),
            'Movie List': ListType(title='Movie List', icon='movie', contentURL='movie-list', createdByUser=1, navbar=True, navbarOrder=4, routeID='movie-list', mainTitle='Movie List'),
            'Bucket List': ListType(title='Bucket List', icon='list', contentURL='bucket-list', createdByUser=1, navbar=True, navbarOrder=5, routeID='bucket-list', mainTitle='Bucket List'),
            'Countdown': ListType(title='Countdown', icon='timer', contentURL='', createdByUser=1, navbar=False, navbarOrder=0, routeID='', mainTitle='Countdown'),
        }
        session.add_all(list_types.values())
        session.flush()  # IDs for list_types and roles available

        # Permissions — CRUD for entities + per-list + global
        perm_names = [
            'Read Setting', 'Update Setting',
        ]
        # Per-list permissions (linked to list type)
        list_perm_actions = ['View', 'Create', 'Update', 'Delete']
        list_perm_names = []
        for lt_name in ['Home', 'Moments', 'Movie List', 'Bucket List', 'Countdown']:
            for action in list_perm_actions:
                list_perm_names.append(f'{action} {lt_name}')

        # Global permissions
        global_perm_names = ['Manage Lists', 'Manage Translations', 'Access Admin Panel', 'Share Items']

        all_perm_names = perm_names + list_perm_names + global_perm_names
        permissions = {}
        for name in all_perm_names:
            permissions[name] = Permission(permissionName=name)
        session.add_all(permissions.values())
        session.flush()  # Permission IDs available

        # Link per-list permissions to their list types
        for lt_name, lt_obj in list_types.items():
            for action in list_perm_actions:
                perm_name = f'{action} {lt_name}'
                permissions[perm_name].listTypeID = lt_obj.id

        # Role permissions — by name instead of hardcoded IDs
        admin_role = roles['Admin']
        adult_role = roles['Adult']
        child_role = roles['Child']

        # Admin gets all permissions
        for perm in permissions.values():
            session.add(RolePermission(roleID=admin_role.id, permissionID=perm.id))

        # Adult permissions
        adult_perms = [
            'Read Setting',
            'View Home', 'Create Home', 'Update Home', 'Delete Home',
            'View Moments', 'Create Moments', 'Update Moments', 'Delete Moments',
            'View Movie List', 'Create Movie List', 'Update Movie List', 'Delete Movie List',
            'View Bucket List', 'Create Bucket List', 'Update Bucket List', 'Delete Bucket List',
            'View Countdown', 'Create Countdown',
            'Share Items',
        ]
        for perm_name in adult_perms:
            session.add(RolePermission(roleID=adult_role.id, permissionID=permissions[perm_name].id))

        # Child permissions
        child_perms = [
            'Read Setting',
            'View Home', 'Create Home',
            'View Moments', 'Create Moments',
            'View Movie List', 'Create Movie List',
            'View Bucket List', 'Create Bucket List',
            'View Countdown',
        ]
        for perm_name in child_perms:
            session.add(RolePermission(roleID=child_role.id, permissionID=permissions[perm_name].id))

        # System user → Admin role
        session.add(UserRole(userID=system_user.id, roleID=admin_role.id))

        # Settings
        settings = [
            Setting(name='sm_edition', value='couples', icon='stacks', edition='all', category='about', type='variant'),
            Setting(name='sm_version', value='2.0alpha', icon='update', edition='all', category='about', type='text'),
            Setting(name='setup_complete', value='False', icon='', edition='all', category='', type='text'),
            Setting(name='title', value='', icon='title', edition='couples', category='general', type='text'),
            Setting(name='family_name', value='', icon='diversity_3', edition='family', category='general', type='text'),
            Setting(name='friend_group_name', value='', icon='group', edition='friends', category='general', type='text'),
            Setting(name='relationship_status', value='', icon='favorite', edition='couples', category='general', type='text'),
            Setting(name='anniversary_date', value='', icon='event', edition='couples', category='general', type='date'),
            Setting(name='engaged_date', value='', icon='event', edition='couples', category='general', type='date'),
            Setting(name='wedding_date', value='', icon='event', edition='couples', category='general', type='date'),
            Setting(name='share_tracking', value='True', icon='analytics', edition='all', category='general', type='toggle'),
        ]
        session.add_all(settings)

        # Relationship statuses
        for i in range(1, 6):
            session.add(RelationshipStatus(id=i))

        # Default user setting
        session.add(UserSetting(userID=system_user.id, name='language', value='en'))

        # Seed translations for list type titles
        list_type_translations = {
            'Home':        {'en': 'Home',        'de': 'Home'},
            'Moments':     {'en': 'Moments',     'de': 'Momente'},
            'Movie List':  {'en': 'Movie List',  'de': 'Filmliste'},
            'Bucket List': {'en': 'Bucket List', 'de': 'Bucketliste'},
            'Countdown':   {'en': 'Countdown',   'de': 'Countdown'},
        }
        for field_name, langs in list_type_translations.items():
            for lang_code, text in langs.items():
                session.add(Translation(
                    entityType='ui', entityID=0,
                    languageCode=lang_code, fieldName=field_name,
                    translatedText=text,
                ))

        session.commit()
        log('info', 'Database initialized successfully')
    finally:
        session.close()


# Table Users

def create_user(firstName, lastName, email, birthDate, profilePicture, passwordHash, passwordSalt, public_key, credential_id, sign_count):
    session = SessionLocal()
    try:
        new_user = User(
            firstName=firstName,
            lastName=lastName,
            email=email,
            birthDate=birthDate,
            profilePicture=profilePicture,
            passwordHash=str(passwordHash),
            passwordSalt=passwordSalt,
            public_key=public_key,
            credential_id=credential_id,
            sign_count=sign_count
        )
        session.add(new_user)
        session.commit()
        return new_user.id
    finally:
        session.close()

def get_user_by_id(user_id):
    session = SessionLocal()
    try:
        user = session.query(User).filter(User.id == user_id).first()
        if user:
            session.expunge(user)
        return user
    finally:
        session.close()

def update_user_profile_picture(user_id, filename):
    session = SessionLocal()
    try:
        user = session.query(User).filter(User.id == user_id).first()
        if user:
            user.profilePicture = filename
            session.commit()
            return True
        return False
    finally:
        session.close()

def get_user_by_email(email):
    session = SessionLocal()
    try:
        user = session.query(User).filter(User.email == email).first()
        if user:
            session.expunge(user)
        return user
    finally:
        session.close()

def get_user_by_credential_id(credential_id):
    session = SessionLocal()
    try:
        credentials = session.query(Passkey).filter(Passkey.credential_id == credential_id).first()
        user = session.query(User).filter(User.id == credentials.userID).first()
        if credentials:
            session.expunge(credentials)
        if user:
            session.expunge(user)
        return credentials, user
    finally:
        session.close()

def update_passkey_sign_count(user_id, sign_count):
    session = SessionLocal()
    try:
        credentials = session.query(Passkey).filter(Passkey.userID == user_id).first()
        if credentials:
            credentials.sign_count = sign_count
            session.commit()
    finally:
        session.close()

# Table Role

def create_role(roleName, description):
    session = SessionLocal()
    try:
        new_role = Role(
            roleName=roleName,
            description=description
        )
        session.add(new_role)
        session.commit()
    finally:
        session.close()

def get_role_by_name(role_name):
    session = SessionLocal()
    try:
        role = session.query(Role).filter(Role.roleName == role_name).first()
        return role.id
    finally:
        session.close()

def update_role(role_id, roleName=None, description=None):
    session = SessionLocal()
    try:
        role = session.query(Role).filter(Role.id == role_id).first()
        if role:
            if roleName:
                role.roleName = roleName
            if description:
                role.description = description
            session.commit()
    finally:
        session.close()

def delete_role(role_id):
    session = SessionLocal()
    try:
        role = session.query(Role).filter(Role.id == role_id).first()
        if role:
            session.delete(role)
            session.commit()
    finally:
        session.close()


# Admin query functions

def get_all_users():
    """Returns all users except the system user (id=1)."""
    session = SessionLocal()
    try:
        users = session.query(User).filter(User.id != 1).all()
        for user in users:
            session.expunge(user)
        return users
    finally:
        session.close()

def get_all_roles():
    """Returns all roles except System (id=1)."""
    session = SessionLocal()
    try:
        roles = session.query(Role).filter(Role.id != 1).all()
        for role in roles:
            session.expunge(role)
        return roles
    finally:
        session.close()

def get_all_permissions_list():
    """Returns all permissions."""
    session = SessionLocal()
    try:
        permissions = session.query(Permission).all()
        for p in permissions:
            session.expunge(p)
        return permissions
    finally:
        session.close()

def get_role_permissions_map():
    """Returns a dict: {roleID: [permissionID, ...]}"""
    session = SessionLocal()
    try:
        rps = session.query(RolePermission).all()
        result = {}
        for rp in rps:
            if rp.roleID not in result:
                result[rp.roleID] = []
            result[rp.roleID].append(rp.permissionID)
        return result
    finally:
        session.close()

def get_user_roles_map():
    """Returns a dict: {userID: [roleID, ...]}"""
    session = SessionLocal()
    try:
        urs = session.query(UserRole).all()
        result = {}
        for ur in urs:
            if ur.userID not in result:
                result[ur.userID] = []
            result[ur.userID].append(ur.roleID)
        return result
    finally:
        session.close()

def get_role_permissions_for_role(role_id):
    """Returns permission IDs for a specific role."""
    session = SessionLocal()
    try:
        rps = session.query(RolePermission.permissionID).filter(RolePermission.roleID == role_id).all()
        return [rp[0] for rp in rps]
    finally:
        session.close()

def get_user_roles_list(user_id):
    """Returns role IDs for a specific user."""
    session = SessionLocal()
    try:
        urs = session.query(UserRole.roleID).filter(UserRole.userID == user_id).all()
        return [ur[0] for ur in urs]
    finally:
        session.close()

def set_role_permissions(role_id, permission_ids):
    """Replaces all permissions for a role."""
    session = SessionLocal()
    try:
        session.query(RolePermission).filter(RolePermission.roleID == role_id).delete()
        for pid in permission_ids:
            session.add(RolePermission(roleID=role_id, permissionID=pid))
        session.commit()
    finally:
        session.close()

def set_user_roles(user_id, role_ids):
    """Replaces all roles for a user."""
    session = SessionLocal()
    try:
        session.query(UserRole).filter(UserRole.userID == user_id).delete()
        for rid in role_ids:
            session.add(UserRole(userID=user_id, roleID=rid))
        session.commit()
    finally:
        session.close()


# Table Permission

def create_permission(permissionName, description):
    session = SessionLocal()
    try:
        new_permission = Permission(
            permissionName=permissionName,
            description=description
        )
        session.add(new_permission)
        session.commit()
    finally:
        session.close()

def get_permission(permission_id):
    session = SessionLocal()
    try:
        permission = session.query(Permission).filter(Permission.id == permission_id).first()
        return permission
    finally:
        session.close()

def update_permission(permission_id, permissionName=None, description=None):
    session = SessionLocal()
    try:
        permission = session.query(Permission).filter(Permission.id == permission_id).first()
        if permission:
            if permissionName:
                permission.permissionName = permissionName
            if description:
                permission.description = description
            session.commit()
    finally:
        session.close()

def delete_permission(permission_id):
    session = SessionLocal()
    try:
        permission = session.query(Permission).filter(Permission.id == permission_id).first()
        if permission:
            session.delete(permission)
            session.commit()
    finally:
        session.close()


# Table RolePermission

def create_role_permission(roleID, permissionID):
    session = SessionLocal()
    try:
        new_role_permission = RolePermission(
            roleID=roleID,
            permissionID=permissionID
        )
        session.add(new_role_permission)
        session.commit()
    finally:
        session.close()

def get_role_permission(roleID, permissionID):
    session = SessionLocal()
    try:
        role_permission = session.query(RolePermission).filter_by(roleID=roleID, permissionID=permissionID).first()
        return role_permission
    finally:
        session.close()

def update_role_permission(roleID, permissionID, new_roleID=None, new_permissionID=None):
    session = SessionLocal()
    try:
        role_permission = session.query(RolePermission).filter_by(roleID=roleID, permissionID=permissionID).first()
        if role_permission:
            if new_roleID is not None:
                role_permission.roleID = new_roleID
            if new_permissionID is not None:
                role_permission.permissionID = new_permissionID
            session.commit()
    finally:
        session.close()

def delete_role_permission(roleID, permissionID):
    session = SessionLocal()
    try:
        role_permission = session.query(RolePermission).filter_by(roleID=roleID, permissionID=permissionID).first()
        if role_permission:
            session.delete(role_permission)
            session.commit()
    finally:
        session.close()


# Table UserRole

def create_user_role(userID, roleID):
    session = SessionLocal()
    try:
        new_user_role = UserRole(
            userID=userID,
            roleID=roleID
        )
        session.add(new_user_role)
        session.commit()
    finally:
        session.close()

def get_user_role(userID, roleID):
    session = SessionLocal()
    try:
        user_role = session.query(UserRole).filter_by(userID=userID, roleID=roleID).first()
        return user_role
    finally:
        session.close()

def update_user_role(userID, roleID, new_userID=None, new_roleID=None):
    session = SessionLocal()
    try:
        user_role = session.query(UserRole).filter_by(userID=userID, roleID=roleID).first()
        if user_role:
            if new_userID:
                user_role.userID = new_userID
            if new_roleID:
                user_role.roleID = new_roleID
            session.commit()
    finally:
        session.close()

def delete_user_role(userID, roleID):
    session = SessionLocal()
    try:
        user_role = session.query(UserRole).filter_by(userID=userID, roleID=roleID).first()
        if user_role:
            session.delete(user_role)
            session.commit()
    finally:
        session.close()

# Table Setting

def create_setting(name, value):
    session = SessionLocal()
    try:
        new_setting = Setting(
            name=name,
            value=value
        )
        session.add(new_setting)
        session.commit()
    finally:
        session.close()

class SettingObject:
    def __init__(self, setting):
        for column in setting.__table__.columns:
            setattr(self, column.name, getattr(setting, column.name))

class SettingsContainer:
    def __init__(self, settings_list):
        self.settings_list = settings_list
        for setting in settings_list:
            setattr(self, setting.name, SettingObject(setting))

    def __iter__(self):
        return iter(self.settings_list)

def get_all_settings():
    session = SessionLocal()
    try:
        settings_list = session.query(Setting).all()
        return SettingsContainer(settings_list)
    finally:
        session.close()

def get_setting_by_name(name):
    session = SessionLocal()
    try:
        setting = session.query(Setting).filter(Setting.name == name).first()
        if setting is None:
            return Setting(name=name, value=None)
        return setting
    finally:
        session.close()

def update_setting(name, new_value):
    session = SessionLocal()
    try:
        setting = session.query(Setting).filter(Setting.name == name).first()
        if setting:
            setting.value = new_value
            session.commit()
    finally:
        session.close()

# Table UserSetting

def create_user_setting(userID, setting, value):
    session = SessionLocal()
    try:
        new_user_setting = UserSetting(
            userID=userID,
            name=setting,
            value=value
        )
        session.add(new_user_setting)
        session.commit()
    finally:
        session.close()

def get_all_user_settings():
    session = SessionLocal()
    try:
        user_settings = session.query(UserSetting).all()
        return user_settings
    finally:
        session.close()

def get_user_setting(userID, name):
    session = SessionLocal()
    try:
        user_setting = session.query(UserSetting).filter(UserSetting.userID == userID, UserSetting.name == name).first()
        return user_setting
    finally:
        session.close()

def get_user_settings(userID):
    session = SessionLocal()
    try:
        user_settings = session.query(UserSetting).filter(UserSetting.userID == userID).all()
        return user_settings
    finally:
        session.close()

def update_user_setting(userID, name=None, value=None):
    session = SessionLocal()
    try:
        user_setting = session.query(UserSetting).filter(UserSetting.userID == userID, UserSetting.name == name).first()
        if user_setting:
            if value is not None:
                user_setting.value = value
            session.commit()
    finally:
        session.close()


def ensure_pwa_settings(userID):
    """Creates default PWA settings for a user if they don't exist yet."""
    pwa_defaults = {
        'pwa_offline_all': 'FALSE',
        'pwa_auto_cache_count': '20',
        'pwa_cache_expiry_days': '14',
        'pwa_wifi_only_upload': 'FALSE',
        'pwa_preload_on_wifi': 'FALSE',
    }
    session = SessionLocal()
    try:
        for name, default_value in pwa_defaults.items():
            existing = session.query(UserSetting).filter(
                UserSetting.userID == userID,
                UserSetting.name == name
            ).first()
            if not existing:
                session.add(UserSetting(userID=userID, name=name, value=default_value))
        session.commit()
    finally:
        session.close()


# Table Item

def create_item(title, content, contentType, listType, contentURL, createdByUser, dateCreated, edition='all'):
    session = SessionLocal()
    try:
        new_item = Item(
            title=title,
            content=content,
            contentType=contentType,
            listType=listType,
            contentURL=contentURL,
            createdByUser=createdByUser,
            dateCreated=dateCreated,
            edition=edition
        )
        session.add(new_item)
        session.commit()
        session.refresh(new_item)
        return new_item.id
    finally:
        session.close()

def get_item_by_id(item_id):
    session = SessionLocal()
    try:
        item = session.query(Item).filter(Item.id == item_id).first()
        return item
    finally:
        session.close()

def get_all_media_urls():
    session = SessionLocal()
    try:
        items = session.query(Item.id, Item.contentType, Item.contentURL).filter(Item.contentURL.isnot(None), Item.contentURL != '').all()
        urls = []
        for item_id, content_type, content_url in items:
            for filename in content_url.split(';'):
                filename = filename.strip()
                if filename:
                    urls.append(f'/api/v2/media/{filename}')
            # Gallery-Seiten auch cachen
            if content_type and content_type.startswith('gallery'):
                urls.append(f'/gallery/{item_id}')
        return urls
    finally:
        session.close()

def get_items_by_type(list_type_id, sort_by='desc', edition=None, checked_last=False):
    session = SessionLocal()
    try:
        order_func = desc if sort_by == 'desc' else asc
        query = session.query(Item, User).join(User, Item.createdByUser == User.id).filter(Item.listType == list_type_id)
        if edition:
            query = query.filter(or_(Item.edition == edition, Item.edition == 'all', Item.edition.is_(None)))
        if checked_last:
            query = query.order_by(asc(Item.content == '1'), order_func(Item.dateCreated))
        else:
            query = query.order_by(order_func(Item.dateCreated))
        items = query.all()
        return items
    finally:
        session.close()

def update_item(item_id, title=None, content=None, contentType=None, contentURL=None, dateCreated=None, edition=None):
    session = SessionLocal()
    try:
        item = session.query(Item).filter(Item.id == item_id).first()
        if item:
            if title is not None:
                item.title = title
            if content is not None:
                item.content = content
            if contentType is not None:
                item.contentType = contentType
            if contentURL is not None:
                item.contentURL = contentURL
            if dateCreated is not None:
                item.dateCreated = dateCreated
            if edition is not None:
                item.edition = edition
            session.commit()
    finally:
        session.close()

def delete_item(item_id):
    session = SessionLocal()
    try:
        session.query(ItemShare).filter(ItemShare.itemID == item_id).delete()
        item = session.query(Item).filter(Item.id == item_id).first()
        if item:
            session.delete(item)
            session.commit()
    finally:
        session.close()


# Table ListType

def create_list_type(title, icon, contentURL, createdByUser, navbar, navbarOrder, routeID, mainTitle):
    session = SessionLocal()
    try:
        new_list_type = ListType(
            title=title,
            icon=icon,
            contentURL=contentURL,
            createdByUser=createdByUser,
            navbarOrder=navbarOrder,
            navbar=navbar,
            routeID=routeID,
            mainTitle=mainTitle
        )
        session.add(new_list_type)
        session.commit()
        session.refresh(new_list_type)
        return new_list_type.id
    finally:
        session.close()

def get_list_type_by_id(list_type_id):
    session = SessionLocal()
    try:
        list_type = session.query(ListType).filter(ListType.id == list_type_id).first()
        return list_type
    finally:
        session.close()

def get_list_type_by_content_url(content_url):
    session = SessionLocal()
    try:
        list_type = session.query(ListType).filter(ListType.contentURL == content_url).first()
        return list_type
    finally:
        session.close()

def get_all_list_types():
    session = SessionLocal()
    try:
        list_types = session.query(ListType).order_by(ListType.navbarOrder.asc()).all()
        return list_types
    finally:
        session.close()

def update_list_type(list_type_id, title=None, icon=None, contentURL=None, navbar=None, navbarOrder=None, routeID=None, mainTitle=None):
    session = SessionLocal()
    try:
        list_type = session.query(ListType).filter(ListType.id == list_type_id).first()
        if list_type:
            if title is not None:
                list_type.title = title
            if icon is not None:
                list_type.icon = icon
            if contentURL is not None:
                list_type.contentURL = contentURL
            if navbar is not None:
                list_type.navbar = navbar
            if routeID is not None:
                list_type.routeID = routeID
            if mainTitle is not None:
                list_type.mainTitle = mainTitle
            if navbarOrder is not None:
                list_type.navbarOrder = navbarOrder
            session.commit()
    finally:
        session.close()

def delete_list_type(list_type_id):
    session = SessionLocal()
    try:
        list_type = session.query(ListType).filter(ListType.id == list_type_id).first()
        if list_type:
            session.delete(list_type)
            session.commit()
    finally:
        session.close()


def get_list_type_by_title(title):
    session = SessionLocal()
    try:
        list_type = session.query(ListType).filter(ListType.title == title).first()
        return list_type
    finally:
        session.close()


def ensure_countdown_list_type():
    """For existing databases: creates the Countdown ListType + permissions if missing."""
    session = SessionLocal()
    try:
        existing = session.query(ListType).filter(ListType.title == 'Countdown').first()
        if existing:
            return
        lt = ListType(title='Countdown', icon='timer', contentURL='', createdByUser=1, navbar=False, navbarOrder=0, routeID='', mainTitle='Countdown')
        session.add(lt)
        session.flush()
        admin_role = session.query(Role).filter(Role.roleName == 'Admin').first()
        for action in ('View', 'Create', 'Update', 'Delete'):
            perm = Permission(permissionName=f'{action} Countdown', listTypeID=lt.id)
            session.add(perm)
            session.flush()
            if admin_role:
                session.add(RolePermission(roleID=admin_role.id, permissionID=perm.id))
        # Seed translations
        for lang_code, text in [('en', 'Countdown'), ('de', 'Countdown')]:
            exists = session.query(Translation).filter(
                Translation.entityType == 'ui', Translation.entityID == 0,
                Translation.languageCode == lang_code, Translation.fieldName == 'Countdown'
            ).first()
            if not exists:
                session.add(Translation(entityType='ui', entityID=0, languageCode=lang_code, fieldName='Countdown', translatedText=text))
        session.commit()
    finally:
        session.close()


# Per-list permission lifecycle functions

def create_permissions_for_list_type(list_type_id, title):
    """Creates View/Create/Update/Delete permissions for a list type and assigns them to the Admin role."""
    session = SessionLocal()
    try:
        admin_role = session.query(Role).filter(Role.roleName == 'Admin').first()
        for action in ('View', 'Create', 'Update', 'Delete'):
            perm = Permission(permissionName=f'{action} {title}', listTypeID=list_type_id)
            session.add(perm)
            session.flush()
            if admin_role:
                session.add(RolePermission(roleID=admin_role.id, permissionID=perm.id))
        session.commit()
    finally:
        session.close()


def delete_permissions_for_list_type(list_type_id):
    """Deletes all permissions (and their RolePermissions) linked to a list type."""
    session = SessionLocal()
    try:
        perms = session.query(Permission).filter(Permission.listTypeID == list_type_id).all()
        for perm in perms:
            session.query(RolePermission).filter(RolePermission.permissionID == perm.id).delete()
            session.delete(perm)
        session.commit()
    finally:
        session.close()


def rename_list_type_permissions(list_type_id, new_title):
    """Renames all permissions linked to a list type to match the new title."""
    session = SessionLocal()
    try:
        perms = session.query(Permission).filter(Permission.listTypeID == list_type_id).all()
        for perm in perms:
            action = perm.permissionName.split(' ', 1)[0]
            perm.permissionName = f'{action} {new_title}'
        session.commit()
    finally:
        session.close()


# Table RelationshipStatus
def get_all_relationship_statuses():
    session = SessionLocal()
    try:
        relationship_statuses = session.query(RelationshipStatus).all()
        return [status.id for status in relationship_statuses]
    finally:
        session.close()

def get_relationship_statuses_with_names(language_code):
    session = SessionLocal()
    try:
        statuses = session.query(RelationshipStatus).all()
        status_ids = [s.id for s in statuses]
        # Batch-load all translations in one query instead of N+1
        translations = session.query(Translation).filter(
            Translation.entityType == 'relationship_status',
            Translation.entityID.in_(status_ids),
            Translation.languageCode == language_code
        ).all()
        translation_map = {t.entityID: t.translatedText for t in translations}
        return [
            {'id': sid, 'name': translation_map.get(sid, f'Status {sid}')}
            for sid in status_ids
        ]
    finally:
        session.close()


# Table Translations

def get_supported_languages():
    session = SessionLocal()
    try:
        languages = session.query(Translation.languageCode).distinct().all()
        return [lang[0] for lang in languages]
    except Exception:
        return []
    finally:
        session.close()

def get_all_translations():
    session = SessionLocal()
    try:
        translations = session.query(Translation).all()
        return translations
    finally:
        session.close()

def get_field_name(entityType, entityID):
    session = SessionLocal()
    try:
        fieldNames = session.query(Translation.fieldName).filter(Translation.entityType == entityType, Translation.entityID == entityID).distinct().all()
        return [name[0] for name in fieldNames][0]
    finally:
        session.close()

def get_translation(fieldName, languageCode):
    session = SessionLocal()
    try:
        translation = session.query(Translation.translatedText).filter(Translation.fieldName == fieldName, Translation.languageCode == languageCode).first()
        return translation[0] if translation and translation[0] != "" else fieldName
    finally:
        session.close()

def get_translation_for_entity(entityType, entityID, languageCode):
    session = SessionLocal()
    try:
        translations = session.query(Translation).filter(Translation.entityType == entityType, Translation.entityID == entityID, Translation.languageCode == languageCode).all()
        return translations[0].translatedText
    finally:
        session.close()

def create_new_translations(new_translations_array):
    session = SessionLocal()
    try:
        for translation in new_translations_array:
            new_translation = Translation(
                entityType=translation['entityType'],
                entityID=0,
                languageCode='en',
                fieldName=translation['fieldName'],
                translatedText="",
                helpText=""
            )
            session.add(new_translation)
        session.commit()
    finally:
        session.close()


def create_new_language(languageCode):
    session = SessionLocal()
    try:
        fields = session.query(Translation).filter(Translation.languageCode == 'en').all()
        for field in fields:
            new_translation = Translation(
                entityType=field.entityType,
                entityID=field.entityID,
                languageCode=languageCode,
                fieldName=field.fieldName,
                translatedText="",
                helpText=field.helpText
            )
            session.add(new_translation)
        session.commit()
        return True
    finally:
        session.close()

def get_translations_by_language(languageCode):
    session = SessionLocal()
    try:
        translations = session.query(Translation).filter(Translation.languageCode == languageCode).all()
        return translations
    finally:
        session.close()

def update_translation(entityType, entityID, languageCode, fieldName, translatedText, helpText):
    session = SessionLocal()
    try:
        translation = session.query(Translation).filter(Translation.entityType == entityType, Translation.entityID == entityID, Translation.languageCode == languageCode, Translation.fieldName == fieldName).first()
        if translation:
            translation.translatedText = translatedText
            translation.helpText = helpText
            session.commit()
    finally:
        session.close()

def get_translation_progress():
    session = SessionLocal()
    try:
        languages = session.query(Translation.languageCode).distinct().all()
        progress = []
        for language in languages:
            total_entries = session.query(Translation).filter(Translation.languageCode == language[0]).count()
            translated_entries = session.query(Translation).filter(Translation.languageCode == language[0], Translation.translatedText != "").count()
            percentage = round((translated_entries / total_entries) * 100)
            progress.append({
                'language': language[0],
                'translated_entries': translated_entries,
                'total_entries': total_entries,
                'percentage': percentage
            })
        return progress
    finally:
        session.close()

# Table ItemShare

def generate_share_token(length=10):
    import secrets
    import string
    alphabet = string.ascii_letters + string.digits
    session = SessionLocal()
    try:
        for _ in range(100):
            token = ''.join(secrets.choice(alphabet) for _ in range(length))
            existing = session.query(ItemShare).filter(ItemShare.token == token).first()
            if not existing:
                return token
        raise RuntimeError('Could not generate unique share token')
    finally:
        session.close()


def create_item_share(item_id, user_id, expires_at=None, password=None):
    from flask_bcrypt import generate_password_hash
    session = SessionLocal()
    try:
        token = generate_share_token()
        password_hash = None
        if password:
            password_hash = generate_password_hash(password).decode('utf-8')
        share = ItemShare(
            itemID=item_id,
            token=token,
            createdByUser=user_id,
            expiresAt=expires_at,
            passwordHash=password_hash,
            isActive=True
        )
        session.add(share)
        session.commit()
        session.refresh(share)
        return {
            'id': share.id,
            'token': share.token,
            'expiresAt': str(share.expiresAt) if share.expiresAt else None,
            'hasPassword': share.passwordHash is not None
        }
    finally:
        session.close()


def get_share_by_token(token):
    session = SessionLocal()
    try:
        share = session.query(ItemShare).filter(
            ItemShare.token == token,
            ItemShare.isActive == True
        ).first()
        if not share:
            return None, None
        item = session.query(Item).filter(Item.id == share.itemID).first()
        session.expunge(share)
        if item:
            session.expunge(item)
        return share, item
    finally:
        session.close()


def get_shares_for_item(item_id):
    session = SessionLocal()
    try:
        shares = session.query(ItemShare).filter(
            ItemShare.itemID == item_id,
            ItemShare.isActive == True
        ).all()
        return [{
            'id': share.id,
            'token': share.token,
            'createdAt': str(share.createdAt) if share.createdAt else None,
            'expiresAt': str(share.expiresAt) if share.expiresAt else None,
            'hasPassword': share.passwordHash is not None,
            'viewCount': share.viewCount or 0
        } for share in shares]
    finally:
        session.close()


def deactivate_share(share_id, user_id=None, admin=False):
    session = SessionLocal()
    try:
        if admin:
            share = session.query(ItemShare).filter(ItemShare.id == share_id).first()
        else:
            share = session.query(ItemShare).filter(
                ItemShare.id == share_id,
                ItemShare.createdByUser == user_id
            ).first()
        if share:
            share.isActive = False
            session.commit()
    finally:
        session.close()


def increment_share_view_count(share_id):
    session = SessionLocal()
    try:
        share = session.query(ItemShare).filter(ItemShare.id == share_id).first()
        if share:
            share.viewCount = (share.viewCount or 0) + 1
            session.commit()
    finally:
        session.close()


def get_shared_item_ids():
    from datetime import datetime
    session = SessionLocal()
    try:
        shares = session.query(ItemShare.itemID).filter(
            ItemShare.isActive == True,
            or_(ItemShare.expiresAt == None, ItemShare.expiresAt > datetime.utcnow())
        ).distinct().all()
        return {s[0] for s in shares}
    finally:
        session.close()


def get_all_active_shares():
    from datetime import datetime
    session = SessionLocal()
    try:
        shares = session.query(ItemShare, Item, User).join(
            Item, ItemShare.itemID == Item.id
        ).join(
            User, ItemShare.createdByUser == User.id
        ).filter(
            ItemShare.isActive == True
        ).order_by(ItemShare.createdAt.desc()).all()
        return [{
            'id': share.id,
            'token': share.token,
            'itemTitle': item.title,
            'itemID': item.id,
            'createdBy': f'{user.firstName} {user.lastName or ""}'.strip(),
            'createdAt': str(share.createdAt) if share.createdAt else None,
            'expiresAt': str(share.expiresAt) if share.expiresAt else None,
            'hasPassword': share.passwordHash is not None,
            'viewCount': share.viewCount or 0,
            'isExpired': share.expiresAt is not None and share.expiresAt < datetime.utcnow()
        } for share, item, user in shares]
    finally:
        session.close()


def verify_share_password(share, password):
    from flask_bcrypt import check_password_hash
    if not share.passwordHash:
        return True
    return check_password_hash(share.passwordHash, password)




def approve_new_translations_to_all_languages():
    session = SessionLocal()
    try:
        all_translations = session.query(Translation).filter(Translation.languageCode == 'en').all()
        all_languages = [lang[0] for lang in session.query(Translation.languageCode).filter(Translation.languageCode != 'en').distinct().all()]

        for translation in all_translations:
            for lang_code in all_languages:
                existing = session.query(Translation).filter_by(
                    entityType=translation.entityType,
                    entityID=translation.entityID,
                    languageCode=lang_code,
                    fieldName=translation.fieldName
                ).first()
                if not existing:
                    session.add(Translation(
                        entityType=translation.entityType,
                        entityID=translation.entityID,
                        languageCode=lang_code,
                        fieldName=translation.fieldName,
                        translatedText="",
                        helpText=translation.helpText
                    ))
            if translation.translatedText == "":
                translation.translatedText = translation.fieldName

        session.commit()
    finally:
        session.close()
