#!/bin/bash

echo "Wait for database... This may take a few minutes at the first start..."

# Aufruf des Python-Skripts und Speichern des Outputs in einer Variable
output=$(python ./backend/database/db_init.py)

# Überprüfung des erwarteten Response im Output
while true; do
    if echo "$output" | grep -q "DB Initalising finished"; then
        break  # Wenn der erwartete Response im Output gefunden wird, beende die Schleife
    fi
    sleep 5  # Warte 5 Sekunden und überprüfe erneut
done

# Überprüfung der Dateien und Generierung, falls sie nicht vorhanden sind
if [ ! -f "./keys/vapid_private.pem" ]; then
    openssl ecparam -name prime256v1 -genkey -noout -out ./keys/vapid_private.pem
fi

if [ ! -f "./keys/private_key.txt" ]; then
    openssl ec -in ./keys/vapid_private.pem -outform DER | tail -c +8 | head -c 32 | base64 | tr -d '=' | tr '/+' '_-' >> ./keys/private_key.txt
fi

if [ ! -f "./keys/public_key.txt" ]; then
    openssl ec -in ./keys/vapid_private.pem -pubout -outform DER | tail -c 65 | base64 | tr -d '=' | tr '/+' '_-' >> ./keys/public_key.txt
fi

# Starte den ersten Prozess (background_worker.py)
python ./backend/utils/background_worker.py &

# Starte den zweiten Prozess (app.py)
python ./backend/api/app.py
