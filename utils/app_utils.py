import os
import json
from utils.constants import DEFAULT_CONFIG_FILE

def load_config(filename = DEFAULT_CONFIG_FILE):
    """
    Carica la configurazione dal file JSON specificato.
    Verifica che il file esista prima di tentare di aprirlo.
    
    Parameters:
    filename (str): Il nome del file di configurazione.

    Returns:
    Il contenuto del file di configurazione come dizionario.
    """
    # Verifica se il file esiste nella directory attuale
    if not os.path.exists(filename):
        raise FileNotFoundError(f"The configuration file '{filename}' does not exist.")

    # Leggi il file JSON
    with open(filename, 'r') as file:
        config = json.load(file)

    return config
