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

from flask import send_file

def frontend_routes(app):
    @app.route('/setup')
    def setup_html():
        return send_file('../../frontend/sites/setup.html')
    
    @app.route('/')
    def home_html():
        return send_file('../../frontend/sites/home.html')

    @app.route('/login')
    def login_html():
        return send_file('../../frontend/sites/login.html')

    @app.route('/filmlist')
    def filmlist_html():
        return send_file('../../frontend/sites/filmlist.html')

    @app.route('/bucketlist')
    def bucketlist_html():
        return send_file('../../frontend/sites/bucketlist.html')

    @app.route('/galleryview')
    def galleyview_html():
        return send_file('../../frontend/sites/gallery.html')
    
    @app.route('/stats')
    def stats_html():
        return send_file('../../frontend/sites/stats.html')

    @app.route('/settings')
    def settings_html():
        return send_file('../../frontend/sites/settings.html')

    @app.route('/css/<filename>')
    def style_css(filename):
        return send_file(f'../../frontend/assets/css/{filename}')

    @app.route('/js/<filename>')
    def script_js(filename):
        return send_file(f'../../frontend/assets/js/{filename}')
    
    @app.route('/favicon.ico')
    def favicon():
        return send_file(f'../../frontend/assets/img/favicon.ico')
    
    @app.route('/icon.png')
    def icon():
        return send_file(f'../../frontend/assets/img/icon.png')

    @app.route("/swagger.json")
    def swagger_spec():
        return send_file('./swagger.json')