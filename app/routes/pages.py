import json
from flask import Blueprint, g, make_response, render_template, send_file, request, redirect, url_for, session
from app.db_queries import (get_all_list_types, get_all_relationship_statuses,
    get_relationship_statuses_with_names, get_items_by_type,
    get_supported_languages, get_translation_for_entity, get_translation_progress,
    get_translations_by_language, get_user_by_id, get_user_setting, get_setting_by_name,
    get_item_by_id, get_user_settings, get_list_type_by_content_url, get_all_settings,
    get_shared_item_ids, get_list_type_by_title, ensure_countdown_list_type,
    ensure_banner_song_setting, get_all_reminders, get_user_muted_reminder_ids,
    ensure_notification_settings, get_passkeys_by_user)
from app.logger import log
import os
from app.utils import generate_banner_text
from app.translation import _, set_locale
from app.routes.auth import jwt_required, login_jwt
from app.permissions import require_permission, has_list_permission

pages_bp = Blueprint('pages', __name__)


def get_display_title():
    """Returns the appropriate title setting based on the current edition."""
    edition = get_setting_by_name('sm_edition').value
    if edition == 'family':
        family_name = get_setting_by_name('family_name')
        if family_name and family_name.value:
            return family_name
    elif edition == 'friends':
        friend_name = get_setting_by_name('friend_group_name')
        if friend_name and friend_name.value:
            return friend_name
    return get_setting_by_name('title')

# Paths that bypass the migration gate
_MIGRATION_ALLOWED_PREFIXES = ('/static/', '/api/v2/migration/', '/migration-complete',
                                '/migration-progress', '/manifest.json', '/sw.js',
                                '/offline', '/favicon.ico')


def _get_migration_target():
    """Determine where to redirect based on migration state. Returns URL or None."""
    # 1. Check if migration review is pending (real migration done, user must review)
    try:
        review = get_setting_by_name('migration_review_complete')
        if review and review.value == 'False':
            return '/migration-complete'
    except Exception:
        pass

    # 2. Check if migration is currently running or dry-run completed
    try:
        from app.migration.status import load_status
        status = load_status()
        if status:
            if status.get('dry_run', False):
                return '/migration-progress'
            if not status.get('completed_at'):
                return '/migration-progress'
    except ImportError:
        pass

    return None


@pages_bp.before_app_request
def _migration_gate():
    """Redirect all non-migration pages when migration is active."""
    path = request.path
    if any(path.startswith(p) for p in _MIGRATION_ALLOWED_PREFIXES):
        return None

    target = _get_migration_target()
    if target:
        return redirect(target)
    return None


# ===== PWA Routes (no auth required) =====

@pages_bp.route('/manifest.json')
def manifest():
    return send_file('static/pwa/manifest.json', mimetype='application/manifest+json')


@pages_bp.route('/sw.js')
def service_worker():
    response = make_response(send_file('static/pwa/sw.js', mimetype='application/javascript'))
    response.headers['Service-Worker-Allowed'] = '/'
    response.headers['Cache-Control'] = 'no-cache'
    return response


@pages_bp.route('/offline')
def offline():
    return render_template('pages/offline.html')


@pages_bp.app_context_processor
def inject_static_text():
    translations_json = '{}'
    try:
        lang = session.get('lang', os.environ.get('LANG', 'en-US'))
        translations = get_translations_by_language(lang)
        translations_json = json.dumps({
            t.fieldName: {'translatedText': t.translatedText}
            for t in translations
        }, ensure_ascii=False)
    except Exception:
        pass
    try:
        nav_edition = get_setting_by_name('sm_edition').value
    except Exception:
        nav_edition = 'couples'
    return dict(_=_, translations_json=translations_json, nav_edition=nav_edition)


@pages_bp.route('/')
def index():
    if get_setting_by_name('setup_complete').value == 'False':
        return redirect(url_for('pages.setup'))
    else:
        return redirect(url_for('auth.login'))


@pages_bp.route('/static/js/<filename>')
@jwt_required
def serve_js(filename):
    return send_file('static/js/' + filename), 200


@pages_bp.route('/setup')
def setup():
    try:
        # If migration is active, go there instead
        target = _get_migration_target()
        if target:
            return redirect(target)

        if get_setting_by_name('setup_complete').value == 'True':
            return redirect(url_for('auth.login'))
        else:
            set_locale()
            setupUser = get_user_by_id(1)
            response = login_jwt(setupUser)
            relationship_statuses = get_all_relationship_statuses()
            relationship_statuses_translated = []
            for status in relationship_statuses:
                translated_text = get_translation_for_entity('relationship_status', status, os.environ['LANG'])
                relationship_statuses_translated.append({
                    'id': status,
                    'translatedText': translated_text
                })

            response.data = render_template('pages/setup.html', relationship_statuses=relationship_statuses, relationship_statuses_translated=relationship_statuses_translated)
            response.mimetype = 'text/html'
            return response

    except Exception as e:
        log('error', f'Error while rendering the pages/setup.html-Template: {e}')
        return "An error occurred while rendering the page. Please check the server logs for details.", 500


@pages_bp.route('/home')
@jwt_required
def home():
    try:
        list_type = 1
        sm_edition = get_setting_by_name('sm_edition').value
        items = get_items_by_type(list_type, 'desc', edition=sm_edition)
        list_types = get_all_list_types()
        title = get_display_title()
        darkmode = get_user_setting(g.user_id, 'darkmode')
        user_data = get_user_by_id(g.user_id)
        settings = get_all_settings()
        list_type_moments = 2
        moments = get_items_by_type(list_type_moments, 'asc', edition=sm_edition)
        banner_text = generate_banner_text(sm_edition)
        shared_item_ids = get_shared_item_ids()

        ensure_countdown_list_type()
        ensure_banner_song_setting()
        countdown_list_type = get_list_type_by_title('Countdown')
        countdowns = get_items_by_type(countdown_list_type.id, 'asc', edition=sm_edition) if countdown_list_type else []
        countdown_list_type_id = countdown_list_type.id if countdown_list_type else ''

        return render_template('pages/home.html', items=items, list_types=list_types, list_type=list_type, title=title, darkmode=darkmode, user_data=user_data, moments=moments, settings=settings, banner_text=banner_text, sm_edition=sm_edition, list_type_title='Home', moments_title='Moments', shared_item_ids=shared_item_ids, countdowns=countdowns, countdown_title='Countdown', countdown_list_type_id=countdown_list_type_id)
    except Exception as e:
        log('error', f'Error while rendering the pages/home.html-Template: {e}')
        return "An error occurred while rendering the page. Please check the server logs for details.", 500


@pages_bp.route('/manage-translations')
@jwt_required
@require_permission('Manage Translations')
def manage_translations():
    try:
        dev = request.args.get('dev')
        list_types = get_all_list_types()
        title = get_display_title()
        darkmode = get_user_setting(g.user_id, 'darkmode')
        user_data = get_user_by_id(g.user_id)
        settings = get_all_settings()
        supported_languages = get_supported_languages()
        translation_progresses = get_translation_progress()

        return render_template('pages/manage-translations.html', dev=dev, list_types=list_types, title=title, darkmode=darkmode, user_data=user_data, settings=settings, supported_languages=supported_languages, translation_progresses=translation_progresses)

    except Exception as e:
        log('error', f'Error while rendering the pages/manage-translations.html-Template: {e}')
        return "An error occurred while rendering the page. Please check the server logs for details.", 500


@pages_bp.route('/settings')
@jwt_required
@require_permission('Read Setting')
def settings():
    try:
        settings = get_all_settings()
        list_types = get_all_list_types()
        title = get_display_title()
        darkmode = get_user_setting(g.user_id, 'darkmode')
        user_data = get_user_by_id(g.user_id)
        settings_type = 'settings'
        lang = os.environ.get('LANG', 'en')
        relationship_statuses = get_relationship_statuses_with_names(lang)
        supported_languages = get_supported_languages()

        sm_edition = get_setting_by_name('sm_edition').value
        return render_template('pages/settings.html', settings=settings, list_types=list_types, title=title, darkmode=darkmode, user_data=user_data, settings_type=settings_type, relationship_statuses=relationship_statuses, supported_languages=supported_languages, sm_edition=sm_edition)
    except Exception as e:
        log('error', f'Error while rendering the settings.html-Template: {e}')
        return "An error occurred while rendering the page. Please check the server logs for details.", 500


@pages_bp.route('/user-settings')
@jwt_required
def user_settings():
    try:
        ensure_notification_settings(g.user_id)
        settings = get_all_settings()
        list_types = get_all_list_types()
        title = get_display_title()
        darkmode = get_user_setting(g.user_id, 'darkmode')
        user_data = get_user_by_id(g.user_id)
        user_settings = get_user_settings(g.user_id)
        settings_type = 'user-settings'
        supported_languages = get_supported_languages()

        smtp_available = bool(os.environ.get('SMTP_HOST', ''))
        telegram_available = bool(os.environ.get('TELEGRAM_BOT_TOKEN', ''))
        telegram_chat_id_setting = get_user_setting(g.user_id, 'notification_telegram_chat_id')
        telegram_chat_id = telegram_chat_id_setting.value if telegram_chat_id_setting else ''
        passkeys = get_passkeys_by_user(g.user_id)

        return render_template('pages/settings.html', settings=settings, list_types=list_types, title=title, darkmode=darkmode, user_data=user_data, user_settings=user_settings, settings_type=settings_type, supported_languages=supported_languages,
            smtp_available=smtp_available, telegram_available=telegram_available, telegram_chat_id=telegram_chat_id, passkeys=passkeys)
    except Exception as e:
        log('error', f'Error while rendering the settings.html-Template: {e}')
        return "An error occurred while rendering the page. Please check the server logs for details.", 500


@pages_bp.route('/gallery/<int:id>')
@jwt_required
def gallery(id):
    try:
        item = get_item_by_id(id)

        if not item.contentType.startswith('gallery'):
            raise Exception(_('Item is not a gallery'))

        list_types = get_all_list_types()
        title = get_display_title()
        darkmode = get_user_setting(g.user_id, 'darkmode')
        user_data = get_user_by_id(g.user_id)

        return render_template('pages/gallery.html', item=item, list_types=list_types, title=title, darkmode=darkmode, user_data=user_data)
    except Exception as e:
        log('error', f'Error while rendering the pages/gallery.html-Template: {e}')
        return "An error occurred while rendering the page. Please check the server logs for details.", 500


@pages_bp.route('/favicon.ico')
def favicon():
    favicon_path = os.path.join(os.path.dirname(__file__), '..', 'static', 'images', 'favicon.ico')
    if os.path.exists(favicon_path):
        return send_file(favicon_path)
    return '', 204


@pages_bp.route('/migration-progress')
def migration_progress():
    try:
        from app.migration.status import load_status, STEPS
        status = load_status()
    except ImportError:
        status = None
        STEPS = []

    # If real migration is done, redirect to review page
    if status and status.get('completed_at') and not status.get('dry_run', False):
        return redirect('/migration-complete')

    error = None
    if status:
        # Top-level error (e.g. MySQL connection failure)
        if status.get('error'):
            error = status['error']
        else:
            for step_info in status.get('steps', {}).values():
                if step_info.get('status') == 'failed' and step_info.get('error'):
                    error = step_info['error']
                    break

    # Build ordered steps list
    steps_ordered = []
    status_steps = status.get('steps', {}) if status else {}
    for step_name in STEPS:
        steps_ordered.append((step_name, status_steps.get(step_name, {'status': 'pending'})))

    dry_run = status.get('dry_run', False) if status else False
    return render_template('pages/migration-progress.html', status=status, error=error, dry_run=dry_run, steps_ordered=steps_ordered)


@pages_bp.route('/migration-complete')
def migration_complete():
    from app.models import User, UserRole, Role, Item, SessionLocal
    try:
        from app.migration.status import load_status as load_migration_status
        status = load_migration_status()
    except ImportError:
        status = None

    # Dry-run: show progress instead
    if status and status.get('dry_run', False):
        return redirect('/migration-progress')

    # Only block access if migration review is already done (no loop risk)
    try:
        review = get_setting_by_name('migration_review_complete')
        if review and review.value == 'True':
            return redirect('/')
    except Exception:
        pass

    db_session = SessionLocal()
    try:
        users = db_session.query(User).filter(User.id > 1).all()
        roles = db_session.query(Role).all()

        # Build user data with current role
        user_data = []
        for u in users:
            user_role = db_session.query(UserRole).filter(UserRole.userID == u.id).first()
            current_role = ''
            if user_role:
                role = db_session.query(Role).filter(Role.id == user_role.roleID).first()
                current_role = role.roleName if role else ''
            user_data.append({
                'id': u.id,
                'firstName': u.firstName,
                'lastName': u.lastName or '',
                'email': u.email,
                'role': current_role,
            })

        has_placeholder = any(u['email'].endswith('@placeholder.local') for u in user_data)

        # Build summary
        summary = {}
        summary['Users'] = len(user_data)
        summary['Home Items'] = db_session.query(Item).filter(Item.listType == 1).count()
        summary['Moments'] = db_session.query(Item).filter(Item.listType == 2).count()
        summary['Movie List'] = db_session.query(Item).filter(Item.listType == 3).count()
        summary['Bucket List'] = db_session.query(Item).filter(Item.listType == 4).count()
    finally:
        db_session.close()

    languages = get_supported_languages()
    role_names = [r.roleName for r in roles if r.roleName != 'System']

    return render_template('pages/migration-complete.html',
        status=status, users=user_data, has_placeholder=has_placeholder, summary=summary,
        languages=languages, roles=role_names)


def _translate_reminder_title(reminder):
    """Translate auto-reminder titles using the current locale."""
    if not reminder.is_auto:
        return reminder.title

    if reminder.title in ('Anniversary', 'Wedding Day', 'Engagement Day', 'Family Day', 'Friendship Day'):
        return _(reminder.title)

    if reminder.auto_source and reminder.auto_source.startswith('user_birthday_'):
        try:
            uid = int(reminder.auto_source.replace('user_birthday_', ''))
            user = get_user_by_id(uid)
            if user:
                return _('Birthday of {name}').format(name=user.firstName)
        except (ValueError, TypeError):
            pass
        return reminder.title

    if reminder.auto_source and 'milestone_' in reminder.auto_source:
        days = reminder.milestone_days
        if days:
            if days % 365 == 0:
                return _('{n}-Year Milestone').format(n=days // 365)
            else:
                return _('{n}-Day Milestone').format(n=days)
        return reminder.title

    if reminder.auto_source and reminder.auto_source.startswith('countdown_'):
        item_title = reminder.title
        if item_title.startswith('Countdown: '):
            item_title = item_title[len('Countdown: '):]
        return _('Countdown: {title}').format(title=item_title)

    return _(reminder.title)


def _translate_reminder_description(reminder):
    """Translate auto-reminder descriptions using the current locale."""
    if not reminder.is_auto or not reminder.description:
        return reminder.description

    if reminder.auto_source and 'milestone_' in reminder.auto_source:
        return ''

    if reminder.auto_source and reminder.auto_source.startswith('countdown_'):
        item_title = reminder.title
        if item_title.startswith('Countdown: '):
            item_title = item_title[len('Countdown: '):]
        return _('Countdown "{title}" reached!').format(title=item_title)

    return reminder.description


@pages_bp.route('/reminders')
@jwt_required
@require_permission('View Reminders')
def reminders():
    try:
        list_types = get_all_list_types()
        title = get_display_title()
        darkmode = get_user_setting(g.user_id, 'darkmode')
        user_data = get_user_by_id(g.user_id)
        reminder_list = get_all_reminders()
        muted_ids = get_user_muted_reminder_ids(g.user_id)

        return render_template('pages/reminders.html',
            list_types=list_types, title=title, darkmode=darkmode, user_data=user_data,
            reminders=reminder_list, muted_ids=muted_ids,
            translate_title=_translate_reminder_title,
            translate_desc=_translate_reminder_description)
    except Exception as e:
        log('error', f'Error while rendering reminders page: {e}')
        return "An error occurred while rendering the page. Please check the server logs for details.", 500


@pages_bp.route('/<path:content_url>')
@jwt_required
def list_view(content_url):
    try:
        error_msg = []
        list_type = get_list_type_by_content_url(content_url)
        if not list_type:
            raise Exception(_('List type not found'))

        if not has_list_permission('View', list_type.title):
            return redirect(url_for('pages.home'))

        sm_edition = get_setting_by_name('sm_edition').value
        items = get_items_by_type(list_type.id, edition=sm_edition, checked_last=True)
        list_types = get_all_list_types()
        title = get_display_title()
        darkmode = get_user_setting(g.user_id, 'darkmode')
        user_data = get_user_by_id(g.user_id)

        return render_template('pages/list.html',
                               items=items,
                               list_type=list_type.id,
                               list_types=list_types,
                               mainTitle=list_type.mainTitle,
                               title=title,
                               darkmode=darkmode,
                               user_data=user_data,
                               error_msg=error_msg,
                               list_type_title=list_type.title,
                               sm_edition=sm_edition)
    except Exception as e:
        log('error', f'Error while processing the list view: {e}')
        return "An error occurred while processing your request. Page not found.", 500
