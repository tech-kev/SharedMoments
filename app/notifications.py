import os
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.logger import log
from app.db_queries import (get_push_subscriptions_for_user, get_user_setting,
                            get_setting_by_name, update_setting, get_user_by_id)
from app.models import Setting, SessionLocal


def _ensure_vapid_keys():
    """Auto-generate VAPID keys on first run, store in Settings (category='system')."""
    existing = get_setting_by_name('vapid_private_key')
    if existing and existing.value:
        return

    try:
        import base64
        from py_vapid import Vapid
        from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat, NoEncryption
        vapid = Vapid()
        vapid.generate_keys()
        # Store private key as raw base64url (32 bytes) — required by Vapid.from_string()
        from cryptography.hazmat.primitives.asymmetric.ec import ECDSA
        private_numbers = vapid.private_key.private_numbers()
        private_bytes = private_numbers.private_value.to_bytes(32, 'big')
        private_raw = base64.urlsafe_b64encode(private_bytes).decode('utf-8').rstrip('=')
        # Public key as URL-safe base64 (uncompressed point format)
        pk_bytes = vapid.public_key.public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
        public_raw = base64.urlsafe_b64encode(pk_bytes).decode('utf-8').rstrip('=')

        session = SessionLocal()
        try:
            for name, value in [('vapid_private_key', private_raw), ('vapid_public_key', public_raw)]:
                existing = session.query(Setting).filter(Setting.name == name).first()
                if existing:
                    existing.value = value
                else:
                    session.add(Setting(name=name, value=value, icon='', edition='all', category='system', type='text'))
            session.commit()
            log('info', 'VAPID keys generated and stored')
        finally:
            session.close()
    except Exception as e:
        log('error', f'Failed to generate VAPID keys: {e}')


def get_vapid_public_key():
    """Return the VAPID public key for the client."""
    setting = get_setting_by_name('vapid_public_key')
    return setting.value if setting else None


def send_push_notification(user_id, title, body, url='/reminders'):
    """Send push notification to all subscriptions of a user."""
    try:
        from pywebpush import webpush, WebPushException

        private_key_setting = get_setting_by_name('vapid_private_key')
        if not private_key_setting or not private_key_setting.value:
            log('warning', 'VAPID private key not configured')
            return False

        subscriptions = get_push_subscriptions_for_user(user_id)
        if not subscriptions:
            return False

        payload = json.dumps({'title': title, 'body': body, 'url': url})
        private_key = private_key_setting.value

        sent = False
        for sub in subscriptions:
            try:
                webpush(
                    subscription_info={
                        'endpoint': sub['endpoint'],
                        'keys': {'p256dh': sub['p256dh'], 'auth': sub['auth']}
                    },
                    data=payload,
                    vapid_private_key=private_key,
                    vapid_claims={'sub': 'mailto:noreply@sharedmoments.app'},
                    content_encoding='aes128gcm'
                )
                sent = True
            except WebPushException as e:
                log('warning', f'Push notification failed for endpoint: {e}')
                response = getattr(e, 'response', None)
                status = getattr(response, 'status_code', 0) if response else 0
                if status in (404, 410) or '410' in str(e) or 'Gone' in str(e):
                    from app.db_queries import delete_push_subscription
                    delete_push_subscription(sub['endpoint'])
                    log('info', f'Removed expired push subscription')
            except Exception as e:
                log('error', f'Push notification error: {e}')

        return sent
    except ImportError:
        log('warning', 'pywebpush not installed')
        return False


def send_email_notification(to, subject, body):
    """Send an email notification via SMTP."""
    smtp_host = os.environ.get('SMTP_HOST', '')
    smtp_port = int(os.environ.get('SMTP_PORT', '587'))
    smtp_user = os.environ.get('SMTP_USER', '')
    smtp_pass = os.environ.get('SMTP_PASS', '')
    smtp_from = os.environ.get('SMTP_FROM', smtp_user)

    if not smtp_host or not smtp_user:
        log('debug', 'SMTP not configured, skipping email notification')
        return False

    try:
        msg = MIMEMultipart()
        msg['From'] = smtp_from
        msg['To'] = to
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)

        log('info', f'Email sent to {to}: {subject}')
        return True
    except Exception as e:
        log('error', f'Failed to send email to {to}: {e}')
        return False


def send_telegram_notification(chat_id, message):
    """Send a Telegram notification via Bot API."""
    import requests

    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', '')
    if not bot_token:
        log('debug', 'Telegram bot token not configured, skipping')
        return False

    try:
        url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
        resp = requests.post(url, json={'chat_id': chat_id, 'text': message, 'parse_mode': 'HTML'}, timeout=10)
        if resp.status_code == 200:
            log('info', f'Telegram message sent to {chat_id}')
            return True
        else:
            log('error', f'Telegram API error: {resp.status_code} {resp.text}')
            return False
    except Exception as e:
        log('error', f'Failed to send Telegram message: {e}')
        return False


def send_notification(user_id, title, body, channels='all'):
    """Send notification via configured channels.

    channels: 'all' | 'push' | 'email' | 'telegram' | list of channels
    """
    if isinstance(channels, str) and channels != 'all':
        channels = [channels]

    results = {}

    # Push
    if channels == 'all' or 'push' in channels:
        push_enabled = get_user_setting(user_id, 'notification_push_enabled')
        if not push_enabled or push_enabled.value != 'False':
            results['push'] = send_push_notification(user_id, title, body)

    # Email — use email from user profile
    if channels == 'all' or 'email' in channels:
        email_enabled = get_user_setting(user_id, 'notification_email_enabled')
        if email_enabled and email_enabled.value == 'True':
            user = get_user_by_id(user_id)
            if user and user.email:
                results['email'] = send_email_notification(user.email, title, body)

    # Telegram
    if channels == 'all' or 'telegram' in channels:
        telegram_enabled = get_user_setting(user_id, 'notification_telegram_enabled')
        if telegram_enabled and telegram_enabled.value == 'True':
            chat_id = get_user_setting(user_id, 'notification_telegram_chat_id')
            if chat_id and chat_id.value:
                results['telegram'] = send_telegram_notification(chat_id.value, f'<b>{title}</b>\n{body}')

    return results
