from PIL import Image

def find_opaque_element_in_image(image_path, percent=True, normalization_factor=2.5):
    """
    Trova la prima occorrenza di un pixel non trasparente in un'immagine PNG.

    :param image_path: Percorso del file dell'immagine.
    :param percent: Se True, ritorna le coordinate in percentuale rispetto alla dimensione dell'immagine.
    :param normalization_factor: Fattore di normalizzazione per width e height. Default è 2.5.
    :return: Tuple con le coordinate (top, left, width, height) del primo pixel non trasparente trovato,
             oppure (0, 0, 0, 0) se tutti i pixel sono trasparenti o l'immagine non ha un canale alpha.
    """
    try:
        with Image.open(image_path) as img:
            print(f"\tPlease wait while checking alpha channel for image file: {image_path}")

            if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                img = img.convert("RGBA")
                image_width, image_height = img.size

                minX, minY = image_width, image_height
                maxX, maxY = 0, 0
                sumX, sumY = 0, 0
                counterX, counterY = 0, 0

                for y in range(image_height):
                    for x in range(image_width):
                        r, g, b, a = img.getpixel((x, y))
                        if a > 0:
                            # calcolo e aggiornamento di min e max 
                            if x < minX:
                                minX = x
                            if y < minY:
                                minY = y

                            if x > maxX and x > minX:
                                maxX = x                # Aggiorno max X solo se maggiore dal minimo x
                            if y > maxY and y > minY:
                                maxY = y                # Aggiorno max Y solo se maggiore dal minimo y

                            # Calcolo media dei valori compresi tra min e max
                            if minX < x < maxX:
                                counterX += 1
                                sumX += x
                            if minY < y < maxY:
                                counterY += 1
                                sumY += y

                # aggiorno max nel caso non fosse stato calcolato 
                if maxX == 0:
                    maxX = minX
                if maxY == 0:
                    maxY = minY

                # Calcola top, left, width e height
                top = round((sumY / counterY) if counterY > 0 else (minY + maxY) / 2 , 2)
                left = round((sumX / counterX) if counterX > 0 else (minX + maxX) / 2, 2)

                width = round((maxX - minX) / normalization_factor, 2)
                height = round((maxY - minY) / normalization_factor, 2)

                if percent:
                    top = round((top / image_height) * 100, 2)
                    left = round((left / image_width) * 100, 2)
                
                print(f"\t{image_path} recognized at top: {top}, left: {left}, width: {width}, height: {height}")
                
                if counterY > 0 or counterX > 0:
                    print(f"\t\t - top = ({sumY} / {counterY}) / {image_height}, left = ({sumX} / {counterX}) / {image_width}")
                          
                return (top, left, width, height)

            else:
                print(f"\tImage does not have an alpha channel: {image_path}")
                return (0, 0, 0, 0)

    except FileNotFoundError:
        print(f"\tFile {image_path} not found.")
        return None
    except Exception as e:
        print(f"\tAn error occurred: {e}")
        return None

def find_first_non_transparent_pixel(image_path, percent=True):
    """
    Trova la prima occorrenza di un pixel non trasparente in un'immagine PNG.

    :param image_path: Percorso del file dell'immagine.
    :param percent: Se True, ritorna le coordinate in percentuale rispetto alla dimensione dell'immagine.
    :return: Tuple con le coordinate (x, y) del primo pixel non trasparente trovato,
             oppure None se tutti i pixel sono trasparenti o l'immagine non ha un canale alpha.
    """
    try:
        # Apri l'immagine
        with Image.open(image_path) as img:
            print(f"\tPlease wait while checking alpha channel for image file: {image_path}")

            # Verifica se l'immagine ha un canale alpha
            if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                # Converte l'immagine in formato RGBA
                img = img.convert("RGBA")
                width, height = img.size  # Ottieni larghezza e altezza

                # Itera su ogni pixel dall'alto verso il basso e da sinistra a destra
                for y in range(height):  # y itera su height
                    for x in range(width):  # x itera su width
                        # Ottieni il colore del pixel
                        r, g, b, a = img.getpixel((x, y))
                        # Verifica se il pixel non è trasparente (alpha > 0)
                        if a > 0:
                            if percent:
                                x_percent = (x / width) * 100
                                y_percent = (y / height) * 100
                                return (x_percent, y_percent)
                            else:
                                return (x, y)

                # Se non sono stati trovati pixel non trasparenti
                print(f"\tCannot find opaque pixel for image file: {image_path}")
                return None

            else:
                print(f"\tImage does not have an alpha channel: {image_path}")
                return (0, 0)

    except FileNotFoundError:
        print(f"\tFile {image_path} not found.")
        return None
    except Exception as e:
        print(f"\tAn error occurred: {e}")
        return None

def find_pixel_with_color(image_path, target_color):
    """
    Trova la posizione di un pixel con un certo colore in un'immagine.

    :param image_path: Percorso del file dell'immagine.
    :param target_color: Colore da cercare (come tuple RGB).
    :return: Lista di tuple con le coordinate (x, y) dei pixel trovati.
    """
    try:
        # Apri l'immagine
        with Image.open(image_path) as img:
            # Converte l'immagine in formato RGB
            img = img.convert("RGB")
            width, height = img.size
            found_pixels = []

            # Itera su ogni pixel
            for y in range(height):
                for x in range(width):
                    # Ottieni il colore del pixel
                    current_color = img.getpixel((x, y))
                    # Confronta il colore del pixel con il target
                    if current_color == target_color:
                        found_pixels.append((x, y))

            return found_pixels
    except FileNotFoundError:
        print(f"File {image_path} not found.")
        return []
    except Exception as e:
        print(f"An error occurred: {e}")
        return []


### Piece Detection
import json

def detect_piece_at_square(square_img):
    """
    Placeholder for piece detection logic.
    In a real implementation, this function would use template matching or a trained model
    to identify the piece type and color in the given  square image.
    Returns a tuple (color, piece_type) or None if the square is empty.
    Example return values:
        ("bianchi", "pedoni")
        ("neri", "re")
    """
    # TODO: implement actual detection
    return None

def analyze_board(image_path):
    """
    Analyzes the chessboard image and builds a JSON-serializable dictionary
    with piece positions for "neri" and "bianchi".
    """
    im = Image.open(image_path)
    w, h = im.size
    files = "abcdefgh"
    ranks = "87654321"
    square_width = w / 8
    square_height = h / 8

    # initialize board structure
    board = {
        "neri":   {t: [] for t in ["pedoni", "alfieri", "cavalli", "torri", "regina", "re"]},
        "bianchi":{t: [] for t in ["pedoni", "alfieri", "cavalli", "torri", "regina", "re"]}
    }

    # iterate through each square
    for file_idx, file in enumerate(files):
        for rank_idx, rank in enumerate(ranks):
            # calculate pixel bounding box
            left = file_idx * square_width
            upper = rank_idx * square_height
            right = (file_idx + 1) * square_width
            lower = (rank_idx + 1) * square_height

            # crop the square image
            square = im.crop((left, upper, right, lower))
            piece = detect_piece_at_square(square)

            if piece:
                color, piece_type = piece
                board[color][piece_type].append(f"{file}{rank}")

    return board

if __name__ == "__main__":
    image_path = "/mnt/data/ff0fc844-4b8f-4b24-927c-9bd06a9ec5ad.png"
    board_state = analyze_board(image_path)
    print(json.dumps(board_state, indent=2))
