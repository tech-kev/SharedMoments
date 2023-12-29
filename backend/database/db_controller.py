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

import mysql.connector
import bcrypt
import secrets
import datetime
import json
import csv
from datetime import datetime
import os
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

class DBController:
    def __init__(self):
        try:
            self.connection = mysql.connector.connect(
                host=os.environ.get('MYSQL_HOST'),
                port=os.environ.get('MYSQL_PORT'),
                user=os.environ.get('MYSQL_USER'),
                password=os.environ.get('MYSQL_PASSWORD'),
                database=os.environ.get('MYSQL_DATABASE')
            )
            self.cursor = self.connection.cursor()
        except mysql.connector.Error as e:
            error_message = str(e)
            return (locale['database_connection_failed'] + ": ", error_message)
            

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_connection()

    #Import/export
    def export_to_csv(self):
        try:
            tables = ['bucketlist_items', 'feed_items', 'filmlist_items', 'moments_items', 'settings', 'sidemenu', 'users']

            for table in tables:
                filename = f"{table}.csv"
                export_path = os.path.join(current_dir, '..', '..', 'data_transfer/')
                os.makedirs(export_path, exist_ok=True)

                filepath = export_path+filename

                with open(filepath, 'w', newline='') as csvfile:
                    writer = csv.writer(csvfile, delimiter='\t')

                    query = f"SELECT * FROM {table}"
                    self.cursor.execute(query)
                    rows = self.cursor.fetchall()

                    writer.writerow([column[0] for column in self.cursor.description])
                    writer.writerows(rows)

            return "done"
        
        except mysql.connector.Error as e:

            return json.dumps({"Error": str(e)})

    def import_from_csv(self, mode="normal"):
        try:
            tables = ['bucketlist_items', 'feed_items', 'filmlist_items', 'moments_items', 'settings', 'sidemenu', 'users']
            export_path = os.path.join(current_dir, '..', '..', 'data_transfer/')

            counter = 0

            if mode == "setup":
                # Check if all tables have a corresponding file
                missing_files = [table for table in tables if f"{table}.csv" not in os.listdir(export_path)]
                if missing_files:
                    return json.dumps({"Error": f"{locale['import_files_missing']}: {', '.join(missing_files)}"})

            for filename in os.listdir(export_path):
                if filename.endswith('.csv'):
                    table_name = os.path.splitext(filename)[0]
                    if table_name in tables:
                        filepath = os.path.join(export_path, filename)

                        with open(filepath, 'r') as csvfile:
                            reader = csv.reader(csvfile, delimiter='\t')
                            data = list(reader)  # Convert the Reader to a list

                            self.cursor.execute(f"DELETE FROM {table_name}")

                            if not data:
                                break # If Import-File is empty, stop with this table

                            columns = data[0]  # First row contains column names
                            placeholders = ', '.join(['%s'] * len(columns))
                            query = f"INSERT INTO {table_name} VALUES ({placeholders})"
                            self.cursor.executemany(query, data[1:])  # Pass data starting from the second row
                            counter += 1

                            if table_name == 'settings': # Since Version 1.2.0 there is a new setting. If it isn't in the import-file, we add it here.
                                query = "INSERT IGNORE INTO `settings` (`id`, `option`, `value`, `specialvalue`, `dateCreated`, `dateModified`) VALUES (%s, %s, %s, %s, %s, %s)"
                                values = (10, 'wedding_date', '', '', '2023-09-29 22:10:08', '2023-10-03 21:04:29')
                                self.cursor.execute(query, values)

            self.connection.commit()

            if counter == 0:
                return json.dumps({"Error": locale['no_valid_import_files']})

            return "done"

        except mysql.connector.Error as e:
            return json.dumps({"Error": str(e)})




    # INSERT Operationen
    def create_feed_item(self, title, content, contentType, contentURL, dateCreated): 
        try:
            query = "INSERT INTO feed_items (title, content, contentType, contentURL, dateCreated) VALUES (%s, %s, %s, %s, %s)"
            values = (title, content, contentType, contentURL, dateCreated)
            self.cursor.execute(query, values)
            self.connection.commit()
            item_id = self.cursor.lastrowid
            return json.dumps({"item_id": item_id})
        
        except mysql.connector.Error as e:
            return json.dumps({"Error": str(e)})

    def create_bucketlist_item(self, title): 
        try:
            query = "INSERT INTO bucketlist_items (title) VALUES (%s)"
            values = (title,)
            self.cursor.execute(query, values)
            self.connection.commit()
            item_id = self.cursor.lastrowid
            return json.dumps({"item_id": item_id})
        
        except mysql.connector.Error as e:
            return json.dumps({"Error": str(e)})

    def create_filmlist_item(self, title): 
        try:
            query = "INSERT INTO filmlist_items (title) VALUES (%s)"
            values = (title,)
            self.cursor.execute(query, values)
            self.connection.commit()
            item_id = self.cursor.lastrowid
            return json.dumps({"item_id": item_id})
        
        except mysql.connector.Error as e:
            return json.dumps({"Error": str(e)})

    def create_moments_item(self, title, date): 
        try:
            query = "INSERT INTO moments_items (title, date) VALUES (%s, %s)"
            values = (title, date,)
            self.cursor.execute(query, values)
            self.connection.commit()
            item_id = self.cursor.lastrowid
            return json.dumps({"item_id": item_id})
        
        except mysql.connector.Error as e:
            return json.dumps({"Error": str(e)})

    def create_push_token(self, token): 
        try:
            query = "INSERT INTO pushtokens (token) VALUES (%s)"
            values = (token,)
            self.cursor.execute(query, values)
            self.connection.commit()
            item_id = self.cursor.lastrowid
            return json.dumps({"item_id": item_id})
        except mysql.connector.Error as e:
            return json.dumps({"Error": str(e)})

    def create_session_id(self, session_id, expiration, last_login, ip_addr, user_agent): 
        try:
            query = "INSERT INTO sessions (session_id, expiration, last_login, ip_addr, user_agent) VALUES (%s, %s, %s, %s, %s)"
            values = (session_id, expiration, last_login, ip_addr, user_agent)
            self.cursor.execute(query, values)
            self.connection.commit()
            session_id = self.cursor.lastrowid
            return json.dumps({"session_id": session_id})
        except mysql.connector.Error as e:
            return json.dumps({"Error": str(e)})
    
    def create_user(self, username, password):
        try:
            salt = secrets.token_hex(16)
            salted_password = password.encode('utf-8') + salt.encode('utf-8')
            password_hash = bcrypt.hashpw(salted_password, bcrypt.gensalt())
            query = "INSERT INTO users (username, password_salt, password_hash) VALUES (%s, %s, %s)"
            values = (username, salt, password_hash)
            self.cursor.execute(query, values)
            self.connection.commit()
            user_id = self.cursor.lastrowid
            return json.dumps({"user_id": user_id})
        except mysql.connector.Error as e:
            return json.dumps({"Error": str(e)})
        
    def create_sidemenu_item(self, custom_id, menu, href, icon): 
        try:
            query = "INSERT INTO sidemenu (custom_id, menu, href, icon) VALUES (%s, %s, %s, %s)"
            values = (custom_id, menu, href, icon)
            self.cursor.execute(query, values)
            self.connection.commit()
            item_id = self.cursor.lastrowid
            return json.dumps({"item_id": item_id})
        
        except mysql.connector.Error as e:
            return json.dumps({"Error": str(e)})

    # UPDATE Operationen
    def update_feed_item(self, item_id, title, content, contentType, contentURL, dateCreated): 
        try:
            query = "UPDATE feed_items SET title = %s, content = %s, contentType = %s, contentURL = %s, dateCreated = %s WHERE id = %s"
            values = (title, content, contentType, contentURL, dateCreated, item_id)
            self.cursor.execute(query, values)
            self.connection.commit()
            return "done"

        except mysql.connector.Error as e:
            return json.dumps({"Error": str(e)})

    def update_bucketlist_item(self, item_id, title, done): 
        try:
            query = "UPDATE bucketlist_items SET title = %s, done = %s WHERE id = %s"
            values = (title, done, item_id)
            self.cursor.execute(query, values)
            self.connection.commit()
            return "done"

        except mysql.connector.Error as e:
            return json.dumps({"Error": str(e)})

    def update_filmlist_item(self, item_id, title, done): 
        try:
            query = "UPDATE filmlist_items SET title = %s, done = %s WHERE id = %s"
            values = (title, done, item_id)
            self.cursor.execute(query, values)
            self.connection.commit()
            return "done"

        except mysql.connector.Error as e:
            return json.dumps({"Error": str(e)})

    def update_moments_item(self, item_id, title, date): 
        try:
            query = "UPDATE moments_items SET title = %s, date = %s WHERE id = %s"
            values = (title, date, item_id)
            self.cursor.execute(query, values)
            self.connection.commit()
            return "done"

        except mysql.connector.Error as e:
            return json.dumps({"Error": str(e)})
        

    def update_option(self, option, value, specialvalue=""): 
        try:
            query = "UPDATE `settings` SET value = %s, specialvalue = %s WHERE `option` = %s"
            values = (value, specialvalue, option)
            self.cursor.execute(query, values)
            self.connection.commit()
            return "done"

        except mysql.connector.Error as e:
            return json.dumps({"Error": str(e)})

    def update_use_music(self, specialvalue): 
        try:
            option = "music"
            query = "UPDATE `settings` SET specialvalue = %s WHERE `option` = %s"
            values = (specialvalue, option)
            self.cursor.execute(query, values)
            self.connection.commit()
            return "done"

        except mysql.connector.Error as e:
            return json.dumps({"Error": str(e)})

    def update_user(self, username, password): 
        try:
            salt = secrets.token_hex(16)
            salted_password = password.encode('utf-8') + salt.encode('utf-8')
            password_hash = bcrypt.hashpw(salted_password, bcrypt.gensalt())
            query = "UPDATE users SET password_salt = %s, password_hash = %s WHERE username = %s"
            values = (salt, password_hash, username)
            self.cursor.execute(query, values)
            self.connection.commit()
            return "done"

        except mysql.connector.Error as e:
            return json.dumps({"Error": str(e)})
        
    def update_sidemenu_item(self, item_id, custom_id, menu, href, icon): 
        try:
            query = "UPDATE sidemenu SET custom_id = %s, menu = %s, href = %s, icon = %s WHERE id = %s"
            values = (custom_id, menu, href, icon, item_id)
            self.cursor.execute(query, values)
            self.connection.commit()
            return "done"

        except mysql.connector.Error as e:
            return json.dumps({"Error": str(e)})

    # SELECT Operationen
    def fetch_feed_items(self):
        try:
            query = "SELECT * FROM feed_items ORDER BY dateCreated DESC;"
            self.cursor.execute(query)
            result = self.cursor.fetchall()
            columns = [desc[0] for desc in self.cursor.description]
            feed_items = []
            
            for row in result:
                item = {}
                for i in range(len(columns)):
                    column_name = columns[i]
                    column_value = row[i]
                    
                    # Konvertiere datetime-Objekte in Zeichenketten
                    if isinstance(column_value, datetime):
                        column_value = column_value.strftime("%Y-%m-%dT%H:%M:%SZ")
                    
                    item[column_name] = column_value
                
                feed_items.append(item)

            return json.dumps({"feed_items": feed_items})
        
        except mysql.connector.Error as e:
            return json.dumps({"Error": str(e)})

    def fetch_feed_item_by_id(self, id): 
        try:
            query = "SELECT * FROM feed_items WHERE id = %s"
            self.cursor.execute(query, (id,))
            result = self.cursor.fetchall()
            columns = [desc[0] for desc in self.cursor.description]
            feed_item = []
            
            for row in result:
                item = {}
                for i in range(len(columns)):
                    column_name = columns[i]
                    column_value = row[i]
                    
                    # Konvertiere datetime-Objekte in Zeichenketten
                    if isinstance(column_value, datetime):
                        column_value = column_value.strftime("%Y-%m-%dT%H:%M:%SZ")
                    
                    item[column_name] = column_value
                
                feed_item.append(item)

            return json.dumps({"feed_item": feed_item})
        
        except mysql.connector.Error as e:
            return json.dumps({"Error": str(e)})

    def fetch_bucketlist_items(self): 
        try:
            query = "SELECT * FROM bucketlist_items"
            self.cursor.execute(query)
            result = self.cursor.fetchall()
            columns = [desc[0] for desc in self.cursor.description]
            bucketlist_items = []
            
            for row in result:
                item = {}
                for i in range(len(columns)):
                    column_name = columns[i]
                    column_value = row[i]
                    
                    # Konvertiere datetime-Objekte in Zeichenketten
                    if isinstance(column_value, datetime):
                        column_value = column_value.strftime("%Y-%m-%dT%H:%M:%SZ")
                    
                    item[column_name] = column_value
                
                bucketlist_items.append(item)

            return json.dumps({"bucketlist_items": bucketlist_items})
        
        except mysql.connector.Error as e:
            return json.dumps({"Error": str(e)})

    def fetch_filmlist_items(self): 
        try:
            query = "SELECT * FROM filmlist_items"
            self.cursor.execute(query)
            result = self.cursor.fetchall()
            columns = [desc[0] for desc in self.cursor.description]
            filmlist_items = []
            
            for row in result:
                item = {}
                for i in range(len(columns)):
                    column_name = columns[i]
                    column_value = row[i]
                    
                    # Konvertiere datetime-Objekte in Zeichenketten
                    if isinstance(column_value, datetime):
                        column_value = column_value.strftime("%Y-%m-%dT%H:%M:%SZ")
                    
                    item[column_name] = column_value
                
                filmlist_items.append(item)

            return json.dumps({"filmlist_items": filmlist_items})
        
        except mysql.connector.Error as e:
            return json.dumps({"Error": str(e)})

    def fetch_moments_items(self): 
        try:
            query = "SELECT * FROM moments_items ORDER BY date"
            self.cursor.execute(query)
            result = self.cursor.fetchall()
            columns = [desc[0] for desc in self.cursor.description]
            moments_items = []
            
            for row in result:
                item = {}
                for i in range(len(columns)):
                    column_name = columns[i]
                    column_value = row[i]
                    
                    # Konvertiere datetime-Objekte in Zeichenketten
                    if isinstance(column_value, datetime):
                        column_value = column_value.strftime("%Y-%m-%dT%H:%M:%SZ")
                    
                    item[column_name] = column_value
                
                moments_items.append(item)

            return json.dumps({"moments_items": moments_items})
        
        except mysql.connector.Error as e:
            return json.dumps({"Error": str(e)})
        
    
    def fetch_moment_item_by_id(self, id): 
        try:
            query = "SELECT * FROM moments_items WHERE id = %s"
            self.cursor.execute(query, (id,))
            result = self.cursor.fetchall()
            columns = [desc[0] for desc in self.cursor.description]
            moment_item = []
            
            for row in result:
                item = {}
                for i in range(len(columns)):
                    column_name = columns[i]
                    column_value = row[i]
                    
                    # Konvertiere datetime-Objekte in Zeichenketten
                    if isinstance(column_value, datetime):
                        column_value = column_value.strftime("%Y-%m-%dT%H:%M:%SZ")
                    
                    item[column_name] = column_value
                
                moment_item.append(item)

            return json.dumps({"moment_item": moment_item})
        
        except mysql.connector.Error as e:
            return json.dumps({"Error": str(e)})

    def fetch_push_token(self): 
        try:
            query = "SELECT * FROM pushtokens"
            self.cursor.execute(query)
            result = self.cursor.fetchall()
            columns = [desc[0] for desc in self.cursor.description]
            tokens = []
            
            for row in result:
                item = {}
                for i in range(len(columns)):
                    column_name = columns[i]
                    column_value = row[i]
                    
                    # Konvertiere datetime-Objekte in Zeichenketten
                    if isinstance(column_value, datetime):
                        column_value = column_value.strftime("%Y-%m-%dT%H:%M:%SZ")
                    
                    item[column_name] = column_value
                
                tokens.append(item)

            return json.dumps({"tokens": tokens})
        
        except mysql.connector.Error as e:
            return json.dumps({"Error": str(e)})

    def fetch_session_id(self, session_id): 
        query = "SELECT * FROM sessions WHERE session_id = %s"
        values = (session_id,)
        self.cursor.execute(query, values)
        session = self.cursor.fetchone()
        return session
        
    def fetch_push_token_by_token(self, token): 
        try:
            query = "SELECT * FROM pushtokens WHERE token = %s"
            values = (token,)
            self.cursor.execute(query, values)
            result = self.cursor.fetchone()
            if result:
                return json.dumps({"Done": locale['token_found']})
            else:
                return json.dumps({"Error": locale['token_not_found']})
        
        except mysql.connector.Error as e:
            return json.dumps({"Error": str(e)})

    def fetch_settings_by_option(self, option): 
        try:
            query = "SELECT id, value, specialvalue FROM `settings` WHERE `option` = %s"
            values = (option,)
            self.cursor.execute(query, values)
            selected_option = self.cursor.fetchone()
            if selected_option:
                option_dict = {
                    "id": selected_option[0],
                    "value": selected_option[1],
                    "specialvalue": selected_option[2]
                }
                return json.dumps({"option": option_dict})
            else:
                return json.dumps({"Error": locale['option_not_found']})
        
        except mysql.connector.Error as e:
            return json.dumps({"Error": str(e)})
    
    def fetch_user_by_username(self, username): 
        try:
            query = "SELECT id, username, password_salt, password_hash FROM users WHERE username = %s"
            values = (username,)
            self.cursor.execute(query, values)
            user = self.cursor.fetchone()
            if self.cursor.rowcount > 0:
                return json.dumps({"userinfo": user})
            else:
                return json.dumps({"Error": locale['user_not_found']})
            
        except mysql.connector.Error as e:
            return json.dumps({"Error": str(e)})
        
    def fetch_sidemenu(self):
        try:
            query = "SELECT * FROM sidemenu ORDER BY custom_id"
            self.cursor.execute(query)
            result = self.cursor.fetchall()
            columns = [desc[0] for desc in self.cursor.description]
            sidemenu = []
            
            for row in result:
                item = {}
                for i in range(len(columns)):
                    column_name = columns[i]
                    column_value = row[i]
                    
                    # Konvertiere datetime-Objekte in Zeichenketten
                    if isinstance(column_value, datetime):
                        column_value = column_value.strftime("%Y-%m-%dT%H:%M:%SZ")
                    
                    item[column_name] = column_value
                
                sidemenu.append(item)

            return json.dumps({"sidemenu": sidemenu})
        
        except mysql.connector.Error as e:
            return json.dumps({"Error": str(e)})

    # DELETE Operationen
    def delete_feed_item(self, item_id): 
        try:
            query = "DELETE FROM feed_items WHERE id = %s"
            values = (item_id,)
            self.cursor.execute(query, values)
            self.connection.commit()
            return "done"

        except mysql.connector.Error as e:
            return json.dumps({"Error": str(e)})

    def delete_bucketlist_item(self, item_id): 
        try:
            query = "DELETE FROM bucketlist_items WHERE id = %s"
            values = (item_id,)
            self.cursor.execute(query, values)
            self.connection.commit()
            return "done"

        except mysql.connector.Error as e:
            return json.dumps({"Error": str(e)})

    def delete_filmlist_item(self, item_id): 
        try:
            query = "DELETE FROM filmlist_items WHERE id = %s"
            values = (item_id,)
            self.cursor.execute(query, values)
            self.connection.commit()
            return "done"

        except mysql.connector.Error as e:
            return json.dumps({"Error": str(e)})

    def delete_moments_item(self, item_id): 
        try:
            query = "DELETE FROM moments_items WHERE id = %s"
            values = (item_id,)
            self.cursor.execute(query, values)
            self.connection.commit()
            return "done"

        except mysql.connector.Error as e:
            return json.dumps({"Error": str(e)})

    def delete_push_token(self, token): 
        try:
            query = "DELETE FROM pushtokens WHERE token = %s"
            values = (token,)
            self.cursor.execute(query, values)
            self.connection.commit()
            return "done"

        except mysql.connector.Error as e:
            return json.dumps({"Error": str(e)})

    def delete_session(self, session_id): 
        try:
            query = "DELETE FROM sessions WHERE session_id = %s"
            values = (session_id,)
            self.cursor.execute(query, values)
            self.connection.commit()
            return "done"

        except mysql.connector.Error as e:
            return json.dumps({"Error": str(e)})
        
    def delete_sidemenu_item(self, item_id): 
        try:
            query = "DELETE FROM sidemenu WHERE id = %s"
            values = (item_id,)
            self.cursor.execute(query, values)
            self.connection.commit()
            return "done"

        except mysql.connector.Error as e:
            return json.dumps({"Error": str(e)})

    def cleanup_database(self):
        try:
            # Delete expired sessions
            self.cursor = self.connection.cursor(buffered=True)
            query = "DELETE FROM sessions WHERE expiration < NOW();"
            self.cursor.execute(query)
            self.connection.commit()
        
        except mysql.connector.Error as e:
            return json.dumps({"Error": str(e)})

        try:
            # Delete unused Images
            query = "SELECT `id`, `contentURL` FROM `feed_items`;"
            self.cursor.execute(query)
            self.connection.commit()
            result = self.cursor.fetchall()
            columns = [desc[0] for desc in self.cursor.description]

            # Retrieve the 'banner' option from the 'settings' table
            query = "SELECT `value` FROM `settings` WHERE `option` = 'banner';"
            self.cursor.execute(query)
            banner_result = self.cursor.fetchone()
            banner_path = banner_result[0] if banner_result else None

            if banner_path == "https://fakeimg.pl/600x400?text=Banner-Image":
                banner_path = ""

            # Retrieve the 'music' option from the 'settings' table
            query = "SELECT `value` FROM `settings` WHERE `option` = 'music';"
            self.cursor.execute(query)
            music_result = self.cursor.fetchone()
            music_path = music_result[0] if music_result else None

            file_names = []

            for row in result:
                item = {}
                for i in range(len(columns)):
                    column_name = columns[i]
                    column_value = row[i]

                    item[column_name] = column_value

                content_urls = item['contentURL'].split(';')
                for url in content_urls:
                    file_name = url.split('/')[-1]
                    if file_name != "":
                        file_names.append(file_name)

            banner_file = banner_path.split('/')[-1]
            file_names.append(banner_file)
            music_file = music_path.split('/')[-1]
            file_names.append(music_file)

            current_dir = os.path.dirname(os.path.abspath(__file__))
            feed_folder_path = os.path.join(current_dir, '..', '..', 'upload/feed_items')
            stock_folder_path = os.path.join(current_dir, '..', '..', 'upload/stock_items')

            deleted_files = []
            missing_files = []

            # Alle Dateien im Ordner lesen
            feed_files = os.listdir(feed_folder_path)
            stock_files = os.listdir(stock_folder_path)

            # Dateien abgleichen und löschen, wenn sie nicht in der Datenbankabfrage vorkommen
            for file_name in feed_files + stock_files:
                if file_name not in file_names:
                    if file_name in feed_files:
                        file_path = os.path.join(feed_folder_path, file_name)
                    elif file_name in stock_files:
                        file_path = os.path.join(stock_folder_path, file_name)
                    else:
                        continue

                    os.remove(file_path)
                    deleted_files.append(file_name)

            # Umgekehrter Abgleich: Überprüfen, ob Dateien in der Datenbank fehlen
            for file_name in file_names:
                if file_name.startswith("banner_") or file_name.startswith("song_"):
                    continue  # Datei mit Präfix überspringen
                    
                file_path = os.path.join(feed_folder_path, file_name)
                if not os.path.exists(file_path):

                    query = "SELECT `title`, `dateCreated` FROM `feed_items` WHERE contentURL LIKE %s;"
                    values = ('%' + file_name + '%',)
                    self.cursor.execute(query, values)
                    self.connection.commit()
                    result = self.cursor.fetchall()
                    columns = [desc[0] for desc in self.cursor.description]
            
                    for row in result:
                        item = {}
                        for i in range(len(columns)):
                            column_name = columns[i]
                            column_value = row[i]
                            
                            # Konvertiere datetime-Objekte in Zeichenketten
                            if isinstance(column_value, datetime):
                                column_value = column_value.strftime("%Y-%m-%d")
                            
                            item[column_name] = column_value
                        
                        item['file_name'] = file_name
                        missing_files.append(item)

            return json.dumps({"deleted_files_count": len(deleted_files), "deleted_files": deleted_files, "missing_files_count": len(missing_files), "missing_files": missing_files})

        except mysql.connector.Error as e:
            return json.dumps({"Error": str(e)})



    def close_connection(self):
        self.cursor.close()
        self.connection.close()

    def create_database(self):

        # SQL-Dump aus Textdatei lesen
        with open(f'{current_dir}/sql_dump.sql', 'r') as file:
            sql_dump = file.read()

        # SQL-Dump in einzelne Abfragen aufteilen
        queries = sql_dump.split(';')

        for query in queries:
            query = query.strip()
            if query:
                self.cursor.execute(query)

        # Update Table -> Bestehende DB updaten

        # Charset ändern, falls erster init falsch
        query = "SHOW TABLES;"
        self.cursor.execute(query)
        result = self.cursor.fetchall()
        tables = [row[0] for row in result]

        for table in tables:
            query = f"ALTER TABLE `{table}` CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
            self.cursor.execute(query)        

        self.connection.commit()
        self.cursor.close()
        self.connection.close()
        