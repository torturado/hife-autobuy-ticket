import requests
import schedule
import time
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters
import os
import asyncio
from datetime import datetime, timedelta
import pytz
from dotenv import load_dotenv
import logging
from logging.handlers import RotatingFileHandler
import json
from urllib3.filepost import encode_multipart_formdata
import secrets
from urllib.parse import urlencode
import signal
import threading

"""
HIFE BOT - Sistema automatizado de compra de billetes para HIFE.es

Este script permite la compra automatizada de billetes de autobús en la página web de HIFE,
personalizando horarios, rutas y bonos según las necesidades del usuario. 
El bot se conecta a Telegram para preguntar si deseas comprar los billetes según los horarios configurados.

Uso:
1. Configura el archivo .env usando setup_wizard.py
2. Ejecuta este script (python main.py)
3. El bot enviará notificaciones a Telegram en los horarios configurados

Autor: [Tu nombre/nickname si deseas]
Licencia: MIT
Versión: 1.0
"""

# Cargar variables de entorno desde archivo .env
load_dotenv()

# Configuración básica
BASE_URL = "https://www.hife.es"  # URL base de HIFE
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")  # Token del bot de Telegram
ALLOWED_USER_ID = int(os.getenv("TELEGRAM_USER_ID"))  # ID del usuario autorizado
HIFE_EMAIL = os.getenv("HIFE_EMAIL")  # Email de la cuenta HIFE
HIFE_PASSWORD = os.getenv("HIFE_PASSWORD")  # Contraseña de la cuenta HIFE

# Configuración de estaciones
ORIGIN_ID = os.getenv("ORIGIN_ID")  # ID de la estación de origen
ORIGIN_NAME = os.getenv("ORIGIN_NAME")  # Nombre de la estación de origen
DESTINATION_ID = os.getenv("DESTINATION_ID")  # ID de la estación de destino
DESTINATION_NAME = os.getenv("DESTINATION_NAME")  # Nombre de la estación de destino

# Verificar que todas las variables necesarias están disponibles
if not all([TELEGRAM_TOKEN, ALLOWED_USER_ID, HIFE_EMAIL, HIFE_PASSWORD, ORIGIN_ID, ORIGIN_NAME, DESTINATION_ID, DESTINATION_NAME]):
    print("Error: Faltan variables de entorno necesarias. Ejecuta setup_wizard.py primero.")
    exit(1)

# Estados para la conversación
WAITING_RESPONSE = 1

# Headers HTTP utilizados para las peticiones a HIFE
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "X-Requested-With": "XMLHttpRequest",
    "Origin": BASE_URL,
    "Referer": f"{BASE_URL}/rutas",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors", 
    "Sec-Fetch-Site": "same-origin"
}

# Inicializar la sesión HTTP
session = requests.Session()
session.headers.update(HEADERS)

# Variable global para la aplicación de Telegram
telegram_app = None
current_conversation_data = {
    'pending_response': False,
    'trip_type': None,
    'response_received': asyncio.Event()
}

# Cargar horarios desde las variables de entorno
def load_schedule_config():
    """Carga la configuración de horarios desde las variables de entorno."""
    horarios = {
        'ida': {
            'hora': os.getenv('OUTWARD_TIME_DEFAULT', ''),
            'pregunta': os.getenv('NOTIFICATION_ADVANCE', '75')  # Minutos de antelación
        },
        'vuelta': {}
    }
    
    # Cargar horarios específicos por día para ida
    for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']:
        day_time = os.getenv(f'OUTWARD_TIME_{day.upper()}', '')
        if day_time:
            horarios['ida'][day] = {'hora': day_time, 'pregunta': os.getenv('NOTIFICATION_ADVANCE', '75')}
    
    # Cargar horarios para vuelta
    for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']:
        day_time = os.getenv(f'RETURN_TIME_{day.upper()}', os.getenv('RETURN_TIME_DEFAULT', ''))
        if day_time:
            horarios['vuelta'][day] = {'hora': day_time, 'pregunta': os.getenv('NOTIFICATION_ADVANCE', '75')}
    
    return horarios

# Cargar IDs de viajes desde las variables de entorno
def load_trip_ids():
    """Carga los IDs de viajes desde las variables de entorno."""
    viajes = {
        'ida': {},
        'vuelta': {}
    }
    
    # Cargar IDs para ida
    default_ida = os.getenv('OUTWARD_TRIP_ID_DEFAULT', '')
    if default_ida:
        default_hora = os.getenv('OUTWARD_TIME_DEFAULT', '')
        if default_hora:
            viajes['ida'][default_hora] = default_ida
    
    # Cargar IDs específicos por día para ida
    for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']:
        day_id = os.getenv(f'OUTWARD_TRIP_ID_{day.upper()}', '')
        if day_id:
            day_time = os.getenv(f'OUTWARD_TIME_{day.upper()}', default_hora)
            if day_time:
                viajes['ida'][day_time] = day_id
    
    # Cargar IDs para vuelta
    default_vuelta = os.getenv('RETURN_TRIP_ID_DEFAULT', '')
    if default_vuelta:
        default_hora = os.getenv('RETURN_TIME_DEFAULT', '')
        if default_hora:
            viajes['vuelta'][default_hora] = default_vuelta
    
    # Cargar IDs específicos por día para vuelta
    for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']:
        day_id = os.getenv(f'RETURN_TRIP_ID_{day.upper()}', '')
        if day_id:
            day_time = os.getenv(f'RETURN_TIME_{day.upper()}', default_hora)
            if day_time:
                viajes['vuelta'][day_time] = day_id
    
    return viajes

# Cargar configuraciones
HORARIOS = load_schedule_config()
VIAJES = load_trip_ids()

# Constantes para el bono
BONUS_ID = os.getenv('BONUS_ID', '')

# Crear directorio para las respuestas si no existe
if not os.path.exists('responses'):
    os.makedirs('responses')

def verify_env_variables():
    """Verifica que todas las variables de entorno necesarias estén configuradas."""
    required_vars = {
        "TELEGRAM_TOKEN": TELEGRAM_TOKEN,
        "TELEGRAM_USER_ID": ALLOWED_USER_ID,
        "HIFE_EMAIL": HIFE_EMAIL,
        "HIFE_PASSWORD": HIFE_PASSWORD,
        "ORIGIN_ID": ORIGIN_ID,
        "ORIGIN_NAME": ORIGIN_NAME,
        "DESTINATION_ID": DESTINATION_ID,
        "DESTINATION_NAME": DESTINATION_NAME,
        "BONUS_ID": BONUS_ID
    }
    
    missing_vars = [var for var, value in required_vars.items() if not value]
    
    if missing_vars:
        print("Error: Faltan las siguientes variables en el archivo .env:")
        for var in missing_vars:
            print(f"- {var}")
        exit(1)
    
    # Verificar horarios y viajes
    if not HORARIOS['ida'].get('hora'):
        print("Error: No hay horarios de ida configurados (OUTWARD_TIME_DEFAULT)")
        exit(1)
    
    if not any(HORARIOS['vuelta'].get(day, {}).get('hora') for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']):
        print("Error: No hay horarios de vuelta configurados (RETURN_TIME_*)")
        exit(1)
    
    if not any(VIAJES['ida'].values()):
        print("Error: No hay IDs de viajes de ida configurados (OUTWARD_TRIP_ID_*)")
        exit(1)
    
    if not any(VIAJES['vuelta'].values()):
        print("Error: No hay IDs de viajes de vuelta configurados (RETURN_TRIP_ID_*)")
        exit(1)
    
    print("Variables de entorno verificadas correctamente")

# Añadir al inicio del script, después de load_dotenv()
verify_env_variables()

def login():
    """Inicia sesión en HIFE."""
    logger.info("Iniciando sesión en HIFE...")
    try:
        # 1. GET a la página de login para obtener el token CSRF
        r = session.get(f"{BASE_URL}/en/client/login")
        if r.status_code != 200:
            logger.error("Error al obtener página de login: %d", r.status_code)
            return False
            
        # Extraer token CSRF
        soup = BeautifulSoup(r.text, 'html.parser')
        csrf_meta = soup.find('meta', {'name': 'csrf-token'})
        if not csrf_meta or not csrf_meta.get('content'):
            logger.error("No se encontró token CSRF en la página de login")
            return False
            
        csrf_token = csrf_meta['content']
        
        # 2. Actualizar headers para el login
        session.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Cache-Control': 'max-age=0',
            'Connection': 'keep-alive',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://www.hife.es',
            'Referer': 'https://www.hife.es/en/client/login',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Sec-GPC': '1',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
            'sec-ch-ua': '"Not(A:Brand";v="99", "Brave";v="133", "Chromium";v="133"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
        })
        
        # 3. Preparar datos del login
        login_data = {
            '_token': csrf_token,
            'email': HIFE_EMAIL,
            'password': HIFE_PASSWORD,
            'redirect': ''
        }
        
        # 4. Realizar el POST de login
        r = session.post(
            f"{BASE_URL}/en/client/login",
            data=login_data,
            allow_redirects=True
        )
        
        # 5. Verificar si el login fue exitoso
        if '/my-private-area' not in r.url and '/mi-area-privada' not in r.url:
            logger.error("Login fallido - URL después del login: %s", r.url)
            return False
            
        logger.info("Login exitoso")
        return True
        
    except Exception as e:
        logger.exception("Error en el proceso de login")
        return False

def keep_session_alive():
    """Mantiene la sesión viva mediante heartbeats periódicos."""
    try:
        logger.debug("Ejecutando heartbeat...")
        
        # 1. Verificar cookies básicas
        if not all(cookie in session.cookies for cookie in ['XSRF-TOKEN', 'hife_session']):
            logger.warning("Faltan cookies esenciales en el heartbeat")
            return init_session()
            
        # 2. Intentar acceder al área privada
        r = session.get(
            f"{BASE_URL}/en/my-private-area",
            timeout=10,
            allow_redirects=False
        )
        
        # 3. Verificar respuesta
        if r.status_code in [301, 302, 401, 403] or '/login' in r.headers.get('Location', ''):
            logger.warning(f"Sesión expirada durante heartbeat (status: {r.status_code})")
            return init_session()
            
        # 4. Si la respuesta es 200 pero no contiene elementos esperados
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            if "Your current balance in Bono Virtual" not in r.text:
                logger.warning("Sesión parece inválida (no se encontraron elementos de usuario)")
                return init_session()
                
        # 5. Refrescar CSRF token periódicamente
        if r.status_code == 200:
            csrf_meta = soup.find('meta', {'name': 'csrf-token'})
            if csrf_meta and csrf_meta.get('content'):
                session.headers.update({
                    'X-CSRF-TOKEN': csrf_meta['content'],
                    'X-XSRF-TOKEN': session.cookies.get('XSRF-TOKEN', '')
                })
                logger.debug("Tokens actualizados en heartbeat")
            else:
                logger.warning("No se pudo actualizar CSRF token en heartbeat")
                return init_session()
        
        return r.status_code == 200
        
    except Exception as e:
        logger.warning(f"Error en heartbeat: {str(e)}")
        return init_session()

def init_session():
    """Inicia sesión en HIFE con reintentos y manejo de errores mejorado."""
    retry_count = 0
    max_retries = 3
    
    while retry_count < max_retries:
        try:
            logger.info(f"Iniciando sesión en HIFE (intento {retry_count + 1}/{max_retries})...")
            
            # 1. Limpiar cookies y headers anteriores
            session.cookies.clear()
            session.headers.clear()
            session.headers.update(HEADERS)
            
            # Configurar timeouts más agresivos
            session.timeout = (5, 15)  # (connect timeout, read timeout)
            
            # Configurar keep-alive
            session.headers.update({
                'Connection': 'keep-alive',
                'Keep-Alive': 'timeout=600, max=1000'  # 10 minutos de timeout
            })
            
            # 2. GET inicial para obtener el CSRF token
            login_headers = {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
                'Connection': 'keep-alive',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache',
                'sec-ch-ua': '"Not(A:Brand";v="99", "Brave";v="133", "Chromium";v="133"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'Upgrade-Insecure-Requests': '1',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36'
            }
            
            r = session.get(
                f"{BASE_URL}/en/client/login",
                headers=login_headers,
                timeout=10
            )
            
            if r.status_code != 200:
                logger.error(f"Error al obtener página de login: {r.status_code}")
                retry_count += 1
                time.sleep(5)
                continue
                
            # Extraer CSRF token
            soup = BeautifulSoup(r.text, 'html.parser')
            csrf_meta = soup.find('meta', {'name': 'csrf-token'})
            if not csrf_meta or not csrf_meta.get('content'):
                logger.error("No se encontró CSRF token")
                retry_count += 1
                time.sleep(5)
                continue
                
            csrf_token = csrf_meta['content']
            logger.info(f"CSRF token obtenido: {csrf_token}")
            
            # 3. POST con credenciales
            login_data = {
                '_token': csrf_token,
                'email': HIFE_EMAIL,
                'password': HIFE_PASSWORD,
                'redirect': ''
            }
            
            login_headers.update({
                'Cache-Control': 'max-age=0',
                'Content-Type': 'application/x-www-form-urlencoded',
                'Origin': BASE_URL,
                'Referer': f"{BASE_URL}/en/client/login"
            })
            
            r = session.post(
                f"{BASE_URL}/en/client/login",
                data=login_data,
                headers=login_headers,
                allow_redirects=True,
                timeout=15
            )
            
            # 4. Verificar login exitoso
            if r.status_code != 200:
                logger.error(f"Error en login: {r.status_code}")
                retry_count += 1
                time.sleep(5)
                continue
                
            # Verificar que estamos logueados buscando elementos específicos
            soup = BeautifulSoup(r.text, 'html.parser')
            if "Your current balance in Bono Virtual" not in r.text:
                logger.error("No se detectó login exitoso")
                retry_count += 1
                time.sleep(5)
                continue
                
            # 5. Actualizar headers de la sesión con los nuevos tokens
            xsrf_token = session.cookies.get('XSRF-TOKEN')
            if xsrf_token:
                session.headers.update({
                    'X-CSRF-TOKEN': csrf_token,
                    'X-XSRF-TOKEN': xsrf_token
                })
            
            # 6. Iniciar heartbeat periódico
            schedule.every(5).minutes.do(keep_session_alive)
            
            logger.info("Login exitoso y heartbeat programado")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error de red en login: {str(e)}")
            retry_count += 1
            time.sleep(5)
            continue
        except Exception as e:
            logger.exception("Error inesperado en login")
            retry_count += 1
            time.sleep(5)
            continue
            
    logger.error("Se agotaron todos los intentos de login")
    return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja el comando /start."""
    if update.effective_user.id != ALLOWED_USER_ID:
        await update.message.reply_text("Lo siento, no estás autorizado para usar este bot.")
        return
        
    welcome_message = (
        f"¡Hola! Soy tu bot para comprar billetes en HIFE.\n\n"
        f"🚌 *Ruta configurada:* {ORIGIN_NAME} ↔️ {DESTINATION_NAME}\n\n"
        f"Te preguntaré cada día si quieres comprar billetes según los horarios configurados.\n"
        f"Usa /ayuda para ver todos los comandos disponibles."
    )
    
    await update.message.reply_text(welcome_message, parse_mode='Markdown')

async def handle_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja la respuesta del usuario."""
    if update.effective_user.id != ALLOWED_USER_ID:
        return
    
    if not current_conversation_data['pending_response']:
        return
    
    response = update.message.text.lower()
    trip_type = current_conversation_data['trip_type']
    date_str = current_conversation_data.get('date_str')
    going_date = current_conversation_data.get('going_date')
    
    if response in ['si', 'sí', 's', 'yes', 'y']:
        await update.message.reply_text(f"¡Perfecto! Procedo a comprar el billete de {trip_type}...")
        result = purchase_ticket(
            trip_type=trip_type,
            date_str=date_str,
            going_date=going_date
        )
        
        if result:
            # Obtener la hora según el tipo de viaje
            hora_viaje = get_trip_time(trip_type)
            origen = ORIGIN_NAME if trip_type == "ida" else DESTINATION_NAME
            destino = DESTINATION_NAME if trip_type == "ida" else ORIGIN_NAME
            
            mensaje = (
                f"✅ Billete comprado correctamente\n\n"
                f"🚌 Trayecto: {origen} → {destino}\n"
                f"📅 Fecha: {going_date}\n"
                f"⏰ Hora de salida: {hora_viaje}\n"
                f"📱 Ya lo tienes disponible en la APP de HIFE"
            )
            await update.message.reply_text(mensaje)
            
            if verify_purchase(trip_type, date_str):
                logger.info("Billete verificado en cartera")
            else:
                logger.warning("No se pudo verificar el billete en cartera")
        else:
            await update.message.reply_text(
                f"❌ Error: No se pudo completar la compra del billete de {trip_type}.\n"
                "Por favor, intenta comprarlo manualmente."
            )
    else:
        await update.message.reply_text(f"De acuerdo, no compraré el billete de {trip_type}.")
    
    current_conversation_data['pending_response'] = False
    current_conversation_data['response_received'].set()

    current_conversation_data['date_str'] = date_str
    current_conversation_data['going_date'] = going_date

def get_trip_time(trip_type):
    """Obtiene la hora del viaje según el tipo y día de la semana."""
    today = datetime.now(pytz.timezone('Europe/Madrid'))
    weekday = today.strftime('%A').lower()
    
    if trip_type == "ida":
        # Buscar horario específico para el día
        if weekday in HORARIOS['ida']:
            return HORARIOS['ida'][weekday]['hora']
        # Si no hay específico, usar el default
        return HORARIOS['ida']['hora']
    else:  # vuelta
        # Buscar horario específico para el día
        if weekday in HORARIOS['vuelta']:
            return HORARIOS['vuelta'][weekday]['hora']
        # Si no hay específico, usar el default (no debería ocurrir)
        return HORARIOS['vuelta'].get('default', {}).get('hora', '')

async def ask_for_ticket(trip_type: str):
    """Pregunta al usuario si desea comprar un billete."""
    if telegram_app is None:
        print("Error: La aplicación de Telegram no está inicializada")
        return

    # Calcular fecha actual (no mañana)
    today = datetime.now(pytz.timezone('Europe/Madrid'))
    date_str = today.strftime("%d-%m-%Y")
    going_date = today.strftime("%d/%m/%Y")

    current_conversation_data['pending_response'] = True
    current_conversation_data['trip_type'] = trip_type
    current_conversation_data['response_received'].clear()
    current_conversation_data['date_str'] = date_str
    current_conversation_data['going_date'] = going_date

    # Obtener la hora del viaje según el tipo y día
    hora_viaje = get_trip_time(trip_type)
    
    if not hora_viaje:
        logger.warning(f"No hay hora configurada para {trip_type} en {today.strftime('%A').lower()}")
        return

    # Origen y destino según el tipo de viaje
    origen = ORIGIN_NAME if trip_type == "ida" else DESTINATION_NAME
    destino = DESTINATION_NAME if trip_type == "ida" else ORIGIN_NAME

    # Enviar mensaje al usuario con la hora del viaje
    await telegram_app.bot.send_message(
        chat_id=ALLOWED_USER_ID,
        text=f"¿Quieres que compre el billete de {trip_type} para hoy? "
             f"({origen} → {destino} a las {hora_viaje}) (Sí/No)"
    )

    # Esperar la respuesta con un timeout de 50 minutos
    try:
        await asyncio.wait_for(current_conversation_data['response_received'].wait(), timeout=3000)
    except asyncio.TimeoutError:
        await telegram_app.bot.send_message(
            chat_id=ALLOWED_USER_ID,
            text=f"No se recibió respuesta a tiempo para el billete de {trip_type}. "
                 f"Se canceló la compra del viaje de las {hora_viaje}."
        )
        current_conversation_data['pending_response'] = False

def refresh_tokens():
    """Refresca los tokens CSRF y la sesión."""
    try:
        # 1. Primero obtener la página principal para obtener los tokens iniciales
        r = session.get(f"{BASE_URL}/en")
        if r.status_code != 200:
            logger.error("Error al obtener página principal: %d", r.status_code)
            return False
            
        # 2. Extraer el token CSRF del meta tag
        soup = BeautifulSoup(r.text, 'html.parser')
        csrf_meta = soup.find('meta', {'name': 'csrf-token'})
        if not csrf_meta or not csrf_meta.get('content'):
            logger.error("No se encontró token CSRF")
            return False
            
        csrf_token = csrf_meta['content']
        
        # 3. Actualizar los headers con los tokens y otros headers necesarios
        session.headers.update({
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.5',
            'X-CSRF-TOKEN': csrf_token,
            'X-XSRF-TOKEN': session.cookies.get('XSRF-TOKEN', ''),
            'X-Requested-With': 'XMLHttpRequest',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
            'sec-ch-ua': '"Not(A:Brand";v="99", "Brave";v="133", "Chromium";v="133"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-GPC': '1'
        })
        
        # 4. Hacer una petición a /my-private-area para validar la sesión
        r = session.get(f"{BASE_URL}/en/my-private-area")
        if r.status_code != 200:
            logger.error("Error al validar sesión: %d", r.status_code)
            return False
        
        # 5. Verificar que tenemos todas las cookies necesarias
        required_cookies = ['XSRF-TOKEN', 'hife_session']
        missing_cookies = [cookie for cookie in required_cookies if cookie not in session.cookies]
        if missing_cookies:
            logger.error(f"Faltan cookies: {missing_cookies}")
            return False
            
        logger.info("Tokens refrescados correctamente")
        logger.debug("CSRF Token: %s", csrf_token)
        logger.debug("XSRF Token: %s", session.cookies.get('XSRF-TOKEN'))
        logger.debug("Session: %s", session.cookies.get('hife_session'))
        
        return True
        
    except Exception as e:
        logger.exception("Error al refrescar tokens")
        return False

def verify_session():
    """Verifica que la sesión sigue activa y la renueva si es necesario.
    
    Realiza una verificación completa para asegurar que la sesión con HIFE
    está activa y operativa, no solo que tenemos las cookies necesarias.
    
    Returns:
        bool: True si la sesión está activa, False en caso contrario
    """
    try:
        # 1. Verificar que tenemos las cookies necesarias
        xsrf_token = session.cookies.get('XSRF-TOKEN')
        hife_session = session.cookies.get('hife_session')
        
        if not xsrf_token or not hife_session:
            logger.warning("Faltan cookies de sesión, necesitamos renovar")
            return False
            
        # 2. Verificar que tenemos el token CSRF en los headers
        if 'X-CSRF-TOKEN' not in session.headers:
            logger.warning("Falta X-CSRF-TOKEN en headers, necesitamos renovar")
            return False
            
        # 3. Verificación principal: Acceder al área privada
        try:
            r = session.get(
                f"{BASE_URL}/en/my-private-area",
                timeout=10,
                allow_redirects=False  # No seguir redirecciones para detectar mejor el estado de la sesión
            )
            
            # Si nos redirige al login o hay error de autenticación
            if r.status_code in [301, 302, 401, 403] or '/login' in r.headers.get('Location', ''):
                logger.warning(f"Sesión expirada (status: {r.status_code}), necesitamos renovar")
                return False
                
            if r.status_code != 200:
                logger.error(f"Error al verificar sesión: {r.status_code}")
                return False
                
            # Verificación profunda: Verificar que estamos realmente logueados 
            # buscando elementos específicos en el HTML
            soup = BeautifulSoup(r.text, 'html.parser')
            
            # Buscar elementos que solo aparecen cuando estamos logueados
            user_menu = soup.find('div', class_='align-self-center dropdownMainMenuText dropdownMainMenuTextHife')
            logged_in_element = soup.find(string=lambda text: "Your current balance in Bono Virtual" in text if text else False)
            
            if not user_menu and not logged_in_element:
                logger.warning("No se detectaron elementos de usuario logueado")
                return False
                
            # 4. Verificación secundaria: Intentar acceder a tickets
            try:
                tickets_check = session.get(
                    f"{BASE_URL}/en/tickets-management", 
                    timeout=5,
                    allow_redirects=False
                )
                if tickets_check.status_code != 200:
                    logger.warning(f"No se pudo acceder a tickets (status: {tickets_check.status_code})")
                    return False
            except Exception as e:
                logger.warning(f"Error al verificar tickets: {str(e)}")
                # No fallamos aquí, ya que el área privada estaba bien
            
            logger.info("Sesión verificada correctamente")
            return True
                
        except requests.exceptions.RequestException as e:
            logger.warning(f"Error de red al verificar sesión: {str(e)}")
            return False
                
    except Exception as e:
        logger.exception("Error inesperado al verificar sesión")
        return False
        
def verify_purchase(trip_type, date_str):
    """Verifica que el billete existe en la cartera."""
    try:
        logger.info("Verificando billete en cartera...")
        r = session.get(f"{BASE_URL}/en/tickets-management")
        logger.info(f"Status de tickets-management: {r.status_code}")
        
        if r.status_code != 200:
            logger.error("Error al verificar billete")
            return False
            
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # Buscar el localizador
        locator_div = soup.find('div', class_='locator_info')
        if locator_div:
            locator = locator_div.text.strip().split(':')[-1].strip()
            logger.info(f"Localizador encontrado: {locator}")
            
        # Buscar el número de billete
        ticket_number = soup.find('div', class_='ticket-number')
        if ticket_number:
            ticket_id = ticket_number.find('strong').text.strip()
            logger.info(f"Número de billete: {ticket_id}")
            
        # Buscar la fecha y hora
        trip_date = soup.find('div', class_='trip_date_go')
        trip_times = soup.find_all('div', class_='trip_time')
        if trip_date and len(trip_times) >= 2:
            fecha = trip_date.text.strip()
            hora_salida = trip_times[0].text.strip()
            hora_llegada = trip_times[1].text.strip()
            logger.info(f"Fecha: {fecha}")
            logger.info(f"Horario: {hora_salida} - {hora_llegada}")
            
            if date_str in fecha:
                logger.info(f"Billete verificado para fecha {date_str}")
                return True
                
        logger.error(f"No se encontró billete para fecha {date_str}")
        return False
        
    except Exception as e:
        logger.exception("Error al verificar billete")
        return False

def refresh_csrf():
    """Actualiza el token CSRF y las cookies de sesión con reintentos.
    
    Esta función es crítica para mantener una sesión válida con HIFE.
    Obtiene un nuevo token CSRF y actualiza las cookies para permitir 
    peticiones autenticadas.
    
    Returns:
        bool: True si se actualizaron los tokens correctamente, False en caso contrario
    """
    retry_count = 0
    max_retries = 3
    
    while retry_count < max_retries:
        try:
            logger.info(f"Intentando refrescar CSRF token (intento {retry_count + 1}/{max_retries})...")
            
            # 1. Primero obtener cookies frescas de la página principal
            headers = {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'Pragma': 'no-cache',
                'Upgrade-Insecure-Requests': '1',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36'
            }
            
            # Usar un timeout más corto para detectar problemas de red rápidamente
            try:
                r = session.get(
                    f"{BASE_URL}/",
                    headers=headers,
                    timeout=10,
                    allow_redirects=True
                )
            except requests.exceptions.Timeout:
                logger.error("Timeout al conectar con HIFE. Verificando conexión a internet...")
                retry_count += 1
                time.sleep(5)
                continue
            except requests.exceptions.ConnectionError:
                logger.error("Error de conexión. Verificando red...")
                retry_count += 1
                time.sleep(5)
                continue
            
            if r.status_code != 200:
                logger.error(f"Error al obtener página principal: {r.status_code}")
                retry_count += 1
                time.sleep(5)
                continue
                
            # 2. Obtener el token CSRF de la página de login
            try:
                r = session.get(
                    f"{BASE_URL}/client/login",
                    headers=headers,
                    timeout=10
                )
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
                logger.error("Problema de conexión al obtener página de login")
                retry_count += 1
                time.sleep(5)
                continue
            
            if r.status_code != 200:
                logger.error(f"Error al obtener página de login: {r.status_code}")
                retry_count += 1
                time.sleep(5)
                continue
                
            soup = BeautifulSoup(r.text, 'html.parser')
            csrf = soup.find('meta', {'name': 'csrf-token'})
            
            if not csrf or not csrf.get('content'):
                logger.error("No se encontró CSRF token en página de login")
                retry_count += 1
                time.sleep(5)
                continue
                
            csrf_token = csrf['content']
            logger.info(f"CSRF token obtenido: {csrf_token}")
            
            # 3. Verificar y obtener cookies necesarias
            xsrf_token = session.cookies.get('XSRF-TOKEN')
            hife_session = session.cookies.get('hife_session')
            
            if not xsrf_token or not hife_session:
                logger.warning("Faltan cookies esenciales, intentando renovar sesión...")
                if not init_session():
                    retry_count += 1
                    time.sleep(5)
                    continue
                # Obtener cookies actualizadas después de init_session
                xsrf_token = session.cookies.get('XSRF-TOKEN')
                hife_session = session.cookies.get('hife_session')
                
            # 4. Actualizar headers de la sesión
            session.headers.update({
                'X-CSRF-TOKEN': csrf_token,
                'X-XSRF-TOKEN': xsrf_token if xsrf_token else '',
                'Cookie': f'XSRF-TOKEN={xsrf_token}; hife_session={hife_session}'
            })
            
            # 5. Verificar que la sesión está activa
            r = session.get(
                f"{BASE_URL}/mi-area-privada",
                headers=headers,
                timeout=10,
                allow_redirects=False
            )
            
            if r.status_code in [301, 302, 401, 403] or '/login' in r.headers.get('Location', ''):
                logger.warning("Sesión no válida después de refrescar tokens")
                retry_count += 1
                time.sleep(5)
                continue
                
            if r.status_code != 200:
                logger.error(f"Error al verificar sesión después de refrescar tokens: {r.status_code}")
                retry_count += 1
                time.sleep(5)
                continue
                
            logger.info("CSRF token y cookies actualizados correctamente")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error de red al refrescar tokens: {str(e)}")
            retry_count += 1
            time.sleep(5)
            continue
        except Exception as e:
            logger.exception("Error inesperado al refrescar tokens")
            retry_count += 1
            time.sleep(5)
            continue
            
    logger.error("Se agotaron todos los intentos de refrescar tokens")
    return False

def check_session():
    """Verifica si la sesión sigue activa"""
    r = session.get(f"{BASE_URL}/en/my-private-area")
    if "Your current balance in Bono Virtual" not in r.text:
        logger.warning("Sesión expirada, renovando...")
        return init_session()
    return True

def get_available_bonuses(html):
    """Extrae los bonos disponibles del HTML de la página de pasajeros."""
    soup = BeautifulSoup(html, 'html.parser')
    select = soup.find('select', {'name': 'passenger[1][1][form_bonus]'})
    if not select:
        return []
    
    bonuses = []
    for option in select.find_all('option'):
        if option.get('value'):  # Ignorar la opción "Seleccionar..."
            bonuses.append({
                'value': option['value'],
                'text': option.text
            })
    return bonuses

def purchase_ticket(trip_type="ida", date_str=None, going_date=None):
    """Realiza el proceso completo de compra del billete.
    
    Args:
        trip_type (str): Tipo de viaje ('ida' o 'vuelta')
        date_str (str): Fecha del viaje en formato DD-MM-YYYY
        going_date (str): Fecha del viaje en formato DD/MM/YYYY
        
    Returns:
        bool: True si la compra fue exitosa, False en caso contrario
    """
    retry_count = 0
    max_retries = 3
    
    # Validar argumentos
    if trip_type not in ["ida", "vuelta"]:
        logger.error(f"Tipo de viaje inválido: {trip_type}. Debe ser 'ida' o 'vuelta'.")
        return False
        
    if not date_str or not going_date:
        # Usar fecha actual si no se proporciona
        today = datetime.now(pytz.timezone('Europe/Madrid'))
        date_str = date_str or today.strftime("%d-%m-%Y")
        going_date = going_date or today.strftime("%d/%m/%Y")
        logger.info(f"Usando fecha actual: {going_date}")
    
    logger.info(f"Iniciando compra de billete de {trip_type} para {going_date}")
    
    while retry_count < max_retries:
        try:
            # Verificar y renovar sesión si es necesario
            if not verify_session():
                logger.info("Renovando sesión...")
                if not init_session():
                    logger.error("No se pudo renovar la sesión")
                    retry_count += 1
                    time.sleep(2)  # Añadir delay entre reintentos
                    continue

            # Refrescar CSRF token antes de iniciar el proceso
            csrf_retry_count = 0
            max_csrf_retries = 3

            while csrf_retry_count < max_csrf_retries:
                if refresh_csrf():
                    break
                logger.warning(f"Intento {csrf_retry_count + 1} de {max_csrf_retries} para refrescar CSRF token")
                csrf_retry_count += 1
                if csrf_retry_count < max_csrf_retries:
                    time.sleep(5)  # Esperar más tiempo entre intentos
                    # Intentar renovar la sesión antes de reintentar
                    init_session()
                else:
                    logger.error("No se pudo refrescar el CSRF token después de todos los intentos")
                    return False

            # Obtener nuevo CSRF token de la página de rutas
            rutas_headers = {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
                'Connection': 'keep-alive',
                'sec-ch-ua': '"Not(A:Brand";v="99", "Brave";v="133", "Chromium";v="133"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'Upgrade-Insecure-Requests': '1',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
                'Sec-GPC': '1',
                'Sec-Fetch-Site': 'same-origin',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-User': '?1',
                'Sec-Fetch-Dest': 'document',
                'Referer': f"{BASE_URL}/mi-area-privada"
            }

            # Construir URL de rutas con parámetros
            # Configurar origen/destino según dirección
            from_id = ORIGIN_ID if trip_type == "ida" else DESTINATION_ID
            to_id = DESTINATION_ID if trip_type == "ida" else ORIGIN_ID
            from_name = ORIGIN_NAME if trip_type == "ida" else DESTINATION_NAME
            to_name = DESTINATION_NAME if trip_type == "ida" else ORIGIN_NAME
            
            rutas_params = {
                'ts': int(time.time() * 1000),
                'filter_pmrsr': '0',
                'filter_open_return': '0',
                'enterprise_slug': '',
                'is_round_trip_same_day': 'false',
                'filter_from': from_id,
                'filter_from_name': from_name,
                'filter_to': to_id,
                'filter_to_name': to_name,
                'filter_departure': going_date,
                'filter_arrival': '',
                'filter_adult': '1',
                'filter_child': '0',
                'filter_child_without_seat': '0'
            }

            rutas_url = f"{BASE_URL}/rutas?" + "&".join([f"{k}={v}" for k, v in rutas_params.items()])
            
            r = session.get(
                rutas_url,
                headers=rutas_headers,
                cookies=session.cookies
            )

            if r.status_code != 200:
                logger.error(f"Error al obtener página de rutas: {r.status_code}")
                retry_count += 1
                continue

            soup = BeautifulSoup(r.text, 'html.parser')
            csrf_meta = soup.find('meta', {'name': 'csrf-token'})
            if not csrf_meta:
                logger.error("No se encontró CSRF token en página de rutas")
                retry_count += 1
                continue

            csrf_token = csrf_meta['content']
            
            # Verificar estado de la sesión antes de hacer la reserva
            session_check = session.get(f"{BASE_URL}/mi-area-privada", allow_redirects=False)
            if session_check.status_code in [301, 302, 401, 403] or '/login' in session_check.headers.get('Location', ''):
                logger.warning("Sesión inválida antes de hacer la reserva, intentando renovar...")
                if not init_session():
                    logger.error("No se pudo renovar la sesión")
                    retry_count += 1
                    time.sleep(5)
                    continue
                # Obtener nuevo CSRF token después de renovar sesión
                r = session.get(f"{BASE_URL}/rutas")
                if r.status_code != 200:
                    logger.error("Error al obtener nuevo CSRF token")
                    retry_count += 1
                    continue
                soup = BeautifulSoup(r.text, 'html.parser')
                csrf_meta = soup.find('meta', {'name': 'csrf-token'})
                if not csrf_meta:
                    logger.error("No se encontró nuevo CSRF token")
                    retry_count += 1
                    continue
                csrf_token = csrf_meta['content']

            # Obtener ID del viaje según tipo y hora
            today = datetime.now(pytz.timezone('Europe/Madrid'))
            weekday = today.strftime('%A').lower()
            
            if trip_type == "ida":
                # Buscar ID específico para el día
                if weekday in HORARIOS['ida'] and HORARIOS['ida'][weekday]['hora'] in VIAJES['ida']:
                    viaje_id = VIAJES['ida'][HORARIOS['ida'][weekday]['hora']]
                # Si no hay específico, usar default
                elif HORARIOS['ida']['hora'] in VIAJES['ida']:
                    viaje_id = VIAJES['ida'][HORARIOS['ida']['hora']]
                else:
                    logger.error("No se encontró ID para el viaje de ida")
                    return False
            else:  # vuelta
                # Buscar ID específico para el día
                if weekday in HORARIOS['vuelta'] and HORARIOS['vuelta'][weekday]['hora'] in VIAJES['vuelta']:
                    viaje_id = VIAJES['vuelta'][HORARIOS['vuelta'][weekday]['hora']]
                # Si no hay específico, usar default
                elif 'default' in HORARIOS['vuelta'] and HORARIOS['vuelta']['default']['hora'] in VIAJES['vuelta']:
                    viaje_id = VIAJES['vuelta'][HORARIOS['vuelta']['default']['hora']]
                else:
                    logger.error("No se encontró ID para el viaje de vuelta")
                    return False

            # Preparar datos de reserva
            boundary = f'----WebKitFormBoundary{secrets.token_hex(8)}'
            
            form_data = {
                'quantity': '1',
                'quantity_childs': '0',
                'quantity_childs_without_seat': '0',
                'pmrsr': '0',
                'origin_schedule': viaje_id,
                'goingTripDay': going_date,
                'goingPrice': '995',
                'insurance': '0',
                'operation_type': '0'
            }

            # Preparar headers para la petición
            headers = HEADERS.copy()
            headers.update({
                'Content-Type': f'multipart/form-data; boundary={boundary}',
                'Referer': f"{BASE_URL}/rutas",
                'X-CSRF-TOKEN': csrf_token,
                'X-XSRF-TOKEN': session.cookies.get('XSRF-TOKEN', '')
            })

            # Log datos de la petición
            logger.info(f"Enviando petición de reserva para viaje {trip_type}")
            logger.debug(f"URL de reserva: {BASE_URL}/route/reservation")
            logger.debug(f"Datos del formulario: {form_data}")
            logger.debug(f"Headers de la petición: {headers}")

            # Codificar los datos del formulario con el boundary correcto
            body, content_type = encode_multipart_formdata(form_data, boundary=boundary)

            # Actualizar Content-Type con el generado por encode_multipart_formdata
            headers.update({
                'Content-Type': content_type
            })

            # Log cookies y tokens
            logger.debug(f"Cookies de sesión: {dict(session.cookies)}")
            logger.debug(f"CSRF Token: {csrf_token}")
            logger.debug(f"XSRF Token: {session.cookies.get('XSRF-TOKEN', '')}")

            r = session.post(
                f"{BASE_URL}/route/reservation",
                data=body,
                headers=headers,
                cookies=session.cookies
            )
            
            # Guardar respuesta de reserva inicial
            with open(f'responses/1_reservation.txt', 'w', encoding='utf-8') as f:
                f.write(f"Status: {r.status_code}\n")
                f.write(f"Headers: {dict(r.headers)}\n")
                f.write(f"Response: {r.text}\n")

            if r.status_code != 200:
                logger.error(f"Error en reserva inicial: {r.status_code}")
                retry_count += 1
                continue

            try:
                reservation_response = r.json()
                logger.debug(f"Respuesta de reserva completa: {reservation_response}")
                
                if not isinstance(reservation_response, dict):
                    logger.error(f"Respuesta de reserva no es un diccionario: {type(reservation_response)}")
                    retry_count += 1
                    continue
                    
                operation_token = reservation_response.get('operation_token')
                
                if not operation_token:
                    logger.error("No se recibió token de operación en la respuesta")
                    logger.error(f"Contenido de la respuesta: {reservation_response}")
                    
                    # Verificar si hay algún mensaje de error en la respuesta
                    if 'error' in reservation_response:
                        logger.error(f"Error reportado por el servidor: {reservation_response['error']}")
                    if 'message' in reservation_response:
                        logger.error(f"Mensaje del servidor: {reservation_response['message']}")
                        
                    retry_count += 1
                    time.sleep(5)  # Esperar más tiempo antes de reintentar
                    continue
                    
            except json.JSONDecodeError as e:
                logger.error(f"Error al decodificar respuesta JSON: {str(e)}")
                logger.error(f"Respuesta recibida: {r.text}")
                retry_count += 1
                continue
            except Exception as e:
                logger.exception("Error inesperado al procesar respuesta de reserva")
                retry_count += 1
                continue

            # Si el token viene en una lista, tomar el primer elemento
            if isinstance(operation_token, list):
                if not operation_token[0]:
                    logger.error("Token de operación vacío en la lista")
                    retry_count += 1
                    time.sleep(2)
                    continue
                operation_token = operation_token[0]
                
            # Verificar longitud del token
            if len(operation_token) < 32:  # Los tokens suelen ser largos
                logger.error(f"Token de operación demasiado corto: {operation_token}")
                retry_count += 1
                time.sleep(2)
                continue

            logger.info(f"Token de operación válido obtenido: {operation_token}")

            # URLs correctas según peticiones.txt
            passengers_url = f"{BASE_URL}/pasajeros/{operation_token}"
            operation_update_url = f"{BASE_URL}/actualizar-operacion/{operation_token}"
            payment_url = f"{BASE_URL}/pago/{operation_token}"
            proceed_url = f"{BASE_URL}/route/{operation_token}/proceed-reservation"
            complete_url = f"{BASE_URL}/compra-completada/{operation_token}"

            # Modificar la parte de acceso a la página de pasajeros
            passengers_retry = 0
            max_passengers_retries = 3
            
            while passengers_retry < max_passengers_retries:
                logger.info(f"Intento {passengers_retry + 1} de acceder a página de pasajeros: {passengers_url}")
                r = session.get(
                    passengers_url,
                    headers=HEADERS,
                    cookies=session.cookies
                )

                # Guardar respuesta de pasajeros
                with open('responses/2_passengers.txt', 'w', encoding='utf-8') as f:
                    f.write(f"Status: {r.status_code}\n")
                    f.write(f"Headers: {dict(r.headers)}\n")
                    f.write(f"Response: {r.text}\n")

                if r.status_code != 200:
                    logger.error(f"Error al acceder a página de pasajeros: {r.status_code}")
                    return False


                if r.status_code == 500:
                    logger.warning(f"Error 500 al acceder a pasajeros (intento {passengers_retry + 1})")
                    passengers_retry += 1
                    if passengers_retry < max_passengers_retries:
                        logger.info("Esperando 5 segundos antes de reintentar...")
                        time.sleep(5)
                        # Renovar sesión antes de reintentar
                        init_session()
                        continue
                    else:
                        logger.error("Se agotaron los reintentos para página de pasajeros")
                        return False
                elif r.status_code != 200:
                    logger.error(f"Error no esperado al acceder a pasajeros: {r.status_code}")
                    return False
                else:
                    break  # Si llegamos aquí, la petición fue exitosa

            # Obtener bonos disponibles
            bonuses = get_available_bonuses(r.text)
            logger.info(f"Bonos disponibles: {bonuses}")
            
            if not bonuses:
                logger.error("No hay bonos disponibles")
                return False
                
            # Verificar si nuestro bono está disponible
            available_bonus_ids = [b['value'] for b in bonuses]
            if BONUS_ID not in available_bonus_ids:
                logger.error(f"El bono {BONUS_ID} no está disponible")
                logger.error(f"Bonos disponibles: {bonuses}")
                return False

            # Actualizar operación
            logger.info(f"Actualizando operación: {operation_update_url}")

            # Continuar con la actualización de operación
            update_data = {
                '_method': 'PATCH',
                '_token': csrf_token,
                'filter_adult': '1',
                'filter_child': '0',
                'filter_childs_without_seat': '0',
                'passenger[1][1][form_bonus]': BONUS_ID
            }

            # Headers exactamente como en la petición original
            update_headers = {
                'Connection': 'keep-alive',
                'Cache-Control': 'max-age=0',
                'sec-ch-ua': '"Not(A:Brand";v="99", "Brave";v="133", "Chromium";v="133"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'Origin': BASE_URL,
                'Content-Type': 'application/x-www-form-urlencoded',
                'Upgrade-Insecure-Requests': '1',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Sec-GPC': '1',
                'Sec-Fetch-Site': 'same-origin',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-User': '?1',
                'Sec-Fetch-Dest': 'document',
                'Referer': passengers_url,
                'Accept-Encoding': 'gzip, deflate, br, zstd',
                'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8'
            }

            # Asegurarnos de que los datos se codifican correctamente
            encoded_data = urlencode(update_data)

            r = session.post(
                operation_update_url,
                data=encoded_data,
                headers=update_headers,
                cookies=session.cookies,
                allow_redirects=True  # Importante para seguir la redirección
            )

            # Guardar respuesta de actualización
            with open('responses/3_operation_update.txt', 'w', encoding='utf-8') as f:
                f.write(f"Status: {r.status_code}\n")
                f.write(f"Headers: {dict(r.headers)}\n")
                f.write(f"Response: {r.text}\n")

            if r.status_code != 200:
                logger.error(f"Error al actualizar operación: {r.status_code}")
                try:
                    error_data = r.json()
                    logger.error(f"Detalles del error: {error_data}")
                except:
                    logger.error(f"Respuesta del servidor: {r.text}")
                return False

            # Acceder a página de pago
            logger.info(f"Accediendo a página de pago: {payment_url}")
            payment_headers = HEADERS.copy()
            payment_headers['Referer'] = passengers_url

            r = session.get(
                payment_url,
                headers=payment_headers,
                cookies=session.cookies
            )

            # Guardar respuesta de pago
            with open('responses/4_payment.txt', 'w', encoding='utf-8') as f:
                f.write(f"Status: {r.status_code}\n")
                f.write(f"Headers: {dict(r.headers)}\n")
                f.write(f"Response: {r.text}\n")

            if r.status_code != 200:
                logger.error(f"Error al obtener página de pago: {r.status_code}")
                if r.status_code == 500:
                    logger.error("Error 500 del servidor - Posible problema con la sesión o datos inválidos")
                return False

            # Obtener nuevo CSRF token de la página de pago
            soup = BeautifulSoup(r.text, 'html.parser')
            csrf_meta = soup.find('meta', {'name': 'csrf-token'})
            if not csrf_meta:
                logger.error("No se encontró CSRF token en página de pago")
                return False
            csrf_token = csrf_meta['content']

            # Hacer proceed-reservation directamente
            boundary = '----WebKitFormBoundarycKiu9w9s9pPbEtBQ'
            proceed_data = {
                'payment_method': '5',  # Bono gratuito
                '_method': 'PATCH'
            }

            proceed_headers = {
                'Accept': 'application/json, text/plain, */*',
                'Content-Type': f'multipart/form-data; boundary={boundary}',
                'Origin': BASE_URL,
                'Referer': payment_url,
                'X-CSRF-TOKEN': csrf_token,
                'X-XSRF-TOKEN': session.cookies.get('XSRF-TOKEN', ''),
                'X-Requested-With': 'XMLHttpRequest',
                'sec-ch-ua': '"Not(A:Brand";v="99", "Brave";v="133", "Chromium";v="133"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"'
            }

            body, _ = encode_multipart_formdata(proceed_data, boundary=boundary)

            r = session.post(
                proceed_url,
                data=body,
                headers=proceed_headers,
                cookies=session.cookies
            )

            # Guardar respuesta
            with open('responses/5_proceed_reservation.txt', 'w', encoding='utf-8') as f:
                f.write(f"Status: {r.status_code}\n")
                f.write(f"Headers: {dict(r.headers)}\n")
                f.write(f"Response: {r.text}\n")

            if r.status_code != 200:
                logger.error(f"Error en proceed-reservation: {r.status_code}")
                return False

            try:
                response_data = r.json()
                if not response_data.get('error', True):  # Si error es False, la compra fue exitosa
                    # Seguir el flujo de redirección para completar la compra
                    bonus_url = f"{payment_url}/bono-gratuito"
                    
                    # Headers para la petición del bono gratuito
                    bonus_headers = {
                        'Connection': 'keep-alive',
                        'Upgrade-Insecure-Requests': '1',
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                        'Sec-GPC': '1',
                        'Sec-Fetch-Site': 'same-origin',
                        'Sec-Fetch-Mode': 'navigate',
                        'Sec-Fetch-User': '?1',
                        'Sec-Fetch-Dest': 'document',
                        'sec-ch-ua': '"Not(A:Brand";v="99", "Brave";v="133", "Chromium";v="133"',
                        'sec-ch-ua-mobile': '?0',
                        'sec-ch-ua-platform': '"Windows"',
                        'Referer': payment_url,
                        'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8'
                    }

                    # Hacer la petición al bono gratuito que nos redirigirá
                    r = session.get(
                        bonus_url,
                        headers=bonus_headers,
                        cookies=session.cookies,
                        allow_redirects=False  # No seguir redirecciones automáticamente
                    )

                    # Guardar respuesta del bono gratuito
                    with open('responses/5_free_bonus.txt', 'w', encoding='utf-8') as f:
                        f.write(f"Status: {r.status_code}\n")
                        f.write(f"Headers: {dict(r.headers)}\n")
                        f.write(f"Response: {r.text}\n")

                    if r.status_code == 302:  # Verificar que recibimos la redirección
                        completed_url = r.headers.get('Location')
                        if completed_url:
                            # Headers para la petición final
                            complete_headers = {
                                'Connection': 'keep-alive',
                                'Upgrade-Insecure-Requests': '1',
                                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
                                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                                'Sec-GPC': '1',
                                'Sec-Fetch-Site': 'same-origin',
                                'Sec-Fetch-Mode': 'navigate',
                                'Sec-Fetch-Dest': 'document',
                                'sec-ch-ua': '"Not(A:Brand";v="99", "Brave";v="133", "Chromium";v="133"',
                                'sec-ch-ua-mobile': '?0',
                                'sec-ch-ua-platform': '"Windows"',
                                'Referer': completed_url,
                                'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8'
                            }

                            # Hacer la petición final a la página de compra completada
                            r = session.get(
                                completed_url,
                                headers=complete_headers,
                                cookies=session.cookies
                            )

                            # Guardar respuesta de compra completada
                            with open('responses/6_purchase_completed.txt', 'w', encoding='utf-8') as f:
                                f.write(f"Status: {r.status_code}\n")
                                f.write(f"Headers: {dict(r.headers)}\n")
                                f.write(f"Response: {r.text}\n")

                            if r.status_code == 200:
                                # Extraer el localizador final del HTML
                                soup = BeautifulSoup(r.text, 'html.parser')
                                locator_div = soup.find('div', class_='locator_info')
                                if locator_div:
                                    locator = locator_div.text.strip().split(':')[-1].strip()
                                    logger.info(f"¡Compra finalizada! Localizador final: {locator}")
                                    return True

            except Exception as e:
                logger.exception("Error al procesar la respuesta")

            return False

        except requests.exceptions.RequestException as e:
            logger.exception("Error de red al comprar billete")
            retry_count += 1
            time.sleep(2)
            continue
        except Exception as e:
            logger.exception("Error inesperado al comprar billete")
            retry_count += 1
            time.sleep(2)
            continue
            
    logger.error("Se agotaron todos los intentos de compra")
    return False

def get_return_time():
    """Obtiene la hora del viaje de vuelta según el día."""
    now = datetime.now(pytz.timezone('Europe/Madrid'))
    weekday = now.strftime('%A').lower()
    
    # Buscar horario específico para el día
    if weekday in HORARIOS['vuelta']:
        return HORARIOS['vuelta'][weekday]['hora']
    
    # Si no hay específico, usar default (no debería ocurrir)
    return HORARIOS['vuelta'].get('default', {}).get('hora', '')

def calculate_notification_time(trip_time, minutes_before=75):
    """Calcula la hora de notificación basada en el tiempo de viaje."""
    hour, minute = map(int, trip_time.split(':'))
    trip_datetime = datetime.now(pytz.timezone('Europe/Madrid')).replace(
        hour=hour, minute=minute, second=0, microsecond=0
    )
    notification_time = trip_datetime - timedelta(minutes=int(minutes_before))
    return notification_time.strftime("%H:%M")

def schedule_daily_messages():
    """Programa los mensajes diarios según los horarios configurados."""
    # Crear wrappers síncronos para las funciones asíncronas
    def sync_send_ida():
        asyncio.create_task(send_ida_message())
        
    def sync_send_vuelta():
        asyncio.create_task(send_vuelta_message())

    # Obtener minutos de antelación
    notification_advance = int(os.getenv('NOTIFICATION_ADVANCE', '75'))

    # Programar billete de ida para los días configurados
    for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']:
        # Usar hora específica del día si existe, sino usar default
        if day in HORARIOS['ida']:
            ida_time = HORARIOS['ida'][day]['hora']
        else:
            ida_time = HORARIOS['ida']['hora']
        
        if ida_time:
            notification_time = calculate_notification_time(ida_time, notification_advance)
            getattr(schedule.every(), day).at(notification_time).do(sync_send_ida)
            logger.info(f"Programada notificación de ida para {day} a las {notification_time}")

    # Programar billete de vuelta para los días configurados
    for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']:
        if day in HORARIOS['vuelta'] and HORARIOS['vuelta'][day]['hora']:
            vuelta_time = HORARIOS['vuelta'][day]['hora']
            notification_time = calculate_notification_time(vuelta_time, notification_advance)
            getattr(schedule.every(), day).at(notification_time).do(sync_send_vuelta)
            logger.info(f"Programada notificación de vuelta para {day} a las {notification_time}")

    logger.info("Tareas programadas correctamente")

async def send_ida_message():
    """Envía mensaje preguntando por el billete de ida."""
    await ask_for_ticket("ida")
    logger.info("Mensaje de ida enviado")

async def send_vuelta_message():
    """Envía mensaje preguntando por el billete de vuelta."""
    await ask_for_ticket("vuelta")
    logger.info("Mensaje de vuelta enviado")

async def handle_ida_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja la respuesta afirmativa para comprar billete de ida."""
    if update.effective_user.id != ALLOWED_USER_ID:
        return
        
    today = datetime.now(pytz.timezone('Europe/Madrid'))
    date_str = today.strftime("%d-%m-%Y")
    going_date = today.strftime("%d/%m/%Y")
    
    await update.message.reply_text("Comprando billete de ida...")
    
    result = purchase_ticket(
        trip_type="ida",
        date_str=date_str,
        going_date=going_date
    )
    
    if result:
        hora_viaje = get_trip_time("ida")
        await update.message.reply_text(f"✅ Billete de ida comprado correctamente para las {hora_viaje}")
    else:
        await update.message.reply_text("❌ Error al comprar el billete de ida")

async def handle_vuelta_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja la respuesta afirmativa para comprar billete de vuelta."""
    if update.effective_user.id != ALLOWED_USER_ID:
        return
        
    today = datetime.now(pytz.timezone('Europe/Madrid'))
    date_str = today.strftime("%d-%m-%Y")
    going_date = today.strftime("%d/%m/%Y")
    
    await update.message.reply_text("Comprando billete de vuelta...")
    
    result = purchase_ticket(
        trip_type="vuelta",
        date_str=date_str,
        going_date=going_date
    )
    
    if result:
        hora_viaje = get_trip_time("vuelta")
        await update.message.reply_text(f"✅ Billete de vuelta comprado correctamente para las {hora_viaje}")
    else:
        await update.message.reply_text("❌ Error al comprar el billete de vuelta")

async def show_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra la programación de billetes configurada."""
    if update.effective_user.id != ALLOWED_USER_ID:
        return
    
    message = "📅 Programación de billetes:\n\n"
    
    # Información de estaciones
    message += f"🚏 Ruta: {ORIGIN_NAME} ↔️ {DESTINATION_NAME}\n\n"
    
    # Horarios de IDA
    message += "🚌 HORARIOS IDA:\n"
    if 'hora' in HORARIOS['ida'] and HORARIOS['ida']['hora']:
        message += f"- Default: {HORARIOS['ida']['hora']}\n"
    
    for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']:
        day_names = {
            'monday': 'Lunes',
            'tuesday': 'Martes',
            'wednesday': 'Miércoles',
            'thursday': 'Jueves',
            'friday': 'Viernes'
        }
        if day in HORARIOS['ida'] and 'hora' in HORARIOS['ida'][day]:
            message += f"- {day_names[day]}: {HORARIOS['ida'][day]['hora']}\n"
    
    # Horarios de VUELTA
    message += "\n🚌 HORARIOS VUELTA:\n"
    for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']:
        if day in HORARIOS['vuelta'] and 'hora' in HORARIOS['vuelta'][day]:
            message += f"- {day_names[day]}: {HORARIOS['vuelta'][day]['hora']}\n"
    
    # Bono usado
    message += f"\n🎫 ID de bono: {BONUS_ID}"
    
    await update.message.reply_text(message)

async def init_telegram():
    """Inicializa el bot de Telegram."""
    global telegram_app
    telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Añadir manejadores de comandos
    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(CommandHandler("si_ida", handle_ida_command))
    telegram_app.add_handler(CommandHandler("si_vuelta", handle_vuelta_command))
    telegram_app.add_handler(CommandHandler("horarios", show_schedule))
    telegram_app.add_handler(CommandHandler("ayuda", show_help))
    telegram_app.add_handler(CommandHandler("estado", check_status))
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_response))
    
    await telegram_app.initialize()
    await telegram_app.start()
    await telegram_app.updater.start_polling()
    
    print("Bot de Telegram iniciado.")

async def main_async():
    """Función principal asíncrona."""
    try:
        # Iniciar sesión inicial
        if not init_session():
            logger.error("Error en el login inicial")
            return
            
        # Iniciar bot de Telegram
        await init_telegram()
        
        # Programar tareas diarias
        schedule_daily_messages()
        logger.info("Bot iniciado. Esperando tareas programadas...")
        
        last_heartbeat = time.time()
        last_full_session_check = time.time()
        heartbeat_interval = 180  # 3 minutos en segundos
        full_check_interval = 1800  # 30 minutos en segundos
        
        while True:
            current_time = time.time()
            
            # Ejecutar heartbeat cada 3 minutos
            if current_time - last_heartbeat >= heartbeat_interval:
                logger.debug("Ejecutando heartbeat programado...")
                if not keep_session_alive():
                    logger.warning("Heartbeat falló, intentando renovar sesión...")
                    retry_count = 0
                    while retry_count < 3:
                        if init_session():
                            logger.info("Sesión renovada exitosamente después de heartbeat fallido")
                            break
                        retry_count += 1
                        await asyncio.sleep(5)
                    if retry_count == 3:
                        logger.error("No se pudo renovar la sesión después de 3 intentos")
                last_heartbeat = current_time
            
            # Verificación completa de sesión cada 30 minutos
            if current_time - last_full_session_check >= full_check_interval:
                logger.info("Realizando verificación completa de sesión...")
                try:
                    # Verificar acceso completo
                    r = session.get(f"{BASE_URL}/en/my-private-area", timeout=15)
                    if "Your current balance in Bono Virtual" not in r.text:
                        logger.warning("Verificación completa falló, renovando sesión...")
                        if not init_session():
                            logger.error("Error al renovar sesión en verificación completa")
                    else:
                        # Refrescar tokens aunque la sesión parezca válida
                        if not refresh_csrf():
                            logger.warning("Error al refrescar tokens en verificación completa")
                            if not init_session():
                                logger.error("Error al renovar sesión después de fallo en tokens")
                except Exception as e:
                    logger.error(f"Error en verificación completa: {str(e)}")
                    if not init_session():
                        logger.error("Error al renovar sesión después de excepción")
                
                last_full_session_check = current_time
            
            # Ejecutar las tareas pendientes
            pending_jobs = [job for job in schedule.get_jobs() if job.should_run]
            for job in pending_jobs:
                try:
                    # Verificar sesión antes de ejecutar cada tarea
                    if not verify_session():
                        logger.warning("Sesión inválida antes de ejecutar tarea, renovando...")
                        if not init_session():
                            logger.error("No se pudo renovar la sesión antes de ejecutar tarea")
                            continue
                    
                    # Obtener los argumentos del job de forma segura
                    args = job.args if hasattr(job, 'args') else []
                    # Ejecutar la función del job (que ahora es síncrona)
                    job.job_func(*args)
                    job.last_run = datetime.now()
                    job._schedule_next_run()
                except Exception as e:
                    logger.exception(f"Error al ejecutar tarea programada: {str(e)}")
            
            # Esperar un segundo antes de la siguiente iteración
            await asyncio.sleep(1)
            
    except asyncio.CancelledError:
        logger.info("Tarea principal cancelada")
    except Exception as e:
        logger.exception("Error inesperado en main_async")
    finally:
        # Limpiar recursos
        if telegram_app:
            await telegram_app.updater.stop()
            await telegram_app.stop()
            await telegram_app.shutdown()
        
        # Cancelar todas las tareas programadas
        schedule.clear()
        
        logger.info("Recursos liberados correctamente")

def main():
    """Punto de entrada principal del programa.
    
    Configura el manejo de señales, ejecuta la aplicación principal 
    y gestiona la limpieza de recursos al finalizar.
    """
    # Configurar manejo de señales para cierre ordenado
    def signal_handler(sig, frame):
        if sig in (signal.SIGINT, signal.SIGTERM):
            logger.info(f"Recibida señal {sig}, cerrando el bot...")
            # La limpieza se hará en el bloque finally
            # Forzar la salida solo después del tiempo máximo de espera
            threading.Timer(10, lambda: os._exit(0)).start()
            raise KeyboardInterrupt
    
    # Registrar manejadores de señales en sistemas compatibles
    if hasattr(signal, 'SIGINT'):
        signal.signal(signal.SIGINT, signal_handler)
    if hasattr(signal, 'SIGTERM'):
        signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        logger.info("Iniciando bot HIFE")
        asyncio.run(main_async())
    except KeyboardInterrupt:
        logger.info("Cerrando el bot por interrupción del usuario")
    except Exception as e:
        logger.exception("Error inesperado")
    finally:
        logger.info("Bot cerrado correctamente")

def setup_logging():
    """Configura el sistema de logging."""
    # Crear el directorio logs si no existe
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # Configurar el logger principal
    logger = logging.getLogger('hife_bot')
    logger.setLevel(logging.DEBUG)
    
    # Formato detallado para los logs
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    
    # Handler para archivo con rotación (máximo 5 archivos de 1MB cada uno)
    file_handler = RotatingFileHandler(
        'logs/hife_bot.log',
        maxBytes=1024*1024,  # 1MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    
    # Handler para consola
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    # Añadir handlers al logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

# Crear logger global
logger = setup_logging()

def verify_purchase(trip_type, date_str):
    """Verifica que el billete existe en la cartera."""
    try:
        logger.info("Verificando billete en cartera...")
        r = session.get(f"{BASE_URL}/en/tickets-management")
        logger.info(f"Status de tickets-management: {r.status_code}")
        
        if r.status_code != 200:
            logger.error("Error al verificar billete")
            return False
            
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # Buscar el localizador
        locator_div = soup.find('div', class_='locator_info')
        if locator_div:
            locator = locator_div.text.strip().split(':')[-1].strip()
            logger.info(f"Localizador encontrado: {locator}")
            
        # Buscar el número de billete
        ticket_number = soup.find('div', class_='ticket-number')
        if ticket_number:
            ticket_id = ticket_number.find('strong').text.strip()
            logger.info(f"Número de billete: {ticket_id}")
            
        # Buscar la fecha y hora
        trip_date = soup.find('div', class_='trip_date_go')
        trip_times = soup.find_all('div', class_='trip_time')
        if trip_date and len(trip_times) >= 2:
            fecha = trip_date.text.strip()
            hora_salida = trip_times[0].text.strip()
            hora_llegada = trip_times[1].text.strip()
            logger.info(f"Fecha: {fecha}")
            logger.info(f"Horario: {hora_salida} - {hora_llegada}")
            
            if date_str in fecha:
                logger.info(f"Billete verificado para fecha {date_str}")
                return True
                
        logger.error(f"No se encontró billete para fecha {date_str}")
        return False
        
    except Exception as e:
        logger.exception("Error al verificar billete")
        return False

def refresh_csrf():
    """Actualiza el token CSRF y las cookies de sesión con reintentos.
    
    Esta función es crítica para mantener una sesión válida con HIFE.
    Obtiene un nuevo token CSRF y actualiza las cookies para permitir 
    peticiones autenticadas.
    
    Returns:
        bool: True si se actualizaron los tokens correctamente, False en caso contrario
    """
    retry_count = 0
    max_retries = 3
    
    while retry_count < max_retries:
        try:
            logger.info(f"Intentando refrescar CSRF token (intento {retry_count + 1}/{max_retries})...")
            
            # 1. Primero obtener cookies frescas de la página principal
            headers = {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'Pragma': 'no-cache',
                'Upgrade-Insecure-Requests': '1',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36'
            }
            
            # Usar un timeout más corto para detectar problemas de red rápidamente
            try:
                r = session.get(
                    f"{BASE_URL}/",
                    headers=headers,
                    timeout=10,
                    allow_redirects=True
                )
            except requests.exceptions.Timeout:
                logger.error("Timeout al conectar con HIFE. Verificando conexión a internet...")
                retry_count += 1
                time.sleep(5)
                continue
            except requests.exceptions.ConnectionError:
                logger.error("Error de conexión. Verificando red...")
                retry_count += 1
                time.sleep(5)
                continue
            
            if r.status_code != 200:
                logger.error(f"Error al obtener página principal: {r.status_code}")
                retry_count += 1
                time.sleep(5)
                continue
                
            # 2. Obtener el token CSRF de la página de login
            try:
                r = session.get(
                    f"{BASE_URL}/client/login",
                    headers=headers,
                    timeout=10
                )
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
                logger.error("Problema de conexión al obtener página de login")
                retry_count += 1
                time.sleep(5)
                continue
            
            if r.status_code != 200:
                logger.error(f"Error al obtener página de login: {r.status_code}")
                retry_count += 1
                time.sleep(5)
                continue
                
            soup = BeautifulSoup(r.text, 'html.parser')
            csrf = soup.find('meta', {'name': 'csrf-token'})
            
            if not csrf or not csrf.get('content'):
                logger.error("No se encontró CSRF token en página de login")
                retry_count += 1
                time.sleep(5)
                continue
                
            csrf_token = csrf['content']
            logger.info(f"CSRF token obtenido: {csrf_token}")
            
            # 3. Verificar y obtener cookies necesarias
            xsrf_token = session.cookies.get('XSRF-TOKEN')
            hife_session = session.cookies.get('hife_session')
            
            if not xsrf_token or not hife_session:
                logger.warning("Faltan cookies esenciales, intentando renovar sesión...")
                if not init_session():
                    retry_count += 1
                    time.sleep(5)
                    continue
                # Obtener cookies actualizadas después de init_session
                xsrf_token = session.cookies.get('XSRF-TOKEN')
                hife_session = session.cookies.get('hife_session')
                
            # 4. Actualizar headers de la sesión
            session.headers.update({
                'X-CSRF-TOKEN': csrf_token,
                'X-XSRF-TOKEN': xsrf_token if xsrf_token else '',
                'Cookie': f'XSRF-TOKEN={xsrf_token}; hife_session={hife_session}'
            })
            
            # 5. Verificar que la sesión está activa
            r = session.get(
                f"{BASE_URL}/mi-area-privada",
                headers=headers,
                timeout=10,
                allow_redirects=False
            )
            
            if r.status_code in [301, 302, 401, 403] or '/login' in r.headers.get('Location', ''):
                logger.warning("Sesión no válida después de refrescar tokens")
                retry_count += 1
                time.sleep(5)
                continue
                
            if r.status_code != 200:
                logger.error(f"Error al verificar sesión después de refrescar tokens: {r.status_code}")
                retry_count += 1
                time.sleep(5)
                continue
                
            logger.info("CSRF token y cookies actualizados correctamente")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error de red al refrescar tokens: {str(e)}")
            retry_count += 1
            time.sleep(5)
            continue
        except Exception as e:
            logger.exception("Error inesperado al refrescar tokens")
            retry_count += 1
            time.sleep(5)
            continue
            
    logger.error("Se agotaron todos los intentos de refrescar tokens")
    return False

def check_session():
    """Verifica si la sesión sigue activa"""
    r = session.get(f"{BASE_URL}/en/my-private-area")
    if "Your current balance in Bono Virtual" not in r.text:
        logger.warning("Sesión expirada, renovando...")
        return init_session()
    return True

def handle_response(response, expected_status=200):
    """Maneja las respuestas HTTP"""
    if response.status_code != expected_status:
        logger.error(f"Error en petición: {response.status_code}")
        logger.error(f"Respuesta: {response.text}")
        if response.status_code == 419:  # CSRF token mismatch
            refresh_csrf()
            return False
        elif response.status_code in [401, 403]:
            init_session()
            return False
    return True

# Añadir nuevas funciones para comandos
async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra la ayuda del bot."""
    if update.effective_user.id != ALLOWED_USER_ID:
        return
        
    help_text = (
        "🤖 *Comandos disponibles:*\n\n"
        "/start - Inicia la conversación con el bot\n"
        "/si_ida - Compra inmediatamente un billete de ida para hoy\n"
        "/si_vuelta - Compra inmediatamente un billete de vuelta para hoy\n"
        "/horarios - Muestra los horarios configurados\n"
        "/estado - Comprueba el estado de la conexión con HIFE\n"
        "/ayuda - Muestra este mensaje de ayuda\n\n"
        "El bot te enviará automáticamente mensajes en los horarios programados "
        "para preguntarte si quieres comprar billetes."
    )
    
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def check_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comprueba el estado de la conexión con HIFE."""
    if update.effective_user.id != ALLOWED_USER_ID:
        return
        
    await update.message.reply_text("Comprobando conexión con HIFE...")
    
    # Verificar sesión
    if not verify_session():
        await update.message.reply_text("❌ Error: No hay sesión activa con HIFE. Intentando reconectar...")
        
        if init_session():
            await update.message.reply_text("✅ Reconexión exitosa.")
        else:
            await update.message.reply_text("❌ Error: No se pudo conectar con HIFE. Revisa tus credenciales.")
    else:
        # Verificar bono
        try:
            r = session.get(f"{BASE_URL}/en/tickets-management")
            if r.status_code == 200:
                await update.message.reply_text("✅ Conexión con HIFE correcta. Sesión activa.")
            else:
                await update.message.reply_text("⚠️ Conexión con HIFE inestable. Intentando reconectar...")
                # Intentar reconectar inmediatamente en lugar de esperar
                if init_session():
                    await update.message.reply_text("✅ Reconexión exitosa.")
                else:
                    await update.message.reply_text("❌ Error: No se pudo reconectar. Revisa tu conexión a internet.")
        except Exception as e:
            await update.message.reply_text(f"❌ Error de conexión: {str(e)[:100]}...")
            # También intentar reconectar en caso de excepción
            logger.error(f"Error al verificar tickets: {str(e)}")
            await update.message.reply_text("Intentando reconectar...")
            if init_session():
                await update.message.reply_text("✅ Reconexión exitosa después del error.")
            else:
                await update.message.reply_text("❌ No se pudo reconectar después del error.")

if __name__ == "__main__":
    main() 