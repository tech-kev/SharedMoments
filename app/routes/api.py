from flask import Blueprint, g, make_response, render_template, send_file, request, jsonify, session, abort, current_app as app
from werkzeug.utils import secure_filename
from app.db_queries import (approve_new_translations_to_all_languages, create_new_language,
    create_new_translations, get_all_list_types, get_all_relationship_statuses, get_items_by_type,
    create_item, get_supported_languages, get_translation_progress, get_translations_by_language,
    get_user_by_id, get_user_setting, get_setting_by_name, delete_item, get_item_by_id,
    update_item, get_list_type_by_id, update_list_type, delete_list_type, create_list_type,
    get_all_settings, update_setting, create_user, get_role_by_name, create_user_role,
    create_user_setting, update_translation, update_user_setting, update_user_profile_picture,
    create_permissions_for_list_type, delete_permissions_for_list_type, rename_list_type_permissions, get_user_by_email, update_user_password,
    create_item_share, get_shares_for_item, deactivate_share, get_shared_item_ids,
    get_all_media_urls, get_list_type_by_title,
    get_all_reminders, get_reminder_by_id, create_reminder as db_create_reminder,
    update_reminder as db_update_reminder, delete_reminder as db_delete_reminder,
    get_user_muted_reminder_ids, mute_reminder, unmute_reminder,
    save_push_subscription, delete_push_subscription,
    get_passkeys_by_user, create_passkey as db_create_passkey, delete_passkey as db_delete_passkey, rename_passkey as db_rename_passkey)
from datetime import datetime
from app.logger import log
import os, json, subprocess, shutil, threading, uuid, zipfile, tempfile, time
from app.models import Passkey, SessionLocal, User, UserRole, Setting, UserSetting, Role, Item, ListType, Reminder, ReminderMute
from app.utils import export_data, find_unmatched_translations, generate_lqip, generate_admin_filename
from app.translation import _, load_translation_in_cache, set_locale, migrateTranslations
from app.version import __version__, VERSION_MAJOR
from app.routes.auth import jwt_required, login_jwt
from app.permissions import require_permission, require_list_permission

api_bp = Blueprint('api', __name__)

_export_jobs = {}
_import_jobs = {}

# File-based job status for multi-worker environments (gunicorn)
_JOBS_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', 'uploads', 'temp', 'jobs')
os.makedirs(_JOBS_DIR, exist_ok=True)

def _write_job(job_id, data):
    path = os.path.join(_JOBS_DIR, job_id + '.json')
    tmp_path = path + '.tmp'
    with open(tmp_path, 'w') as f:
        json.dump(data, f)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, path)

def _read_job(job_id):
    path = os.path.join(_JOBS_DIR, job_id + '.json')
    if not os.path.exists(path):
        return None
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, ValueError):
        return None

class _FileJob:
    """Dict-like job tracker that auto-syncs to a JSON file on every write."""
    def __init__(self, job_id, initial):
        self._job_id = job_id
        self._data = dict(initial)
        _write_job(job_id, self._data)

    def __setitem__(self, key, value):
        self._data[key] = value
        _write_job(self._job_id, self._data)

    def __getitem__(self, key):
        return self._data[key]

    def get(self, key, default=None):
        return self._data.get(key, default)


@api_bp.route('/api/v2/setup', methods=['POST'])
def setup_complete():
    # Prevent re-running setup after initial completion
    setup_setting = get_setting_by_name('setup_complete')
    if setup_setting and setup_setting.value == 'True':
        return jsonify({'status': 'error', 'message': 'Setup already completed'}), 403

    setup_data = json.loads(request.form['setupData'])
    db_session = SessionLocal()

    try:
        set_locale()
        sm_edition = setup_data['sm_edition']
        users = setup_data['users']
        settings = setup_data['settings']

        # Save edition to DB
        sm_edition_setting = db_session.query(Setting).filter_by(name='sm_edition').first()
        if sm_edition_setting:
            sm_edition_setting.value = sm_edition.lower()

        title = settings[0]['title']
        relationship_status = settings[0]['relationshipStatus']
        anniversary_date = settings[0]['anniversary']
        family_name = settings[0]['familyName']
        friend_group_name = settings[0]['friendGroupName']
        wedding_date = settings[0]['weddingAnniversary']
        engaged_date = settings[0]['engagement']
        family_founding_date = settings[0].get('familyFoundingDate', '')
        friend_group_founding_date = settings[0].get('friendGroupFoundingDate', '')

        title_setting = db_session.query(Setting).filter_by(name='title').first()
        if title_setting:
            title_setting.value = title

        relationship_status_setting = db_session.query(Setting).filter_by(name='relationship_status').first()
        if relationship_status_setting:
            relationship_status_setting.value = relationship_status

        anniversary_date_setting = db_session.query(Setting).filter_by(name='anniversary_date').first()
        if anniversary_date_setting:
            anniversary_date_setting.value = anniversary_date

        family_name_setting = db_session.query(Setting).filter_by(name='family_name').first()
        if family_name_setting:
            family_name_setting.value = family_name

        friend_group_name_setting = db_session.query(Setting).filter_by(name='friend_group_name').first()
        if friend_group_name_setting:
            friend_group_name_setting.value = friend_group_name

        wedding_date_setting = db_session.query(Setting).filter_by(name='wedding_date').first()
        if wedding_date_setting:
            wedding_date_setting.value = wedding_date

        engaged_date_setting = db_session.query(Setting).filter_by(name='engaged_date').first()
        if engaged_date_setting:
            engaged_date_setting.value = engaged_date

        family_founding_date_setting = db_session.query(Setting).filter_by(name='family_founding_date').first()
        if family_founding_date_setting:
            family_founding_date_setting.value = family_founding_date

        friend_group_founding_date_setting = db_session.query(Setting).filter_by(name='friend_group_founding_date').first()
        if friend_group_founding_date_setting:
            friend_group_founding_date_setting.value = friend_group_founding_date

        db_session.flush()

        for i, user in enumerate(users):
            firstName = user['firstname']
            lastName = user['lastname']
            email = user['email']
            birthDate = datetime.strptime(user['birthdate'], '%Y-%m-%d').date()
            profilePicture = user['profilePicture']
            password = user['password']
            if i == 0:  # First user is always Admin
                user_role = 'Admin'
            else:
                user_role = user.get('role', 'Adult')

            if email in session.get('webauth_data', {}):
                public_key = session['webauth_data'][email].get('public_key', '')
                credential_id = session['webauth_data'][email].get('credential_id', '')
                sign_count = session['webauth_data'][email].get('sign_count', '')
            else:
                public_key = ''
                credential_id = ''
                sign_count = ''

            passwordHash, passwordSalt = User().hash_password(password)

            new_user = User(
                firstName=firstName,
                lastName=lastName,
                email=email,
                birthDate=birthDate,
                profilePicture=profilePicture,
                passwordHash=passwordHash,
                passwordSalt=passwordSalt,
            )

            db_session.add(new_user)
            db_session.flush()

            user_id = new_user.id

            # Rename and move profile picture from static/images/ to uploads/profiles/
            if profilePicture and profilePicture != 'profile-placeholder.jpg':
                basedir = os.path.abspath(os.path.dirname(__file__))
                static_folder = os.path.join(basedir, '..', 'static', 'images')
                profiles_folder = os.path.join(basedir, '..', 'uploads', 'profiles')
                os.makedirs(profiles_folder, exist_ok=True)
                old_path = os.path.join(static_folder, profilePicture)
                if os.path.exists(old_path):
                    ext = profilePicture.rsplit('.', 1)[-1] if '.' in profilePicture else 'jpg'
                    identifier = f"{firstName}_{lastName}" if lastName else firstName
                    new_name = generate_admin_filename('profile', identifier, ext)
                    new_path = os.path.join(profiles_folder, new_name)
                    shutil.move(old_path, new_path)
                    new_user.profilePicture = new_name

            if credential_id:
                new_passkey = Passkey(
                    userID=new_user.id,
                    name=_('Security Key'),
                    credential_id=credential_id,
                    public_key=public_key,
                    sign_count=sign_count
                )
                db_session.add(new_passkey)
                db_session.flush()

            roleId = db_session.query(Role).filter_by(roleName=user_role).first().id

            db_session.add(UserRole(
                userID=user_id,
                roleID=roleId
            ))
            db_session.flush()

            db_session.add(UserSetting(
                userID=user_id,
                name='language',
                value=session['lang'],
                icon='language',
                edition='all',
                category='about',
                type='text'
            ))
            db_session.flush()

            db_session.add(UserSetting(
                userID=user_id,
                name='darkmode',
                value='FALSE',
                icon='dark_mode',
                edition='all',
                category='about',
                type='text'
            ))
            db_session.flush()

            setup_complete_setting = db_session.query(Setting).filter_by(name='setup_complete').first()
            setup_complete_setting.value = 'True'

        db_session.commit()
        db_session.close()

        # Sync auto-reminders before returning so the DB is not locked when login page loads
        from app.scheduler import sync_auto_reminders
        try:
            sync_auto_reminders()
        except Exception as e:
            log('warning', f'Auto-reminder sync after setup failed: {e}')

        response = make_response(jsonify({
            'status': 'success',
            'message': _('Setup successful')
        }))

        response.delete_cookie('jwt_token')
        return response

    except Exception as e:
        db_session.rollback()
        db_session.close()

        log('error', f'Error while completing the setup: {e}')
        return jsonify({
            'status': 'error',
            'message': _('An error occurred while completing the setup.'),
            'data': {
                'error_code': 500,
                'error_message': str(e) if app.debug else None
            }
        }), 500


@api_bp.route('/api/v2/settings', methods=['PUT'])
@jwt_required
@require_permission('Update Setting')
def update_settings():
    try:
        setting = request.form['setting']
        value = request.form['value']

        if setting in ('banner_image', 'family_banner_image', 'friends_banner_image') and value:
            ext = value.rsplit('.', 1)[-1].lower() if '.' in value else ''
            if ext not in IMAGE_EXTENSIONS:
                return jsonify({
                    'status': 'error',
                    'message': _('Only image files are allowed for the banner.'),
                    'data': {'error_code': 400}
                }), 400

        if setting == 'banner_song' and value:
            ext = value.rsplit('.', 1)[-1].lower() if '.' in value else ''
            if ext != 'mp3':
                return jsonify({
                    'status': 'error',
                    'message': _('Only MP3 files are allowed for the banner song.'),
                    'data': {'error_code': 400}
                }), 400

        # Rename banner files to descriptive names
        if setting in ('banner_image', 'family_banner_image', 'friends_banner_image', 'banner_song') and value:
            basedir = os.path.abspath(os.path.dirname(__file__))
            if setting in ('banner_image', 'family_banner_image', 'friends_banner_image'):
                folder = os.path.join(basedir, '..', 'uploads', 'images')
            else:
                folder = os.path.join(basedir, '..', 'uploads', 'music')
            old_path = os.path.join(folder, value)
            if os.path.exists(old_path):
                ext = value.rsplit('.', 1)[-1] if '.' in value else ''
                new_name = generate_admin_filename(setting, '', ext)
                new_path = os.path.join(folder, new_name)
                shutil.move(old_path, new_path)
                value = new_name

        update_setting(setting, value)

        log('info', f'Setting updated: {setting}')

        # Trigger reminder sync when edition changes
        if setting == 'sm_edition':
            try:
                from app.scheduler import sync_auto_reminders
                sync_auto_reminders()
            except Exception as e:
                log('warning', f'Failed to sync reminders after edition change: {e}')

        return jsonify({
            'status': 'success',
            'message': _('Setting updated successfully'),
            'data': {
                'setting': setting,
                'value': value
            }
        }), 200

    except Exception as e:
        log('error', f'Error while updating the setting: {e}')
        return jsonify({
            'status': 'error',
            'message': _('An error occurred while updating the setting.'),
            'data': {
                'error_code': 500,
                'error_message': str(e) if app.debug else None
            }
        }), 500


@api_bp.route('/api/v2/user-settings', methods=['PUT'])
@jwt_required
def update_user_settings():
    try:
        setting = request.form['setting']
        value = request.form['value']

        update_user_setting(g.user_id, setting, value)

        log('info', f'User-Setting updated: {setting} for user {g.user_id}')

        return jsonify({
            'status': 'success',
            'message': _('User-Setting updated successfully'),
            'data': {
                'setting': setting,
                'value': value
            }
        }), 200

    except Exception as e:
        log('error', f'Error while updating the user-setting: {e}')
        return jsonify({
            'status': 'error',
            'message': _('An error occurred while updating the user-setting.'),
            'data': {
                'error_code': 500,
                'error_message': str(e) if app.debug else None
            }
        }), 500


@api_bp.route('/api/v2/user/profile-picture', methods=['PUT'])
@jwt_required
def update_profile_picture():
    try:
        file = request.files.get('file')
        if not file:
            return jsonify({'status': 'error', 'message': _('No file provided')}), 400

        user = get_user_by_id(g.user_id)
        if user and user.firstName:
            identifier = f"{user.firstName}_{user.lastName}" if user.lastName else user.firstName
        else:
            identifier = f"User_{g.user_id}"
        ext = file.filename.rsplit('.', 1)[-1] if '.' in file.filename else 'jpg'
        filename = generate_admin_filename('profile', identifier, ext)

        upload_dir = os.path.join(os.path.dirname(__file__), '..', 'uploads', 'profiles')
        os.makedirs(upload_dir, exist_ok=True)
        file.save(os.path.join(upload_dir, filename))

        update_user_profile_picture(g.user_id, filename)
        log('info', f'Profile picture updated for user {g.user_id}')

        return jsonify({
            'status': 'success',
            'message': _('Profile picture updated'),
            'data': {'filename': filename}
        }), 200
    except Exception as e:
        log('error', f'Error updating profile picture: {e}')
        return jsonify({
            'status': 'error',
            'message': str(e) if app.debug else None
        }), 500


@api_bp.route('/api/v2/user/password', methods=['PUT'])
@jwt_required
def change_password():
    try:
        data = request.get_json()
        current_password = data.get('current_password', '')
        new_password = data.get('new_password', '')

        if not current_password or not new_password:
            return jsonify({'status': 'error', 'message': _('Please fill in all fields')}), 400

        if len(new_password) < 6:
            return jsonify({'status': 'error', 'message': _('Password must be at least 6 characters')}), 400

        user = get_user_by_id(g.user_id)
        if not user or not user.check_password(current_password):
            return jsonify({'status': 'error', 'message': _('Incorrect password')}), 403

        password_hash, password_salt = user.hash_password(new_password)
        update_user_password(g.user_id, password_hash, password_salt)

        log('info', f'Password changed for user {g.user_id}')
        return jsonify({'status': 'success', 'message': _('Password updated')}), 200
    except Exception as e:
        log('error', f'Error changing password: {e}')
        return jsonify({'status': 'error', 'message': str(e) if app.debug else _('An error occurred')}), 500


def _secure_filename_preserve(filename):
    """secure_filename that preserves tildes in filenames."""
    return secure_filename(filename.replace('~', '_TILDE_')).replace('_TILDE_', '~')


def _safe_send_file(base_folder, filename):
    """Send a file after validating against path traversal."""
    safe = _secure_filename_preserve(filename)
    if not safe or safe != filename:
        abort(400)
    base_folder = os.path.abspath(base_folder)
    file_path = os.path.abspath(os.path.join(base_folder, safe))
    if not file_path.startswith(base_folder):
        abort(403)
    if not os.path.exists(file_path):
        abort(404)
    response = send_file(file_path, conditional=True)
    response.headers['Accept-Ranges'] = 'bytes'
    return response


@api_bp.route('/api/v2/media/<filename>')
@jwt_required
def media(filename):
    return _safe_send_file(_find_media_folder(filename), filename)


def _ensure_video_thumbnail(filename):
    """Generate a JPEG thumbnail for a video file and return its path, or None on failure."""
    safe = _secure_filename_preserve(filename)
    if not safe:
        return None

    videos_folder = os.path.abspath(_find_media_folder(filename))
    video_path = os.path.abspath(os.path.join(videos_folder, safe))

    if not os.path.exists(video_path):
        return None

    basedir = os.path.abspath(os.path.dirname(__file__))
    thumb_folder = os.path.join(basedir, '..', 'uploads', 'thumbs')
    os.makedirs(thumb_folder, exist_ok=True)

    thumb_name = os.path.splitext(safe)[0] + '.jpg'
    thumb_path = os.path.join(thumb_folder, thumb_name)

    if not os.path.exists(thumb_path):
        try:
            ffmpeg_bin = shutil.which('ffmpeg')
            if not ffmpeg_bin:
                try:
                    import imageio_ffmpeg
                    ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
                except ImportError:
                    pass
            if not ffmpeg_bin:
                log('error', 'ffmpeg not found')
                return None
            subprocess.run([
                ffmpeg_bin, '-i', video_path,
                '-ss', '00:00:00.5',
                '-frames:v', '1',
                '-vf', 'scale=800:-1',
                '-q:v', '5',
                '-update', '1',
                '-y', thumb_path
            ], capture_output=True, timeout=10)
        except Exception as e:
            log('error', f'Thumbnail generation failed for {filename}: {e}')
            return None

    return thumb_path if os.path.exists(thumb_path) else None


@api_bp.route('/api/v2/media/thumb/<filename>')
@jwt_required
def media_thumb(filename):
    """Generate and serve a JPEG thumbnail for a video file using ffmpeg."""
    safe = _secure_filename_preserve(filename)
    if not safe or safe != filename:
        abort(400)

    videos_folder = os.path.abspath(_find_media_folder(filename))
    video_path = os.path.abspath(os.path.join(videos_folder, safe))

    if not video_path.startswith(videos_folder) or not os.path.exists(video_path):
        abort(404)

    thumb_path = _ensure_video_thumbnail(filename)
    if not thumb_path:
        abort(500)

    return send_file(thumb_path, mimetype='image/jpeg')


@api_bp.route('/api/v2/media/static/<filename>')
@jwt_required
def static_media(filename):
    basedir = os.path.abspath(os.path.dirname(__file__))
    # Check uploads/profiles first (user-uploaded), then fall back to static/images (stock)
    profiles_folder = os.path.abspath(os.path.join(basedir, '..', 'uploads', 'profiles'))
    static_folder = os.path.abspath(os.path.join(basedir, '..', 'static', 'images'))
    safe = _secure_filename_preserve(filename)
    if not safe or safe != filename:
        abort(400)
    profile_path = os.path.join(profiles_folder, safe)
    if os.path.exists(profile_path):
        return _safe_send_file(profiles_folder, filename)
    return _safe_send_file(static_folder, filename)


@api_bp.route('/api/v2/media/export/<filename>')
@jwt_required
def export_media(filename):
    basedir = os.path.abspath(os.path.dirname(__file__))
    return _safe_send_file(os.path.join(basedir, '..', 'export'), filename)


@api_bp.route('/api/v2/all-media-urls')
@jwt_required
def all_media_urls():
    urls = get_all_media_urls()
    return jsonify({'status': 'success', 'data': {'urls': urls}})


IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp'}
VIDEO_EXTENSIONS = {'mp4', 'mov', 'avi', 'webm', 'mkv'}
MUSIC_EXTENSIONS = {'mp3'}
ALLOWED_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS | MUSIC_EXTENSIONS
MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024  # 2 GB


def _get_upload_folder(ext):
    """Return the upload folder path based on file extension."""
    basedir = os.path.abspath(os.path.dirname(__file__))
    if ext in VIDEO_EXTENSIONS:
        return os.path.join(basedir, '..', 'uploads', 'videos')
    elif ext in MUSIC_EXTENSIONS:
        return os.path.join(basedir, '..', 'uploads', 'music')
    return os.path.join(basedir, '..', 'uploads', 'images')


def _find_media_folder(filename):
    """Find which upload folder contains the file (with fallback to images/)."""
    safe = _secure_filename_preserve(filename)
    ext = safe.rsplit('.', 1)[-1].lower() if '.' in safe else ''
    basedir = os.path.abspath(os.path.dirname(__file__))
    primary = _get_upload_folder(ext)
    fallback = os.path.join(basedir, '..', 'uploads', 'images')
    if os.path.exists(os.path.join(os.path.abspath(primary), safe)):
        return primary
    if os.path.exists(os.path.join(os.path.abspath(fallback), safe)):
        return fallback
    return primary


@api_bp.route('/api/v2/upload-chunk', methods=['POST'])
@jwt_required
def upload_chunk():
    """Chunked upload endpoint — receives file in small chunks to bypass browser upload limits."""
    try:
        upload_id = request.headers.get('X-Upload-ID', '')
        chunk_index = int(request.headers.get('X-Chunk-Index', 0))
        total_chunks = int(request.headers.get('X-Total-Chunks', 1))
        filename = request.headers.get('X-Filename', '')

        if not upload_id or not filename:
            return jsonify({'status': 'error', 'message': _('No file provided'), 'data': {'error_code': 400}}), 400

        safe_name = secure_filename(filename)
        if not safe_name:
            return jsonify({'status': 'error', 'message': _('Invalid filename'), 'data': {'error_code': 400}}), 400

        ext = safe_name.rsplit('.', 1)[-1].lower() if '.' in safe_name else ''
        if ext not in ALLOWED_EXTENSIONS:
            return jsonify({
                'status': 'error',
                'message': _('File type not allowed. Allowed types: ') + ', '.join(ALLOWED_EXTENSIONS),
                'data': {'error_code': 400}
            }), 400

        basedir = os.path.abspath(os.path.dirname(__file__))
        temp_dir = os.path.join(basedir, '..', 'uploads', 'temp')
        os.makedirs(temp_dir, exist_ok=True)

        temp_path = os.path.join(temp_dir, secure_filename(upload_id))

        with open(temp_path, 'ab') as f:
            while True:
                data = request.stream.read(1024 * 1024)
                if not data:
                    break
                f.write(data)

        # Last chunk: move to final location
        if chunk_index == total_chunks - 1:
            file_size = os.path.getsize(temp_path)
            if file_size > MAX_FILE_SIZE:
                os.remove(temp_path)
                max_mb = MAX_FILE_SIZE // (1024 * 1024)
                return jsonify({
                    'status': 'error',
                    'message': _('File too large. Maximum size: ') + f'{max_mb} MB',
                    'data': {'error_code': 400}
                }), 400

            dest_folder = _get_upload_folder(ext)
            os.makedirs(dest_folder, exist_ok=True)
            final_name = datetime.now().strftime("%Y%m%d") + '-' + safe_name
            final_path = os.path.join(dest_folder, final_name)
            shutil.move(temp_path, final_path)

            return jsonify({
                'status': 'success',
                'message': _('File uploaded successfully'),
                'data': {'filename': final_name}
            })

        return jsonify({'status': 'success', 'data': {'chunk': chunk_index}})

    except Exception as e:
        log('error', f'Error during chunk upload: {e}')
        return jsonify({
            'status': 'error',
            'message': _('An error occurred during file upload'),
            'data': {'error_code': 500, 'error_message': str(e) if app.debug else None}
        }), 500


@api_bp.route('/api/v2/upload', methods=['POST'])
@jwt_required
def upload():
    try:
        static_media_flag = request.form.get('staticMedia', False)
        basedir = os.path.abspath(os.path.dirname(__file__))

        if 'file' not in request.files:
            return jsonify({
                'status': 'error',
                'message': _('No file provided'),
                'data': { 'error_code': 400 }
            }), 400

        file = request.files['file']
        if not file or not file.filename:
            return jsonify({
                'status': 'error',
                'message': _('No file provided'),
                'data': { 'error_code': 400 }
            }), 400

        ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
        if ext not in ALLOWED_EXTENSIONS:
            return jsonify({
                'status': 'error',
                'message': _('File type not allowed. Allowed types: ') + ', '.join(ALLOWED_EXTENSIONS),
                'data': { 'error_code': 400 }
            }), 400

        file.seek(0, 2)
        file_size = file.tell()
        file.seek(0)
        if file_size > MAX_FILE_SIZE:
            max_mb = MAX_FILE_SIZE // (1024 * 1024)
            return jsonify({
                'status': 'error',
                'message': _('File too large. Maximum size: ') + f'{max_mb} MB',
                'data': { 'error_code': 400 }
            }), 400

        filename = datetime.now().strftime("%Y%m%d") + '-' + secure_filename(file.filename)
        if static_media_flag == 'true':
            dest_folder = os.path.join(basedir, '..', 'static', 'images')
        else:
            dest_folder = _get_upload_folder(ext)
        os.makedirs(dest_folder, exist_ok=True)
        file.save(os.path.join(dest_folder, filename))

        return jsonify({
            'status': 'success',
            'message': _('File uploaded successfully'),
            'data': {
                'filename': filename,
            }
        })

    except Exception as e:
        log('error', f'Error during file upload: {e}')
        return jsonify({
            'status': 'error',
            'message': _('An error occurred during file upload'),
            'data': {
                'error_code': 500,
                'error_message': str(e) if app.debug else None
            }
        }), 500


@api_bp.route('/api/v2/items', methods=['POST', 'DELETE'])
@jwt_required
def item():
    if request.method == 'POST':
        try:
            title = request.form.get('title')
            content = request.form.get('content', '')
            content_type = request.form.get('contentType')
            list_type = int(request.form['listType'])

            perm_check = require_list_permission('Create', list_type)
            if perm_check is not None:
                return perm_check
            content_url = request.form.get('contentURL', '')
            created_by_user = g.user_id
            dateCreated = request.form.get('dateCreated', '')

            if dateCreated:
                dateCreated = datetime.strptime(request.form['dateCreated'], "%Y-%m-%d")
            else:
                dateCreated = datetime.utcnow()

            edition = request.form.get('edition', 'all')

            # LQIP + Dimensionen generieren
            lqip, media_w, media_h = None, None, None
            first_url = content_url.split(';')[0].strip() if content_url else ''
            if first_url and content_type in ('image', 'galleryStartWithImage'):
                ext = first_url.rsplit('.', 1)[-1].lower() if '.' in first_url else ''
                img_path = os.path.join(os.path.abspath(_get_upload_folder(ext)), first_url)
                lqip, media_w, media_h = generate_lqip(img_path)
            elif first_url and content_type in ('video', 'video-mov', 'galleryStartWithVideo'):
                thumb_path = _ensure_video_thumbnail(first_url)
                if thumb_path:
                    lqip, media_w, media_h = generate_lqip(thumb_path)

            new_item_id = create_item(title, content, content_type, list_type, content_url, created_by_user, dateCreated, edition=edition, blurPlaceholder=lqip, mediaWidth=media_w, mediaHeight=media_h)

            log('info', f'Item created: ID={new_item_id}, ContentType={content_type}, ListType={list_type}, User={created_by_user}')

            sm_edition = get_setting_by_name('sm_edition').value
            list_type_obj = get_list_type_by_id(list_type)
            list_type_title = list_type_obj.title if list_type_obj else ''
            shared_item_ids = get_shared_item_ids()
            if list_type == 1:
                items = get_items_by_type(list_type, 'desc', edition=sm_edition)
                rendered_items = render_template('layouts/home-items.html', items=items, list_type_title=list_type_title, shared_item_ids=shared_item_ids)
            elif list_type == 2:
                items = get_items_by_type(list_type, 'asc', edition=sm_edition)
                rendered_items = render_template('layouts/timeline-card.html', moments=items, moments_title=list_type_title)
            elif list_type_title == 'Countdown':
                items = get_items_by_type(list_type, 'asc', edition=sm_edition)
                rendered_items = render_template('layouts/countdown-card.html', countdowns=items, countdown_title='Countdown')
            else:
                items = get_items_by_type(list_type, 'desc', edition=sm_edition, checked_last=True)
                rendered_items = render_template('layouts/list-items.html', items=items, mainTitle=list_type_obj.mainTitle, list_type_title=list_type_title)

            return jsonify({
                'status': 'success',
                'message': _('Item created successfully'),
                'data': {
                    'id': new_item_id,
                    'rendered_items': rendered_items
                }
            }), 201

        except Exception as e:
            log('error', f'Error while creating the item: {e}')
            return jsonify({
                'status': 'error',
                'message': _('An error occurred while creating the item.'),
                'data': {
                    'error_code': 500,
                    'error_message': str(e) if app.debug else None
                }
            }), 500

    elif request.method == 'DELETE':
        ids = request.form['ids']
        list_type = int(request.form['listType'])

        perm_check = require_list_permission('Delete', list_type)
        if perm_check is not None:
            return perm_check
        if ids:
            try:
                ids = ids.split(',')
                for id in ids:
                    delete_item(id)

                log('info', f'Items deleted successfully:\nIDs: {ids}')

                sm_edition = get_setting_by_name('sm_edition').value
                list_type_obj = get_list_type_by_id(list_type)
                list_type_title = list_type_obj.title if list_type_obj else ''

                if list_type == 2:
                    items = get_items_by_type(list_type, sort_by='asc', edition=sm_edition)
                    rendered_items = render_template('layouts/timeline-card.html', moments=items, moments_title=list_type_title)
                elif list_type_title == 'Countdown':
                    items = get_items_by_type(list_type, sort_by='asc', edition=sm_edition)
                    rendered_items = render_template('layouts/countdown-card.html', countdowns=items, countdown_title='Countdown')
                else:
                    items = get_items_by_type(list_type, edition=sm_edition)
                    shared_item_ids = get_shared_item_ids()
                    rendered_items = render_template('layouts/home-items.html', items=items, list_type_title=list_type_title, shared_item_ids=shared_item_ids)

                return jsonify({
                    'status': 'success',
                    'message': _('Item(s) deleted successfully'),
                    'data': {
                        'deleted_ids': ids,
                        'rendered_items': rendered_items
                    }
                }), 200

            except Exception as e:
                log('error', f'Error while deleting the items: {e}\nIDs: {ids}')
                return jsonify({
                    'status': 'error',
                    'message': _('An error occurred while deleting the items.'),
                    'data': {
                        'error_code': 500,
                        'error_message': str(e) if app.debug else None
                    }
                }), 500


@api_bp.route('/api/v2/item/<int:id>', methods=['GET', 'PUT'])
@jwt_required
def item_by_id(id):
    if request.method == 'GET':
        try:
            item = get_item_by_id(id)

            perm_check = require_list_permission('Update', item.listType)
            if perm_check is not None:
                return perm_check

            log('debug', f'Item loaded: ID {id}')

            item_list_type = get_list_type_by_id(item.listType)
            renderd_item = render_template('layouts/edit-home-item.html', item=item, list_type_title=item_list_type.title if item_list_type else '')

            return jsonify({
                'status': 'success',
                'message': _('Item(s) loaded successfully'),
                'data': {
                    'id': id,
                    'renderd_item': renderd_item
                }
            }), 200

        except Exception as e:
            log('error', f'Error while loading the item: {e}\nID: {id}')
            return jsonify({
                'status': 'error',
                'message': _('An error occurred while loading the item.'),
                'data': {
                    'error_code': 500,
                    'error_message': str(e) if app.debug else None
                }
            }), 500

    elif request.method == 'PUT':
        try:
            title = request.form.get('title', '')
            content = request.form.get('content', '')
            content_type = request.form.get('contentType', '')
            list_type = int(request.form.get('listType', ''))

            perm_check = require_list_permission('Update', list_type)
            if perm_check is not None:
                return perm_check
            content_url = request.form.get('contentURL', '')
            dateCreated = request.form.get('dateCreated', '')

            if dateCreated:
                dateCreated = datetime.strptime(request.form['dateCreated'], "%Y-%m-%d")

            if not title or content is None or not content_type or not list_type or not content_url:
                item = get_item_by_id(id)
                if not title:
                    title = item.title
                if content is None or (content == '' and 'content' not in request.form):
                    content = item.content
                if not content_type:
                    content_type = item.contentType
                if not list_type:
                    list_type = item.listType
                if not content_url:
                    content_url = item.contentURL
                if not dateCreated:
                    dateCreated = item.dateCreated

                if dateCreated.date() == item.dateCreated.date():
                    dateCreated = item.dateCreated

            edition = request.form.get('edition')

            # LQIP + Dimensionen neu generieren wenn sich das Bild geändert hat
            lqip, media_w, media_h = None, None, None
            first_url = content_url.split(';')[0].strip() if content_url else ''
            if first_url and content_type in ('image', 'galleryStartWithImage'):
                ext = first_url.rsplit('.', 1)[-1].lower() if '.' in first_url else ''
                img_path = os.path.join(os.path.abspath(_get_upload_folder(ext)), first_url)
                lqip, media_w, media_h = generate_lqip(img_path)
            elif first_url and content_type in ('video', 'video-mov', 'galleryStartWithVideo'):
                thumb_path = _ensure_video_thumbnail(first_url)
                if thumb_path:
                    lqip, media_w, media_h = generate_lqip(thumb_path)

            update_item(id, title, content, content_type, content_url, dateCreated, edition=edition, blurPlaceholder=lqip, mediaWidth=media_w, mediaHeight=media_h)

            log('info', f'Item updated: ID={id}, ContentType={content_type}')

            sm_edition = get_setting_by_name('sm_edition').value
            list_type_obj = get_list_type_by_id(list_type)
            list_type_title = list_type_obj.title if list_type_obj else ''

            shared_item_ids = get_shared_item_ids()
            if list_type == 1:
                items = get_items_by_type(list_type, edition=sm_edition)
                rendered_items = render_template('layouts/home-items.html', items=items, list_type_title=list_type_title, shared_item_ids=shared_item_ids)
            elif list_type == 2:
                items = get_items_by_type(list_type, sort_by='asc', edition=sm_edition)
                rendered_items = render_template('layouts/timeline-card.html', moments=items, moments_title=list_type_title)
            elif list_type_title == 'Countdown':
                items = get_items_by_type(list_type, sort_by='asc', edition=sm_edition)
                rendered_items = render_template('layouts/countdown-card.html', countdowns=items, countdown_title='Countdown')
            else:
                items = get_items_by_type(list_type, edition=sm_edition, checked_last=True)
                rendered_items = render_template('layouts/list-items.html', items=items, mainTitle=list_type_obj.mainTitle, list_type_title=list_type_title)

            return jsonify({
                'status': 'success',
                'message': _('Item updated successfully'),
                'data': {
                    'id': id,
                    'rendered_items': rendered_items
                }
            }), 200

        except Exception as e:
            log('error', f'Error while updating the item: {e}\nID: {id}')
            return jsonify({
                'status': 'error',
                'message': _('An error occurred while updating the item.'),
                'data': {
                    'error_code': 500,
                    'error_message': str(e) if app.debug else None
                }
            }), 500


@api_bp.route('/api/v2/list_type/<int:id>', methods=['PUT', 'DELETE'])
@jwt_required
def list_type_by_id(id):
    if request.method == 'PUT':
        if 'Manage Lists' not in g.user_permissions:
            log('warning', f'Permission denied: {g.user_name} tried to update list type {id} (requires "Manage Lists")')
            return jsonify({'status': 'error', 'message': _('Insufficient permissions'), 'data': {'error_code': 403, 'error_message': _('Insufficient permissions')}}), 403
        try:
            title = request.form.get('title', '')
            icon = request.form.get('icon', '')
            contentURL = request.form.get('contentURL', '')
            navbarOrder = request.form.get('navbarOrder', '')
            routeID = request.form.get('routeID', '')
            mainTitle = request.form.get('mainTitle', '')
            navbar = request.form.get('navbar', '')
            edition = request.form.get('edition', '')

            message = _('List type updated successfully')

            if title:
                message = _('List Name updated successfully')

            if icon:
                message = _('List Icon updated successfully')

            if not title or not icon or not contentURL or not navbarOrder or not routeID or not mainTitle or not navbar:
                list_type = get_list_type_by_id(id)
                if not title:
                    title = list_type.title
                if not icon:
                    icon = list_type.icon
                if not contentURL:
                    contentURL = list_type.contentURL
                if not navbarOrder:
                    navbarOrder = list_type.navbarOrder
                if not routeID:
                    routeID = list_type.routeID
                if not mainTitle:
                    mainTitle = list_type.mainTitle
                if not navbar:
                    navbar = list_type.navbar
                if not edition:
                    edition = list_type.edition

            # Check if title changed — rename associated permissions
            old_title = list_type.title if list_type else None
            update_list_type(id, title, icon, contentURL, navbar, navbarOrder, routeID, mainTitle, edition=edition)
            if old_title and title != old_title:
                rename_list_type_permissions(id, title)

            log('info', f'List type updated: ID={id}')

            list_types = get_all_list_types()
            rendered_list_types = render_template('layouts/nav-drawer.html', list_types=list_types, render_after_change=True)

            return jsonify({
                'status': 'success',
                'message': message,
                'data': {
                    'id': id,
                    'rendered_list_types': rendered_list_types
                }
            }), 200

        except Exception as e:
            log('error', f'Error while updating the List type: {e}\nID: {id}')
            return jsonify({
                'status': 'error',
                'message': _('An error occurred while updating the List type.'),
                'data': {
                    'error_code': 500,
                    'error_message': str(e) if app.debug else None
                }
            }), 500

    elif request.method == 'DELETE':
        if 'Manage Lists' not in g.user_permissions:
            log('warning', f'Permission denied: {g.user_name} tried to delete list type {id} (requires "Manage Lists")')
            return jsonify({'status': 'error', 'message': _('Insufficient permissions'), 'data': {'error_code': 403, 'error_message': _('Insufficient permissions')}}), 403
        try:
            delete_permissions_for_list_type(id)
            delete_list_type(id)

            log('info', f'List type deleted: ID={id}')

            list_types = get_all_list_types()
            rendered_list_types = render_template('layouts/nav-drawer.html', list_types=list_types, render_after_put=True)

            return jsonify({
                'status': 'success',
                'message': _('List type deleted successfully'),
                'data': {
                    'id': id,
                    'rendered_list_types': rendered_list_types
                }
            }), 200

        except Exception as e:
            log('error', f'Error while deleting the List type: {e}\nID: {id}')
            return jsonify({
                'status': 'error',
                'message': _('An error occurred while deleting the List type.'),
                'data': {
                    'error_code': 500,
                    'error_message': str(e) if app.debug else None
                }
            }), 500


@api_bp.route('/api/v2/list_type', methods=['POST'])
@jwt_required
@require_permission('Manage Lists')
def list_types():
    try:
        title = request.form.get('title', '')
        icon = request.form.get('icon', '')
        contentURL = request.form.get('contentURL', '')
        navbarOrder = request.form.get('navbarOrder', '')
        routeID = request.form.get('routeID', '')
        mainTitle = request.form.get('mainTitle', '')
        navbar = request.form.get('navbar', '')
        createdByUser = g.user_id

        if navbar == 'true':
            navbar = True

        edition = request.form.get('edition', 'all')
        new_item_id = create_list_type(title, icon, contentURL, createdByUser, navbar, navbarOrder, routeID, mainTitle, edition=edition)
        create_permissions_for_list_type(new_item_id, title)

        log('info', f'List type created: ID={new_item_id}')

        list_types = get_all_list_types()
        rendered_list_types = render_template('layouts/nav-drawer.html', list_types=list_types, render_after_change=True)

        return jsonify({
            'status': 'success',
            'message': _('List type created successfully'),
            'data': {
                'id': new_item_id,
                'rendered_list_types': rendered_list_types
            }
        }), 200

    except Exception as e:
        log('error', f'Error while creating the List type: {e}')
        return jsonify({
            'status': 'error',
            'message': _('An error occurred while creating the List type.'),
            'data': {
                'error_code': 500,
                'error_message': str(e) if app.debug else None
            }
        }), 500


@api_bp.route('/api/v2/translations', methods=['GET', 'POST'])
@jwt_required
@require_permission('Manage Translations')
def translations():
    if request.method == 'GET':
        try:
            supported_languages = get_supported_languages()
            translation_progresses = get_translation_progress()
            rendered_languages = render_template('layouts/available-translations.html', supported_languages=supported_languages, translation_progresses=translation_progresses)

            log('debug', 'Languages loaded successfully')

            return jsonify({
                'status': 'success',
                'message': _('Languages loaded successfully'),
                'data': {
                    'rendered_languages': rendered_languages
                }
            }), 200
        except Exception as e:
            log('error', f'Error while loading the Languages: {e}')
            return jsonify({
                'status': 'error',
                'message': _('An error occurred while loading the Languages.'),
                'data': {
                    'error_code': 500,
                    'error_message': str(e) if app.debug else None
                }
            }), 500

    elif request.method == 'POST':
        try:
            languageCode = request.form.get('languageCode', '')

            if languageCode:
                create_new_language(languageCode)
                log('info', f'Language created successfully:\nLanguage-Code: {languageCode}')

                supported_languages = get_supported_languages()
                translation_progresses = get_translation_progress()
                rendered_languages = render_template('layouts/available-translations.html', supported_languages=supported_languages, translation_progresses=translation_progresses)

            else:
                raise Exception(_('No language code provided'))

            return jsonify({
                'status': 'success',
                'message': _('Language created successfully'),
                'data': {
                    'rendered_languages': rendered_languages
                }
            }), 201

        except Exception as e:
            log('error', f'Error while creating the Language: {e}')
            return jsonify({
                'status': 'error',
                'message': _('An error occurred while creating the Language.'),
                'data': {
                    'error_code': 500,
                    'error_message': str(e) if app.debug else None
                }
            }), 500


@api_bp.route('/api/v2/translations/<languageCode>', methods=['GET'])
@jwt_required
def translations_by_language_read(languageCode):
    """GET translations — available to all authenticated users."""
    return _get_translations(languageCode)


@api_bp.route('/api/v2/translations/<languageCode>', methods=['PUT'])
@jwt_required
@require_permission('Manage Translations')
def translations_by_language_write(languageCode):
    """PUT translations — requires Manage Translations permission."""
    return _update_translation(languageCode)


def _get_translations(languageCode):
        try:
            if languageCode == 'currentLang':
                languageCode = session['lang']

            translations = get_translations_by_language(languageCode)

            translations_dict = [{
                'id': translation.id,
                'entityType': translation.entityType,
                'entityID': translation.entityID,
                'languageCode': translation.languageCode,
                'fieldName': translation.fieldName,
                'translatedText': translation.translatedText,
                'helpText': translation.helpText
            } for translation in translations]

            translations_by_fieldName = {
                translation.fieldName: {
                    'translatedText': translation.translatedText
                }
                for translation in translations
            }

            log('debug', f'Translations loaded for language: {languageCode}')

            rendered_translations = render_template('layouts/translations-for-language.html', translations=translations)

            return jsonify({
                'status': 'success',
                'message': _('Translations loaded successfully'),
                'data': {
                    'rendered_translations': rendered_translations,
                    'translations': translations_dict,
                    'translations_by_fieldName': translations_by_fieldName
                }
            }), 200

        except Exception as e:
            log('error', f'Error while loading the Translations: {e}\nLanguage-Code: {languageCode}')
            return jsonify({
                'status': 'error',
                'message': _('An error occurred while loading the Translations.'),
                'data': {
                    'error_code': 500,
                    'error_message': str(e) if app.debug else None
                }
            }), 500


def _update_translation(languageCode):
    try:
        entityType = request.form.get('entityType', '')
        entityID = request.form.get('entityID', '')
        fieldName = request.form.get('fieldName', '')
        translatedText = request.form.get('translatedText', '')
        helpText = request.form.get('helpText', '')

        translatedText = translatedText.rstrip()

        update_translation(entityType, entityID, languageCode, fieldName, translatedText, helpText)

        log('info', f'Translation updated: {entityType}/{entityID}/{languageCode}/{fieldName}')

        load_translation_in_cache()

        return jsonify({
            'status': 'success',
            'message': _('Translation updated successfully'),
            'data': {
                'entityType': entityType,
                'entityID': entityID,
                'languageCode': languageCode,
                'fieldName': fieldName,
                'translatedText': translatedText
            }
        }), 200

    except Exception as e:
        log('error', f'Error while creating the Translation: {e}')
        return jsonify({
            'status': 'error',
            'message': _('An error occurred while updating the Translation.'),
            'data': {
                'error_code': 500,
                'error_message': str(e) if app.debug else None
            }
        }), 500


@api_bp.route('/api/v2/devtools', methods=['POST'])
@jwt_required
@require_permission('Access Admin Panel')
def devtools():
    try:
        mode = request.form.get('mode', '')

        if mode == "loadNewTranslationsFromCode":
            new_translations = find_unmatched_translations()
            create_new_translations(new_translations)

            log('info', f'New translations loaded successfully')
            return jsonify({
                'status': 'success',
                'message': 'New translations loaded successfully'
            }), 200

        elif mode == "approveNewTranslationsToAllLanguages":
            approve_new_translations_to_all_languages()

            log('info', f'New translations approved successfully')
            return jsonify({
                'status': 'success',
                'message': 'New translations approved successfully'
            }), 200

        elif mode == "resetTranslations":
            migrateTranslations(True)
            load_translation_in_cache()

            log('info', 'Translations reset successfully')
            return jsonify({
                'status': 'success',
                'message': 'Translations reseted successfully'
            }), 200
        else:
            raise Exception('No mode provided')

    except Exception as e:
        log('error', f'Error while loading new translations: {e}')
        return jsonify({
            'status': 'error',
            'message': 'An error occurred while loading new translations.',
            'data': {
                'error_code': 500,
                'error_message': str(e) if app.debug else None
            }
        }), 500


@api_bp.route('/api/v2/export/<mode>', methods=['POST'])
@jwt_required
@require_permission('Access Admin Panel')
def export_route(mode):
    try:
        if mode == 'translations':
            languageCode = request.form.get('languageCode', '')
            type = request.form.get('type', '')
            parameters = {
                'languageCode': languageCode,
                'exportWithDbId': False
            }
            file_name = export_data('translation', type, parameters)
            download_path = f'/api/v2/media/export/{file_name}'

            log('info', f'Translations exported: {languageCode}')
            return jsonify({
                'status': 'success',
                'message': _('Translations exported successfully'),
                'data': {
                    'download_link': download_path
                }
            }), 200

    except Exception as e:
        log('error', f'Error while exporting data: {e}')
        return jsonify({
            'status': 'error',
            'message': _('An error occurred while exporting data.'),
            'data': {
                'error_code': 500,
                'error_message': str(e) if app.debug else None
            }
        }), 500


@api_bp.route('/api/v2/items/<int:id>/share', methods=['POST'])
@jwt_required
@require_permission('Share Items')
def create_share(id):
    try:
        item = get_item_by_id(id)
        if not item:
            return jsonify({'status': 'error', 'message': _('Item not found')}), 404

        expires_at = request.form.get('expiresAt')
        password = request.form.get('password')

        if expires_at:
            expires_at = datetime.strptime(expires_at, '%Y-%m-%dT%H:%M')
            if expires_at < datetime.utcnow():
                return jsonify({
                    'status': 'error',
                    'message': _('Expiration date must be in the future')
                }), 400

        share_data = create_item_share(id, g.user_id, expires_at=expires_at, password=password if password else None)

        log('info', f'Share created for item {id} by user {g.user_id}, token: {share_data["token"]}')

        return jsonify({
            'status': 'success',
            'message': _('Share link created successfully'),
            'data': {
                'token': share_data['token'],
                'url': f'/s/{share_data["token"]}',
                'expiresAt': share_data['expiresAt'],
                'hasPassword': share_data['hasPassword']
            }
        }), 201

    except Exception as e:
        log('error', f'Error while creating share for item {id}: {e}')
        return jsonify({
            'status': 'error',
            'message': _('An error occurred while creating the share link.'),
            'data': {
                'error_code': 500,
                'error_message': str(e) if app.debug else None
            }
        }), 500


@api_bp.route('/api/v2/items/<int:id>/shares', methods=['GET'])
@jwt_required
@require_permission('Share Items')
def list_shares(id):
    try:
        shares = get_shares_for_item(id)
        return jsonify({
            'status': 'success',
            'message': _('Shares loaded successfully'),
            'data': {
                'shares': shares
            }
        }), 200

    except Exception as e:
        log('error', f'Error while loading shares for item {id}: {e}')
        return jsonify({
            'status': 'error',
            'message': _('An error occurred while loading shares.'),
            'data': {
                'error_code': 500,
                'error_message': str(e) if app.debug else None
            }
        }), 500


@api_bp.route('/api/v2/items/<int:id>/share/<int:share_id>', methods=['DELETE'])
@jwt_required
@require_permission('Share Items')
def delete_share(id, share_id):
    try:
        deactivate_share(share_id, g.user_id)

        log('info', f'Share {share_id} deactivated for item {id} by user {g.user_id}')

        return jsonify({
            'status': 'success',
            'message': _('Share link revoked successfully')
        }), 200

    except Exception as e:
        log('error', f'Error while revoking share {share_id} for item {id}: {e}')
        return jsonify({
            'status': 'error',
            'message': _('An error occurred while revoking the share link.'),
            'data': {
                'error_code': 500,
                'error_message': str(e) if app.debug else None
            }
        }), 500


# ==================== Reminders API ====================

@api_bp.route('/api/v2/reminders', methods=['GET'])
@jwt_required
@require_permission('View Reminders')
def list_reminders():
    try:
        reminders = get_all_reminders()
        muted_ids = get_user_muted_reminder_ids(g.user_id)
        data = []
        for r in reminders:
            data.append({
                'id': r.id,
                'title': r.title,
                'description': r.description,
                'reminder_type': r.reminder_type,
                'month': r.month,
                'day': r.day,
                'target_date': r.target_date.isoformat() if r.target_date else None,
                'milestone_days': r.milestone_days,
                'countdown_id': r.countdown_id,
                'notify_days_before': r.notify_days_before,
                'is_global': r.is_global,
                'is_auto': r.is_auto,
                'auto_source': r.auto_source,
                'created_by': r.created_by,
                'active': r.active,
                'muted': r.id in muted_ids,
            })
        return jsonify({'status': 'success', 'data': {'reminders': data}}), 200
    except Exception as e:
        log('error', f'Error loading reminders: {e}')
        return jsonify({'status': 'error', 'message': _('An error occurred while loading reminders.'),
                        'data': {'error_code': 500, 'error_message': str(e) if app.debug else None}}), 500


@api_bp.route('/api/v2/reminders', methods=['POST'])
@jwt_required
@require_permission('Create Reminder')
def create_reminder_endpoint():
    try:
        data = request.get_json() if request.is_json else request.form
        title = data.get('title', '')
        description = data.get('description', '')
        reminder_type = data.get('reminder_type', '')
        notify_days_before = data.get('notify_days_before', '0')
        target_date_str = data.get('target_date')

        # Parse optional int fields
        month = data.get('month')
        day = data.get('day')
        milestone_days = data.get('milestone_days')
        countdown_id = data.get('countdown_id')
        month = int(month) if month is not None and str(month).strip() else None
        day = int(day) if day is not None and str(day).strip() else None
        milestone_days = int(milestone_days) if milestone_days is not None and str(milestone_days).strip() else None
        countdown_id = int(countdown_id) if countdown_id is not None and str(countdown_id).strip() else None

        parsed_target = None
        if target_date_str:
            parsed_target = datetime.strptime(target_date_str, '%Y-%m-%d').date()

        if not title or not reminder_type:
            return jsonify({'status': 'error', 'message': _('Title and type are required')}), 400

        new_id = db_create_reminder(
            title=title, description=description, reminder_type=reminder_type,
            created_by=g.user_id, month=month, day=day,
            target_date=parsed_target, milestone_days=milestone_days,
            countdown_id=countdown_id, notify_days_before=notify_days_before
        )
        log('info', f'Reminder created: ID={new_id} by user {g.user_id}')
        return jsonify({'status': 'success', 'message': _('Reminder created successfully'), 'data': {'id': new_id}}), 201
    except Exception as e:
        log('error', f'Error creating reminder: {e}')
        return jsonify({'status': 'error', 'message': _('An error occurred while creating the reminder.'),
                        'data': {'error_code': 500, 'error_message': str(e) if app.debug else None}}), 500


@api_bp.route('/api/v2/reminders/<int:id>', methods=['PUT'])
@jwt_required
@require_permission('Update Reminder')
def update_reminder_endpoint(id):
    try:
        data = request.get_json() if request.is_json else request.form
        kwargs = {}
        for field in ('title', 'description', 'reminder_type', 'notify_days_before'):
            val = data.get(field)
            if val is not None:
                kwargs[field] = val
        for int_field in ('month', 'day', 'milestone_days', 'countdown_id'):
            val = data.get(int_field)
            if val is not None and str(val).strip():
                kwargs[int_field] = int(val)
        target_date = data.get('target_date')
        if target_date:
            kwargs['target_date'] = datetime.strptime(target_date, '%Y-%m-%d').date()

        db_update_reminder(id, **kwargs)
        log('info', f'Reminder updated: ID={id}')
        return jsonify({'status': 'success', 'message': _('Reminder updated successfully')}), 200
    except Exception as e:
        log('error', f'Error updating reminder {id}: {e}')
        return jsonify({'status': 'error', 'message': _('An error occurred while updating the reminder.'),
                        'data': {'error_code': 500, 'error_message': str(e) if app.debug else None}}), 500


@api_bp.route('/api/v2/reminders/<int:id>', methods=['DELETE'])
@jwt_required
@require_permission('Delete Reminder')
def delete_reminder_endpoint(id):
    try:
        db_delete_reminder(id)
        log('info', f'Reminder deleted: ID={id}')
        return jsonify({'status': 'success', 'message': _('Reminder deleted successfully')}), 200
    except Exception as e:
        log('error', f'Error deleting reminder {id}: {e}')
        return jsonify({'status': 'error', 'message': _('An error occurred while deleting the reminder.'),
                        'data': {'error_code': 500, 'error_message': str(e) if app.debug else None}}), 500


@api_bp.route('/api/v2/reminders/<int:id>/mute', methods=['POST'])
@jwt_required
def mute_reminder_endpoint(id):
    try:
        mute_reminder(g.user_id, id)
        return jsonify({'status': 'success', 'message': _('Reminder muted')}), 200
    except Exception as e:
        log('error', f'Error muting reminder {id}: {e}')
        return jsonify({'status': 'error', 'message': _('An error occurred while muting the reminder.')}), 500


@api_bp.route('/api/v2/reminders/<int:id>/mute', methods=['DELETE'])
@jwt_required
def unmute_reminder_endpoint(id):
    try:
        unmute_reminder(g.user_id, id)
        return jsonify({'status': 'success', 'message': _('Reminder unmuted')}), 200
    except Exception as e:
        log('error', f'Error unmuting reminder {id}: {e}')
        return jsonify({'status': 'error', 'message': _('An error occurred while unmuting the reminder.')}), 500


# ==================== Push Subscription API ====================

@api_bp.route('/api/v2/push/subscribe', methods=['POST'])
@jwt_required
def push_subscribe():
    try:
        data = request.get_json() if request.is_json else {}
        endpoint = data.get('endpoint', '')
        keys = data.get('keys', {})
        p256dh = keys.get('p256dh', '')
        auth = keys.get('auth', '')
        if not endpoint or not p256dh or not auth:
            return jsonify({'status': 'error', 'message': 'Invalid subscription data'}), 400
        save_push_subscription(g.user_id, endpoint, p256dh, auth)
        return jsonify({'status': 'success', 'message': 'Subscription saved'}), 200
    except Exception as e:
        log('error', f'Error saving push subscription: {e}')
        return jsonify({'status': 'error', 'message': str(e)}), 500


@api_bp.route('/api/v2/push/subscribe', methods=['DELETE'])
@jwt_required
def push_unsubscribe():
    try:
        data = request.get_json() if request.is_json else {}
        endpoint = data.get('endpoint', '')
        if endpoint:
            delete_push_subscription(endpoint)
        return jsonify({'status': 'success', 'message': 'Subscription removed'}), 200
    except Exception as e:
        log('error', f'Error removing push subscription: {e}')
        return jsonify({'status': 'error', 'message': str(e)}), 500


@api_bp.route('/api/v2/push/vapid-key', methods=['GET'])
@jwt_required
def get_vapid_key():
    try:
        from app.notifications import get_vapid_public_key
        key = get_vapid_public_key()
        if not key:
            return jsonify({'status': 'error', 'message': 'VAPID key not available'}), 503
        return jsonify({'status': 'success', 'data': {'publicKey': key}}), 200
    except Exception as e:
        log('error', f'Error getting VAPID key: {e}')
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ==================== Passkeys API ====================

@api_bp.route('/api/v2/passkeys', methods=['GET'])
@jwt_required
def list_passkeys():
    try:
        passkeys = get_passkeys_by_user(g.user_id)
        data = [{
            'id': p.id,
            'name': p.name,
            'dateCreated': p.dateCreated.strftime('%d.%m.%Y') if p.dateCreated else None
        } for p in passkeys]
        return jsonify({'status': 'success', 'data': {'passkeys': data}}), 200
    except Exception as e:
        log('error', f'Error loading passkeys: {e}')
        return jsonify({'status': 'error', 'message': _('An error occurred while loading passkeys.')}), 500


@api_bp.route('/api/v2/passkeys', methods=['POST'])
@jwt_required
def create_passkey_endpoint():
    try:
        data = request.get_json() if request.is_json else request.form
        name = data.get('name', '').strip()
        if not name:
            return jsonify({'status': 'error', 'message': _('Name is required')}), 400

        email = session.get('email')
        webauth_data = session.get('webauth_data', {})
        user_data = webauth_data.get(email, {})

        credential_id = user_data.get('credential_id')
        public_key = user_data.get('public_key')
        sign_count = user_data.get('sign_count', 0)

        if not credential_id or not public_key:
            return jsonify({'status': 'error', 'message': _('No passkey registration data found. Please register a passkey first.')}), 400

        new_id = db_create_passkey(g.user_id, name, credential_id, public_key, sign_count)

        # Clear session data after saving
        if email in webauth_data:
            del webauth_data[email]
            session['webauth_data'] = webauth_data

        log('info', f'Passkey created: ID={new_id} for user {g.user_id}')
        return jsonify({'status': 'success', 'message': _('Passkey created successfully'), 'data': {'id': new_id}}), 201
    except Exception as e:
        log('error', f'Error creating passkey: {e}')
        return jsonify({'status': 'error', 'message': _('An error occurred while creating the passkey.'),
                        'data': {'error_code': 500, 'error_message': str(e) if app.debug else None}}), 500


@api_bp.route('/api/v2/passkeys/<int:id>', methods=['PUT'])
@jwt_required
def update_passkey_endpoint(id):
    try:
        data = request.get_json() if request.is_json else request.form
        name = data.get('name', '').strip()
        if not name:
            return jsonify({'status': 'error', 'message': _('Name is required')}), 400

        success = db_rename_passkey(id, g.user_id, name)
        if success:
            log('info', f'Passkey renamed: ID={id}')
            return jsonify({'status': 'success', 'message': _('Passkey renamed successfully')}), 200
        else:
            return jsonify({'status': 'error', 'message': _('Passkey not found')}), 404
    except Exception as e:
        log('error', f'Error renaming passkey {id}: {e}')
        return jsonify({'status': 'error', 'message': _('An error occurred while renaming the passkey.'),
                        'data': {'error_code': 500, 'error_message': str(e) if app.debug else None}}), 500


@api_bp.route('/api/v2/passkeys/<int:id>', methods=['DELETE'])
@jwt_required
def delete_passkey_endpoint(id):
    try:
        # Check if this is the last passkey and user has no password
        passkeys = get_passkeys_by_user(g.user_id)
        user = get_user_by_id(g.user_id)

        if len(passkeys) <= 1 and (not user.passwordHash or user.passwordHash == ''):
            return jsonify({'status': 'error', 'message': _('Cannot delete the last passkey when no password is set.')}), 400

        success = db_delete_passkey(id, g.user_id)
        if success:
            log('info', f'Passkey deleted: ID={id} by user {g.user_id}')
            return jsonify({'status': 'success', 'message': _('Passkey deleted successfully')}), 200
        else:
            return jsonify({'status': 'error', 'message': _('Passkey not found')}), 404
    except Exception as e:
        log('error', f'Error deleting passkey {id}: {e}')
        return jsonify({'status': 'error', 'message': _('An error occurred while deleting the passkey.'),
                        'data': {'error_code': 500, 'error_message': str(e) if app.debug else None}}), 500


# ==================== Notification Test API ====================

@api_bp.route('/api/v2/notifications/test', methods=['POST'])
@jwt_required
def test_notification():
    try:
        from app.notifications import send_notification, send_push_notification, send_email_notification, send_telegram_notification
        data = request.get_json() if request.is_json else request.form
        channel = data.get('channel', 'push')

        if channel == 'push':
            from app.db_queries import get_push_subscriptions_for_user
            subs = get_push_subscriptions_for_user(g.user_id)
            if not subs:
                return jsonify({'status': 'error', 'message': _('No push subscription found. Please allow notifications first.')}), 400
            result = send_push_notification(g.user_id, 'SharedMoments Test', _('This is a test notification!'))
        elif channel == 'email':
            user = get_user_by_id(g.user_id)
            if not user or not user.email:
                return jsonify({'status': 'error', 'message': _('No email address in your profile')}), 400
            if not os.environ.get('SMTP_HOST'):
                return jsonify({'status': 'error', 'message': _('SMTP server not configured')}), 400
            result = send_email_notification(user.email, 'SharedMoments Test', _('This is a test notification!'))
        elif channel == 'telegram':
            chat_id_setting = get_user_setting(g.user_id, 'notification_telegram_chat_id')
            if not chat_id_setting or not chat_id_setting.value:
                return jsonify({'status': 'error', 'message': _('No Telegram Chat-ID configured')}), 400
            if not os.environ.get('TELEGRAM_BOT_TOKEN'):
                return jsonify({'status': 'error', 'message': _('Telegram bot not configured')}), 400
            result = send_telegram_notification(chat_id_setting.value, '<b>SharedMoments Test</b>\n' + _('This is a test notification!'))
        else:
            return jsonify({'status': 'error', 'message': 'Unknown channel'}), 400

        if result:
            return jsonify({'status': 'success', 'message': _('Test notification sent!')}), 200
        else:
            return jsonify({'status': 'error', 'message': _('Failed to send test notification. Check configuration.')}), 500
    except Exception as e:
        log('error', f'Error sending test notification: {e}')
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ==================== Migration API ====================

@api_bp.route('/api/v2/migration/status', methods=['GET'])
def migration_status():
    """Return current migration status for progress polling."""
    try:
        from app.migration.status import load_status
        status = load_status()
    except ImportError:
        return jsonify({'steps': None, 'message': 'Migration module not available'}), 200

    if status is None:
        return jsonify({'steps': None, 'message': 'No migration running'}), 200

    # If real migration is complete, tell the client to redirect
    if status.get('completed_at') and not status.get('dry_run', False):
        return jsonify({'redirect': '/migration-complete'}), 200

    return jsonify({
        'steps': status.get('steps', {}),
        'started_at': status.get('started_at'),
        'completed_at': status.get('completed_at'),
        'dry_run': status.get('dry_run', False),
        'error': status.get('error'),
    }), 200


@api_bp.route('/api/v2/migration/update-user', methods=['POST'])
def migration_update_user():
    """Update a migrated user's email and password during migration review."""
    db_session = SessionLocal()
    try:
        review_setting = db_session.query(Setting).filter(Setting.name == 'migration_review_complete').first()
        if not review_setting or review_setting.value != 'False':
            return jsonify({'status': 'error', 'message': 'Migration review is not active'}), 403

        user_id = request.form.get('user_id', type=int)
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()

        if not user_id or not email:
            return jsonify({'status': 'error', 'message': 'User ID and email are required'}), 400

        if email.endswith('@placeholder.local'):
            return jsonify({'status': 'error', 'message': 'Please use a real email address'}), 400

        user = db_session.query(User).filter(User.id == user_id).first()
        if not user:
            return jsonify({'status': 'error', 'message': 'User not found'}), 404

        existing = db_session.query(User).filter(User.email == email, User.id != user_id).first()
        if existing:
            return jsonify({'status': 'error', 'message': 'Email already in use'}), 400

        user.email = email
        if password:
            user.hash_password(password)

        first_name = request.form.get('firstName', '').strip()
        last_name = request.form.get('lastName', '').strip()
        if first_name:
            user.firstName = first_name
        if last_name is not None and request.form.get('lastName') is not None:
            user.lastName = last_name

        # Update role if provided
        role_name = request.form.get('role', '').strip()
        if role_name:
            role = db_session.query(Role).filter(Role.roleName == role_name).first()
            if role:
                user_role = db_session.query(UserRole).filter(UserRole.userID == user_id).first()
                if user_role:
                    user_role.roleID = role.id
                else:
                    db_session.add(UserRole(userID=user_id, roleID=role.id))

        db_session.commit()
        return jsonify({'status': 'success', 'message': 'User updated'}), 200
    except Exception as e:
        log('error', f'[Migration] Error updating user: {e}')
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        db_session.close()


@api_bp.route('/api/v2/migration/set-language', methods=['POST'])
def migration_set_language():
    """Set the language for all migrated users."""
    db_session = SessionLocal()
    try:
        review_setting = db_session.query(Setting).filter(Setting.name == 'migration_review_complete').first()
        if not review_setting or review_setting.value != 'False':
            return jsonify({'status': 'error', 'message': 'Migration review is not active'}), 403

        language = request.form.get('language', 'en-US').strip()
        users = db_session.query(User).filter(User.id > 1).all()
        for user in users:
            lang_setting = db_session.query(UserSetting).filter(
                UserSetting.userID == user.id, UserSetting.name == 'language'
            ).first()
            if lang_setting:
                lang_setting.value = language
            else:
                db_session.add(UserSetting(userID=user.id, name='language', value=language, icon='language', edition='all', category='about', type='text'))

        # Set app-wide language
        os.environ['LANG'] = language

        db_session.commit()
        return jsonify({'status': 'success', 'message': f'Language set to {language} for {len(users)} users'}), 200
    except Exception as e:
        log('error', f'[Migration] Error setting language: {e}')
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        db_session.close()


@api_bp.route('/api/v2/migration/complete', methods=['POST'])
def migration_review_complete():
    """Mark migration review as complete. Only works when no placeholder emails remain."""
    db_session = SessionLocal()
    try:
        review_setting = db_session.query(Setting).filter(Setting.name == 'migration_review_complete').first()
        if not review_setting or review_setting.value != 'False':
            return jsonify({'status': 'error', 'message': 'Migration review is not active'}), 403

        placeholder_users = db_session.query(User).filter(
            User.id > 1, User.email.endswith('@placeholder.local')
        ).count()
        if placeholder_users > 0:
            return jsonify({'status': 'error', 'message': f'{placeholder_users} user(s) still have placeholder emails'}), 400

        # Validate at least one Admin exists
        admin_role = db_session.query(Role).filter(Role.roleName == 'Admin').first()
        if admin_role:
            admin_count = db_session.query(UserRole).filter(
                UserRole.roleID == admin_role.id,
                UserRole.userID > 1
            ).count()
            if admin_count == 0:
                return jsonify({'status': 'error', 'message': 'At least one user must have the Admin role'}), 400

        # Ensure all migrated users have required UserSettings
        users = db_session.query(User).filter(User.id > 1).all()
        for user in users:
            for setting_name, default_value, icon in [
                ('darkmode', 'FALSE', 'dark_mode'),
                ('language', os.environ.get('LANG', 'en-US'), 'language'),
            ]:
                existing = db_session.query(UserSetting).filter(
                    UserSetting.userID == user.id, UserSetting.name == setting_name
                ).first()
                if not existing:
                    db_session.add(UserSetting(
                        userID=user.id, name=setting_name, value=default_value,
                        icon=icon, edition='all', category='about', type='text'
                    ))

        review_setting.value = 'True'
        db_session.commit()

        # Clear session and JWT cookie so user must log in fresh
        session.clear()
        response = jsonify({'status': 'success', 'message': 'Migration review complete'})
        response.delete_cookie('jwt_token')
        return response, 200
    except Exception as e:
        log('error', f'[Migration] Error completing review: {e}')
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        db_session.close()


# ==================== Data Export/Import API ====================

@api_bp.route('/api/v2/data/export', methods=['POST'])
@jwt_required
@require_permission('Access Admin Panel')
def data_export():
    try:
        export_id = str(uuid.uuid4())
        _write_job('export-' + export_id, {'progress': 0, 'status': 'starting', 'filename': None, 'error': None})
        app_ref = app._get_current_object()
        t = threading.Thread(target=_run_export, args=(export_id, g.user_id, app_ref), daemon=True)
        t.start()
        return jsonify({'status': 'success', 'data': {'export_id': export_id}}), 202
    except Exception as e:
        log('error', f'Error starting export: {e}')
        return jsonify({'status': 'error', 'message': str(e)}), 500


@api_bp.route('/api/v2/data/export/status/<export_id>', methods=['GET'])
def data_export_status(export_id):
    # No JWT/DB needed — reads only from JSON file, UUID is unguessable
    job = _read_job('export-' + export_id)
    if not job:
        return jsonify({'status': 'error', 'message': 'Export not found'}), 404
    return jsonify({
        'status': 'success',
        'data': {
            'progress': job['progress'],
            'export_status': job['status'],
            'filename': job['filename'],
            'error': job['error']
        }
    }), 200


@api_bp.route('/api/v2/data/import-chunk', methods=['POST'])
@jwt_required
@require_permission('Access Admin Panel')
def data_import_chunk():
    return _handle_import_chunk(g.user_id, is_setup=False)


@api_bp.route('/api/v2/setup/import-chunk', methods=['POST'])
@jwt_required
def setup_import_chunk():
    setup_setting = get_setting_by_name('setup_complete')
    if setup_setting and setup_setting.value == 'True':
        return jsonify({'status': 'error', 'message': 'Setup already completed'}), 403
    return _handle_import_chunk(g.user_id, is_setup=True)


@api_bp.route('/api/v2/data/import/status/<import_id>', methods=['GET'])
def data_import_status(import_id):
    # No JWT/DB needed — reads only from JSON file, UUID is unguessable
    job = _read_job('import-' + import_id)
    if not job:
        return jsonify({'status': 'error', 'message': 'Import not found'}), 404
    return jsonify({
        'status': 'success',
        'data': {
            'import_status': job['status'],
            'progress': job['progress'],
            'phase': job['phase'],
            'result': job.get('result'),
            'error': job.get('error')
        }
    })


def _handle_import_chunk(user_id, is_setup=False):
    try:
        upload_id = request.headers.get('X-Upload-ID', '')
        chunk_index = int(request.headers.get('X-Chunk-Index', 0))
        total_chunks = int(request.headers.get('X-Total-Chunks', 1))

        if not upload_id:
            return jsonify({'status': 'error', 'message': _('No file provided'), 'data': {'error_code': 400}}), 400

        basedir = os.path.abspath(os.path.dirname(__file__))
        temp_dir = os.path.join(basedir, '..', 'uploads', 'temp')
        os.makedirs(temp_dir, exist_ok=True)

        temp_path = os.path.join(temp_dir, secure_filename(upload_id))

        with open(temp_path, 'ab') as f:
            while True:
                data = request.stream.read(1024 * 1024)
                if not data:
                    break
                f.write(data)

        # Not the last chunk yet — acknowledge and wait for more
        if chunk_index < total_chunks - 1:
            return jsonify({'status': 'success', 'data': {'chunk': chunk_index}})

        # Last chunk — start async processing
        import_id = str(uuid.uuid4())
        _write_job('import-' + import_id, {'progress': 0, 'status': 'starting', 'phase': 'extracting', 'result': None, 'error': None})
        app_ref = app._get_current_object()
        t = threading.Thread(target=_run_import, args=(import_id, temp_path, user_id, app_ref, is_setup), daemon=True)
        t.start()

        return jsonify({'status': 'success', 'data': {'import_id': import_id}}), 202

    except Exception as e:
        log('error', f'Error during import chunk: {e}')
        return jsonify({
            'status': 'error',
            'message': _('An error occurred during import.'),
            'data': {'error_code': 500, 'error_message': str(e) if app.debug else None}
        }), 500


def _run_import(import_id, zip_path, user_id, app_ref, is_setup=False):
    with app_ref.app_context():
        job = _FileJob('import-' + import_id, {'progress': 0, 'status': 'running', 'phase': 'extracting', 'result': None, 'error': None})
        basedir = os.path.abspath(os.path.dirname(__file__))
        tmp_dir = tempfile.mkdtemp()

        try:
            # Phase 1: Extract ZIP (0-30%)
            job['phase'] = 'extracting'
            job['progress'] = 0
            extract_dir = os.path.join(tmp_dir, 'extract')
            try:
                with zipfile.ZipFile(zip_path, 'r') as zf:
                    members = zf.namelist()
                    for member in members:
                        member_path = os.path.realpath(os.path.join(extract_dir, member))
                        if not member_path.startswith(os.path.realpath(extract_dir)):
                            job['status'] = 'error'
                            job['error'] = 'Invalid ZIP: path traversal detected'
                            return
                    total_members = len(members)
                    for i, member in enumerate(members):
                        zf.extract(member, extract_dir)
                        job['progress'] = int((i + 1) / total_members * 30)
            except zipfile.BadZipFile:
                job['status'] = 'error'
                job['error'] = _('Invalid or corrupted ZIP file')
                return

            data_json_path = os.path.join(extract_dir, 'data.json')
            if not os.path.exists(data_json_path):
                # Search in subdirectories (e.g. ZIP created with wrapper folder)
                for root, dirs, files in os.walk(extract_dir):
                    if 'data.json' in files:
                        data_json_path = os.path.join(root, 'data.json')
                        extract_dir = root
                        break
                else:
                    job['status'] = 'error'
                    job['error'] = 'Invalid ZIP: data.json not found'
                    return

            with open(data_json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if 'items' not in data or 'listTypes' not in data:
                job['status'] = 'error'
                job['error'] = 'Invalid ZIP: missing items or listTypes in data.json'
                return

            export_version = data.get('version', '')
            if export_version and not export_version.startswith(f'{VERSION_MAJOR}.'):
                job['status'] = 'error'
                job['error'] = f'Incompatible export version: {export_version}. Only v{VERSION_MAJOR}.x exports are supported.'
                return

            # Phase 2: Import data (30-60%)
            job['phase'] = 'importing'
            job['progress'] = 30

            PROTECTED_SETTINGS = {'sm_version', 'setup_complete', 'migration_review_complete'}
            settings_updated = 0
            db_session = SessionLocal()
            try:
                for s_data in data.get('settings', []):
                    s_name = s_data.get('name', '')
                    if s_name in PROTECTED_SETTINGS or not s_name:
                        continue
                    existing = db_session.query(Setting).filter(Setting.name == s_name).first()
                    if existing:
                        existing.value = s_data.get('value', existing.value)
                        existing.icon = s_data.get('icon', existing.icon)
                        existing.edition = s_data.get('edition', existing.edition)
                        existing.category = s_data.get('category', existing.category)
                        existing.type = s_data.get('type', existing.type)
                    else:
                        db_session.add(Setting(
                            name=s_name,
                            value=s_data.get('value'),
                            icon=s_data.get('icon'),
                            edition=s_data.get('edition'),
                            category=s_data.get('category'),
                            type=s_data.get('type')
                        ))
                    settings_updated += 1
                db_session.commit()
            finally:
                db_session.close()

            # ── Wipe existing data and re-import everything ──
            from datetime import date as date_type
            wipe_session = SessionLocal()
            try:
                wipe_session.query(ReminderMute).delete()
                wipe_session.query(Reminder).delete()
                wipe_session.query(UserSetting).delete()
                wipe_session.query(UserRole).delete()
                wipe_session.query(Item).delete()
                wipe_session.commit()
            finally:
                wipe_session.close()

            # Import users (update existing by email, create new)
            users_imported = 0
            user_email_to_id = {}
            user_session = SessionLocal()
            try:
                for u_data in data.get('users', []):
                    try:
                        email = u_data.get('email', '')
                        if not email:
                            continue
                        birth_date = None
                        if u_data.get('birthDate'):
                            birth_date = date_type.fromisoformat(u_data['birthDate'])
                        existing_user = user_session.query(User).filter(User.email == email).first()
                        if existing_user:
                            existing_user.firstName = u_data.get('firstName', existing_user.firstName)
                            existing_user.lastName = u_data.get('lastName', existing_user.lastName)
                            existing_user.birthDate = birth_date or existing_user.birthDate
                            existing_user.profilePicture = u_data.get('profilePicture', existing_user.profilePicture)
                            existing_user.passwordHash = u_data.get('passwordHash', existing_user.passwordHash)
                            existing_user.passwordSalt = u_data.get('passwordSalt', existing_user.passwordSalt)
                            user_email_to_id[email] = existing_user.id
                        else:
                            new_user = User(
                                firstName=u_data.get('firstName', ''),
                                lastName=u_data.get('lastName', ''),
                                email=email,
                                birthDate=birth_date,
                                profilePicture=u_data.get('profilePicture', 'profile-placeholder.jpg'),
                                passwordHash=str(u_data.get('passwordHash', '')),
                                passwordSalt=u_data.get('passwordSalt', '')
                            )
                            user_session.add(new_user)
                            user_session.flush()
                            user_email_to_id[email] = new_user.id
                        users_imported += 1
                    except Exception as e:
                        log('error', f'Error importing user: {e}')
                user_session.commit()
            finally:
                user_session.close()

            # Assign roles
            for u_data in data.get('users', []):
                email = u_data.get('email', '')
                uid = user_email_to_id.get(email)
                if not uid:
                    continue
                for role_name in u_data.get('roles', []):
                    if not role_name:
                        continue
                    try:
                        role_id = get_role_by_name(role_name)
                        if role_id:
                            create_user_role(uid, role_id)
                    except Exception:
                        pass

            # Import user settings
            user_settings_imported = 0
            us_session = SessionLocal()
            try:
                for us_data in data.get('userSettings', []):
                    try:
                        email = us_data.get('userEmail', '')
                        uid = user_email_to_id.get(email)
                        if not uid or not us_data.get('name'):
                            continue
                        us_session.add(UserSetting(
                            userID=uid,
                            name=us_data['name'],
                            value=us_data.get('value', ''),
                            icon=us_data.get('icon'),
                            edition=us_data.get('edition'),
                            category=us_data.get('category'),
                            type=us_data.get('type')
                        ))
                        user_settings_imported += 1
                    except Exception as e:
                        log('error', f'Error importing user setting: {e}')
                us_session.commit()
            finally:
                us_session.close()

            # Import reminders
            reminders_imported = 0
            for r_data in data.get('reminders', []):
                try:
                    target_date = None
                    if r_data.get('target_date'):
                        target_date = date_type.fromisoformat(r_data['target_date'])
                    db_create_reminder(
                        title=r_data.get('title', ''),
                        description=r_data.get('description', ''),
                        reminder_type=r_data.get('reminder_type', ''),
                        created_by=user_id,
                        month=r_data.get('month'),
                        day=r_data.get('day'),
                        target_date=target_date,
                        milestone_days=r_data.get('milestone_days'),
                        countdown_id=r_data.get('countdown_id'),
                        notify_days_before=r_data.get('notify_days_before', '0'),
                        is_global=r_data.get('is_global', True),
                        is_auto=r_data.get('is_auto', False),
                        auto_source=r_data.get('auto_source')
                    )
                    reminders_imported += 1
                except Exception as e:
                    log('error', f'Error importing reminder: {e}')

            # Import list types
            local_list_types = get_all_list_types()
            lt_map = {}
            for lt_data in data.get('listTypes', []):
                title = lt_data['title']
                local_lt = None
                for llt in local_list_types:
                    if llt.title == title:
                        local_lt = llt
                        break
                if local_lt:
                    lt_map[title] = local_lt.id
                else:
                    new_id = create_list_type(
                        title=title,
                        icon=lt_data.get('icon', 'list'),
                        contentURL=lt_data.get('contentURL', title.lower()),
                        createdByUser=user_id,
                        navbar=lt_data.get('navbar', True),
                        navbarOrder=lt_data.get('navbarOrder', 99),
                        routeID=lt_data.get('routeID', 0),
                        mainTitle=lt_data.get('mainTitle', title)
                    )
                    create_permissions_for_list_type(new_id, title)
                    lt_map[title] = new_id

            # Import items
            imported = 0
            skipped_duplicate = 0
            skipped_error = 0
            items_list = data.get('items', [])
            total_items = len(items_list)

            for idx, item_data in enumerate(items_list):
                try:
                    lt_info = item_data.get('listType', {})
                    lt_title = lt_info.get('title', '')
                    list_type_id = lt_map.get(lt_title)
                    if not list_type_id:
                        skipped_error += 1
                        continue

                    date_created_str = item_data.get('dateCreated', '')
                    date_created = datetime.fromisoformat(date_created_str) if date_created_str else datetime.utcnow()

                    creator_email = item_data.get('creatorEmail', '')
                    item_owner = user_email_to_id.get(creator_email, user_id) if creator_email else user_id

                    create_item(
                        title=item_data.get('title', ''),
                        content=item_data.get('content', ''),
                        contentType=item_data.get('contentType', ''),
                        listType=list_type_id,
                        contentURL=item_data.get('contentURL', ''),
                        createdByUser=item_owner,
                        dateCreated=date_created,
                        edition=item_data.get('edition', 'all'),
                        blurPlaceholder=item_data.get('blurPlaceholder'),
                        mediaWidth=item_data.get('mediaWidth'),
                        mediaHeight=item_data.get('mediaHeight')
                    )
                    imported += 1
                except Exception as e:
                    log('error', f'Error importing item: {e}')
                    skipped_error += 1

                if total_items > 0:
                    job['progress'] = 30 + int((idx + 1) / total_items * 30)

                # Yield DB lock every 10 items so other requests can proceed
                if (idx + 1) % 10 == 0:
                    time.sleep(0.05)

            # Phase 3: Copy media (60-100%)
            job['phase'] = 'copying_media'
            job['progress'] = 60
            media_copied = 0

            media_dir = os.path.join(extract_dir, 'media')
            if os.path.isdir(media_dir):
                media_files = []
                for subfolder in ('images', 'videos', 'music', 'profiles'):
                    src_dir = os.path.join(media_dir, subfolder)
                    if not os.path.isdir(src_dir):
                        continue
                    for fname in os.listdir(src_dir):
                        src_file = os.path.join(src_dir, fname)
                        if os.path.isfile(src_file):
                            media_files.append((src_file, subfolder, fname))

                total_media = len(media_files)
                for idx, (src_file, subfolder, fname) in enumerate(media_files):
                    dest_dir = os.path.join(basedir, '..', 'uploads', subfolder)
                    os.makedirs(dest_dir, exist_ok=True)
                    dest_file = os.path.join(dest_dir, fname)
                    if not os.path.exists(dest_file):
                        shutil.copy2(src_file, dest_file)
                        media_copied += 1
                    if total_media > 0:
                        job['progress'] = 60 + int((idx + 1) / total_media * 40)

            job['progress'] = 100
            job['status'] = 'done'
            job['phase'] = 'done'
            job['result'] = {
                'imported': imported,
                'skipped_duplicate': skipped_duplicate,
                'skipped_error': skipped_error,
                'media_copied': media_copied,
                'settings_updated': settings_updated,
                'users_imported': users_imported,
                'user_settings_imported': user_settings_imported,
                'reminders_imported': reminders_imported
            }

            # If setup import, mark setup as complete
            if is_setup:
                # Get edition from imported settings
                edition_setting = get_setting_by_name('sm_edition')
                if edition_setting:
                    update_setting('sm_edition', edition_setting.value)
                update_setting('setup_complete', 'True')

            log('info', f'Data import completed: {imported} items, {skipped_duplicate} duplicates, {skipped_error} errors, {media_copied} media, {settings_updated} settings, {users_imported} users, {user_settings_imported} user settings, {reminders_imported} reminders')

        except Exception as e:
            log('error', f'Error during import: {e}')
            job['status'] = 'error'
            job['error'] = str(e)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)
            if os.path.exists(zip_path):
                os.remove(zip_path)


def _run_export(export_id, user_id, app_ref):
    with app_ref.app_context():
        job = _FileJob('export-' + export_id, {'progress': 0, 'status': 'running', 'filename': None, 'error': None})
        try:

            basedir = os.path.abspath(os.path.dirname(__file__))

            # 1. Query all data (0-10%)
            db_session = SessionLocal()
            try:
                items = db_session.query(Item).all()
                for item in items:
                    db_session.expunge(item)
                list_types_all = db_session.query(ListType).order_by(ListType.navbarOrder.asc()).all()
                for lt in list_types_all:
                    db_session.expunge(lt)
                user_settings_all = db_session.query(UserSetting).all()
                for us in user_settings_all:
                    db_session.expunge(us)
                user_roles_all = db_session.query(UserRole).all()
                for ur in user_roles_all:
                    db_session.expunge(ur)
                roles_all = db_session.query(Role).all()
                for role in roles_all:
                    db_session.expunge(role)
                reminders_all = db_session.query(Reminder).filter(Reminder.active == True).all()
                for r in reminders_all:
                    db_session.expunge(r)
                settings_all = db_session.query(Setting).all()
                for s in settings_all:
                    db_session.expunge(s)
                users = db_session.query(User).all()
                for u in users:
                    db_session.expunge(u)
            finally:
                db_session.close()

            job['progress'] = 10

            # 2. Build data.json and collect media files
            lt_map = {lt.id: lt for lt in list_types_all}

            role_map = {role.id: role.roleName for role in roles_all}
            user_id_map = {u.id: u for u in users}

            export_data_json = {
                'version': __version__,
                'exportedAt': datetime.utcnow().isoformat(),
                'settings': [],
                'listTypes': [],
                'items': [],
                'users': [],
                'userSettings': [],
                'reminders': []
            }

            for s in settings_all:
                export_data_json['settings'].append({
                    'name': s.name,
                    'value': s.value,
                    'icon': s.icon,
                    'edition': s.edition,
                    'category': s.category,
                    'type': s.type
                })

            for lt in list_types_all:
                export_data_json['listTypes'].append({
                    'title': lt.title,
                    'icon': lt.icon,
                    'routeID': lt.routeID,
                    'mainTitle': lt.mainTitle,
                    'contentURL': lt.contentURL,
                    'navbar': lt.navbar,
                    'navbarOrder': lt.navbarOrder
                })

            for user in users:
                user_roles = [role_map.get(ur.roleID, '') for ur in user_roles_all if ur.userID == user.id]
                export_data_json['users'].append({
                    'firstName': user.firstName,
                    'lastName': user.lastName,
                    'email': user.email,
                    'birthDate': user.birthDate.isoformat() if user.birthDate else None,
                    'profilePicture': user.profilePicture,
                    'passwordHash': user.passwordHash,
                    'passwordSalt': user.passwordSalt,
                    'roles': user_roles
                })

            media_files = []

            for item in items:
                lt_obj = lt_map.get(item.listType)
                creator_obj = user_id_map.get(item.createdByUser)
                export_data_json['items'].append({
                    'title': item.title,
                    'content': item.content,
                    'contentType': item.contentType,
                    'contentURL': item.contentURL,
                    'edition': item.edition,
                    'dateCreated': item.dateCreated.isoformat() if item.dateCreated else None,
                    'listType': {
                        'title': lt_obj.title if lt_obj else '',
                        'routeID': lt_obj.routeID if lt_obj else ''
                    },
                    'creatorEmail': creator_obj.email if creator_obj else None,
                    'blurPlaceholder': item.blurPlaceholder,
                    'mediaWidth': item.mediaWidth,
                    'mediaHeight': item.mediaHeight
                })

                if item.contentURL:
                    for fname in item.contentURL.split(';'):
                        fname = fname.strip()
                        if not fname:
                            continue
                        ext = fname.rsplit('.', 1)[-1].lower() if '.' in fname else ''
                        if ext in IMAGE_EXTENSIONS:
                            subfolder = 'images'
                        elif ext in VIDEO_EXTENSIONS:
                            subfolder = 'videos'
                        elif ext in MUSIC_EXTENSIONS:
                            subfolder = 'music'
                        else:
                            subfolder = 'images'
                        src = os.path.join(basedir, '..', 'uploads', subfolder, fname)
                        if not os.path.exists(src):
                            src = os.path.join(basedir, '..', 'uploads', 'images', fname)
                        media_files.append((src, f'media/{subfolder}/{fname}'))

            for us in user_settings_all:
                user_obj = user_id_map.get(us.userID)
                export_data_json['userSettings'].append({
                    'name': us.name,
                    'value': us.value,
                    'icon': us.icon,
                    'edition': us.edition,
                    'category': us.category,
                    'type': us.type,
                    'userEmail': user_obj.email if user_obj else None
                })

            for r in reminders_all:
                export_data_json['reminders'].append({
                    'title': r.title,
                    'reminder_type': r.reminder_type,
                    'month': r.month,
                    'day': r.day,
                    'description': r.description or '',
                    'target_date': r.target_date.isoformat() if r.target_date else None,
                    'milestone_days': r.milestone_days,
                    'countdown_id': r.countdown_id,
                    'notify_days_before': r.notify_days_before,
                    'is_global': r.is_global,
                    'is_auto': r.is_auto,
                    'auto_source': r.auto_source
                })

            for user in users:
                if user.profilePicture and user.profilePicture != 'profile-placeholder.jpg':
                    src = os.path.join(basedir, '..', 'uploads', 'profiles', user.profilePicture)
                    media_files.append((src, f'media/profiles/{user.profilePicture}'))

            # Export settings-referenced files (banner_song, banner_image)
            for s in settings_all:
                if s.name == 'banner_song' and s.value:
                    src = os.path.join(basedir, '..', 'uploads', 'music', s.value)
                    media_files.append((src, f'media/music/{s.value}'))
                elif s.name in ('banner_image', 'family_banner_image', 'friends_banner_image') and s.value:
                    src = os.path.join(basedir, '..', 'uploads', 'images', s.value)
                    media_files.append((src, f'media/images/{s.value}'))

            # 3. Write ZIP (10-95%)
            export_dir = os.path.join(basedir, '..', 'export')
            os.makedirs(export_dir, exist_ok=True)
            filename = datetime.now().strftime('%Y-%m-%d_%H-%M-%S') + '-data-export.zip'
            zip_path = os.path.join(export_dir, filename)

            total_files = len(media_files)
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('data.json', json.dumps(export_data_json, ensure_ascii=False, indent=2))
                for i, (src, zip_name) in enumerate(media_files):
                    if os.path.exists(src):
                        zf.write(src, zip_name)
                    progress = 10 + int((i + 1) / max(total_files, 1) * 85)
                    job['progress'] = min(progress, 95)

            # 4. Done
            job['progress'] = 100
            job['status'] = 'done'
            job['filename'] = filename
            log('info', f'Data export completed: {filename}')

        except Exception as e:
            log('error', f'Data export failed: {e}')
            job['status'] = 'error'
            job['error'] = str(e)
