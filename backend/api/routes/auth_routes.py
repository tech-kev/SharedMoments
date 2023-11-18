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
import json
import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))

# Import utils
utils_dir = os.path.join(current_dir, '..', '..', 'utils')
sys.path.append(utils_dir)
from utils import create_logentry
from utils import check_password
from utils import check_setup_state
from utils import check_session_id

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

def auth_routes(app):

    @app.route('/api/v1/user', methods=['POST', 'PUT'])
    def user():        

        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')

            if username and password:
                with DBController():
                    result = DBController().create_user(username, password)

                if isinstance(result, Exception):
                    create_logentry('applog', 'error', 'auth_routes.py', str(result))
                    return jsonify({'status': 'error', 'message': str(result)}), 500
                else:
                    if 'Error' in result:
                        # Fehler beim Erstellen des Benutzers
                        error_message = json.loads(result)['Error']
                        create_logentry('mainlog', 'error', 'auth_routes.py', error_message)
                        return jsonify({'status': 'error', 'message': error_message}), 200
                    else:
                        # Benutzer erfolgreich erstellt
                        message = locale['password_saved_successful']
                        if app.config['DEBUG']:
                            create_logentry('mainlog', 'debug', 'auth_routes.py', message + " - Username: " + username + " - Passwort: " + password + " - Result: " + str(json.loads(result)))
                        return jsonify({'status': 'success', 'message': message, 'data': json.loads(result)}), 200
            else:
                # Nicht alle Variablen gefüllt
                message = locale['not_all_values_set']
                create_logentry('applog', 'error', 'auth_routes.py', message)
                return jsonify({'status': 'error', 'message': message}), 400

        elif request.method == 'PUT':
            try:
                username = request.form.get('username')
                password = request.form.get('password')

                if username and password:

                    with DBController():
                        result = DBController().update_user(username, password)
                    
                    if isinstance(result, Exception):
                        # Fehler beim Datenbankzugriff
                        create_logentry('applog', 'error', 'auth_routes.py', str(result))
                        return jsonify({'status': 'error', 'message': str(result)}), 500
                    else:
                        if 'Error' in result:
                            # Fehler beim Ändern des Benutzers
                            error_message = json.loads(result)['Error']
                            create_logentry('mainlog', 'error', 'auth_routes.py', error_message)
                            return jsonify({'status': 'error', 'message': error_message}), 200
                        else:
                            # Benutzer erfolgreich geändert
                            message = locale['password_updated_successful']
                            if app.config['DEBUG']:
                                create_logentry('mainlog', 'debug', 'auth_routes.py', message + " - Username: " + username + " - Passwort: " + password + " - Result: " + result)
                            return jsonify({'status': 'success', 'message': message}), 200
            
                else:
                    message = locale['not_all_values_set']
                    create_logentry('applog', 'error', 'auth_routes.py', message)
                    return jsonify({'status': 'error', 'message': f'{message}'}), 400
    
            except Exception as e: 
                # Internal Server Error
                create_logentry('applog', 'error', 'auth_routes.py', str(e))
                return jsonify({'status': 'error', 'message': str(e)}), 500
        

    @app.route('/api/v1/login', methods=['POST'])
    def login():
        try:

            username = request.form.get('username')
            password = request.form.get('password')

            if username and password:
                result = check_password(username, password)
        
                if isinstance(result, Exception):
                    # Fehler beim Datenbankzugriff
                    create_logentry('applog', 'error', 'auth_routes.py', str(result))
                    return jsonify({'status': 'error', 'message': str(result)}), 500
                else:
                    if 'Error' in result:
                        # Fehler beim Prüfen, Benutzername oder Passwort falsch
                        error_message = json.loads(result)['Error']
                        create_logentry('mainlog', 'error', 'auth_routes.py', error_message)
                        return jsonify({'status': 'error', 'message': error_message}), 200
                    else:
                        message = locale['login_successful']
                        if app.config['DEBUG']:
                            create_logentry('mainlog', 'debug', 'auth_routes.py', message + " - Username: " + username + " - Password: " + password + " - data: " + str(json.loads(result)))
                        return jsonify({'status': 'success', 'message': message, 'data': json.loads(result)}), 200
    
            else:
                message = message = locale['not_all_values_set']
                create_logentry('applog', 'error', 'auth_routes.py', message)
                return jsonify({'status': 'error', 'message': f'{message}'}), 400

        except Exception as e: 
            # Internal Server Error
            create_logentry('applog', 'error', 'auth_routes.py', str(e))
            return jsonify({'status': 'error', 'message': str(e)}), 500
       
    @app.route('/api/v1/session', methods=['GET', 'DELETE'])
    def session():
        if request.method == 'GET':
            try:
                session_id = request.args.get('session_id')

                if session_id:
                    result = check_session_id(session_id)

                    if result is True:
                        # Session-ID ist gültig
                        message = locale['session_id_is_valid']
                        if app.config['DEBUG']:
                            ip_addr = request.remote_addr
                            user_agent = request.headers.get('User-Agent')
                            create_logentry('applog', 'debug', 'auth_routes.py', message + " - Session_id: " + session_id + " - IP: " + ip_addr + " - User-Agent: " + user_agent)
                        return jsonify({'status': 'success', 'message': message}), 200

                    elif isinstance(result, Exception):
                        ip_addr = request.remote_addr
                        user_agent = request.headers.get('User-Agent')
                        create_logentry('applog', 'error', 'auth_routes.py', str(result) +  " - Session_id: " + session_id + " - IP: " + ip_addr + " - User-Agent: " + user_agent)
                        return jsonify({'status': 'error', 'message': str(result)}), 500
                    
                    else:
                        # Session-ID ist ungültig oder abgelaufen
                        ip_addr = request.remote_addr
                        user_agent = request.headers.get('User-Agent')
                        message = locale['session_id_is_invalid']
                        create_logentry('applog', 'error', 'auth_routes.py', message +  " - Session_id: " + session_id + " - IP: " + ip_addr + " - User-Agent: " + user_agent)
                        return jsonify({'status': 'error', 'message': message}), 401
                else:
                    # Session-ID ist ungültig oder abgelaufen
                    ip_addr = request.remote_addr
                    user_agent = request.headers.get('User-Agent')
                    message = locale['session_id_is_invalid']
                    create_logentry('applog', 'error', 'auth_routes.py', message +  " - Session_id: " + session_id + " - IP: " + ip_addr + " - User-Agent: " + user_agent)
                    return jsonify({'status': 'error', 'message': message}), 401
                
            except Exception as e: 
                # Internal Server Error
                create_logentry('applog', 'error', 'auth_routes.py', str(e))
                return jsonify({'status': 'error', 'message': str(e)}), 500


        elif request.method == 'DELETE':
            try:
                session_id = request.form.get('session_id')

                if session_id:

                    with DBController():
                        result = DBController().delete_session(session_id)

                    if isinstance(result, Exception):
                        # Fehler beim Datenbankzugriff
                        create_logentry('applog', 'error', 'auth_routes.py', str(result))
                        return jsonify({'status': 'error', 'message': str(result)}), 500
                    else:
                        if 'Error' in result:
                            # Session-ID nicht gelöscht
                            error_message = json.loads(result)['Error']
                            create_logentry('mainlog', 'error', 'auth_routes.py', error_message)
                            return jsonify({'status': 'error', 'message': error_message}), 200
                        else:
                            # Session-ID gelöscht
                            message = locale['session_id_is_valid']
                            create_logentry('mainlog', 'debug', 'auth_routes.py', message + " - session_id: " + session_id)
                            return jsonify({'status': 'success', 'message': message}), 200
            
                else:
                    message = locale['not_all_values_set']
                    create_logentry('applog', 'error', 'auth_routes.py', message)
                    return jsonify({'status': 'error', 'message': f'{message}'}), 400
    
            except Exception as e: 
                # Internal Server Error
                create_logentry('applog', 'error', 'auth_routes.py', str(e))
                return jsonify({'status': 'error', 'message': str(e)}), 500
        
    @app.route('/api/v1/setup', methods=['GET', 'PUT'])
    def setup():
        if request.method == 'GET':
            try:

                result = check_setup_state()
        
                if isinstance(result, Exception):
                    # Fehler beim Datenbankzugriff
                    create_logentry('applog', 'error', 'auth_routes.py', str(result))
                    return jsonify({'status': 'error', 'message': str(result)}), 500
                else:
                    if 'Error' in result:
                        # Fehler beim Laden des setup-states
                        error_message = json.loads(result)['Error']
                        create_logentry('mainlog', 'error', 'auth_routes.py', error_message)
                        return jsonify({'status': 'error', 'message': error_message}), 200
                    else:
                        # Setup-state abgeschlossen
                        message = locale['setup_completed']
                        if app.config['DEBUG']:
                            create_logentry('mainlog', 'debug', 'auth_routes.py', message)
                        return jsonify({'status': 'success', 'message': message}), 200
        
            except Exception as e: 
                # Internal Server Error
                create_logentry('applog', 'error', 'auth_routes.py', str(e))
                return jsonify({'status': 'error', 'message': str(e)}), 500
        
        elif request.method == 'PUT':
            try:
                option = "setup_complete"
                value = request.form.get('value') 

                if value:

                    with DBController():
                        result = DBController().update_option(option, value)
                    
                    if isinstance(result, Exception):
                        # Fehler beim Datenbankzugriff
                        create_logentry('applog', 'error', 'auth_routes.py', str(result))
                        return jsonify({'status': 'error', 'message': str(result)}), 500
                    else:
                        if 'Error' in result:
                            error_message = json.loads(result)['Error']
                            create_logentry('mainlog', 'error', 'auth_routes.py', error_message)
                            return jsonify({'status': 'error', 'message': error_message}), 200
                        else:

                            if value == "true":

                                with DBController():
                                    result = DBController().delete_session("setup_session")
                                
                                if isinstance(result, Exception):
                                    # Fehler beim Datenbankzugriff
                                    create_logentry('applog', 'error', 'auth_routes.py', str(result))
                                    raise Exception(str(result))
                                else:
                                    if 'Error' in result:
                                        error_message = json.loads(result)['Error']
                                        create_logentry('mainlog', 'error', 'auth_routes.py', error_message)
                                        raise Exception(str(result))
                                    else:
                                        message = locale['setup_finished']
                                        create_logentry('mainlog', 'info', 'auth_routes.py', message + " - setup_complete: " + value)
                                        return jsonify({'status': 'success', 'message': message}), 200
                    
                else:
                    message = locale['not_all_values_set']
                    create_logentry('applog', 'error', 'auth_routes.py', message)
                    return jsonify({'status': 'error', 'message': f'{message}'}), 400
    
            except Exception as e: 
                # Internal Server Error
                create_logentry('applog', 'error', 'auth_routes.py', str(e))
                return jsonify({'status': 'error', 'message': str(e)}), 500
