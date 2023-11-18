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

from flask import request, jsonify
import os
import sys
import json

current_dir = os.path.dirname(os.path.abspath(__file__))

# Import utils
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

def moments_routes(app):

    @app.route('/api/v1/moments', methods=['GET', 'POST'])
    def moments():
        if request.method == 'GET':
            try:

                with DBController():
                    result = DBController().fetch_moments_items()
        
                if isinstance(result, Exception):
                    # Fehler beim Datenbankzugriff
                    create_logentry('applog', 'error', 'moments_routes.py', str(result))
                    return jsonify({'status': 'error', 'message': str(result)}), 500
                else:
                    if 'Error' in result:
                        error_message = json.loads(result)['Error']
                        create_logentry('mainlog', 'error', 'moments_routes.py', error_message)
                        return jsonify({'status': 'error', 'message': error_message}), 200
                    else:
                        message = locale['moments_items_loaded_successful']
                        if app.config['DEBUG']:
                            create_logentry('mainlog', 'debug', 'moments_routes.py', message + " - data: " + str(json.loads(result)['moments_items']))
                        return jsonify({'status': 'success', 'message': message, 'data': json.loads(result)['moments_items']}), 200
        
            except Exception as e: 
                # Internal Server Error
                create_logentry('applog', 'error', 'moments_routes.py', str(e))
                return jsonify({'status': 'error', 'message': str(e)}), 500
        
        elif request.method == 'POST':
            try:
                title = request.form.get('title') 
                date = request.form.get('date') 

                if title and date:

                    with DBController():
                        result = DBController().create_moments_item(title, date)
                    
                    if isinstance(result, Exception):
                        # Fehler beim Datenbankzugriff
                        create_logentry('applog', 'error', 'moments_routes.py', str(result))
                        return jsonify({'status': 'error', 'message': str(result)}), 500
                    else:
                        if 'Error' in result:
                            error_message = json.loads(result)['Error']
                            create_logentry('mainlog', 'error', 'moments_routes.py', error_message)
                            return jsonify({'status': 'error', 'message': error_message}), 200
                        else:
                            message = locale['moments_item_saved_successful']
                            if app.config['DEBUG']:
                                create_logentry('mainlog', 'debug', 'moments_routes.py', message + " - item_id: " + str(json.loads(result)['item_id']) + " - title: " + title + " - date: " + date)
                            return jsonify({'status': 'success', 'message': message, 'data': json.loads(result)}), 200
            
                else:
                    message = locale['not_all_values_set']
                    create_logentry('applog', 'error', 'moments_routes.py', message)
                    return jsonify({'status': 'error', 'message': f'{message}'}), 400
    
            except Exception as e: 
                # Internal Server Error
                create_logentry('applog', 'error', 'moments_routes.py', str(e))
                return jsonify({'status': 'error', 'message': str(e)}), 500

    @app.route('/api/v1/moments/<item_id>', methods=['GET', 'PUT', 'DELETE'])
    def moment_by_id(item_id):
        if request.method == 'GET':
            try:

                if item_id:

                    with DBController():
                            result = DBController().fetch_moment_item_by_id(item_id)
            
                    if isinstance(result, Exception):
                        # Fehler beim Datenbankzugriff
                        create_logentry('applog', 'error', 'moments_routes.py', str(result))
                        return jsonify({'status': 'error', 'message': str(result)}), 500
                    else:
                        if 'Error' in result:
                            error_message = json.loads(result)['Error']
                            create_logentry('mainlog', 'error', 'moments_routes.py', error_message)
                            return jsonify({'status': 'error', 'message': error_message}), 200
                        else:
                            message = locale['moments_item_loaded_successful']
                            if app.config['DEBUG']:
                                create_logentry('mainlog', 'debug', 'moments_routes.py', message + " - item_id: " + item_id + " - data: " + str(json.loads(result)['moment_item']))
                            return jsonify({'status': 'success', 'message': message, 'data': json.loads(result)['moment_item']}), 200

                else:
                    message = locale['no_moments_item_id']
                    create_logentry('applog', 'error', 'moments_routes.py', message)
                    return jsonify({'status': 'error', 'message': f'{message}'}), 400

            except Exception as e: 
                # Internal Server Error
                create_logentry('applog', 'error', 'moments_routes.py', str(e))
                return jsonify({'status': 'error', 'message': str(e)}), 500

        elif request.method == 'PUT':
            try:
                title = request.form.get('title') 
                date = request.form.get('date')

                if title and date:

                    with DBController():
                        result = DBController().update_moments_item(item_id, title, date)
                    
                    if isinstance(result, Exception):
                        # Fehler beim Datenbankzugriff
                        create_logentry('applog', 'error', 'moments_routes.py', str(result))
                        return jsonify({'status': 'error', 'message': str(result)}), 500
                    else:
                        if 'Error' in result:
                            error_message = json.loads(result)['Error']
                            create_logentry('mainlog', 'error', 'moments_routes.py', error_message)
                            return jsonify({'status': 'error', 'message': error_message}), 200
                        else:
                            message = locale['moments_item_updated_successful']
                            if app.config['DEBUG']:
                                create_logentry('mainlog', 'debug', 'moments_routes.py', message + " - item_id: " + item_id + " - title: " + title + " - date: " + date)
                            return jsonify({'status': 'success', 'message': message}), 200
            
                else:
                    message = locale['not_all_values_set']
                    create_logentry('applog', 'error', 'moments_routes.py', message)
                    return jsonify({'status': 'error', 'message': f'{message}'}), 400
    
            except Exception as e: 
                # Internal Server Error
                create_logentry('applog', 'error', 'moments_routes.py', str(e))
                return jsonify({'status': 'error', 'message': str(e)}), 500
        
        elif request.method == 'DELETE':
            try:

                with DBController():
                    result = DBController().delete_moments_item(item_id)
                
                if isinstance(result, Exception):
                    # Fehler beim Datenbankzugriff
                    create_logentry('applog', 'error', 'moments_routes.py', str(result))
                    return jsonify({'status': 'error', 'message': str(result)}), 500
                else:
                    if 'Error' in result:
                        error_message = json.loads(result)['Error']
                        create_logentry('mainlog', 'error', 'moments_routes.py', error_message)
                        return jsonify({'status': 'error', 'message': error_message}), 200
                    else:
                        message = locale['moments_item_deleted_successful']
                        if app.config['DEBUG']:
                            create_logentry('mainlog', 'debug', 'moments_routes.py', message + " - item_id: " + item_id)
                        return jsonify({'status': 'success', 'message': message}), 200
        
            except Exception as e: 
                # Internal Server Error
                create_logentry('applog', 'error', 'moments_routes.py', str(e))
                return jsonify({'status': 'error', 'message': str(e)}), 500

