import yaml

def validate_yaml_file(file_path: str) -> bool:
    """
    Validates a YAML file by attempting to load it.

    Parameters:
    file_path (str): The path to the YAML file to validate.

    Returns:
    bool: True if the file is a valid YAML file, False otherwise.
    """
    try:
        with open(file_path, 'r') as file:
            yaml.safe_load(file)
        print(f"\tYAML file '{file_path}' is valid.")
        return True
    except yaml.YAMLError as exc:
        error_message = str(exc).replace('\n', ' ')  # Rimuove gli accapo
        print(f"\tError in YAML file: {error_message}")
        return False


