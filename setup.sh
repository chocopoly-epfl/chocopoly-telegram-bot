#!/bin/bash

echo "Creating constantes.py..."

CONSTANTES_FILE="resources/constantes.py"
CONSTANTES_CONTENT_PARSED=${CONSTANTES_CONTENT:-"please fill the CONSTANTES_CONTENT environment variable"}

mkdir -p resources
cat << EOL > "$CONSTANTES_FILE"
$CONSTANTES_CONTENT_PARSED
EOL

exec python3 bot.py
