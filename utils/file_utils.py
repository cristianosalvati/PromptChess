# file_utils.py
import os
import datetime
from pathlib import Path

def save_content_in_file(content: str, directory: str = ".", prefix: str = "response") -> str:
    """
    Salva `content` in un file con nome progressivo basato sul timestamp.
    Ritorna il percorso del file creato.
    """
    if content is None: 
        return

    now = datetime.datetime.now()
    # formattiamo anno-mese-giorno-ora-minuto-secondo-millisecondi
    timestamp = int(now.timestamp() * 1000)
    filename = f"{prefix}_{timestamp}.txt"
    path = os.path.join(directory, filename)

    # Assicuriamoci che la cartella esista
    os.makedirs(directory, exist_ok=True)

    # Salviamo la stringa
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

    return path

def write_file(output_folder: str, filename: str, output_data: str):
    # Creare la cartella se non esiste
    Path(output_folder).mkdir(parents=True, exist_ok=True)
    
    # Scrivere il file
    with open(Path(output_folder) / filename, 'w') as out_file:
        out_file.write(output_data)
    
    print(f"\tData written to {output_folder + filename}")

def read_file(input_folder: str, filename: str):
    try:
        with open(input_folder + filename, 'r') as file:
            return file.read()
        
    except FileNotFoundError as e1:
        print(f"\tFile not found: {e1}")
        print("\tCurrent working directory:", os.getcwd())
        print("\tFiles in './in/':", os.listdir('./in/'))
    except Exception as e2:
        print(f"\tAn error occurred: {e2}")

def append_text_to_file(filename: str, text: str) -> None:
    """
    Appends the given text to the file specified by filename.
    If the file does not exist, it will be created.

    Parameters:
    filename (str): The name of the file to which the text will be appended.
    text (str): The text to append to the file.
    """
    try:
        with open(filename, 'a') as file:
            file.write(text + '\n')
        print(f"\tData successfully appended to {filename}")
    except Exception as e:
        print(f"\tAn error occurred while appending text to the file: {e}")

def delete_yaml_files(directory: str, extension: str) -> None:
    try:
        # Verificare se la directory esiste
        if not Path(directory).exists():
            print(f"\tDirectory '{directory}' does not exist.")
            return
        
        # Iterare sui file presenti nella directory
        for filename in os.listdir(directory):
            if filename.endswith(extension):
                file_path = os.path.join(directory, filename)
                os.remove(file_path)
                print(f" - Deleted: {file_path}")
                
        print("\tDeletion complete.")
        
    except Exception as e:
        print(f"\tAn error occurred: {e}")
