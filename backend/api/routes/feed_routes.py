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

from flask import request, jsonify, send_file
import os
import sys
import json
from datetime import datetime, timedelta

current_dir = os.path.dirname(os.path.abspath(__file__))

utils_dir = os.path.join(current_dir, '..', '..', 'utils')
sys.path.append(utils_dir)
from utils import create_logentry

# Import db_controller
database_dir = os.path.join(current_dir, '..', '..', 'database')
sys.path.append(database_dir)
from db_controller import DBController

# Import locales
locale_env = os.environ.get('LOCALE')
locales_dir = "locales"
file_path = os.path.join(locales_dir, locale_env + ".json")
with open(file_path, "r") as file:
    locale = json.load(file)

def feed_routes(app):

    @app.route('/upload/feed_items/<filename>')
    def upload_feed_items(filename):
        try:
            return send_file(f'../../upload/feed_items/{filename}')
        
        except Exception as e: 
            # File not found
            create_logentry('applog', 'error', 'feed_routes.py', str(e))
            return jsonify({'status': 'error', 'message': str(e)}), 404
    
    
    @app.route('/api/v1/feed', methods=['GET', 'POST'])
    def feed():
        if request.method == 'GET':
            try:

                with DBController():
                        result = DBController().fetch_feed_items()
        
                if isinstance(result, Exception):
                    # Fehler beim Datenbankzugriff
                    create_logentry('applog', 'error', 'feed_routes.py', str(result))
                    return jsonify({'status': 'error', 'message': str(result)}), 500
                else:
                    if 'Error' in result:
                        # Fehler beim Prüfen, Benutzername oder Passwort falsch
                        error_message = json.loads(result)['Error']
                        create_logentry('mainlog', 'error', 'feed_routes.py', error_message)
                        return jsonify({'status': 'error', 'message': error_message}), 200
                    else:
                        message = locale['feed_items_loaded_successful']
                        if app.config['DEBUG']:
                            create_logentry('mainlog', 'debug', 'feed_routes.py', message + " - data: " + str(json.loads(result)['feed_items']))
                        return jsonify({'status': 'success', 'message': message, 'data': json.loads(result)['feed_items']}), 200
        
            except Exception as e: 
                # Internal Server Error
                create_logentry('applog', 'error', 'feed_routes.py', str(e))
                return jsonify({'status': 'error', 'message': str(e)}), 500
        
        elif request.method == 'POST':
            try:
                title = request.form.get('title')
                content = request.form.get('content')
                contentType = request.form.get('contentType')
                contentURL = request.form.get('contentURL')
                dateCreated = request.form.get('dateCreated')

                if dateCreated == "":
                    current_datetime = datetime.now()
                    formatted_datetime = current_datetime.strftime("%Y-%m-%d %H:%M:%S")
                    dateCreated = formatted_datetime

                if title and content and contentType and dateCreated:

                    with DBController():
                        result = DBController().create_feed_item(title, content, contentType, contentURL, dateCreated)
                    
                    if isinstance(result, Exception):
                        # Fehler beim Datenbankzugriff
                        create_logentry('applog', 'error', 'feed_routes.py', str(result))
                        return jsonify({'status': 'error', 'message': str(result)}), 500
                    else:
                        if 'Error' in result:
                            error_message = json.loads(result)['Error']
                            create_logentry('mainlog', 'error', 'feed_routes.py', error_message)
                            return jsonify({'status': 'error', 'message': error_message}), 200
                        else:
                            message = locale['feed_item_saved_successful']
                            if app.config['DEBUG']:
                                create_logentry('mainlog', 'debug', 'feed_routes.py', message + " - item_id: " + str(json.loads(result)['item_id']) + " - title: " + title + " - content: " + content + " - contentType: " + contentType + " - contentURL: " + contentURL + " - dateCreated: " + dateCreated)
                            return jsonify({'status': 'success', 'message': message, 'data': json.loads(result)}), 200
            
                else:
                    message = locale['not_all_values_set']
                    create_logentry('applog', 'error', 'feed_routes.py', message)
                    return jsonify({'status': 'error', 'message': f'{message}'}), 400
    
            except Exception as e: 
                # Internal Server Error
                create_logentry('applog', 'error', 'feed_routes.py', str(e))
                return jsonify({'status': 'error', 'message': str(e)}), 500


    @app.route('/api/v1/feed/<item_id>', methods=['GET', 'PUT', 'DELETE'])
    def feed_by_id(item_id):
        if request.method == 'GET':
            try:

                if item_id:

                    with DBController():
                            result = DBController().fetch_feed_item_by_id(item_id)
            
                    if isinstance(result, Exception):
                        # Fehler beim Datenbankzugriff
                        create_logentry('applog', 'error', 'feed_routes.py', str(result))
                        return jsonify({'status': 'error', 'message': str(result)}), 500
                    else:
                        if 'Error' in result:
                            error_message = json.loads(result)['Error']
                            create_logentry('mainlog', 'error', 'feed_routes.py', error_message)
                            return jsonify({'status': 'error', 'message': error_message}), 200
                        else:
                            message = locale['feed_item_loaded_successful']
                            if app.config['DEBUG']:
                                create_logentry('mainlog', 'debug', 'feed_routes.py', message + " - item_id: " + item_id + " - data: " + str(json.loads(result)['feed_item']))
                            return jsonify({'status': 'success', 'message': message, 'data': json.loads(result)['feed_item']}), 200

                else:
                    message = locale['no_feed_item_id']
                    create_logentry('applog', 'error', 'feed_routes.py', message)
                    return jsonify({'status': 'error', 'message': f'{message}'}), 400

            except Exception as e: 
                # Internal Server Error
                create_logentry('applog', 'error', 'feed_routes.py', str(e))
                return jsonify({'status': 'error', 'message': str(e)}), 500

        elif request.method == 'PUT':
            try:
                title = request.form.get('title')
                content = request.form.get('content')
                contentType = request.form.get('contentType')
                contentURL = request.form.get('contentURL')
                dateCreated = request.form.get('dateCreated')

                if dateCreated == "":
                    current_datetime = datetime.now()
                    formatted_datetime = current_datetime.strftime("%Y-%m-%d %H:%M:%S")
                    dateCreated = formatted_datetime
                else :
                    dateCreated = datetime.strptime(dateCreated, "%Y-%m-%d")
                    dateCreated = dateCreated + timedelta(hours=0, minutes=0, seconds=0)
                    dateCreated = dateCreated.strftime("%Y-%m-%d %H:%M:%S")

                if title and content and contentType and dateCreated:

                    with DBController():
                        result = DBController().update_feed_item(item_id, title, content, contentType, contentURL, dateCreated)
                    
                    if isinstance(result, Exception):
                        # Fehler beim Datenbankzugriff
                        create_logentry('applog', 'error', 'feed_routes.py', str(result))
                        return jsonify({'status': 'error', 'message': str(result)}), 500
                    else:
                        if 'Error' in result:
                            error_message = json.loads(result)['Error']
                            create_logentry('mainlog', 'error', 'feed_routes.py', error_message)
                            return jsonify({'status': 'error', 'message': error_message}), 200
                        else:
                            message = locale['feed_item_updated_successful']
                            if app.config['DEBUG']:
                                create_logentry('mainlog', 'debug', 'feed_routes.py', message + " - item_id: " + item_id + " - title: " + title + " - content: " + content + " - contentType: " + contentType + " - contentURL: " + contentURL + " - dateCreated: " + dateCreated)
                            return jsonify({'status': 'success', 'message': message}), 200
            
                else:
                    message = locale['not_all_values_set']
                    create_logentry('applog', 'error', 'feed_routes.py', message)
                    return jsonify({'status': 'error', 'message': f'{message}'}), 400
    
            except Exception as e: 
                # Internal Server Error
                create_logentry('applog', 'error', 'feed_routes.py', str(e))
                return jsonify({'status': 'error', 'message': str(e)}), 500
        
        elif request.method == 'DELETE':
            try:

                with DBController():
                    result = DBController().delete_feed_item(item_id)
                
                if isinstance(result, Exception):
                    # Fehler beim Datenbankzugriff
                    create_logentry('applog', 'error', 'feed_routes.py', str(result))
                    return jsonify({'status': 'error', 'message': str(result)}), 500
                else:
                    if 'Error' in result:
                        error_message = json.loads(result)['Error']
                        create_logentry('mainlog', 'error', 'feed_routes.py', error_message)
                        return jsonify({'status': 'error', 'message': error_message}), 200
                    else:
                        message = locale['feed_item_deleted_successful']
                        if app.config['DEBUG']:
                            create_logentry('mainlog', 'debug', 'feed_routes.py', message + " - item_id: " + item_id)
                        return jsonify({'status': 'success', 'message': message}), 200
        
            except Exception as e: 
                # Internal Server Error
                create_logentry('applog', 'error', 'feed_routes.py', str(e))
                return jsonify({'status': 'error', 'message': str(e)}), 500