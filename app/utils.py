import re
import unicodedata
from app.db_queries import get_all_settings, get_all_translations, get_all_user_settings, get_setting_by_name, get_field_name, get_translations_by_language
from app.translation import _
from app.logger import log
from datetime import datetime
from dateutil.relativedelta import relativedelta
import os
from pathlib import Path
import json
import base64
from io import BytesIO
from PIL import Image


def sanitize_identifier(text):
    """Sanitize text for use in filenames: no special chars, spaces to underscores."""
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
    text = re.sub(r'[^\w\s-]', '', text).strip()
    text = re.sub(r'[\s-]+', '_', text)
    return text or 'Unknown'


def generate_admin_filename(image_type, identifier, extension):
    """Generate descriptive filename: {Prefix}_{Identifier}.{ext} or {Prefix}.{ext} if no identifier."""
    PREFIXES = {
        'profile': 'Profilbild',
        'banner_image': 'Banner',
        'banner_song': 'Bannersong',
    }
    prefix = PREFIXES.get(image_type, image_type)
    ext = extension.lower().lstrip('.')
    if identifier and identifier.strip():
        safe_id = sanitize_identifier(identifier)
        return f"{prefix}_{safe_id}.{ext}"
    return f"{prefix}.{ext}"

def generate_lqip(image_path):
    """Generate a low-quality image placeholder (base64 data-URI) and return dimensions."""
    try:
        with Image.open(image_path) as img:
            width, height = img.size
            img = img.convert('RGB')
            img.thumbnail((64, 64))
            buffer = BytesIO()
            img.save(buffer, format='JPEG', quality=40, optimize=True)
            b64 = base64.b64encode(buffer.getvalue()).decode('ascii')
            return f'data:image/jpeg;base64,{b64}', width, height
    except Exception as e:
        log('warning', f'LQIP generation failed for {image_path}: {e}')
        return None, None, None


def generate_banner_text(edition='couples'):
    try:
        if edition == 'family':
            return _generate_banner_text_family()
        elif edition == 'friends':
            return _generate_banner_text_friends()
        else:
            return _generate_banner_text_couples()
    except Exception as e:
        log('error', f'Failed to generate banner text: {e}')
        return None


def _generate_banner_text_couples():
    relationship_status_setting = get_setting_by_name('relationship_status')
    if not relationship_status_setting or not relationship_status_setting.value:
        return None

    relationship_status_id = int(relationship_status_setting.value)
    relationship_status_field = get_field_name('relationship_status', relationship_status_id)
    relationship_status = _(relationship_status_field)

    # Schreibe den ersten Buchstaben klein, damit das in den Text passt
    relationship_status = relationship_status[0].lower() + relationship_status[1:]

    if relationship_status_id == 1 and os.environ['LANG'].startswith('de'): # zusammen klingt im Text besser
        relationship_status = 'zusammen'

    if relationship_status_id == 1 or relationship_status_id == 4 or relationship_status_id == 5: # in einer Beziehung, in einer offenen Beziehung, in einer komplizierten Beziehung
        anniversary_date = get_setting_by_name('anniversary_date').value
        if not anniversary_date:
            return _('Please set your anniversary date in the settings.')
        years_count, months_count, days_count, diffInMonthsTotal, diffInWeeksTotal, diffInDays = calculate_banner_diff(anniversary_date)
        translated_text = _('banner_text_anniversary')

    elif relationship_status_id == 2: # Verlobt
        anniversary_date = get_setting_by_name('anniversary_date').value
        enganment_date = get_setting_by_name('engaged_date').value
        if not enganment_date:
            return _('Please set your engagement date in the settings.')
        years_count, months_count, days_count, diffInMonthsTotal, diffInWeeksTotal, diffInDays = calculate_banner_diff(enganment_date)
        translated_text = _('banner_text_engaged')

        if not anniversary_date:
            return _('Please set your anniversary date in the settings.')

        banner_text = translated_text.format(
        relationship_status=relationship_status,
        years_count=years_count,
        months_count=months_count,
        days_count=days_count,
        diffInMonthsTotal=diffInMonthsTotal,
        diffInWeeksTotal=diffInWeeksTotal,
        diffInDays=diffInDays,
        anniversary_date=datetime.strptime(anniversary_date, "%Y-%m-%d").strftime("%d.%m.%Y") #TODO: Andere Sprache hat anders format! Ganzen Code betrachten
    )

    elif relationship_status_id == 3:
        wedding_date = get_setting_by_name('wedding_date').value
        if not wedding_date:
            return _('Please set your wedding date in the settings.')
        years_count, months_count, days_count, diffInMonthsTotal, diffInWeeksTotal, diffInDays = calculate_banner_diff(wedding_date)
        translated_text = _('banner_text_wedding')

    else:
        return None

    if relationship_status_id != 2:
        banner_text = translated_text.format(
            relationship_status=relationship_status,
            years_count=years_count,
            months_count=months_count,
            days_count=days_count,
            diffInMonthsTotal=diffInMonthsTotal,
            diffInWeeksTotal=diffInWeeksTotal,
            diffInDays=diffInDays
        )

    return banner_text


def _generate_banner_text_family():
    founding_date_setting = get_setting_by_name('family_founding_date')
    if not founding_date_setting or not founding_date_setting.value:
        return None

    years_count, months_count, days_count, diffInMonthsTotal, diffInWeeksTotal, diffInDays = calculate_banner_diff(founding_date_setting.value)
    translated_text = _('banner_text_family')

    return translated_text.format(
        years_count=years_count,
        months_count=months_count,
        days_count=days_count,
        diffInMonthsTotal=diffInMonthsTotal,
        diffInWeeksTotal=diffInWeeksTotal,
        diffInDays=diffInDays
    )


def _generate_banner_text_friends():
    founding_date_setting = get_setting_by_name('friend_group_founding_date')
    if not founding_date_setting or not founding_date_setting.value:
        return None

    years_count, months_count, days_count, diffInMonthsTotal, diffInWeeksTotal, diffInDays = calculate_banner_diff(founding_date_setting.value)
    translated_text = _('banner_text_friends')

    return translated_text.format(
        years_count=years_count,
        months_count=months_count,
        days_count=days_count,
        diffInMonthsTotal=diffInMonthsTotal,
        diffInWeeksTotal=diffInWeeksTotal,
        diffInDays=diffInDays
    )

def calculate_banner_diff(date):
    try:
        date_as_datetime = datetime.strptime(date, "%Y-%m-%d")
        diff = relativedelta(datetime.now(), date_as_datetime)

        # Berechne die Anzahl der Jahre, Monate und Tage
        years_count = f"1 " + _('Year') if diff.years == 1 else f"{diff.years} " + _('Years')
        months_count = f"1 " + _('Month') if diff.months == 1 else f"{diff.months} " + _('Months')
        days_count = f"1 " + _('Day') if diff.days == 1 else f"{diff.days} " + _('Days')

        # Berechne die Anzahl der Monate, Wochen und Tage
        diffInDays = (datetime.now() - date_as_datetime).days
        diffInMonthsTotal = diff.years * 12 + diff.months
        diffInWeeksTotal = diffInDays // 7

        return years_count, months_count, days_count, diffInMonthsTotal, diffInWeeksTotal, diffInDays
    
    except Exception as e:
        raise Exception(f'Error while calculating the banner diff: {e}')
    

def get_texts_for_translations():
    # Das Regex-Muster zum Suchen von Werten innerhalb des Regex
    pattern = re.compile(r"_\('([^']*)'\)")
    results = [] # Liste zum Speichern der Ergebnisse
    seen_matches = set()  # Set zum Vermeiden von Duplikaten
    directory = './' # Verzeichnis, in dem nach Übereinstimmungen gesucht werden soll

    # Lade die .gitignore-Muster, um unnötige Ordner auszuschließen
    gitignore_path = os.path.join(directory, '.gitignore')
    ignore_patterns = []

    # Prüfe, ob die .gitignore-Datei existiert und lade sie
    if os.path.exists(gitignore_path):
        with open(gitignore_path, 'r', encoding='utf-8') as f:
            ignore_patterns = [line.strip() for line in f if line.strip() and not line.startswith('#')]

    def should_ignore(file_path):
        # Überprüfe, ob die Datei ignoriert werden soll
        for pattern in ignore_patterns:
            if Path(file_path).match(pattern):
                return True
        return False

    SKIP_DIRS = {'.git', '__pycache__', 'node_modules', '.venv', 'venv'}
    BINARY_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.ico', '.webp', '.mp4', '.mov', '.zip', '.gz', '.db', '.sqlite', '.woff', '.woff2', '.ttf', '.eot', '.idx', '.pack', '.rev', '.ctl'}

    # Durchlaufe alle Dateien im angegebenen Verzeichnis
    for root, dirs, files in os.walk(directory):
        # Filtere Verzeichnisse, die in .gitignore stehen oder übersprungen werden
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not should_ignore(os.path.join(root, d))]

        for file in files:
            # Überprüfe, ob die Datei ignoriert werden soll
            file_path = os.path.join(root, file)
            if should_ignore(file_path):
                continue

            # Binärdateien überspringen
            ext = os.path.splitext(file)[1].lower()
            if ext in BINARY_EXTENSIONS:
                continue

            # Nur Dateien verarbeiten
            if '.' in file:
                try:
                    # Öffne die Datei und lese ihren Inhalt
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # Finde alle Übereinstimmungen im Dateitext
                        matches = pattern.findall(content)
                        # Speichere den Dateinamen und die extrahierten Werte
                        for match in matches:
                            # Entferne Leerzeichen am Ende des Textes, falls vorhanden
                            match = match.rstrip()
                            # Überprüfe, ob Wert schonmal vorkam
                            if match not in seen_matches:
                                results.append({
                                    'entityType': 'static', # os.path.splitext(file)[0],
                                    'fieldName': match
                                })
                                seen_matches.add(match)  # Markiere den match als gesehen
                except Exception as e:
                    log('warning', f'Error processing file for translation scan {file_path}: {e}')

    settings = get_all_settings()
    user_settings = get_all_user_settings()

    for setting in settings:
        results.append({
            'entityType': 'setting',
            'fieldName': setting.name
        })

    for user_setting in user_settings:
        results.append({
            'entityType': 'user_setting',
            'fieldName': user_setting.name
        })

    return results

def find_unmatched_translations():
    texts_for_translations = get_texts_for_translations()
    all_translations = get_translations_by_language('en-US') # Lade alle Standardübersetzungen

    # Erstelle ein Set für die Kombination aus entityType und fieldName für all_translations
    translations_set = set((item.entityType, item.fieldName) for item in all_translations)
    # Also track all fieldNames regardless of entityType to avoid UNIQUE conflicts
    all_field_names = set(item.fieldName for item in all_translations)

    # Finde die Einträge, die in texts_for_translations sind, aber nicht in translations_set
    unmatched_texts = [item for item in texts_for_translations
                       if (item['entityType'], item['fieldName']) not in translations_set
                       and item['fieldName'] not in all_field_names]

    return unmatched_texts

def export_data(mode, type, parameters):
    if mode == 'translation':
        if type == 'JSON':
            languageCode = parameters['languageCode']
            exportWithDbId = parameters['exportWithDbId']
            export_data = get_translations_by_language(languageCode)

            # Erstelle den Dateinamen für die JSON-Datei
            date = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            directory = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'export')
            file_name = f'{date}-export-translations-{languageCode}.json'
            json_file_path = os.path.join(directory, file_name)

            # Stelle sicher, dass das Verzeichnis existiert
            os.makedirs(os.path.dirname(json_file_path), exist_ok=True)

            # Extrahiere die relevanten Daten
            json_data = [
                {col: getattr(translation, col) for col in translation.__dict__ if not col.startswith('_')}
                for translation in export_data
            ]

            if exportWithDbId == False:
                for translation in json_data:
                    translation.pop('id')

            # Schreibe die Daten in die JSON-Datei
            with open(json_file_path, 'w') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=4)

            # Gib eine Erfolgsmeldung aus
            return file_name

