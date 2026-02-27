import json
from flask import Blueprint, g, make_response, render_template, send_file, request, redirect, url_for, session
from app.db_queries import (get_all_list_types, get_all_relationship_statuses,
    get_relationship_statuses_with_names, get_items_by_type,
    get_supported_languages, get_translation_for_entity, get_translation_progress,
    get_translations_by_language, get_user_by_id, get_user_setting, get_setting_by_name,
    get_item_by_id, get_user_settings, get_list_type_by_content_url, get_all_settings,
    get_shared_item_ids)
from app.logger import log
import os
from app.utils import generate_banner_text
from app.translation import _, set_locale
from app.routes.auth import jwt_required, login_jwt
from app.permissions import require_permission, has_list_permission

pages_bp = Blueprint('pages', __name__)


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
        lang = session.get('lang', os.environ.get('LANG', 'en'))
        translations = get_translations_by_language(lang)
        translations_json = json.dumps({
            t.fieldName: {'translatedText': t.translatedText}
            for t in translations
        }, ensure_ascii=False)
    except Exception:
        pass
    return dict(_=_, translations_json=translations_json)


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
        title = get_setting_by_name('title')
        darkmode = get_user_setting(g.user_id, 'darkmode')
        user_data = get_user_by_id(g.user_id)
        settings = get_all_settings()
        list_type_moments = 2
        moments = get_items_by_type(list_type_moments, 'asc', edition=sm_edition)
        banner_text = generate_banner_text() if sm_edition == 'couples' else None
        shared_item_ids = get_shared_item_ids()

        return render_template('pages/home.html', items=items, list_types=list_types, list_type=list_type, title=title, darkmode=darkmode, user_data=user_data, moments=moments, settings=settings, banner_text=banner_text, sm_edition=sm_edition, list_type_title='Home', moments_title='Moments', shared_item_ids=shared_item_ids)
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
        title = get_setting_by_name('title')
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
        title = get_setting_by_name('title')
        darkmode = get_user_setting(g.user_id, 'darkmode')
        user_data = get_user_by_id(g.user_id)
        settings_type = 'settings'
        lang = os.environ.get('LANG', 'en')
        relationship_statuses = get_relationship_statuses_with_names(lang)
        supported_languages = get_supported_languages()

        return render_template('pages/settings.html', settings=settings, list_types=list_types, title=title, darkmode=darkmode, user_data=user_data, settings_type=settings_type, relationship_statuses=relationship_statuses, supported_languages=supported_languages)
    except Exception as e:
        log('error', f'Error while rendering the settings.html-Template: {e}')
        return "An error occurred while rendering the page. Please check the server logs for details.", 500


@pages_bp.route('/user-settings')
@jwt_required
def user_settings():
    try:
        settings = get_all_settings()
        list_types = get_all_list_types()
        title = get_setting_by_name('title')
        darkmode = get_user_setting(g.user_id, 'darkmode')
        user_data = get_user_by_id(g.user_id)
        user_settings = get_user_settings(g.user_id)
        settings_type = 'user-settings'
        supported_languages = get_supported_languages()

        return render_template('pages/settings.html', settings=settings, list_types=list_types, title=title, darkmode=darkmode, user_data=user_data, user_settings=user_settings, settings_type=settings_type, supported_languages=supported_languages)
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
        title = get_setting_by_name('title')
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
        title = get_setting_by_name('title')
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
                               list_type_title=list_type.title)
    except Exception as e:
        log('error', f'Error while processing the list view: {e}')
        return "An error occurred while processing your request. Page not found.", 500
