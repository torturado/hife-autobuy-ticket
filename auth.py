import requests
import logging
from rich.console import Console

console = Console()
logger = logging.getLogger(__name__)


def get_hife_token(email, password, client_secret=None):
    """
    Obtiene un nuevo token JWT de la API de HIFE.
    """
    headers = {
        'accept': 'application/json; charset=utf-8',
        'app-version': '2.0.8',
        'content-type': 'application/json; charset=utf-8',
        'user-agent': 'Dalvik/2.1.0 (Linux; U; Android 12; SM-S916U Build/9643478.0)'
    }

    # Si no hay client_secret, usamos el conocido por defecto para la app móvil
    if not client_secret:
        client_secret = "SBZD2UnizBSnrZfPReiipqwfGPEHFpPOdAU4uiYN"

    data = {
        'client_id': 2,
        'client_secret': client_secret,
        'grant_type': 'password',
        'username': email,
        'password': password
    }

    try:
        response = requests.post('https://middleware.hife.es/oauth/token',
                                 headers=headers,
                                 json=data,
                                 timeout=15)
        response.raise_for_status()
        result = response.json()

        access_token = result.get('access_token')
        if not access_token:
            logger.error("No se recibió access_token en la respuesta")
            return None

        return f'Bearer {access_token}'

    except Exception as e:
        logger.error(f"Error al obtener token de HIFE: {e}")
        return None
