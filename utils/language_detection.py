"""
Language detection from greeting messages
Detects region and language from specific greeting patterns
"""

import re
from typing import Tuple, Optional

# IMPORTANT: Patterns are checked in order of specificity
# More specific patterns (with punctuation) must be checked FIRST
GREETING_PATTERNS = [
    # Most specific patterns first (with punctuation)
    ("ES", r"^¡hola\s+printerpix!$", "es"),  # ¡Hola Printerpix! - exclamation at start AND end
    ("IN", r"^hello\s+printerpix!$", "en"),   # Hello Printerpix! - exclamation at end only
    ("DE", r"^hallo,\s+printerpix$", "de"),   # Hallo, Printerpix - comma after Hallo
    ("AE", r"^hello,\s+printerpix$", "en"),  # Hello, Printerpix - comma after Hello
    
    # Less specific patterns (no punctuation, but unique words)
    ("US", r"^hi\s+printerpix$", "en"),      # Hi Printerpix - unique word "hi"
    ("FR", r"^bonjour\s+printerpix$", "fr"), # Bonjour Printerpix - unique word
    ("IT", r"^ciao\s+printerpix$", "it"),    # Ciao Printerpix - unique word
    
    # Patterns that need exact matching to avoid conflicts
    ("NL", r"^hallo\s+printerpix$", "nl"),   # Hallo Printerpix - no comma (must come after DE check)
    ("UK", r"^hello\s+printerpix$", "en"),  # Hello Printerpix - no punctuation (must come after IN/AE checks)
]

# Language codes for responses
LANGUAGE_CODES = {
    "UK": "en",
    "US": "en",
    "FR": "fr",
    "IT": "it",
    "ES": "es",
    "DE": "de",
    "NL": "nl",
    "AE": "en",
    "IN": "en",
}

# Welcome messages by language
WELCOME_MESSAGES = {
    "en": "Hi! Welcome to PrinterPix! How can I help?",
    "fr": "Bonjour! Bienvenue chez PrinterPix! Comment puis-je vous aider?",
    "it": "Ciao! Benvenuto su PrinterPix! Come posso aiutarti?",
    "es": "¡Hola! ¡Bienvenido a PrinterPix! ¿Cómo puedo ayudarte?",
    "de": "Hallo! Willkommen bei PrinterPix! Wie kann ich Ihnen helfen?",
    "nl": "Hallo! Welkom bij PrinterPix! Hoe kan ik u helpen?",
}

# Goodbye messages by language
GOODBYE_MESSAGES = {
    "en": "Goodbye! Have a great day! 👋",
    "fr": "Au revoir! Passez une excellente journée! 👋",
    "it": "Arrivederci! Buona giornata! 👋",
    "es": "¡Adiós! ¡Que tengas un gran día! 👋",
    "de": "Auf Wiedersehen! Einen schönen Tag noch! 👋",
    "nl": "Tot ziens! Fijne dag! 👋",
}

# Button labels by language
BUTTON_LABELS = {
    "en": {
        "create": "Start Creating!",
        "order": "Track My Order",
        "bulk": "Bulk Ordering"
    },
    "fr": {
        "create": "Commencer à créer!",
        "order": "Suivre ma commande",
        "bulk": "Commande en gros"
    },
    "it": {
        "create": "Inizia a creare!",
        "order": "Traccia il mio ordine",
        "bulk": "Ordine all'ingrosso"
    },
    "es": {
        "create": "¡Empezar a crear!",
        "order": "Rastrear mi pedido",
        "bulk": "Pedido al por mayor"
    },
    "de": {
        "create": "Erstellen beginnen!",
        "order": "Meine Bestellung verfolgen",
        "bulk": "Großbestellung"
    },
    "nl": {
        "create": "Begin met creëren!",
        "order": "Mijn bestelling volgen",
        "bulk": "Groothandel"
    },
}

# Bulk ordering messages by language
BULK_MESSAGES = {
    "en": {
        "welcome_bulk": "Welcome to bulk ordering!",
        "ask_name": "What's your name?",
        "ask_product": "Which product are you interested in?",
        "ask_quantity": "How many units would you like to order?",
        "completion": "Thank you! We will contact you promptly.",
        "invalid_name": "Please provide a valid name.",
        "invalid_number": "Please enter a valid number. For example: 50, 100, etc.",
        "invalid_quantity": "Please enter a valid quantity greater than 0.",
        "error_generic": "Sorry, there was an error. Please try again.",
        "button_choose_product": "Choose Product",
        "minimum_quantity": "For bulk orders, we require a minimum of 10 units. For smaller orders, please visit our website:"
    },
    "fr": {
        "welcome_bulk": "Bienvenue dans la commande en gros!",
        "ask_name": "Quel est votre nom?",
        "ask_product": "Quel produit vous intéresse?",
        "ask_quantity": "Combien d'unités souhaitez-vous commander?",
        "completion": "Merci! Nous vous contacterons rapidement.",
        "invalid_name": "Veuillez fournir un nom valide.",
        "invalid_number": "Veuillez entrer un nombre valide. Par exemple: 50, 100, etc.",
        "invalid_quantity": "Veuillez entrer une quantité valide supérieure à 0.",
        "error_generic": "Désolé, une erreur s'est produite. Veuillez réessayer.",
        "button_choose_product": "Choisir un produit",
        "minimum_quantity": "Pour les commandes en gros, nous exigeons un minimum de 10 unités. Pour les commandes plus petites, veuillez visiter notre site Web:"
    },
    "it": {
        "welcome_bulk": "Benvenuto nell'ordine all'ingrosso!",
        "ask_name": "Come ti chiami?",
        "ask_product": "Quale prodotto ti interessa?",
        "ask_quantity": "Quante unità vorresti ordinare?",
        "completion": "Grazie! Ti contatteremo prontamente.",
        "invalid_name": "Per favore, fornisci un nome valido.",
        "invalid_number": "Per favore, inserisci un numero valido. Ad esempio: 50, 100, ecc.",
        "invalid_quantity": "Per favore, inserisci una quantità valida maggiore di 0.",
        "error_generic": "Scusa, c'è stato un errore. Per favore riprova.",
        "button_choose_product": "Scegli prodotto",
        "minimum_quantity": "Per ordini all'ingrosso, richiediamo un minimo di 10 unità. Per ordini più piccoli, visitare il nostro sito Web:"
    },
    "es": {
        "welcome_bulk": "¡Bienvenido al pedido al por mayor!",
        "ask_name": "¿Cuál es tu nombre?",
        "ask_product": "¿Qué producto te interesa?",
        "ask_quantity": "¿Cuántas unidades te gustaría pedir?",
        "completion": "¡Gracias! Te contactaremos rápidamente.",
        "invalid_name": "Por favor, proporciona un nombre válido.",
        "invalid_number": "Por favor, ingresa un número válido. Por ejemplo: 50, 100, etc.",
        "invalid_quantity": "Por favor, ingresa una cantidad válida mayor que 0.",
        "error_generic": "Lo siento, hubo un error. Por favor intenta de nuevo.",
        "button_choose_product": "Elegir producto",
        "minimum_quantity": "Para pedidos al por mayor, requerimos un mínimo de 10 unidades. Para pedidos más pequeños, visite nuestro sitio web:"
    },
    "de": {
        "welcome_bulk": "Willkommen bei der Großbestellung!",
        "ask_name": "Wie ist Ihr Name?",
        "ask_product": "Welches Produkt interessiert Sie?",
        "ask_quantity": "Wie viele Einheiten möchten Sie bestellen?",
        "completion": "Vielen Dank! Wir werden Sie umgehend kontaktieren.",
        "invalid_name": "Bitte geben Sie einen gültigen Namen ein.",
        "invalid_number": "Bitte geben Sie eine gültige Zahl ein. Zum Beispiel: 50, 100, usw.",
        "invalid_quantity": "Bitte geben Sie eine gültige Menge größer als 0 ein.",
        "error_generic": "Entschuldigung, es ist ein Fehler aufgetreten. Bitte versuchen Sie es erneut.",
        "button_choose_product": "Produkt wählen",
        "minimum_quantity": "Für Großbestellungen benötigen wir mindestens 10 Einheiten. Für kleinere Bestellungen besuchen Sie bitte unsere Website:"
    },
    "nl": {
        "welcome_bulk": "Welkom bij groothandel!",
        "ask_name": "Wat is uw naam?",
        "ask_product": "Welk product interesseert u?",
        "ask_quantity": "Hoeveel eenheden wilt u bestellen?",
        "completion": "Bedankt! We zullen u spoedig contacten.",
        "invalid_name": "Geef alstublieft een geldige naam op.",
        "invalid_number": "Voer alstublieft een geldig nummer in. Bijvoorbeeld: 50, 100, etc.",
        "invalid_quantity": "Voer alstublieft een geldige hoeveelheid groter dan 0 in.",
        "error_generic": "Sorry, er is een fout opgetreden. Probeer het alstublieft opnieuw.",
        "button_choose_product": "Kies product",
        "minimum_quantity": "Voor groothandel vereisen we een minimum van 10 eenheden. Voor kleinere bestellingen bezoek onze website:"
    },
}

# Region to website URL mapping
REGION_URLS = {
    "UK": "http://printerpix.co.uk/",
    "US": "http://printerpix.com",
    "AE": "https://www.printerpix.ae/",
    "NL": "https://www.printerpix.nl",
    "DE": "https://www.printerpix.de",
    "IT": "https://www.printerpix.it",
    "FR": "https://www.printerpix.fr",
    "IN": "https://www.printerpix.in/",
    "ES": "https://www.printerpix.es",
}

# Product names by language (for product selection list)
PRODUCT_NAMES = {
    "en": {
        "calendars": "Calendars",
        "photobooks": "Photo Books",
        "blankets": "Blankets",
        "canvas": "Canvas Prints",
        "photo_printing": "Photo Printing",
        "mugs": "Mugs",
        "other": "Other"
    },
    "fr": {
        "calendars": "Calendriers",
        "photobooks": "Livres photo",
        "blankets": "Couvertures",
        "canvas": "Impressions sur toile",
        "photo_printing": "Impression photo",
        "mugs": "Tasses",
        "other": "Autre"
    },
    "it": {
        "calendars": "Calendari",
        "photobooks": "Libri fotografici",
        "blankets": "Coperte",
        "canvas": "Stampe su tela",
        "photo_printing": "Stampa fotografica",
        "mugs": "Tazze",
        "other": "Altro"
    },
    "es": {
        "calendars": "Calendarios",
        "photobooks": "Libros de fotos",
        "blankets": "Mantas",
        "canvas": "Impresiones en lienzo",
        "photo_printing": "Impresión de fotos",
        "mugs": "Tazas",
        "other": "Otro"
    },
    "de": {
        "calendars": "Kalender",
        "photobooks": "Fotobücher",
        "blankets": "Decken",
        "canvas": "Leinwanddrucke",
        "photo_printing": "Fotodruck",
        "mugs": "Tassen",
        "other": "Andere"
    },
    "nl": {
        "calendars": "Kalenders",
        "photobooks": "Fotoboeken",
        "blankets": "Dekens",
        "canvas": "Canvasdrukken",
        "photo_printing": "Fotodruk",
        "mugs": "Mokken",
        "other": "Andere"
    },
}


def detect_language_from_greeting(message: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Detect region and language from greeting message
    
    IMPORTANT: Patterns are checked in order - more specific patterns first
    to avoid false matches (e.g., "Hello Printerpix!" vs "Hello Printerpix")
    
    Args:
        message: User's greeting message
        
    Returns:
        Tuple of (region, language_code) or (None, "en") if not detected (defaults to English)
    """
    # Normalize: lowercase, strip whitespace, but preserve punctuation
    message_normalized = message.strip()
    message_lower = message_normalized.lower()
    
    # Check each pattern in order (most specific first)
    for region, pattern, language_code in GREETING_PATTERNS:
        # Use case-insensitive matching but preserve original for exact checks
        if re.match(pattern, message_lower, re.IGNORECASE):
            return region, language_code
    
    # Default to English if no match
    return None, "en"


def get_welcome_message(language_code: str) -> str:
    """Get welcome message in specified language"""
    return WELCOME_MESSAGES.get(language_code, WELCOME_MESSAGES["en"])


def get_goodbye_message(language_code: str) -> str:
    """Get goodbye message in specified language"""
    return GOODBYE_MESSAGES.get(language_code, GOODBYE_MESSAGES["en"])


def get_button_labels(language_code: str) -> dict:
    """Get button labels in specified language"""
    return BUTTON_LABELS.get(language_code, BUTTON_LABELS["en"])


def get_bulk_message(language_code: str, message_key: str) -> str:
    """Get bulk ordering message in specified language"""
    messages = BULK_MESSAGES.get(language_code, BULK_MESSAGES["en"])
    return messages.get(message_key, messages.get("ask_name", "What's your name?"))


def get_product_names(language_code: str) -> dict:
    """Get product names in specified language"""
    return PRODUCT_NAMES.get(language_code, PRODUCT_NAMES["en"])


def get_region_url(region: Optional[str]) -> str:
    """Get website URL for a region, default to UK if not found"""
    if region and region in REGION_URLS:
        return REGION_URLS[region]
    return REGION_URLS["UK"]  # Default to UK

