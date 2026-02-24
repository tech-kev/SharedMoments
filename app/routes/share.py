from flask import Blueprint, render_template, request, redirect, session, send_file, abort
from werkzeug.utils import secure_filename
from app.db_queries import get_share_by_token, verify_share_password, increment_share_view_count, get_setting_by_name
from app.logger import log
from datetime import datetime
import os

share_bp = Blueprint('share', __name__)


@share_bp.route('/s/<token>')
def share_view(token):
    share, item = get_share_by_token(token)

    if not share or not item:
        abort(404)

    # Check expiration
    if share.expiresAt and datetime.utcnow() > share.expiresAt:
        return render_template('pages/share-expired.html'), 410

    # Check password
    if share.passwordHash:
        verified_shares = session.get('verified_shares', [])
        if token not in verified_shares:
            error = request.args.get('error')
            return render_template('pages/share-password.html', token=token, error=error)

    # Build media URLs for share context
    media_urls = []
    if item.contentURL:
        for url in item.contentURL.split(';'):
            if url.strip():
                media_urls.append(url.strip())

    # Increment view counter if tracking is enabled
    tracking = get_setting_by_name('share_tracking')
    if tracking and tracking.value == 'True':
        increment_share_view_count(share.id)

    return render_template('pages/share.html', item=item, share=share, token=token, media_urls=media_urls)


@share_bp.route('/s/<token>/verify', methods=['POST'])
def share_verify(token):
    share, item = get_share_by_token(token)

    if not share or not item:
        abort(404)

    if share.expiresAt and datetime.utcnow() > share.expiresAt:
        return render_template('pages/share-expired.html'), 410

    password = request.form.get('password', '')
    if verify_share_password(share, password):
        verified_shares = session.get('verified_shares', [])
        if token not in verified_shares:
            verified_shares.append(token)
        session['verified_shares'] = verified_shares
        return redirect(f'/s/{token}')
    else:
        return redirect(f'/s/{token}?error=1')


@share_bp.route('/s/<token>/media/<filename>')
def share_media(token, filename):
    share, item = get_share_by_token(token)

    if not share or not item:
        abort(404)

    # Check expiration
    if share.expiresAt and datetime.utcnow() > share.expiresAt:
        abort(410)

    # Check password
    if share.passwordHash:
        verified_shares = session.get('verified_shares', [])
        if token not in verified_shares:
            abort(403)

    # Verify filename belongs to this item
    if not item.contentURL or filename not in item.contentURL.split(';'):
        abort(404)

    safe = secure_filename(filename)
    if not safe or safe != filename:
        abort(400)

    basedir = os.path.abspath(os.path.dirname(__file__))
    images_folder = os.path.abspath(os.path.join(basedir, '..', 'uploads', 'images'))
    file_path = os.path.abspath(os.path.join(images_folder, safe))
    if not file_path.startswith(images_folder):
        abort(403)

    if not os.path.exists(file_path):
        abort(404)

    return send_file(file_path)
