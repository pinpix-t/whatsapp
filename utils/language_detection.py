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
        "welcome_bulk": "Hi! Welcome to our Bulk Ordering Service. I'm here to help get you a quote. First off, what is your name?",
        "ask_name": "What is your name?",
        "ask_product": "Nice to meet you, {name}. Which products would you like to customise today?",
        "ask_quantity": "Great choice. To connect you with the right agent, how many do you need, and when is your deadline?",
        "completion": "Thank you for that information. I will now connect you directly to our specialist who will prepare your quote. They will be with you shortly.",
        "invalid_name": "Please provide a valid name.",
        "invalid_number": "Please enter a valid number. For example: 50, 100, etc.",
        "invalid_quantity": "Please enter a valid quantity greater than 0.",
        "error_generic": "Sorry, there was an error. Please try again.",
        "button_choose_product": "Choose Product",
        "minimum_quantity": "Our bulk ordering service, which includes special pricing and dedicated support, starts at just 11 units.\n\nIf you're looking for a smaller qty, you can order directly and easily on our website: {url}"
    },
    "fr": {
        "welcome_bulk": "Bonjour! Bienvenue dans notre Service de Commande en Gros. Je suis là pour vous aider à obtenir un devis. Pour commencer, quel est votre nom?",
        "ask_name": "Quel est votre nom?",
        "ask_product": "Ravi de vous rencontrer, {name}. Quels produits souhaitez-vous personnaliser aujourd'hui?",
        "ask_quantity": "Excellent choix. Pour vous mettre en contact avec le bon agent, combien en avez-vous besoin et quelle est votre date limite?",
        "completion": "Merci pour ces informations. Je vais maintenant vous connecter directement à notre spécialiste qui préparera votre devis. Il sera avec vous sous peu.",
        "invalid_name": "Veuillez fournir un nom valide.",
        "invalid_number": "Veuillez entrer un nombre valide. Par exemple: 50, 100, etc.",
        "invalid_quantity": "Veuillez entrer une quantité valide supérieure à 0.",
        "error_generic": "Désolé, une erreur s'est produite. Veuillez réessayer.",
        "button_choose_product": "Choisir un produit",
        "minimum_quantity": "Notre service de commande en gros, qui comprend des prix spéciaux et un support dédié, commence à seulement 11 unités.\n\nSi vous recherchez une quantité plus petite, vous pouvez commander directement et facilement sur notre site Web : {url}"
    },
    "it": {
        "welcome_bulk": "Ciao! Benvenuto nel nostro Servizio di Ordini all'Ingrosso. Sono qui per aiutarti a ottenere un preventivo. Prima di tutto, come ti chiami?",
        "ask_name": "Come ti chiami?",
        "ask_product": "Piacere di conoscerti, {name}. Quali prodotti vorresti personalizzare oggi?",
        "ask_quantity": "Ottima scelta. Per metterti in contatto con l'agente giusto, quante ne hai bisogno e qual è la tua scadenza?",
        "completion": "Grazie per queste informazioni. Ti collegherò ora direttamente al nostro specialista che preparerà il tuo preventivo. Sarà con te a breve.",
        "invalid_name": "Per favore, fornisci un nome valido.",
        "invalid_number": "Per favore, inserisci un numero valido. Ad esempio: 50, 100, ecc.",
        "invalid_quantity": "Per favore, inserisci una quantità valida maggiore di 0.",
        "error_generic": "Scusa, c'è stato un errore. Per favore riprova.",
        "button_choose_product": "Scegli prodotto",
        "minimum_quantity": "Il nostro servizio di ordini all'ingrosso, che include prezzi speciali e supporto dedicato, inizia a soli 11 pezzi.\n\nSe stai cercando una quantità più piccola, puoi ordinare direttamente e facilmente sul nostro sito Web: {url}"
    },
    "es": {
        "welcome_bulk": "¡Hola! Bienvenido a nuestro Servicio de Pedidos al por Mayor. Estoy aquí para ayudarte a obtener un presupuesto. Para empezar, ¿cuál es tu nombre?",
        "ask_name": "¿Cuál es tu nombre?",
        "ask_product": "Encantado de conocerte, {name}. ¿Qué productos te gustaría personalizar hoy?",
        "ask_quantity": "Excelente elección. Para conectarte con el agente adecuado, ¿cuántos necesitas y cuál es tu fecha límite?",
        "completion": "Gracias por esa información. Ahora te conectaré directamente con nuestro especialista que preparará tu presupuesto. Estará contigo en breve.",
        "invalid_name": "Por favor, proporciona un nombre válido.",
        "invalid_number": "Por favor, ingresa un número válido. Por ejemplo: 50, 100, etc.",
        "invalid_quantity": "Por favor, ingresa una cantidad válida mayor que 0.",
        "error_generic": "Lo siento, hubo un error. Por favor intenta de nuevo.",
        "button_choose_product": "Elegir producto",
        "minimum_quantity": "Nuestro servicio de pedidos al por mayor, que incluye precios especiales y soporte dedicado, comienza con solo 11 unidades.\n\nSi está buscando una cantidad más pequeña, puede pedir directamente y fácilmente en nuestro sitio web: {url}"
    },
    "de": {
        "welcome_bulk": "Hallo! Willkommen bei unserem Großbestellungs-Service. Ich bin hier, um Ihnen bei der Angebotserstellung zu helfen. Zunächst einmal, wie ist Ihr Name?",
        "ask_name": "Wie ist Ihr Name?",
        "ask_product": "Schön, Sie kennenzulernen, {name}. Welche Produkte möchten Sie heute anpassen?",
        "ask_quantity": "Großartige Wahl. Um Sie mit dem richtigen Agenten zu verbinden, wie viele benötigen Sie und wann ist Ihre Frist?",
        "completion": "Vielen Dank für diese Informationen. Ich verbinde Sie jetzt direkt mit unserem Spezialisten, der Ihr Angebot vorbereiten wird. Er wird in Kürze bei Ihnen sein.",
        "invalid_name": "Bitte geben Sie einen gültigen Namen ein.",
        "invalid_number": "Bitte geben Sie eine gültige Zahl ein. Zum Beispiel: 50, 100, usw.",
        "invalid_quantity": "Bitte geben Sie eine gültige Menge größer als 0 ein.",
        "error_generic": "Entschuldigung, es ist ein Fehler aufgetreten. Bitte versuchen Sie es erneut.",
        "button_choose_product": "Produkt wählen",
        "minimum_quantity": "Unser Großbestellungs-Service, der Sonderpreise und persönlichen Support umfasst, beginnt bereits bei 11 Einheiten.\n\nWenn Sie eine kleinere Menge suchen, können Sie direkt und einfach auf unserer Website bestellen: {url}"
    },
    "nl": {
        "welcome_bulk": "Hallo! Welkom bij onze Groothandel Service. Ik ben hier om u te helpen een offerte te krijgen. Om te beginnen, wat is uw naam?",
        "ask_name": "Wat is uw naam?",
        "ask_product": "Aangenaam kennis te maken, {name}. Welke producten wilt u vandaag aanpassen?",
        "ask_quantity": "Uitstekende keuze. Om u in contact te brengen met de juiste agent, hoeveel heeft u nodig en wat is uw deadline?",
        "completion": "Bedankt voor die informatie. Ik zal u nu direct doorverbinden met onze specialist die uw offerte zal voorbereiden. Ze zullen binnenkort bij u zijn.",
        "invalid_name": "Geef alstublieft een geldige naam op.",
        "invalid_number": "Voer alstublieft een geldig nummer in. Bijvoorbeeld: 50, 100, etc.",
        "invalid_quantity": "Voer alstublieft een geldige hoeveelheid groter dan 0 in.",
        "error_generic": "Sorry, er is een fout opgetreden. Probeer het alstublieft opnieuw.",
        "button_choose_product": "Kies product",
        "minimum_quantity": "Onze groothandel service, die speciale prijzen en toegewijd support omvat, begint bij slechts 11 eenheden.\n\nAls u op zoek bent naar een kleinere hoeveelheid, kunt u direct en gemakkelijk bestellen op onze website: {url}"
    },
}

# Region to website URL mapping (base URLs without trailing slash)
REGION_URLS = {
    "UK": "https://www.printerpix.co.uk",
    "US": "https://www.printerpix.com",
    "AE": "https://www.printerpix.ae",
    "NL": "https://www.printerpix.nl",
    "DE": "https://www.printerpix.de",
    "IT": "https://www.printerpix.it",
    "FR": "https://www.printerpix.fr",
    "IN": "https://www.printerpix.in",
    "ES": "https://www.printerpix.es",
}

# Product URL paths (same across all regions)
PRODUCT_PATHS = {
    "mugs": "/photo-gifts/custom-kitchen-and-drinkware/",
    "photo_printing": "/photo-prints/",
    "canvas": "/photo-gifts/canvas-photo-prints/",
    "blankets": "/photo-blankets/",
    "photobooks": "/photo-books-q/",
    "calendars": "/photo-gifts/photo-calendars/",
    # For "other" products or no product selected, use homepage
    "other": "/",
}

# Black Friday promo messages by region - Angle C: Hard Deadline
BF_PROMO_MESSAGES = {
    "UK": "One final thing! ⏳ It is officially Black Friday and the site is buzzing. Deals this big are about to expire. Lock in up to 80% off before the timer hits zero. 🔥\n\nTell your friends to hurry—once these are gone, they're gone!",
    "US": "One final thing! ⏳ It is officially Black Friday and the site is buzzing. Deals this big are about to expire. Lock in up to 80% off before the timer hits zero. 🔥\n\nTell your friends to hurry—once these are gone, they're gone!",
    "DE": "Eine letzte Sache! ⏳ Es ist offiziell Black Friday und die Seite brummt. Deals dieser Größe laufen bald ab. Sichern Sie sich bis zu 80% Rabatt, bevor der Timer auf Null steht. 🔥\n\nSagen Sie Ihren Freunden, sie sollen sich beeilen—wenn diese weg sind, sind sie weg!",
    "FR": "Une dernière chose ! ⏳ C'est officiellement le Black Friday et le site est en effervescence. Des offres aussi importantes sont sur le point d'expirer. Verrouillez jusqu'à 80% de réduction avant que le minuteur n'atteigne zéro. 🔥\n\nDites à vos amis de se dépêcher—une fois partis, ils sont partis !",
    "ES": "¡Una última cosa! ⏳ Es oficialmente Black Friday y el sitio está en plena actividad. Ofertas tan grandes están a punto de expirar. Bloquea hasta un 80% de descuento antes de que el temporizador llegue a cero. 🔥\n\n¡Dile a tus amigos que se apresuren—una vez que se acaben, se acabaron!",
    "IT": "Un'ultima cosa! ⏳ È ufficialmente Black Friday e il sito è in fermento. Offerte così grandi stanno per scadere. Blocca fino all'80% di sconto prima che il timer arrivi a zero. 🔥\n\nDì ai tuoi amici di sbrigarsi—una volta finiti, sono finiti!",
    "NL": "Een laatste ding! ⏳ Het is officieel Black Friday en de site bruist. Aanbiedingen zo groot staan op het punt te verlopen. Zet tot 80% korting vast voordat de timer op nul staat. 🔥\n\nZeg je vrienden dat ze moeten haasten—als deze weg zijn, zijn ze weg!",
    "IN": "One final thing! ⏳ It is officially Black Friday and the site is buzzing. Deals this big are about to expire. Lock in up to 70% off before the timer hits zero. 🔥\n\nTell your friends to hurry—once these are gone, they're gone!",
    "AE": "One final thing! ⏳ It is officially Black Friday and the site is buzzing. Deals this big are about to expire. Lock in up to 70% off before the timer hits zero. 🔥\n\nTell your friends to hurry—once these are gone, they're gone!",
}

# Black Friday links by region
BF_LINKS = {
    "UK": "https://www.printerpix.co.uk/s/black-friday/",
    "US": "https://www.printerpix.com/s/black-friday/",
    "FR": "https://www.printerpix.fr/s/black-friday/",
    "ES": "https://www.printerpix.es/s/black-friday/",
    "IT": "https://www.printerpix.it/s/black-friday/",
    "DE": "https://www.printerpix.de/s/black-friday/",
    "NL": "https://www.printerpix.nl/s/black-friday/",
    "IN": "https://www.printerpix.in/blackfriday-2025/",
    "AE": "https://www.printerpix.ae/blackfriday-2025/",
}

# Button text by language code - Angle C
BF_BUTTON_TEXT = {
    "en": "Tap here to save",
    "de": "Hier tippen zum Sparen",
    "fr": "Appuyez ici pour économiser",
    "es": "Toca aquí para ahorrar",
    "it": "Tocca qui per risparmiare",
    "nl": "Tik hier om te besparen",
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


def get_product_url_for_region(product: Optional[str], region: Optional[str]) -> str:
    """
    Get product-specific URL for a region
    
    Args:
        product: Product key (e.g., "mugs", "canvas", "blankets", "photobooks", "calendars", "photo_printing")
                 or "other" products (wall_calendar, photo_frame, etc.) which will use homepage
        region: Region code (e.g., "UK", "DE", "FR", etc.)
        
    Returns:
        Full URL for the product in the specified region
    """
    # Get base URL for region
    base_url = get_region_url(region)
    
    # Get product path
    if product and product in PRODUCT_PATHS:
        path = PRODUCT_PATHS[product]
    else:
        # Default to homepage for "other" products (wall_calendar, photo_frame, etc.) or unknown products
        # or when product is "other" (user selected "other" but hasn't chosen specific product yet)
        path = "/"
    
    # Combine base URL + path
    return f"{base_url}{path}"


def get_bf_promo_message(region: Optional[str]) -> Optional[str]:
    """
    Get Black Friday promo message for a specific region
    
    Args:
        region: Region code (e.g., "UK", "US", "DE")
        
    Returns:
        Promo message string or None if not found
    """
    if not region:
        return None
    return BF_PROMO_MESSAGES.get(region, BF_PROMO_MESSAGES.get("UK"))


def get_bf_link(region: Optional[str]) -> Optional[str]:
    """
    Get Black Friday link for a specific region
    
    Args:
        region: Region code (e.g., "UK", "US", "DE")
        
    Returns:
        Black Friday URL string or None if not found
    """
    if not region:
        return None
    return BF_LINKS.get(region, BF_LINKS.get("UK"))


def get_bf_button_text(language_code: str) -> str:
    """
    Get button text in user's language
    
    Args:
        language_code: Language code (e.g., "en", "de", "fr")
        
    Returns:
        Localized button text
    """
    return BF_BUTTON_TEXT.get(language_code, BF_BUTTON_TEXT.get("en"))

