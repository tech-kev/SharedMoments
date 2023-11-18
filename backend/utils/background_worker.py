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

import os
import sys
import datetime
import time
import json
current_dir = os.path.dirname(os.path.abspath(__file__))

available_locales = []

folder_path = os.path.join(current_dir, '..', '..', 'locales')
# Alle Dateien im Ordner lesen
all_files = os.listdir(folder_path)

for filename in all_files:
    if filename.endswith('.json'):
        locale = os.path.splitext(filename)[0]
        available_locales.append(locale)

if not os.environ.get('LOCALE'):
    message = "No language specified in the ENVs! Defaulting to en-US. To change the language, set the environment variable 'LOCALE'!"
    print(message)
    os.environ['LOCALE'] = "en_US"

if not os.environ.get('LOCALE') in available_locales:
    message = os.environ.get('LOCALE') + " language is not available! Defaulting to en-US. To change the language, set the environment variable 'LOCALE'!"
    print(message)
    os.environ['LOCALE'] = "en_US"


# Import locales
locale_env = os.environ.get('LOCALE')
locales_dir = "locales"
file_path = os.path.join(locales_dir, locale_env + ".json")
with open(file_path, "r") as file:
    locale = json.load(file)

from utils import create_push_notifications
from utils import calculate_special_day
from utils import create_logentry
from utils import sendEmail

if os.environ.get('DEBUG_MODE') == 'True':
    debug = True
else:
    debug = False

if not os.environ.get('BW_TIME'):
    os.environ['BW_TIME'] = "6, 0, 0"

bw_time_tulpe = tuple(map(int, os.environ.get('BW_TIME').split(','))) # Mache aus String eine Tulpe

current_dir = os.path.dirname(os.path.abspath(__file__))

# Import db_controller
database_dir = os.path.join(current_dir, '..', 'database')
sys.path.append(database_dir)
from db_controller import DBController

def calculate_sleep_time():
    now = datetime.datetime.now()
    target_time = datetime.datetime(now.year, now.month, now.day, *bw_time_tulpe)  # Notiz: das "*" macht aus den 3 Elementen in der Tulpe (6, 0, 0) drei Einträge
    if now > target_time:
        target_time += datetime.timedelta(days=1)  # Wenn die Zielzeit bereits vergangen ist, auf den nächsten Tag verschieben
    time_difference = target_time - now
    sleep_time = time_difference.total_seconds()
    return sleep_time

while True:
    
    sleep_time = calculate_sleep_time()
    msg = f"{locale['sleep_for']} {sleep_time} s"
    print(msg)
    create_logentry("mainlog", "debug", "background_worker.py", msg)
    time.sleep(sleep_time)
        
    try:
        # DB Aufräumen
        with DBController():
            result = DBController().cleanup_database()

        if isinstance(result, Exception):
            # Fehler beim Datenbankzugriff
            raise Exception(str(result))
        else:
            if 'Error' in result:
                error_message = json.loads(result)['Error']
                raise Exception(str(result))
            else:
                message = locale['cleaning_script_number_of_deleted_files'] + ": " + str(json.loads(result)['deleted_files_count'])
                create_logentry("mainlog", "info", "background_worker.py", message)

                if json.loads(result)['missing_files_count'] > 0:

                    message = locale['handle_missing_mediafiles'] + ": " + locale['cleaning_script_number_of_missing_files'] + ": " + str(json.loads(result)['missing_files_count']) + " - " + locale['missing_mediafiles'] + ": " + str(json.loads(result)['missing_files'])
                    create_logentry("mainlog", "warning", "background_worker.py", message)

                    if os.environ.get('MAIL_ADMIN'):

                        try: # Call for E-Mail
                            admin_mails = os.environ.get('MAIL_ADMIN')

                            if not admin_mails:
                                raise Exception(locale['no_admin_mails_set'])

                            if admin_mails:
                                    try:
                                        receiver_mails = json.loads(admin_mails)['admin_mails']

                                    except json.JSONDecodeError:
                                        raise Exception(locale['admin_mails_format_invalid'])
                                    
                                    title = locale['mail_tile_missing_files']

                                    for receiver_mail in receiver_mails:
                                        result = sendEmail(receiver_mail, title, message)
                                        if 'Error' in result:
                                            error_message = json.loads(result)['Error']
                                            raise Exception(error_message)
                                        else:
                                            msg = json.loads(result)['Done']
                                            if debug:
                                                create_logentry('mainlog', 'debug', 'background_worker.py', msg)

                        except Exception as e:
                            create_logentry("mainlog", "error", 'background_worker.py', str(e))
                        
                    else:
                        message = locale['no_admin_mails_set']
                        create_logentry("mainlog", "info", 'background_worker.py', message)

                
    except Exception as e:
        create_logentry("mainlog", "error", "background_worker.py", str(e))
    
    try:
        # Prüfe, ob Push-Notifications gesendet werden müssen
        day = json.loads(calculate_special_day())['day']
        if day != "None":
            create_push_notifications()
    
    except Exception as e:
        create_logentry("mainlog", "error", "background_worker.py", str(e))


    
