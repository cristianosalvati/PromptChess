# string_utils.py 
import re

def beautify_template_attribute_value(value: str):
    temp = re.sub(r'(?<=\w)-(?=\w)', ' - ', value)
    return temp.strip().replace("_", " ").title()

def clean_template_attribute_value(value: str):
    temp = value.strip().replace(" ", "_").lower()
    return clean_special_characters(temp)

def clean_special_characters(input_string):
    """
    Rimuove i caratteri speciali specificati da una stringa, tranne '_'.
    """
    special_characters = r"[\-\.\+\,\~\!\@\#\$\%\^\&\*\(\)\{\}\[\]\'\"\|\\\/\<\>\?\=\:]"
    return re.sub(special_characters, '', input_string)

def is_string_valid(s):
    return s is not None and s.strip() != ''

def print_formatted_row(row: dict) -> None:
    """
    Prints formatted row (list of dictionaries).

    Parameters:
    row (list): The list of row to print.
    """
    if row:
        print("row found:")
        for item in row:
            for key, value in item.items():
                print(f"{key}: {value}")
            print("-" * 40)  # Separatore tra item
    else:
        print("No row to display.")
