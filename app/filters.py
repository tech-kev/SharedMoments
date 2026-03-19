import hashlib
import os

from app import app
from datetime import datetime
from markupsafe import Markup, escape
import re as _re
from babel.dates import format_date as babel_format_date, get_date_format
from flask import session

_static_hash_cache = {}

def static_versioned(path):
    """Return /static/path?v=<content-hash> for cache busting."""
    if path not in _static_hash_cache:
        file_path = os.path.join(app.static_folder, path)
        try:
            with open(file_path, 'rb') as f:
                h = hashlib.md5(f.read()).hexdigest()[:8]
            _static_hash_cache[path] = h
        except FileNotFoundError:
            _static_hash_cache[path] = '0'
    return f'/static/{path}?v={_static_hash_cache[path]}'

def _get_babel_locale():
    lang = session.get('lang', 'en-US')
    return lang.replace('-', '_')

def _get_full_date_pattern(locale):
    pattern = get_date_format('short', locale=locale).pattern
    pattern = _re.sub(r'y+', 'yyyy', pattern)
    pattern = _re.sub(r'M+', 'MM', pattern)
    pattern = _re.sub(r'd+', 'dd', pattern)
    return pattern

@app.template_filter('format_date_dmy')
def format_date_dmy(value):
    if value is None:
        return ""
    return babel_format_date(value, format='short', locale=_get_babel_locale())

@app.template_filter('format_date_ymd')
def format_date_ymd(value, format="%Y-%m-%d"):
    if value is None:
        return ""
    return value.strftime(format)

@app.template_filter('format_string_date_dmy')
def format_string_date_dmy(value):
    if not value:
        return ""
    dt = datetime.strptime(value, "%Y-%m-%d").date()
    locale = _get_babel_locale()
    return babel_format_date(dt, format=_get_full_date_pattern(locale), locale=locale)

@app.template_filter('nl2br')
def nl2br(value):
    """Escape HTML, then convert newlines to <br> tags."""
    if not value:
        return ""
    import re
    s = re.sub(r'<br\s*/?>', '\n', str(value), flags=re.IGNORECASE)
    return Markup(Markup('<br>').join(escape(line) for line in s.split('\n')))
