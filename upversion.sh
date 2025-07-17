#!/bin/bash

# Legge la versione attuale dal file
version=$(cat modules/version.txt)
echo "UPDATE VERSION (from v$version)"

# Cattura l'output del comando Python
output_version=$(python modules/version_manager.py 2>&1)

# Verifica se il comando Python è stato eseguito con successo
if [[ $? -eq 0 ]]; then
    echo "Version update successful."
else
    echo "Version update failed."

    # Verifica se l'errore è un ValueError
    if echo "$output_version" | grep -q "ValueError"; then
        echo "ONLY MAJOR AND MINOR VERSION: $output_version"
    else
        echo "Unexpected error."
    fi

    # Termina lo script con un codice di errore
    exit 1
fi
