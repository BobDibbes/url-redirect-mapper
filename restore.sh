#!/bin/bash

# Controleer of er een backup bestaat
if [ ! -f "backups/dibbes_redirect_app_stable.py" ]; then
  echo "Geen stabiele versie gevonden!"
  exit 1
fi

# Maak eerst een backup van de huidige versie
./backup.sh "pre_restore"

# Herstel de stabiele versie
cp backups/dibbes_redirect_app_stable.py src/dibbes_redirect_app.py

echo "Stabiele versie hersteld. Start de app opnieuw met: streamlit run src/dibbes_redirect_app.py"
