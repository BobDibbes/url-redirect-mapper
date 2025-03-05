#!/bin/bash

# Maak backupdirectory als die niet bestaat
mkdir -p backups

# Maak een timestamp
TIMESTAMP=$(date +"%Y%m%d_%H%M")

# Kopieer het bestand met een duidelijke naam
cp src/dibbes_redirect_app.py "backups/dibbes_redirect_app_$TIMESTAMP.py"

# Als je een beschrijving wilt toevoegen
if [ "$1" != "" ]; then
  cp src/dibbes_redirect_app.py "backups/dibbes_redirect_app_${TIMESTAMP}_$1.py"
  echo "Backup gemaakt: backups/dibbes_redirect_app_${TIMESTAMP}_$1.py"
else
  echo "Backup gemaakt: backups/dibbes_redirect_app_$TIMESTAMP.py"
fi
