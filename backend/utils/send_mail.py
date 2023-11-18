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

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
import os

# Import locales
locale_env = os.environ.get('LOCALE')
locales_dir = "locales"
file_path = os.path.join(locales_dir, locale_env + ".json")
with open(file_path, "r") as file:
    locale = json.load(file)

def sendEmail(receiver_email, subject, message):
    try:
        # Extrahiere die erforderlichen Daten aus der Konfiguration
        sender_email = os.environ.get('MAIL_SENDER_MAIL')
        smtp_server = os.environ.get('MAIL_SMTP_SERVER')
        smtp_port = os.environ.get('MAIL_SMTP_PORT')
        username = os.environ.get('MAIL_USERNAME')
        password = os.environ.get('MAIL_PASSWORD')

        # Erstelle eine MIME-Nachricht
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = receiver_email
        msg['Subject'] = subject

        # Füge den Nachrichtentext hinzu
        msg.attach(MIMEText(message, 'plain'))

        # Verbinde mit dem SMTP-Server
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(username, password)

        # Sende die E-Mail
        server.send_message(msg)

        # Schließe die Verbindung zum SMTP-Server
        server.quit()

        response = {
            "status": locale['mail_send_successful'],
            "sender_email": sender_email,
            "receiver_email": receiver_email,
            "subject": subject,
            "message": message,
            "smtp_server": smtp_server,
            "smtp_port": smtp_port,
        }

        return json.dumps({"Done": response})
    
    except Exception as e:
        response = {
            "status": locale['mail_send_failed'] + ": " + str(e),
            "sender_email": sender_email,
            "receiver_email": receiver_email,
            "subject": subject,
            "message": message,
            "smtp_server": smtp_server,
            "smtp_port": smtp_port,
        }
        
        return json.dumps({"Error": response})
    