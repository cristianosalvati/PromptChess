import os

def increment_version():
    # Ottiene il percorso della directory in cui è presente lo script corrente
    dir_path = os.path.dirname(os.path.realpath(__file__))
    
    # Costruisce il percorso completo al file version.txt
    version_file = os.path.join(dir_path, 'version.txt')
    version_code_file = os.path.join(dir_path, 'version.py')

    # Legge la versione attuale o inizia da 0.0 se il file non esiste
    if os.path.exists(version_file):
        with open(version_file, 'r') as file:
            version = float(file.read().strip()) + 0.1
    else:
        version = 0.0

    # Scrive la nuova versione nel file di versione
    with open(version_file, 'w') as file:
        file.write(f"{version:.1f}")

    # Scrive la versione nel modulo Python per essere importato dal programma principale
    with open(version_code_file, 'w') as file:
        file.write(f"VERSION = '{version:.1f}'\n")

if __name__ == "__main__":
    increment_version()
