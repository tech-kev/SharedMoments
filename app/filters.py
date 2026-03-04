import hashlib
import os

from app import app
from datetime import datetime
from markupsafe import Markup, escape

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

@app.template_filter('format_date_dmy')
def format_date_dmy(value, format="%d.%m.%y"):
    if value is None:
        return ""
    return value.strftime(format)

@app.template_filter('format_date_ymd')
def format_date_ymd(value, format="%Y-%m-%d"):
    if value is None:
        return ""
    return value.strftime(format)

@app.template_filter('format_string_date_dmy')
def format_string_date_dmy(value, format="%d.%m.%Y"):
    if not value:
        return ""
    return datetime.strptime(value, "%Y-%m-%d").strftime(format)

@app.template_filter('nl2br')
def nl2br(value):
    """Escape HTML, then convert newlines to <br> tags."""
    if not value:
        return ""
    import re
    s = re.sub(r'<br\s*/?>', '\n', str(value), flags=re.IGNORECASE)
    return Markup(Markup('<br>').join(escape(line) for line in s.split('\n')))
