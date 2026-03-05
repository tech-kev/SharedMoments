import glob
import json
from flask_caching import Cache
from flask import session, request
from app.models import SessionLocal, Translation
from app import app
from app.logger import log
from app.db_queries import get_all_translations, get_supported_languages, get_user_setting, get_translation
import os

# Initialize cache
cache = Cache(app, config={'CACHE_TYPE': 'simple'})

def load_translation_in_cache():
    translations = get_all_translations()

    for translation in translations:
        cache_key = f"translation:{translation.fieldName}:{translation.languageCode}"
        cache.set(cache_key, translation.translatedText)

    log('info', f'Loaded {len(translations)} translations into cache')

def _(fieldName):
    languageCode = os.environ['LANG']

    cache_key = f"translation:{fieldName}:{languageCode}"
    translation = cache.get(cache_key)

    if translation:
        return translation
    else:
        return get_translation(fieldName, languageCode)

def set_locale(userID=None):
    try:
        if userID is None:
            locale = request.accept_languages.best_match(get_supported_languages())
        else:
            locale = get_user_setting(userID, 'language').value

        if locale is None:
            locale = 'en'

        session['lang'] = locale
        os.environ['LANG'] = locale

        return True
    except Exception as e:
        log('error', f'Failed to set locale for user {userID}: {e}')
        raise Exception(f'Error while setting the locale: {e}')

def migrateTranslations(overwrite=False):
    db_session = SessionLocal()
    translation_files = glob.glob(os.path.join(os.path.dirname(__file__), 'translations', '*.json'))

    for file_path in translation_files:
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                translations = json.load(f)
            except Exception as e:
                log('error', f'Failed to parse translation file {file_path}: {e}')
                continue

        for translation_data in translations:
            entityType = translation_data['entityType']
            entityID = translation_data['entityID']
            languageCode = translation_data['languageCode']
            fieldName = translation_data['fieldName']
            translatedText = translation_data['translatedText']
            helpText = translation_data.get('helpText', None)

            existing_translation = db_session.query(Translation).filter_by(
                entityType=entityType,
                entityID=entityID,
                languageCode=languageCode,
                fieldName=fieldName
            ).first()

            if not existing_translation:
                new_translation = Translation(
                    entityType=entityType,
                    entityID=entityID,
                    languageCode=languageCode,
                    fieldName=fieldName,
                    translatedText=translatedText,
                    helpText=helpText
                )
                db_session.add(new_translation)
                log('debug', f'Inserting translation: {entityType} (ID: {entityID}), lang={languageCode}, field={fieldName}')

            elif existing_translation and overwrite:
                existing_translation.translatedText = translatedText
                existing_translation.helpText = helpText
                log('debug', f'Updating translation: {entityType} (ID: {entityID}), lang={languageCode}, field={fieldName}')

    try:
        db_session.commit()
    except Exception:
        db_session.rollback()
        # Retry one-by-one to handle concurrent workers
        for file_path in translation_files:
            with open(file_path, 'r', encoding='utf-8') as f:
                try:
                    translations = json.load(f)
                except Exception:
                    continue
            for translation_data in translations:
                try:
                    existing = db_session.query(Translation).filter_by(
                        entityType=translation_data['entityType'],
                        entityID=translation_data['entityID'],
                        languageCode=translation_data['languageCode'],
                        fieldName=translation_data['fieldName']
                    ).first()
                    if not existing:
                        db_session.add(Translation(
                            entityType=translation_data['entityType'],
                            entityID=translation_data['entityID'],
                            languageCode=translation_data['languageCode'],
                            fieldName=translation_data['fieldName'],
                            translatedText=translation_data['translatedText'],
                            helpText=translation_data.get('helpText', None)
                        ))
                        db_session.commit()
                except Exception:
                    db_session.rollback()
    log('info', 'Translation migration completed')
