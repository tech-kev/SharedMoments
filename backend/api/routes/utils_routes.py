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

from flask import jsonify, request
import requests
import json
import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))

# Importiere die erforderlichen Module
utils_dir = os.path.join(current_dir, '..', '..', 'utils')
sys.path.append(utils_dir)
from utils import anniversary_date
from utils import days_together
from utils import main_title
from utils import calculate_special_day
from utils import create_logentry
from utils import save_file
from utils import calculate_stats
from utils import create_push_notifications
from utils import wedding_date
from utils import relationship

# Import db_controller
database_dir = os.path.join(current_dir, '..', '..', 'database')
sys.path.append(database_dir)
from db_controller import DBController

locale_env = os.environ.get('LOCALE')

locales_dir = "locales"
file_path = os.path.join(locales_dir, locale_env + ".json")

with open(file_path, "r") as file:
    locale = json.load(file)

def utils_routes(app):

    @app.route('/api/v1/days_together', methods=['GET'])
    def days_together_text():
        try:

            text = days_together()
    
            if isinstance(text, Exception):
                # Fehler beim Datenbankzugriff
                create_logentry('applog', 'error', 'utils_routes.py', str(text))
                return jsonify({'status': 'error', 'message': str(text)}), 500
            else:
                if 'Error' in text:
                    error_message = json.loads(text)['Error']
                    create_logentry('mainlog', 'error', 'utils_routes.py', error_message)
                    return jsonify({'status': 'error', 'message': error_message}), 200
                else:
                    message = locale['days_together_text_loaded_sucessful']
                    if app.config['DEBUG']:
                        create_logentry('mainlog', 'debug', 'utils_routes.py', message + " - text: " + json.loads(text)['text'])
                    return jsonify({'status': 'success', 'message': message, 'data': json.loads(text)}), 200
    
        except Exception as e: 
            # Internal Server Error
            create_logentry('applog', 'error', 'utils_routes.py', str(e))
            return jsonify({'status': 'error', 'message': str(e)}), 500


    @app.route('/api/v1/anniversary_date', methods=['GET', 'PUT'])
    def anniversary_date_text():
        if request.method == 'GET': # Not in use
            try:

                date = anniversary_date()
        
                if isinstance(date, Exception):
                    # Fehler beim Datenbankzugriff
                    create_logentry('applog', 'error', 'utils_routes.py', str(date))
                    return jsonify({'status': 'error', 'message': str(date)}), 500
                else:
                    if 'Error' in date:
                        error_message = json.loads(date)['Error']
                        create_logentry('mainlog', 'error', 'utils_routes.py', error_message)
                        return jsonify({'status': 'error', 'message': error_message}), 200
                    else:
                        message = locale['aniversary_date_loaded_sucessful']
                        if app.config['DEBUG']:
                            create_logentry('mainlog', 'debug', 'utils_routes.py', message + " - anniversary date: " + json.loads(date)['anniversary_date'])
                        return jsonify({'status': 'success', 'message': message, 'data': json.loads(date)}), 200
        
            except Exception as e: 
                # Internal Server Error
                create_logentry('applog', 'error', 'utils_routes.py', str(e))               
                return jsonify({'status': 'error', 'message': str(e)}), 500
            
        elif request.method == 'PUT':
            try:
                option = "anniversary"
                value = request.form.get('value') 

                if value:

                    with DBController():
                        result = DBController().update_option(option, value)
                    
                    if isinstance(result, Exception):
                        # Fehler beim Datenbankzugriff
                        create_logentry('applog', 'error', 'utils_routes.py', str(result))
                        return jsonify({'status': 'error', 'message': str(result)}), 500
                    else:
                        if 'Error' in result:
                            error_message = json.loads(result)['Error']
                            create_logentry('mainlog', 'error', 'utils_routes.py', error_message)
                            return jsonify({'status': 'error', 'message': error_message}), 200
                        else:
                            message = locale['aniversary_date_updated_sucessful']
                            if app.config['DEBUG']:
                                create_logentry('mainlog', 'debug', 'utils_routes.py', message + " - anniversary date: " + value)
                            return jsonify({'status': 'success', 'message': message}), 200
            
                else:
                    message = locale['not_all_values_set']
                    create_logentry('applog', 'error', 'utils_routes.py', message)
                    return jsonify({'status': 'error', 'message': f'{message}'}), 400
    
            except Exception as e: 
                # Internal Server Error
                create_logentry('applog', 'error', 'utils_routes.py', str(e))
                return jsonify({'status': 'error', 'message': str(e)}), 500

        
    @app.route('/api/v1/main_title', methods=['GET', 'PUT'])
    def main_title_text():
        if request.method == 'GET':
            try:

                title = main_title()
        
                if isinstance(title, Exception):
                    # Fehler beim Datenbankzugriff
                    create_logentry('applog', 'error', 'utils_routes.py', str(title))
                    return jsonify({'status': 'error', 'message': str(title)}), 500
                else:
                    if 'Error' in title:
                        error_message = json.loads(title)['Error']
                        create_logentry('mainlog', 'error', 'utils_routes.py', error_message)
                        return jsonify({'status': 'error', 'message': error_message}), 200
                    else:
                        message = locale['main_title_loaded_sucessful']
                        if app.config['DEBUG']:
                            create_logentry('mainlog', 'debug', 'utils_routes.py', message + " - Main Title: " + json.loads(title)['mainTitle'])
                        return jsonify({'status': 'success', 'message': message, 'data': json.loads(title)}), 200
        
            except Exception as e: 
                # Internal Server Error
                create_logentry('applog', 'error', 'utils_routes.py', str(e))
            return jsonify({'status': 'error', 'message': str(e)}), 500
        
        elif request.method == 'PUT':
            try:
                option = "mainTitle"
                value = request.form.get('value') 

                if value:

                    with DBController():
                        result = DBController().update_option(option, value)
                    
                    if isinstance(result, Exception):
                        # Fehler beim Datenbankzugriff
                        create_logentry('applog', 'error', 'utils_routes.py', str(result))
                        return jsonify({'status': 'error', 'message': str(result)}), 500
                    else:
                        if 'Error' in result:
                            error_message = json.loads(result)['Error']
                            create_logentry('mainlog', 'error', 'utils_routes.py', error_message)
                            return jsonify({'status': 'error', 'message': error_message}), 200
                        else:
                            message = locale['main_title_updated_sucessful']
                            if app.config['DEBUG']:
                                create_logentry('mainlog', 'debug', 'utils_routes.py', message + " - Main Title: " + value)
                            return jsonify({'status': 'success', 'message': message}), 200
            
                else:
                    message = locale['not_all_values_set']
                    create_logentry('applog', 'error', 'utils_routes.py', message)
                    return jsonify({'status': 'error', 'message': f'{message}'}), 400
    
            except Exception as e: 
                # Internal Server Error
                create_logentry('applog', 'error', 'utils_routes.py', str(e))
                return jsonify({'status': 'error', 'message': str(e)}), 500
        

    @app.route('/api/v1/special_day', methods=['GET'])
    def special_day_text():
        try:

            result = calculate_special_day()
    
            if isinstance(result, Exception):
                # Fehler beim Datenbankzugriff
                create_logentry('applog', 'error', 'utils_routes.py', str(result))
                return jsonify({'status': 'error', 'message': str(result)}), 500
            else:
                if 'Error' in result:
                    error_message = json.loads(result)['Error']
                    create_logentry('mainlog', 'error', 'utils_routes.py', error_message)
                    return jsonify({'status': 'error', 'message': error_message}), 200
                else:
                    message = locale['special_day_loaded_sucessful']
                    if app.config['DEBUG']:
                        create_logentry('mainlog', 'debug', 'utils_routes.py', message + " - day_text: " + json.loads(result)['day_text'] + " - day: " + json.loads(result)['day'])
                    return jsonify({'status': 'success', 'message': message, 'data': json.loads(result)}), 200
    
        except Exception as e: 
            # Internal Server Error
            create_logentry('applog', 'error', 'utils_routes.py', str(e))
            return jsonify({'status': 'error', 'message': str(e)}), 500

    @app.route('/api/v1/upload', methods=['POST'])
    def upload():
        try:
            file = request.files['file']
            item_type = request.form.get('item_type') # feed_item or stock_item
            option = request.form.get('option') # 

            if file and item_type and option:

                result = save_file(file, item_type, option)
                
                if isinstance(result, Exception):
                    # Fehler beim Datenbankzugriff
                    create_logentry('applog', 'error', 'utils_routes.py', str(result))
                    return jsonify({'status': 'error', 'message': str(result)}), 500
                else:
                    if 'Error' in result:
                        error_message = json.loads(result)['Error']
                        create_logentry('mainlog', 'error', 'utils_routes.py', error_message)
                        return jsonify({'status': 'error', 'message': error_message}), 200
                    else:
                        message = locale['file_upload_sucessful']
                        if app.config['DEBUG']:
                            create_logentry('mainlog', 'debug', 'utils_routes.py', str(json.loads(result)['logmsg']))
                        return jsonify({'status': 'success', 'message': message, 'data': str(json.loads(result)['filepath'])}), 200
        
            else:
                message = locale['not_all_values_set']
                create_logentry('applog', 'error', 'utils_routes.py', message)
                return jsonify({'status': 'error', 'message': f'{message}'}), 400

        except Exception as e: 
            # Internal Server Error
            create_logentry('applog', 'error', 'utils_routes.py', str(e))
            return jsonify({'status': 'error', 'message': str(e)}), 500


    @app.route('/api/v1/stats', methods=['GET'])
    def stats():
        try:

            stats = calculate_stats()
    
            if isinstance(stats, Exception):
                # Fehler beim Datenbankzugriff
                create_logentry('applog', 'error', 'utils_routes.py', str(stats))
                return jsonify({'status': 'error', 'message': str(stats)}), 500
            else:
                if 'Error' in stats:
                    error_message = json.loads(stats)['Error']
                    create_logentry('mainlog', 'error', 'utils_routes.py', error_message)
                    return jsonify({'status': 'error', 'message': error_message}), 200
                else:
                    message = locale['stats_loaded_sucessful']
                    if app.config['DEBUG']:
                        create_logentry('mainlog', 'debug', 'utils_routes.py', message + " - data: " + str(json.loads(stats)))
                    return jsonify({'status': 'success', 'message': message, 'data': json.loads(stats)}), 200
    
        except Exception as e: 
            # Internal Server Error
            create_logentry('applog', 'error', 'utils_routes.py', str(e))
            return jsonify({'status': 'error', 'message': str(e)}), 500
        

    @app.route('/api/v1/import/<method>', methods=['GET'])
    def import_csv(method):
        try:
    
            with DBController():
                    result = DBController().import_from_csv(method)

            if isinstance(result, Exception):
                # Fehler beim Datenbankzugriff
                create_logentry('applog', 'error', 'utils_routes.py', str(result))
                return jsonify({'status': 'error', 'message': str(result)}), 500
            else:
                if 'Error' in result:
                    error_message = json.loads(result)['Error']
                    create_logentry('mainlog', 'error', 'utils_routes.py', error_message)
                    return jsonify({'status': 'error', 'message': error_message}), 200
                else:
                    message = locale['import_successful']
                    if app.config['DEBUG']:
                        create_logentry('mainlog', 'debug', 'utils_routes.py', message)
                    return jsonify({'status': 'success', 'message': message}), 200

        except Exception as e: 
            # Internal Server Error
            create_logentry('applog', 'error', 'utils_routes.py', str(e))
            return jsonify({'status': 'error', 'message': str(e)}), 500
        
    
    @app.route('/api/v1/export', methods=['GET'])
    def export_csv():
        try:
    
            with DBController():
                    result = DBController().export_to_csv()

            if isinstance(result, Exception):
                # Fehler beim Datenbankzugriff
                create_logentry('applog', 'error', 'utils_routes.py', str(result))
                return jsonify({'status': 'error', 'message': str(result)}), 500
            else:
                if 'Error' in result:
                    error_message = json.loads(result)['Error']
                    create_logentry('mainlog', 'error', 'utils_routes.py', error_message)
                    return jsonify({'status': 'error', 'message': error_message}), 200
                else:
                    message = locale['export_successful']
                    if app.config['DEBUG']:
                        create_logentry('mainlog', 'debug', 'utils_routes.py', message)
                    return jsonify({'status': 'success', 'message': message}), 200

        except Exception as e: 
            # Internal Server Error
            create_logentry('applog', 'error', 'utils_routes.py', str(e))
            return jsonify({'status': 'error', 'message': str(e)}), 500
        
    
    @app.route('/api/v1/send_push_notifications', methods=['GET'])
    def send_push_notifications():
        try:

            response = create_push_notifications()
    
            if isinstance(response, Exception):
                create_logentry('applog', 'error', 'utils_routes.py', str(response))
                return jsonify({'status': 'error', 'message': str(response)}), 500
            else:
                message = locale['send_push_done']
                if app.config['DEBUG']:
                    create_logentry('mainlog', 'debug', 'utils_routes.py', message)
                return jsonify({'status': 'success', 'message': message}), 200

        except Exception as e: 
            # Internal Server Error
            create_logentry('applog', 'error', 'utils_routes.py', str(e))               
            return jsonify({'status': 'error', 'message': str(e)}), 500
        
        
    @app.route('/api/v1/main_date', methods=['GET'])
    def main_date():
        if request.method == 'GET':
            try:

                relationship()

                if os.environ.get('WEDDING') == 'True': # Der Status ist verheiratet
                    date = json.loads(wedding_date())['wedding_date']
                else:
                    date = json.loads(anniversary_date())['anniversary_date']
        
                if isinstance(date, Exception):
                    # Fehler beim Datenbankzugriff
                    create_logentry('applog', 'error', 'utils_routes.py', str(date))
                    return jsonify({'status': 'error', 'message': str(date)}), 500
                else:
                    if 'Error' in date:
                        error_message = json.loads(date)['Error']
                        create_logentry('mainlog', 'error', 'utils_routes.py', error_message)
                        return jsonify({'status': 'error', 'message': error_message}), 200
                    else:
                        message = locale['wedding_date_loaded_sucessful']
                        if app.config['DEBUG']:
                            create_logentry('mainlog', 'debug', 'utils_routes.py', message + " - date: " + date)
                        return jsonify({'status': 'success', 'message': message, 'date': date}), 200
        
            except Exception as e: 
                # Internal Server Error
                create_logentry('applog', 'error', 'utils_routes.py', str(e))               
                return jsonify({'status': 'error', 'message': str(e)}), 500

    @app.route('/api/v1/check_new_release', methods=['GET'])
    def check_new_release():
        if request.method == 'GET':
            try:
                url = "https://api.github.com/repos/tech-kev/SharedMoments/releases/latest"
                response = requests.get(url)
                
                if response.status_code == 200:
                    latest_release = response.json()
                    latest_release_tag = latest_release['name']
                    
                    version = os.environ.get('VERSION')

                    if latest_release_tag > version:
                        new_version = True
                    else:
                        new_version = False
                        
                    data = {
                        'new_version': new_version,
                        'installed_version': version,
                        'latest_version': latest_release_tag
                    }
                    
                    message = locale['versionInfoLoadedSuccessful']
                    return jsonify({'status': 'success', 'message': message, 'data': data}), 200
                else:
                    message = locale['versionInfoLoadingFailed']
                    create_logentry('applog', 'error', 'utils_routes.py', message)
                    return jsonify({'status': 'error', 'message': message}), 503

            except Exception as e: 
                # Internal Server Error
                create_logentry('applog', 'error', 'utils_routes.py', str(e))               
                return jsonify({'status': 'error', 'message': str(e)}), 500

