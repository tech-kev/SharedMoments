# Copyright (C) 2023 techkev
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import datetime
from datetime import datetime
from dateutil.relativedelta import relativedelta
import logging
import subprocess
import json
import os
import sys
import bcrypt
import secrets
import asyncio
import time

from pywebpush import webpush, WebPushException
from telegrambot import send_telegram_message
from send_mail import sendEmail
from flask import jsonify, request

# Import locales
locale_env = os.environ.get('LOCALE')
locales_dir = "locales"
file_path = os.path.join(locales_dir, locale_env + ".json")
with open(file_path, "r") as file:
    locale = json.load(file)

current_dir = os.path.dirname(os.path.abspath(__file__))

# Import db_controller
database_dir = os.path.join(current_dir, '..', 'database')
sys.path.append(database_dir)
from db_controller import DBController

if os.environ.get('DEBUG_MODE') == 'True':
    debug = True
else:
    debug = False

import logging
import sys

def create_logentry(log_file, log_level, creator, message):
    logger = logging.getLogger()

    if debug:
        console_output = True  # Hier optional den Output in die Console aktivieren
    else:
        console_output = False

    # Definiere die Logdateien
    sharedmoments = f"{current_dir}/../../logs/sharedmoments.log"
    applog = f"{current_dir}/../../logs/app.log"
    #sharedmoments = f"{current_dir}/../../logs/sharedmoments.log"
    #sharedmoments = f"{current_dir}/../../logs/sharedmoments.log"

    # Wähle das richtige Logfile basierend auf dem übergebenen Logfile-Parameter
    if log_file == "mainlog":
        logfile = sharedmoments
    elif log_file == "applog":
        logfile = applog
    else:
        # Wenn kein gültiges Logfile übergeben wurde, verwende ein Standard-Logfile
        logfile = sharedmoments

    # Konvertiere den übergebenen Log-Level-String in das entsprechende logging-Level-Objekt
    log_level_obj = getattr(logging, log_level.upper(), logging.INFO)
    logger.setLevel(log_level_obj)

    # Erstelle einen FileHandler, um die Logeinträge in eine Datei zu schreiben
    file_handler = logging.FileHandler(logfile)
    file_handler.setLevel(log_level_obj)

    # Erstelle einen Formatter, um das Format der Logeinträge anzupassen
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(creator)s - %(message)s')
    file_handler.setFormatter(formatter)

    # Füge den FileHandler zum Logger hinzu
    logger.addHandler(file_handler)

    if console_output:
        # Erstelle einen StreamHandler, um die Logeinträge auf der Konsole auszugeben
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setLevel(log_level_obj)
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

    # Schreibe den Logeintrag
    extra = {'creator': creator}
    logger.log(log_level_obj, message, extra=extra)

    # Entferne den FileHandler vom Logger, um Ressourcen freizugeben
    logger.removeHandler(file_handler)

    if console_output:
        # Entferne den StreamHandler vom Logger, um Ressourcen freizugeben
        logger.removeHandler(stream_handler)


def check_session_id(session_id):
    try:
        with DBController():
            session = DBController().fetch_session_id(session_id)

        if session:
            # Session-ID vorhanden
            expiration = session[2]
            current_time = datetime.now()

            if current_time <= expiration:
                # Session-ID gültig
                return True
            
            else:
                # Session-ID abgelaufen
                return False
            
        else:
            # Session-ID ungültig
            return False
    
    except Exception as e:
        # Fehler beim Checken
        return e
    

def check_password(username, password):

    try:

        with DBController():
            userinfo_json = DBController().fetch_user_by_username(username)

        if userinfo_json:

            if 'Error' in userinfo_json:
                # Fehler beim Prüfen, Benutzername oder Passwort falsch
                return json.dumps({"Error": json.loads(userinfo_json)['Error']})
           
            else:
                # Gespeichertes Passwort-Hash und Salt aus der Datenbank abrufen
                userinfo = json.loads(userinfo_json)['userinfo']
                stored_password_hash = userinfo[3].encode('utf-8')
                salt = userinfo[2].encode('utf-8')
                salted_password = password.encode('utf-8') + salt

                if bcrypt.checkpw(salted_password, stored_password_hash):
                    # Das Passwort ist korrekt, eine Session-ID generieren
                    session_id = secrets.token_hex(16)
                    expiration = (datetime.now() + relativedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
                    last_login = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    ip_addr = request.remote_addr
                    user_agent = request.headers.get('User-Agent')

                    try:
                        with DBController():
                            DBController().create_session_id(session_id, expiration, last_login, ip_addr, user_agent)

                        return json.dumps({"session_id": session_id, "expiration": expiration})
                    
                    except Exception as e:
                        # Fehler bei der Überprüfung des Passworts
                        return json.dumps({"Error": str(e)})
                
                else:
                    raise Exception(locale['username_or_password_wrong'])
            
        else:
                raise Exception(locale['username_or_password_wrong'])
    
    except Exception as e:
        # Fehler bei der Überprüfung des Passworts
        return json.dumps({"Error": str(e)})


def check_setup_state():
    try:
        with DBController():
            result_json = DBController().fetch_settings_by_option('setup_complete')

        if result_json:

            if 'Error' in result_json:
                return json.dumps({"Error": json.loads(result_json)['Error']})
           
            else:
                setup_state = json.loads(result_json)['option']['value']
                
                if setup_state == "true":
                    message = locale['setup_completed']
                    return json.dumps({"message": message})
                    
                else:
                    raise Exception(locale['setup_incomplete'])
        else:
            raise Exception(locale['setup_incomplete'])
    
    except Exception as e:
        return json.dumps({"Error": str(e)})
    


def days_together():
    try:
        date = json.loads(anniversary_date())['anniversary_date']
        datumInHtml = datetime.strptime(date, "%Y-%m-%d")
        diff = relativedelta(datetime.now(), datumInHtml)

        
        with DBController():
            result_json = DBController().fetch_settings_by_option('relationship_status')

        if result_json:

            if 'Error' in result_json:
                raise Exception(locale['days_together_text_loaded_failed'])
                        
            else:
                relationship_status = json.loads(result_json)['option']['value']
                # Schreibe den ersten Buchstaben klein, damit das in den Text passt
                relationship_status = relationship_status[0].lower() + relationship_status[1:]

                if relationship_status == 'in einer Beziehung': # zusammen klingt im Text besser
                    relationship_status = 'zusammen'
                

        # Berechne die Anzahl der Jahre, Monate und Tage
        years_count = f"1 {locale['year']}" if diff.years == 1 else f"{diff.years} {locale['years']}"
        months_count = f"1 {locale['month']}" if diff.months == 1 else f"{diff.months} {locale['months']}"
        days_count = f"1 {locale['day']}" if diff.days == 1 else f"{diff.days} {locale['days']}"

        # Berechne die Anzahl der Monate, Wochen und Tage
        diffInDays = (datetime.now() - datumInHtml).days
        diffInMonthsTotal = diff.years * 12 + diff.months
        diffInWeeksTotal = diffInDays // 7

        text = locale['text'].format(
            years_count = years_count,
            months_count = months_count,
            days_count = days_count,
            relationship_status = relationship_status,
            diffInMonthsTotal = diffInMonthsTotal,
            diffInWeeksTotal = diffInWeeksTotal,
            diffInDays = diffInDays
        ) 

        return json.dumps({"text": text})

    except Exception as e:
        return json.dumps({"Error": str(e)})
    

def anniversary_date():
    try:
        result_json = DBController().fetch_settings_by_option('anniversary')

        if result_json:

            if 'Error' in result_json:
                return json.dumps({"Error": json.loads(result_json)['Error']})

            else:

                anniversary_date = json.loads(result_json)['option']['value']
            
            return json.dumps({"anniversary_date": anniversary_date})
        
        else:
            raise Exception(locale['anniversary_date_loaded_failed'])

    except Exception as e:
        return json.dumps({"Error": str(e)})
    

def main_title():
    try:
        result_json = DBController().fetch_settings_by_option('mainTitle')

        if result_json:

            if 'Error' in result_json:
                return json.dumps({"Error": json.loads(result_json)['Error']})

            else:

                mainTitle = json.loads(result_json)['option']['value']
            
            return json.dumps({"mainTitle": mainTitle})
        
        else:
            raise Exception(locale['main_title_loaded_failed'])

    except Exception as e:
        return json.dumps({"Error": str(e)})
    

def save_file(file, item_type, option):
    try:
        # Zielverzeichnis erstellen, falls es noch nicht existiert
        if item_type == "feed_item":
            target_dir = './upload/feed_items/'
        elif item_type == "stock_item":
            target_dir = './upload/stock_items/'
        else:
            raise Exception(locale['wrong_upload_type'])

        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
        
         # Datei im Zielverzeichnis speichern
        file_name, file_extension = os.path.splitext(file.filename)

        allowed_file_extensions = ['.jpg', '.jpeg', '.jfif', '.pjpeg', '.pjp', '.png']

        if item_type == "stock_item" and option != "music" and file_extension not in allowed_file_extensions:
            raise Exception(locale['invalid_filetype'])

        timestamp = str(int(time.time()))  # Aktueller Zeitstempel
        new_file_name = file_name + '_' + timestamp + file_extension
        file_path = os.path.join(target_dir, new_file_name)
        file.save(file_path)
        
        try:

            value = file_path
            specialvalue = ""

            if option == "music":
                specialvalue = "true" # Wenn Musik hochgeladen wird, soll der Button direkt angezeigt werden

            with DBController():
                result = DBController().update_option(option, value, specialvalue)
            
            if isinstance(result, Exception):
                # Fehler beim Datenbankzugriff
                create_logentry('mainlog', 'error', 'utils.py', str(result))
                raise Exception(str(result))
            else:
                if 'Error' in result:
                    error_message = json.loads(result)['Error']
                    create_logentry('mainlog', 'error', 'utils.py', error_message)
                    raise Exception(str(result))
                else:
                    message = locale['file_upload_sucessful']
                    logmsg = message + " - Option: " + option + " - Typ: " + item_type + " - Filepath: " + file_path
                    return json.dumps({"Done": message, "logmsg": logmsg, "filepath": file_path})
        
        except Exception as e:
            return json.dumps({"Error": str(e)})
    
    except Exception as e:
        return json.dumps({"Error": str(e)})
    

def create_push_notifications():

    try: # Call for WebPush

        with DBController():
            result = DBController().fetch_push_token()
        
        tokens = json.loads(result)['tokens']

        if debug:
            create_logentry("mainlog", "debug", 'utils.py', locale['token_loaded_successful'] +" " + str(tokens))
        
        if not tokens:
            raise Exception(locale['token_not_found'])

        title = locale['today_is_a_special_day']
        message = json.loads(days_together())['text']
        click_action = os.environ.get('DOMAIN_URL')

        if not click_action:
            click_action = "https://github.com/tech-kev/sharedmoments"
        

        DER_BASE64_ENCODED_PRIVATE_KEY_FILE_PATH = os.path.abspath("keys/private_key.txt")
        VAPID_PRIVATE_KEY = open(DER_BASE64_ENCODED_PRIVATE_KEY_FILE_PATH, "r+").readline().strip("\n")

        payload = json.dumps({
            "title": title,
            "message": message,
            "url": click_action
        })

        def send_web_push(subscription_information):
            return webpush(
                subscription_info=subscription_information,
                data=payload,
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims={
                    "sub": "mailto:mail@example.com"
                },
                ttl=86000
            )
        
        for token in tokens:

            try:
                response = send_web_push(json.loads(token['token']))
                if debug:
                    create_logentry("mainlog", "debug", 'utils.py', locale['webpush_response_code'] + ": " + str(response.status_code) + " - " + locale['status'] + ": " + str(response.reason))
                

            except WebPushException as ex:

                if ex.response.status_code == 410: #410 -> Nicht mehr registriert, also löschen
                    with DBController():
                        result = DBController().delete_push_token(token['token'])
                    create_logentry('mainlog', 'info', 'utils.py', locale['webpush_response_code'] + ': ' + str(ex.response.status_code) + ' - ' + locale['token_deleted'] + ': ' + str(token))

    except Exception as e:
        create_logentry("mainlog", "error", 'utils.py', str(e))

    
    if os.environ.get('TG_BOT_TOKEN') and os.environ.get('TG_CHAT_IDS'):

        try: # Call for Telegrambot
            bot_token = os.environ.get('TG_BOT_TOKEN')
            if debug:
                create_logentry("mainlog", "debug", 'utils.py', locale['telegrambot_token_found'] + ": " + bot_token)

            if not bot_token:
                raise Exception(locale['telegrambot_token_not_found'])

            async def main():
                result = await send_telegram_message(message)

                if 'Error' in result:
                        error_message = json.loads(result)['Error']
                        raise Exception(error_message)
                else:
                    msg = json.loads(result)['Done']
                    if debug:
                        create_logentry('mainlog', 'debug', 'utils.py', msg)

            asyncio.run(main())
        
        except Exception as e:
            create_logentry("mainlog", "error", 'utils.py', str(e))
        
    else:
        msg = locale['telegrambot_not_configured']
        create_logentry("mainlog", "info", 'utils.py', msg)

    if os.environ.get('MAIL_RECEIVER_MAILS'):

        try: # Call for E-Mail
            receiver = os.environ.get('MAIL_RECEIVER_MAILS')

            if not receiver:
                raise Exception(locale['mail_not_configured'])

            receiver_mails_env = os.environ.get('MAIL_RECEIVER_MAILS')
            if receiver_mails_env:
                    try:
                        receiver_mails = json.loads(receiver_mails_env)['receiver_mails']

                    except json.JSONDecodeError:
                        raise Exception(locale['receiver_mails_format_invalid'])
                    
                    for receiver_mail in receiver_mails:
                        result = sendEmail(receiver_mail, title, message)
                        if 'Error' in result:
                            error_message = json.loads(result)['Error']
                            raise Exception(error_message)
                        else:
                            msg = json.loads(result)['Done']
                            if debug:
                                create_logentry('mainlog', 'debug', 'utils.py', msg)

        except Exception as e:
            create_logentry("mainlog", "error", 'utils.py', str(e))
        
    else:
        message = locale['mail_not_configured']
        create_logentry("mainlog", "info", 'utils.py', message)

    return True

    
def calculate_special_day():
    try:
        unformattedDate = json.loads(anniversary_date())['anniversary_date']
        datumInHtml = datetime.strptime(unformattedDate, "%Y-%m-%d")
        # Berechne die Differenz zwischen dem heutigen Datum und dem Datum in der index.html
        heute = datetime.now()
        diff = relativedelta(heute, datumInHtml)

        # Berechne die Anzahl der Monate, Wochen und Tage
        diffInMonatenGesamt = diff.years * 12 + diff.months

        # Überprüfe, ob heute der Jahrestag ist
        if heute.month == datumInHtml.month and heute.day == datumInHtml.day:
            day = locale['anniversary_name_year']
            day_text = locale['anniversary_today_is_text'] + " " + day

        # Überprüfe, ob heute der Halbjahrestag ist
        elif diffInMonatenGesamt % 6 == 0 and heute.day == datumInHtml.day:
            day = locale['anniversary_name_halfyear']
            day_text = locale['anniversary_today_is_text'] + " " + day

        # Überprüfe, ob der heutige Tag dem Monatstag entspricht
        elif datetime.now().day == datumInHtml.day:
            day = locale['anniversary_name_month']
            day_text = locale['anniversary_today_is_text'] + " " + day

        # Wenn keine Nachricht zu senden ist, JSON Rückmeldung
        else:
            day_text = ""
            day = "None"

        return json.dumps({"day_text": day_text, "day": day})

    except Exception as e:
        return json.dumps({"Error": str(e)})
    

def calculate_stats():
    try:
        with DBController():
            userA_json = DBController().fetch_settings_by_option('userA')

        if userA_json:

            if 'Error' in userA_json:
                raise Exception(locale['usera_loading_failed'])
                        
            else:
                userA_name = json.loads(userA_json)['option']['value']
                userA_birthday = json.loads(userA_json)['option']['specialvalue']

        with DBController():
            userB_json = DBController().fetch_settings_by_option('userB')

        if userB_json:

            if 'Error' in userB_json:
                raise Exception(locale['userb_loading_failed'])
                        
            else:
                userB_name = json.loads(userB_json)['option']['value']
                userB_birthday = json.loads(userB_json)['option']['specialvalue']


        with DBController():
            anniversary_date_json = DBController().fetch_settings_by_option('anniversary')

        if anniversary_date_json:

            if 'Error' in anniversary_date_json:
                raise Exception(locale['anniversary_date_loaded_failed'])
                        
            else:
                anniversary_date = json.loads(anniversary_date_json)['option']['value']

        # Aktuelles Datum
        current_date = datetime.now().date()

        # Dauer in Tagen seit dem Geburtsdatum von User A und User B
        userA_lifetime = (current_date - datetime.strptime(userA_birthday, "%Y-%m-%d").date()).days
        userB_lifetime = (current_date - datetime.strptime(userB_birthday, "%Y-%m-%d").date()).days

        # Dauer in Tagen seit dem Anniversary-Datum
        relationship_duration = (current_date - datetime.strptime(anniversary_date, "%Y-%m-%d").date()).days

        # Prozentsatz der Lebenszeit als Paar für User A und User B
        userA_percentage = round((relationship_duration / userA_lifetime) * 100, 2)
        userB_percentage = round((relationship_duration / userB_lifetime) * 100, 2)

        # Ideen 
        # - Numerologie https://www.koordinaten-umrechner.de/lebenszahl-berechnen
        # - Anzahl hochgeladener Bilder

        data = {
            "userA": {
                "name": userA_name,
                "percentage": userA_percentage
            },
            "userB": {
                "name": userB_name,
                "percentage": userB_percentage
            }
        }

        return json.dumps(data)

    except Exception as e:
        return json.dumps({"Error": str(e)})