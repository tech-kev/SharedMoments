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

from telegram import Bot
import os
import json

# Import locales
locale_env = os.environ.get('LOCALE')
locales_dir = "locales"
file_path = os.path.join(locales_dir, locale_env + ".json")
with open(file_path, "r") as file:
    locale = json.load(file)

if os.environ.get('DEBUG_MODE') == 'True':
    debug = True

async def send_telegram_message(message):
    # Telegram Bot Token aus der Umgebungsvariable laden
    bot_token = os.environ.get('TG_BOT_TOKEN')
    
    # Prüfen, ob der Bot Token vorhanden ist
    if not bot_token:
        errmsg = locale['telegrambot_token_not_found']
        return json.dumps({"Error": errmsg})
        
    
    # Telegram Bot erstellen
    bot = Bot(token=bot_token)
    
    # Telegram-Nachricht senden
    chat_ids = os.environ.get('TG_CHAT_IDS')
    if chat_ids:
            try:
                chat_ids = json.loads(chat_ids)['chat_ids']
                
            except json.JSONDecodeError: # Wird das returned?
                errmsg = locale['chat_id_format_invalid']
                return json.dumps({"Error": errmsg})
            
            for chat_id in chat_ids:
                await bot.send_message(chat_id=chat_id, text=message)

            msg = locale['telegrambot_message_send_successful']
            return json.dumps({"Done": msg})
    
    else:
        errmsg = locale['chat_id_format_invalid']
        return json.dumps({"Error": errmsg})

