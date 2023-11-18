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

DER_BASE64_ENCODED_PUBLIC_KEY_FILE_PATH = os.path.abspath("keys/public_key.txt")
VAPID_PUBLIC_KEY = open(DER_BASE64_ENCODED_PUBLIC_KEY_FILE_PATH, "r+").read().strip("\n")


def push_routes(app):

    @app.route('/api/v1/push_token', methods=['GET', 'POST'])
    def push_token():
        if request.method == 'GET':
            try:

                with DBController():
                    result = DBController().fetch_push_token()
        
                if isinstance(result, Exception):
                    create_logentry('applog', 'error', 'push_routes.py', str(result))
                    return jsonify({'status': 'error', 'message': str(result)}), 500
                else:
                    if 'Error' in result:
                        error_message = json.loads(result)['Error']
                        create_logentry('mainlog', 'error', 'push_routes.py', error_message)
                        return jsonify({'status': 'error', 'message': error_message}), 200
                    else:
                        message = locale['token_loaded_successful']
                        if app.config['DEBUG']:
                            create_logentry('mainlog', 'debug', 'push_routes.py', message + " - data: " + str(json.loads(result)['tokens']))
                        return jsonify({'status': 'success', 'message': message, 'data': json.loads(result)['tokens']}), 200
        
            except Exception as e: 
                create_logentry('applog', 'error', 'push_routes.py', str(e))
                return jsonify({'status': 'error', 'message': str(e)}), 500
        
        elif request.method == 'POST':
            try:
                token = request.form.get('token') 

                if token:

                    with DBController():
                        result = DBController().fetch_push_token_by_token(token)

                    if isinstance(result, Exception):
                        create_logentry('applog', 'error', 'push_routes.py', str(result))
                        return jsonify({'status': 'error', 'message': str(result)}), 500
                    else:
                        if 'Error' in result:
                            with DBController():
                                result = DBController().create_push_token(token)
                            
                            if isinstance(result, Exception):
                                create_logentry('applog', 'error', 'push_routes.py', str(result))
                                return jsonify({'status': 'error', 'message': str(result)}), 500
                        
                            else:
                                if 'Error' in result:
                                    error_message = json.loads(result)['Error']
                                    create_logentry('mainlog', 'error', 'push_routes.py', error_message)
                                    return jsonify({'status': 'error', 'message': error_message}), 200
                                else:
                                    message = locale['token_saved_successful']
                                    if app.config['DEBUG']:
                                        create_logentry('mainlog', 'debug', 'push_routes.py', message + " - item_id: " + str(json.loads(result)['item_id']) + " - token: " + token)
                                    return jsonify({'status': 'success', 'message': message, 'data': json.loads(result)}), 200

                        else:
                            message = locale['token_available']
                            if app.config['DEBUG']:
                                create_logentry('mainlog', 'debug', 'push_routes.py', message + " - token: " + token)
                            return jsonify({'status': 'success', 'message': message, 'data': json.loads(result)}), 200
                else:
                    message = locale['not_all_values_set']
                    create_logentry('applog', 'error', 'push_routes.py', message)
                    return jsonify({'status': 'error', 'message': f'{message}'}), 400
    
            except Exception as e: 
                create_logentry('applog', 'error', 'push_routes.py', str(e))
                return jsonify({'status': 'error', 'message': str(e)}), 500


    @app.route('/api/v1/push_token/', methods=['GET', 'DELETE'])
    def push_token_by_id():
        if request.method == 'GET':
            try:
                token = ""
                with DBController():
                    result = DBController().fetch_push_token_by_token(token)
                
                if isinstance(result, Exception):
                    create_logentry('applog', 'error', 'push_routes.py', str(result))
                    return jsonify({'status': 'error', 'message': str(result)}), 500
                else:
                    if 'Error' in result:
                        error_message = json.loads(result)['Error']
                        create_logentry('mainlog', 'error', 'push_routes.py', error_message)
                        return jsonify({'status': 'error', 'message': error_message}), 200
                    
                    elif 'Done' in result:
                        message = locale['token_available']
                        if app.config['DEBUG']:
                            create_logentry('mainlog', 'debug', 'push_routes.py', message + " - token: " + token)
                        return jsonify({'status': 'success', 'message': message}), 200
        
            except Exception as e: 
                create_logentry('applog', 'error', 'push_routes.py', str(e))
                return jsonify({'status': 'error', 'message': str(e)}), 500
        
        elif request.method == 'DELETE':
            try:
                token = request.form.get('token') 
                
                with DBController():
                    result = DBController().delete_push_token(token)
                
                if isinstance(result, Exception):
                    create_logentry('applog', 'error', 'push_routes.py', str(result))
                    return jsonify({'status': 'error', 'message': str(result)}), 500
                else:
                    if 'Error' in result:
                        error_message = json.loads(result)['Error']
                        create_logentry('mainlog', 'error', 'push_routes.py', error_message)
                        return jsonify({'status': 'error', 'message': error_message}), 200
                    else:
                        message = locale['token_deleted_successful']
                        if app.config['DEBUG']:
                            create_logentry('mainlog', 'debug', 'push_routes.py', message + " - Token: " + token)
                        return jsonify({'status': 'success', 'message': message}), 200
        
            except Exception as e: 
                create_logentry('applog', 'error', 'push_routes.py', str(e))
                return jsonify({'status': 'error', 'message': str(e)}), 500
        
    @app.route("/api/v1/push_public_key/", methods=["GET"])
    def push_public_key():
        
        return jsonify({"public_key": VAPID_PUBLIC_KEY}), 200

    
        