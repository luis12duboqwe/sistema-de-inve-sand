"""
Sistema de detección de solicitudes de fotos en conversaciones con clientes.

Cuando el bot detects que el cliente pide fotos, debe:
1. Responder al cliente: "Dame un momento, estoy tomando las fotos de los colores disponibles..."
2. Por detrás, llamar a POST /api/photo-requests/create para notificar al agente

Este módulo proporciona:
- Patrones para detectar solicitudes de fotos
- Funciones helper para crear solicitudes
- Respuestas canned para el cliente
"""

import re
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


# Patrones de solicit de fotos en español e inglés
PHOTO_REQUEST_PATTERNS = [
    # Español
    r"foto",
    r"fotos",
    r"imagen",
    r"imagenes",
    r"imagen(?:es)?",
    r"c[óo]mo se ve",
    r"muestra?(?:me)?",
    r"ense[ñn]a?(?:me)?.*(?:foto|imagen)",
    r"d[ée]jame ver",
    r"color[es]?\s+(?:disponible|que hay)",
    r"en qu[eé] colores",
    r"v(?:ari|a)ntes de color",
    r"ver (.*) en (.*) color",
    # English
    r"photo",
    r"photos",
    r"picture",
    r"pictures",
    r"image",
    r"images",
    r"show me",
    r"can i see",
    r"let me see",
    r"what (?:color|colours) (?:does|do)",
    r"available colors",
    r"color variants",
    r"see.*in.*color",
]

COMPILED_PATTERNS = [re.compile(pattern, re.IGNORECASE) for pattern in PHOTO_REQUEST_PATTERNS]

# Respuestas del bot cuando se pide foto
BOT_PHOTO_RESPONSE_TEMPLATES = [
    "Dame un momento, estoy tomando fotos de los colores disponibles...",
    "Claro, un segundo que busco las imágenes...",
    "Perfecto, déjame obtener las fotos para ti...",
    "Espera un momento mientras recopilo las imágenes...",
]

BOT_PHOTO_RESPONSE_EN = [
    "Give me a moment, I'm getting the photos of the available colors...",
    "Sure, let me fetch the images for you...",
    "Perfect, let me gather those photos for you...",
    "One moment while I retrieve the images...",
]


def detect_photo_request(text: str) -> bool:
    """
    Detecta si el cliente está pidiendo fotos.
    
    Args:
        text: Mensaje del cliente
    
    Returns:
        True si parece una solicitud de fotos
    """
    if not text:
        return False

    text_lower = text.lower().strip()

    # Buscar patrones
    for pattern in COMPILED_PATTERNS:
        if pattern.search(text_lower):
            return True

    return False


def extract_photo_request_context(text: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Extrae contexto de la solicitud de fotos.
    
    Args:
        text: Mensaje del cliente
    
    Returns:
        Tuple[color_requested, size_requested]
        Ej: ("gris", "128GB") o ("negro", None) o (None, None)
    """
    color = None
    size = None

    # Colores comunes en español
    spanish_colors = {
        "negro": "negro",
        "blanco": "blanco",
        "gris": "gris",
        "azul": "azul",
        "verde": "verde",
        "rojo": "rojo",
        "dorado": "dorado",
        "oro": "oro",
        "plata": "plata",
        "rosa": "rosa",
        "de titán": "titán",
        "titanio": "titán",
        "púrpura": "púrpura",
        "naranja": "naranja",
    }

    # Colores en inglés
    english_colors = {
        "black": "negro",
        "white": "blanco",
        "gray": "gris",
        "grey": "gris",
        "blue": "azul",
        "green": "verde",
        "red": "rojo",
        "gold": "dorado",
        "silver": "plata",
        "pink": "rosa",
        "purple": "púrpura",
        "orange": "naranja",
        "titanium": "titán",
    }

    text_lower = text.lower()

    # Buscar colores
    for color_key, color_normal in {**spanish_colors, **english_colors}.items():
        if color_key in text_lower:
            color = color_normal
            break

    # Tamaños comunes (GB, TB, etc.)
    size_match = re.search(r"(\d+(?:TB|GB))", text_lower, re.IGNORECASE)
    if size_match:
        size = size_match.group(1)

    # RAM
    ram_match = re.search(r"(\d+(?:GB|TB)?\s*(?:RAM|memoria))", text_lower, re.IGNORECASE)
    if ram_match and not size:
        size = ram_match.group(1)

    return color, size


def get_response_for_photo_request(language: str = "es") -> str:
    """
    Obtiene una respuesta canned para responder al cliente.
    
    Args:
        language: "es" o "en"
    
    Returns:
        Respuesta del bot
    """
    import random

    templates = BOT_PHOTO_RESPONSE_TEMPLATES if language == "es" else BOT_PHOTO_RESPONSE_EN
    return random.choice(templates)


# Instrucciones para el prompt del bot
BOT_PHOTO_DETECTION_INSTRUCTIONS = """
## Solicitudes de Fotos

Si el cliente te pide fotos de un producto (expresiones como "foto", "imagen", "muéstrame", "en qué colores", etc.):

1. **Responde cálidamente**: Usa una de estas respuestas:
   - "Dame un momento, estoy tomando fotos de los colores disponibles..."
   - "Claro, déjame obtener las imágenes para ti..."

2. **Internamente (no el cliente lo ve)**: 
   - Llama a endpoint: POST /api/photo-requests/create
   - Payload: {
       "customer_id": "<phone_number>",
       "product_id": <product_id>,
       "product_name": "<nombre del producto>",
       "color_requested": "<color si mencionó>",
       "size_requested": "<GB/RAM si mencionó>"
     }

3. **Notificación al agente**:
   - El agente recibe notificación: "Cliente Juan pide fotos iPhone 15 en gris"
   - El agente toma/sube las fotos en el dashboard
   - Las fotos se envían al cliente automáticamente
   - El cliente cree que fue "el bot" quien las envió

**Ejemplo de flujo**:
- Cliente: "¿Tienes fotos del iPhone 15 en gris?"
- Bot (respuesta al cliente): "Claro, dame un momento que busco las imágenes"
- Bot (internamente): Crea photo request → Notifica agente
- Agente: Ve dashboard "Juan pide fotos iPhone 15 gris" → Toma fotos → Carga
- Sistema: Envía fotos a Juan
- Juan: Las recibe (cree que del bot)
- Bot (continúa): "Aquí están las fotos del iPhone 15 en gris. Como ves..."
"""

__all__ = [
    "detect_photo_request",
    "extract_photo_request_context",
    "get_response_for_photo_request",
    "BOT_PHOTO_DETECTION_INSTRUCTIONS",
]
