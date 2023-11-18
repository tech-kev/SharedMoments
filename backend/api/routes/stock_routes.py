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

from flask import request, jsonify, send_file, Response
import os
import sys
import json
from pywebpush import webpush, WebPushException

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

def stock_routes(app):

    @app.route('/upload/stock_items/<filename>')
    def upload_stock_items(filename):
        try:
            return send_file(f'../../upload/stock_items/{filename}'), 200
        
        except Exception as e: 
            # File not found
            create_logentry('applog', 'error', 'stock_routes.py', str(e))
            return jsonify({'status': 'error', 'message': str(e)}), 404
        
    
    @app.route('/api/v1/settings/<option>', methods=['GET', 'PUT'])
    def settings(option):
        if request.method == 'GET':
            try:

                with DBController():
                        result = DBController().fetch_settings_by_option(option)
        
                if isinstance(result, Exception):
                    # Fehler beim Datenbankzugriff
                    create_logentry('applog', 'error', 'stock_routes.py', str(result))
                    return jsonify({'status': 'error', 'message': str(result)}), 500
                else:
                    if 'Error' in result:
                        error_message = json.loads(result)['Error']
                        create_logentry('mainlog', 'error', 'stock_routes.py', error_message)
                        return jsonify({'status': 'error', 'message': error_message}), 200
                    else:
                        message = locale['setting_loaded_successful']
                        if app.config['DEBUG']:
                            create_logentry('mainlog', 'debug', 'stock_routes.py', message + " - option: " + option + " - " + str(json.loads(result)['option']))
                        return jsonify({'status': 'success', 'message': message, 'data': json.loads(result)['option']}), 200
        
            except Exception as e: 
                # Internal Server Error
                create_logentry('applog', 'error', 'stock_routes.py', str(e))
                return jsonify({'status': 'error', 'message': str(e)}), 500
         
        elif request.method == 'PUT':
            try:
                
                value = request.form.get('value')
                specialvalue = request.form.get('specialvalue') 

                if value:

                    if value == "use_music":
                        with DBController():
                            result = DBController().update_use_music(specialvalue)
                    else:
                        with DBController():
                            result = DBController().update_option(option, value, specialvalue)
                    
                    if isinstance(result, Exception):
                        # Fehler beim Datenbankzugriff
                        create_logentry('applog', 'error', 'stock_routes.py', str(result))
                        return jsonify({'status': 'error', 'message': str(result)}), 500
                    else:
                        if 'Error' in result:
                            error_message = json.loads(result)['Error']
                            create_logentry('mainlog', 'error', 'stock_routes.py', error_message)
                            return jsonify({'status': 'error', 'message': error_message}), 200
                        else:
                            message = locale['setting_updated_successful']
                            if app.config['DEBUG']:
                                create_logentry('mainlog', 'debug', 'stock_routes.py', message + " - option: " + option + " - value: " + value + " - specialvalue: " + str(specialvalue))
                            
                            return jsonify({'status': 'success', 'message': message}), 200
            
                else:
                    message = locale['not_all_values_set']
                    create_logentry('applog', 'error', 'stock_routes.py', message)
                    return jsonify({'status': 'error', 'message': f'{message}'}), 400
    
            except Exception as e: 
                # Internal Server Error
                create_logentry('applog', 'error', 'stock_routes.py', str(e))
                return jsonify({'status': 'error', 'message': str(e)}), 500