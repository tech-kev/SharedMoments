from app import app
from datetime import datetime
from markupsafe import Markup, escape

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
