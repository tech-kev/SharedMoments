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

import time
import os
import sys
from db_controller import DBController

# Check ob alle DB envs gesetzt sind
if not all([
    os.environ.get('MYSQL_HOST'),
    os.environ.get('MYSQL_PORT'),
    os.environ.get('MYSQL_DATABASE'),
    os.environ.get('MYSQL_USER'),
    os.environ.get('MYSQL_PASSWORD')
]):
    err_message = "Not all environment variables for the database connection are set! Please check the environment variables and restart the container."
    raise Exception(err_message)

current_dir = os.path.dirname(os.path.abspath(__file__))

# Import utils
utils_dir = os.path.join(current_dir, '..', 'utils')
sys.path.append(utils_dir)

def initialize_database():
    while True:
        try:
            print("DB Initalising started")
            with DBController():
                DBController().create_database() # Run DB init
            print("DB Initalising finished")
            break  # Exit the loop if the DB call is successful
        except Exception as e:
            print("DB Initalising failed:", str(e))
            print("Retrying in 2 seconds...")
            time.sleep(2)


initialize_database()

