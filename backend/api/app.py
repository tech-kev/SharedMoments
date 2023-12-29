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

from flask import Flask, request, jsonify
import os
import sys
import json
current_dir = os.path.dirname(os.path.abspath(__file__))

available_locales = []

folder_path = os.path.join(current_dir, '..', '..', 'locales')

all_files = os.listdir(folder_path)

for filename in all_files: # Lade verfügbare Sprachen dynamisch aus dem Ordner
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

# Set Version Number
os.environ['VERSION'] = '1.3.0'

# Import logger
utils_dir = os.path.join(current_dir, '..', 'utils')
sys.path.append(utils_dir)
from utils import create_logentry
from utils import check_session_id

app = Flask(__name__)

if os.environ.get('DEBUG_MODE') == 'True':
    app.config['DEBUG'] = True
else:
    app.config['DEBUG'] = False


@app.before_request
def check_session():
    try:
        excluded_endpoints = ['login', 'session', 'setup', 'setup_html', 'login_html', 'home_html', 'filmlist_html', 'bucketlist_html', 'galleyview_html', 'settings_html', 'favicon', 'script_js', 'style_css', 'swagger_spec', 'locales']  # Liste der Endpunkte, die von der Überprüfung ausgenommen werden sollen
        session_id = request.cookies.get('session_id')
        if request.endpoint in excluded_endpoints:
            pass
        
        elif session_id:
            result = check_session_id(session_id)

            if result is True:
                # Session-ID ist gültig
                pass

            elif isinstance(result, Exception):
                create_logentry('applog', 'error', 'app.py', str(result))
                return jsonify({'status': 'error', 'message': str(result)}), 500
            
            else:
                # Session-ID ist ungültig oder abgelaufen
                ip_addr = request.remote_addr
                user_agent = request.headers.get('User-Agent')
                message = locale['session_id_is_invalid']
                create_logentry('applog', 'error', 'app.py', message + " - IP: " + ip_addr + " - User-Agent: "+ user_agent)
                return jsonify({'status': 'error', 'message': message}), 401
        else:
            # Session-ID ist ungültig oder abgelaufen
            ip_addr = request.remote_addr
            user_agent = request.headers.get('User-Agent')
            message = locale['session_id_is_invalid']
            create_logentry('applog', 'error', 'app.py', message + " - IP: " + ip_addr + " - User-Agent: "+ user_agent)
            return jsonify({'status': 'error', 'message': message}), 401
        
    except Exception as e: 
        # Internal Server Error
        create_logentry('applog', 'error', 'app.py', str(e))
        return jsonify({'status': 'error', 'message': str(e)}), 500
    

# Errorhandling für 404
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404

# Errorhandling für 500
@app.errorhandler(500)
def internal_server_error(error):
    create_logentry('app', 'error', 'app.py', f'{error}')
    return jsonify({'status': 'error', 'message': f'{error}'}), 500
    
if __name__ == '__main__':
    routes = os.path.join(current_dir, 'routes')
    sys.path.append(routes)
    from auth_routes import auth_routes
    from bucketlist_routes import bucketlist_routes
    from feed_routes import feed_routes
    from filmlist_routes import filmlist_routes
    from frontend_routes import frontend_routes
    from moments_routes import moments_routes
    from push_routes import push_routes
    from stock_routes import stock_routes
    from utils_routes import utils_routes
    from sidemenu_routes import sidemenu_routes
    from locales_routes import locales_routes
    from swagger_ui import swagger_ui
    
    auth_routes(app)
    bucketlist_routes(app)
    feed_routes(app)
    filmlist_routes(app)
    frontend_routes(app)
    moments_routes(app)
    push_routes(app)
    stock_routes(app)
    utils_routes(app)
    sidemenu_routes(app)
    locales_routes(app)
    app.register_blueprint(swagger_ui())

    
    app.run(host='0.0.0.0')
