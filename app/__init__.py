from flask import Flask, request, session
from flask_bcrypt import Bcrypt
import os
from .db_queries import get_supported_languages


# Initialisierung der Flask-App

app = Flask(__name__)
app.config.from_object('config.Config')

base_dir = os.path.abspath(os.path.dirname(__file__))

# Konfiguration der Sprache
app.config['DEFAULT_LOCALE'] = 'en'
app.config['SUPPORTED_LOCALES'] = get_supported_languages() # Lade die unterstützten Sprachen aus der Datenbank

bcrypt = Bcrypt(app)

# Session cookie security
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Security headers
@app.after_request
def set_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    if request.is_secure:
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response

# Jinja2 Template-Filter registrieren
from app.filters import *
from app.filters import static_versioned
app.jinja_env.globals['static_versioned'] = static_versioned

# Context Processor for permission checks in templates
from app.permissions import has_permission, has_list_permission

@app.context_processor
def inject_permissions():
    return dict(has_permission=has_permission, has_list_permission=has_list_permission)

# Import und Registrierung der Blueprints
from app.routes import auth_bp, pages_bp, api_bp, ai_bp, share_bp
app.register_blueprint(auth_bp)
app.register_blueprint(pages_bp)
app.register_blueprint(api_bp)
app.register_blueprint(ai_bp)
app.register_blueprint(share_bp)

from app.routes.admin import admin_bp
app.register_blueprint(admin_bp)

# Context Processor: AI-Feature-Flag für Templates
from app.ai import get_active_provider

@app.context_processor
def inject_ai_enabled():
    return dict(ai_enabled=bool(get_active_provider()))

@app.context_processor
def inject_accent_color():
    accent_color = '#6750A4'
    try:
        from flask import g
        if hasattr(g, 'user_id') and g.user_id:
            from app.db_queries import get_user_setting
            setting = get_user_setting(g.user_id, 'accent_color')
            if setting and setting.value:
                accent_color = setting.value
    except Exception:
        pass
    return dict(accent_color=accent_color)
