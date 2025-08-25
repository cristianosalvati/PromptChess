#!/usr/bin/env python3
import requests
import json
import sys

CATEGORIES_URL = "https://world.openfoodfacts.org/data/taxonomies/categories.json"
SEARCH_URL    = "https://world.openfoodfacts.org/api/v2/search"
PRODUCT_URL   = "https://world.openfoodfacts.org/api/v2/product/{}"

def load_categories():
    resp = requests.get(CATEGORIES_URL)
    resp.raise_for_status()
    return list(resp.json().keys())

def find_best_matches(query_words, categories):
    """Ritorna le categorie che contengono il maggior numero di parole di query."""
    scores = {}
    for cat in categories:
        words = cat.split('-')
        match_count = sum(1 for w in query_words if w.lower() in words)
        if match_count > 0:
            scores.setdefault(match_count, []).append(cat)
    if not scores:
        return []
    max_score = max(scores)
    return scores[max_score]

def prompt_select(options):
    """Chiede all’utente di scegliere uno degli slug proposti."""
    if len(options) == 1:
        return options[0]
    print("Ho trovato più categorie possibili:")
    for i, opt in enumerate(options, 1):
        print(f" {i}) {opt}")
    while True:
        choice = input(f"Scegli un numero (1–{len(options)}): ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(options):
            return options[int(choice) - 1]
        print("Selezione non valida, riprova.")

def search_category(query):
    categories = load_categories()
    words = query.lower().split()
    while True:
        matches = find_best_matches(words, categories)
        if matches:
            return matches
        if len(words) == 0:
            # "Nessuna categoria trovata; interrompo la ricerca."
            return None
        # rimuovo la parola più lunga e riprovo
        longest = max(words, key=len)
        print(f"Nessun match: elimino la parola più lunga '{longest}' e riprovo…")
        words.remove(longest)

def list_products_for_category(slug, page_size=100):
    params = {
        "categories_tags_en": slug,
        "page_size": page_size,
        "fields": "code,product_name,brands"
    }
    try:
        resp = requests.get(SEARCH_URL, params=params)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"[ERROR] Impossibile recuperare i prodotti per la categoria '{slug}': {e}")
        return []
    
    data = resp.json()
    return data.get("products", [])

def fetch_product_detail(code):
    try:
        resp = requests.get(PRODUCT_URL.format(code))
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"[ERROR] Impossibile recuperare il prodotto {code}: {e}")
        return {
            "code": code,
            "name": None,
            "brands": None,
            "ingredients": None,
            "allergens": None
        }
    
    data = resp.json().get("product", {})

    # Prendo la lista di oggetti "ingredients" (ognuno con chiave "text")
    ingredients_list = data.get("ingredients", [])
    ingredients = [ing.get("text", "").strip() for ing in ingredients_list if isinstance(ing, dict)]

    # Per gli allergeni viene bene "allergens_tags", che è già lista di stringhe
    allergens = data.get("allergens_tags", [])

    return {
        "code": data.get("code"),
        "name": data.get("product_name"),
        "brands": data.get("brands"),
        "ingredients": ingredients or ["N/D"],
        "allergens": allergens or ["nessuno segnalato"]
    }

def main():
    query = input("Inserisci il nome di una categoria (es. 'iced tea lemonade'): ").strip()
    print("Cerco la categoria più attinente…")
    slug = search_category(query)
    print(f"Categoria selezionata: {slug}\n")

    print("Recupero lista prodotti…")
    products = list_products_for_category(slug)
    if not products:
        print("Nessun prodotto trovato in questa categoria.")
        return

    print(f"Trovati {len(products)} prodotti. Recupero dettagli:\n")
    for p in products:
        detail = fetch_product_detail(p["code"])
        print(f"— Codice   : {detail['code']}")
        print(f"  Nome     : {detail['name']}")
        print(f"  Marca    : {detail['brands']}")
        print(f"  Ingredienti: {', '.join(detail['ingredients']) or 'N/D'}")
        print(f"  Allergeni  : {', '.join(detail['allergens']) or 'Nessuno segnalato'}")
        print()

if __name__ == "__main__":
    main()