import requests
from bs4 import BeautifulSoup
import json
import time
from datetime import datetime, timedelta
import pytz
import os
from getpass import getpass
from urllib.parse import urlencode
import secrets
import html
from urllib3.filepost import encode_multipart_formdata
from urllib.parse import quote

"""
HIFE BOT - Asistente de configuración

Este script guía al usuario a través del proceso de configuración para el bot de HIFE.
Permite configurar las credenciales, estaciones, horarios y bonos para la compra automática
de billetes de autobús en HIFE.es.

Uso:
1. Ejecutar este script (python setup_wizard.py)
2. Seguir las instrucciones interactivas
3. Al finalizar, se generará un archivo .env con la configuración

Autor: [Tu nombre/nickname si deseas]
Licencia: MIT
Versión: 1.0
"""

def print_header(text):
    """
    Imprime un encabezado formateado para las secciones del asistente.
    
    Args:
        text (str): Texto a mostrar como encabezado
    """
    print("\n" + "="*50)
    print(text)
    print("="*50 + "\n")

def get_telegram_info():
    """
    Solicita al usuario información sobre su bot de Telegram.
    
    Returns:
        tuple: (token del bot, ID de usuario)
    """
    print_header("Configuración de Telegram")
    print("Para obtener el token de tu bot:")
    print("1. Habla con @BotFather en Telegram")
    print("2. Usa el comando /newbot")
    print("3. Sigue las instrucciones y copia el token que te da")
    
    token = input("\nIntroduce el token de tu bot: ")
    user_id = input("Introduce tu ID de usuario de Telegram (puedes obtenerlo hablando con @userinfobot): ")
    
    return token, user_id

def get_hife_credentials():
    print_header("Credenciales de HIFE")
    print("Introduce tus credenciales de la web de HIFE")
    email = input("Email: ")
    password = getpass("Contraseña: ")
    return email, password

BASE_URL = "https://www.hife.es"

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

def login_hife(session, email, password):
    """Inicia sesión en HIFE."""
    print("\nIniciando sesión en HIFE...")
    try:
        # 1. GET a la página de login para obtener el token CSRF
        r = session.get(f"{BASE_URL}/en/client/login")
        if r.status_code != 200:
            print(f"Error al obtener página de login: {r.status_code}")
            return False
            
        # Extraer token CSRF
        soup = BeautifulSoup(r.text, 'html.parser')
        csrf_meta = soup.find('meta', {'name': 'csrf-token'})
        if not csrf_meta or not csrf_meta.get('content'):
            print("No se encontró token CSRF en la página de login")
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
            'Referer': f"https://www.hife.es/en/client/login",
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
        
        # 3. Realizar POST con credenciales
        login_data = {
            '_token': csrf_token,
            'email': email,
            'password': password,
            'redirect': ''
        }
        
        r = session.post(
            f"{BASE_URL}/en/client/login",
            data=login_data,
            allow_redirects=True
        )
        
        # 4. Verificar que estamos logueados correctamente
        if f"{BASE_URL}/en/my-private-area" not in r.url:
            print("Login fallido - URL después del login:", r.url)
            return False
            
        print("Login exitoso")
        return True
        
    except Exception as e:
        print(f"Error en el proceso de login: {e}")
        return False

def get_stations():
    print_header("Configuración de Estaciones")
    
    print("Estación de origen:")
    origin_name = input("Nombre (ej: VINARÒS): ").upper()
    
    print("\nEstación de destino:")
    dest_name = input("Nombre (ej: AMPOSTA): ").upper()
    
    return origin_name, dest_name

def get_station_ids(session, origin_name, dest_name):
    """Obtiene los IDs de las estaciones."""
    print("\nObteniendo IDs de estaciones...")
    
    try:
        # 1. Obtener lista inicial de estaciones
        print(f"Obteniendo lista de estaciones...")
        r = session.get(f"{BASE_URL}/en/free-bonus/register")
        if r.status_code != 200:
            print("Error al obtener página de registro")
            return None, None

        # Buscar el array de estaciones en el HTML
        soup = BeautifulSoup(r.text, 'html.parser')
        stops_data = soup.find('free-bonus-register', {':stops': True})
        if not stops_data:
            print("No se encontró la lista de estaciones")
            return None, None

        # Obtener y procesar el array de estaciones
        stops_str = stops_data[':stops']
        stops = json.loads(html.unescape(stops_str))

        # Buscar la estación de origen
        origin_station = None
        for station in stops:
            if station['name'].upper() == origin_name:
                origin_station = station
                print(f"Estación de origen encontrada: {station['name']} (código: {station['code']})")
                break

        if not origin_station:
            print(f"No se encontró la estación de origen: {origin_name}")
            print("\nEstaciones disponibles:")
            for station in stops:
                print(f"- {station['name']}")
            return None, None

        # 2. Obtener destinos válidos usando el código de la estación de origen
        print(f"\nBuscando destinos válidos desde {origin_name}...")
        r = session.get(f"{BASE_URL}/free-bonus/get-valid-destination-stops/{origin_station['code']}")
        if r.status_code != 200:
            print("Error al obtener destinos válidos")
            return None, None

        destinations = r.json()
        dest_station = None

        # Buscar la estación de destino
        for station in destinations:
            if station['name'].upper() == dest_name:
                dest_station = station
                print(f"Estación de destino encontrada: {station['name']} (código: {station['code']})")
                break

        if not dest_station:
            print(f"No se encontró la estación de destino: {dest_name}")
            print("\nDestinos válidos disponibles desde {origin_name}:")
            for station in destinations:
                print(f"- {station['name']}")
            return None, None

        # Devolver los IDs sin ceros iniciales
        return origin_station['code'].lstrip('0'), dest_station['code'].lstrip('0')

    except Exception as e:
        print(f"Error al obtener IDs de estaciones: {e}")
        return None, None

def get_schedule():
    print_header("Configuración de Horarios")
    
    schedules = {
        'outward': {'default': None},
        'return': {'monday': None, 'tuesday': None, 'wednesday': None, 'thursday': None, 'friday': None}
    }
    
    print("Horarios de IDA:")
    schedules['outward']['default'] = input("Hora por defecto (HH:MM): ")
    
    for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']:
        day_names = {
            'monday': 'lunes',
            'tuesday': 'martes',
            'wednesday': 'miércoles',
            'thursday': 'jueves',
            'friday': 'viernes'
        }
        custom = input(f"Hora específica para {day_names[day]} (Enter para usar default): ")
        if custom:
            schedules['outward'][day] = custom
    
    print("\nHorarios de VUELTA:")
    default_return = input("Hora por defecto para vuelta (HH:MM, Enter para configurar por día): ")
    if default_return:
        schedules['return']['default'] = default_return
    
    for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']:
        if schedules['return'][day] is None:  # Si no hay default o se necesita específico
            custom = input(f"Hora para {day_names[day]} (HH:MM): ")
            schedules['return'][day] = custom or schedules['return'].get('default', '')
    
    # Minutos de antelación para notificaciones
    print("\nConfiguración de notificaciones:")
    advance = input("Minutos de antelación para notificar (default: 75): ") or "75"
    schedules['notification_advance'] = advance
    
    return schedules

def get_trip_ids(session, origin_id, dest_id, schedules, origin_name, dest_name):
    """Obtiene los IDs de los viajes."""
    print_header("Obteniendo IDs de viajes")
    print("Este proceso puede tardar unos minutos...")
    
    trip_ids = {
        'outward': {},
        'return': {}
    }
    
    # Inicializar sesión
    r = session.get(f"{BASE_URL}/en/routes")
    if r.status_code == 200:
        soup = BeautifulSoup(r.text, 'html.parser')
        csrf_meta = soup.find('meta', {'name': 'csrf-token'})
        if csrf_meta and csrf_meta.get('content'):
            session.headers.update({
                'X-CSRF-TOKEN': csrf_meta['content'],
                'X-XSRF-TOKEN': session.cookies.get('XSRF-TOKEN', ''),
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
                'Connection': 'keep-alive',
                'Content-Type': 'application/json',
                'Origin': BASE_URL,
                'Referer': f"{BASE_URL}/en/routes",
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-origin',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            })
    
    # Probar hasta 2 días consecutivos
    for day_offset in range(2):
        search_date = datetime.now(pytz.timezone('Europe/Madrid')) + timedelta(days=1+day_offset)
        
        # Solo probar días laborables
        if search_date.strftime('%A').lower() in ['saturday', 'sunday']:
            continue
            
        print(f"\nProbando fecha: {search_date.strftime('%d/%m/%Y')}")
        
        date_str = search_date.strftime("%d/%m/%Y")
        date_str_hyphen = search_date.strftime("%d-%m-%Y")
        
        try:
            # Para cada dirección (ida/vuelta)
            for direction in ['outward', 'return']:
                print(f"\nBuscando viajes de {'ida' if direction == 'outward' else 'vuelta'}...")
                
                # Configurar origen/destino según dirección
                from_id = origin_id if direction == 'outward' else dest_id
                to_id = dest_id if direction == 'outward' else origin_id
                from_name = origin_name if direction == 'outward' else dest_name
                to_name = dest_name if direction == 'outward' else origin_name
                
                print(f"De: {from_name} ({from_id}) a {to_name} ({to_id})")

                # Construir URL de rutas
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
                    'filter_departure': date_str,
                    'filter_arrival': '',
                    'filter_adult': '1',
                    'filter_child': '0',
                    'filter_child_without_seat': '0',
                }
                
                rutas_url = f"{BASE_URL}/en/routes?" + "&".join([f"{k}={quote(str(v))}" for k, v in rutas_params.items()])
                
                rutas_headers = {
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                    'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
                    'Cache-Control': 'max-age=0',
                    'Connection': 'keep-alive',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'same-origin',
                    'Sec-Fetch-User': '?1',
                    'Upgrade-Insecure-Requests': '1',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36'
                }
                
                r = session.get(
                    rutas_url,
                    headers=rutas_headers,
                    cookies=session.cookies
                )
                print(f"GET /routes status: {r.status_code}")
                
                if r.status_code != 200:
                    print(f"Error al obtener página de rutas: {r.status_code}")
                    continue

                # Extraer CSRF token
                soup = BeautifulSoup(r.text, 'html.parser')
                csrf_meta = soup.find('meta', {'name': 'csrf-token'})
                if not csrf_meta:
                    print("No se encontró CSRF token en página de rutas")
                    continue

                csrf_token = csrf_meta['content']
                
                # Preparar datos para la petición de viajes
                boundary = f'----WebKitFormBoundary{secrets.token_hex(8)}'
                
                form_data = {
                    'date': date_str_hyphen,
                    'from': from_id,
                    'to': to_id,
                    'pmrsr': '0',
                    'locale': 'en',
                    'operation_type_id': '0',
                    'going_date': date_str,
                    'adults_num': '1',
                    'childs_num': '0',
                    'childs_without_seat_num': '0',
                    'enterprise_slug': ''
                }

                # Codificar los datos del formulario con el boundary correcto
                body, content_type = encode_multipart_formdata(form_data, boundary=boundary)

                headers = {
                    'Accept': 'application/json, text/plain, */*',
                    'Content-Type': content_type,
                    'Origin': BASE_URL,
                    'Referer': rutas_url,
                    'X-CSRF-TOKEN': csrf_token,
                    'X-XSRF-TOKEN': session.cookies.get('XSRF-TOKEN', ''),
                    'X-Requested-With': 'XMLHttpRequest'
                }

                print("Buscando IDs de viajes...")

                r = session.post(
                    f"{BASE_URL}/route/trips",
                    data=body,
                    headers=headers,
                    cookies=session.cookies
                )
                
                print(f"POST /route/trips status: {r.status_code}")
                    
                try:
                    response = r.json()
                    if response.get('error'):
                        print("Error en la respuesta:", response.get('message', 'Unknown error'))
                        continue
                        
                    # Si encontramos viajes, procesar y salir del bucle de días
                    if response.get('result'):
                        print(f"Viajes encontrados para {date_str}")
                        
                        # Procesar los viajes
                        for trip in response.get('result', []):
                            departure_time = trip.get('departure_time')
                            
                            # Extraer el ID del viaje (ahora es solo el ID numérico)
                            trip_id = str(trip.get('id'))
                            
                            print(f"- Viaje encontrado: {departure_time}, ID: {trip_id}")
                            
                            # Guardar ID según la hora
                            if direction == 'outward':
                                if departure_time == schedules['outward']['default']:
                                    trip_ids['outward']['default'] = trip_id
                                    print(f"  > Asignado como ida default")
                                
                                # Buscar coincidencias con horarios específicos
                                for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']:
                                    if day in schedules['outward'] and schedules['outward'][day] == departure_time:
                                        trip_ids['outward'][day] = trip_id
                                        print(f"  > Asignado como ida para {day}")
                            else:
                                if 'default' in schedules['return'] and departure_time == schedules['return']['default']:
                                    trip_ids['return']['default'] = trip_id
                                    print(f"  > Asignado como vuelta default")
                                
                                # Buscar coincidencias con horarios específicos
                                for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']:
                                    if day in schedules['return'] and schedules['return'][day] == departure_time:
                                        trip_ids['return'][day] = trip_id
                                        print(f"  > Asignado como vuelta para {day}")
                        
                        # Si encontramos todos los IDs necesarios, salir
                        found_all = True
                        
                        # Verificar IDs de ida
                        if schedules['outward']['default'] and 'default' not in trip_ids['outward']:
                            print(f"No se encontró ID para ida default ({schedules['outward']['default']})")
                            found_all = False
                        
                        # Verificar IDs de vuelta para cada día
                        for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']:
                            if schedules['return'][day] and day not in trip_ids['return'] and 'default' not in trip_ids['return']:
                                print(f"No se encontró ID para vuelta de {day} ({schedules['return'][day]})")
                                found_all = False
                        
                        if found_all:
                            print("Se encontraron todos los IDs necesarios")
                            return trip_ids
                            
                except json.JSONDecodeError:
                    print("Error al decodificar respuesta JSON")
                    continue
                    
        except Exception as e:
            print(f"Error al obtener IDs de viajes: {e}")
            continue
            
    # Si llegamos aquí es que no encontramos todos los IDs necesarios
    print("\nAdvertencia: No se encontraron todos los IDs de viajes necesarios")
    
    # Permitir introducción manual de IDs no encontrados
    print_header("Introducción manual de IDs")
    print("Para los horarios que no se encontraron automáticamente, puedes introducir los IDs manualmente.")
    print("Si no conoces el ID, deja en blanco y luego deberás editarlo en el archivo .env")
    
    # IDs de ida
    if schedules['outward']['default'] and 'default' not in trip_ids['outward']:
        trip_ids['outward']['default'] = input(f"ID para ida default ({schedules['outward']['default']}): ")
    
    # IDs específicos de ida por día
    for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']:
        if day in schedules['outward'] and schedules['outward'][day] and day not in trip_ids['outward']:
            trip_ids['outward'][day] = input(f"ID para ida de {day} ({schedules['outward'][day]}): ")
    
    # ID de vuelta default
    if 'default' in schedules['return'] and schedules['return']['default'] and 'default' not in trip_ids['return']:
        trip_ids['return']['default'] = input(f"ID para vuelta default ({schedules['return']['default']}): ")
    
    # IDs específicos de vuelta por día
    for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']:
        if schedules['return'][day] and day not in trip_ids['return'] and 'default' not in trip_ids['return']:
            trip_ids['return'][day] = input(f"ID para vuelta de {day} ({schedules['return'][day]}): ")
    
    return trip_ids

def get_bonus_id(session):
    """Obtiene el ID del bono gratuito."""
    print("\nObteniendo ID del bono gratuito...")
    
    try:
        r = session.get(f"{BASE_URL}/en/free-bonus-movements")
        if r.status_code != 200:
            print("Error al acceder a la página de bonos")
            return None
            
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # Buscar la tabla principal
        table = soup.find('table', class_='table table-bordered')
        if not table:
            print("No se encontró la tabla de bonos")
            return None
            
        # Buscar todas las filas excepto el encabezado
        rows = table.find_all('tr')
        if not rows:
            print("No se encontraron filas en la tabla")
            return None
            
        bonuses = []
        for row in rows:
            # Saltar la fila del título
            if 'tableTitleRow' in row.get('class', []):
                continue
                
            try:
                # Buscar la columna del ID (segunda columna)
                cols = row.find_all('td')
                if len(cols) < 7:
                    continue
                    
                id_col = cols[1]
                if not id_col:
                    continue
                    
                # Obtener el ID (está en el primer texto antes del <br>)
                bonus_id = id_col.get_text().strip().split('\n')[0]
                
                # Buscar la columna de estado (séptima columna)
                status_col = cols[6]
                if not status_col:
                    continue
                    
                # Buscar el div con el texto "Active" o "Activo"
                status_text = status_col.get_text().strip()
                if "Active" in status_text or "Activo" in status_text:
                    # Quitar ceros iniciales
                    bonus_id = bonus_id.lstrip('0')
                    print(f"Bono activo encontrado: {bonus_id}")
                    bonuses.append(bonus_id)
                    
            except Exception as e:
                print(f"Error procesando fila: {e}")
                continue
        
        if bonuses:
            if len(bonuses) > 1:
                print("\nSe encontraron varios bonos activos:")
                for i, bonus_id in enumerate(bonuses):
                    print(f"{i+1}. {bonus_id}")
                
                choice = input("\nSelecciona el número del bono que quieres usar: ")
                try:
                    index = int(choice) - 1
                    if 0 <= index < len(bonuses):
                        return bonuses[index]
                    else:
                        print("Selección inválida")
                        return None
                except ValueError:
                    print("Selección inválida")
                    return None
            else:
                return bonuses[0]
        
        print("No se encontró ningún bono activo")
        manual_bonus = input("Introduce manualmente el ID del bono (o deja en blanco para configurarlo después): ")
        return manual_bonus if manual_bonus else None
        
    except Exception as e:
        print(f"Error al obtener ID del bono: {e}")
        manual_bonus = input("Introduce manualmente el ID del bono (o deja en blanco para configurarlo después): ")
        return manual_bonus if manual_bonus else None

def generate_env_file(config):
    """Genera el archivo .env con la configuración obtenida."""
    # Mapeo de días de la semana para variables de entorno
    day_map = {
        'monday': 'MONDAY',
        'tuesday': 'TUESDAY',
        'wednesday': 'WEDNESDAY',
        'thursday': 'THURSDAY',
        'friday': 'FRIDAY'
    }
    
    env_content = f"""# Token de acceso del bot de Telegram
TELEGRAM_TOKEN={config['telegram_token']}

# ID del usuario autorizado en Telegram
TELEGRAM_USER_ID={config['telegram_user_id']}

# Credenciales de inicio de sesión en HIFE
HIFE_EMAIL={config['hife_email']}
HIFE_PASSWORD={config['hife_password']}

# Estación de origen
ORIGIN_ID={config['origin_id']}
ORIGIN_NAME={config['origin_name']}

# Estación de destino
DESTINATION_ID={config['destination_id']}
DESTINATION_NAME={config['destination_name']}

# ====== HORARIOS DE IDA ======
"""
    
    # Añadir hora por defecto para ida
    if 'outward' in config['schedules'] and 'default' in config['schedules']['outward']:
        env_content += f"OUTWARD_TIME_DEFAULT={config['schedules']['outward']['default']}\n"
    else:
        env_content += "OUTWARD_TIME_DEFAULT=\n"
        
    # Añadir horas específicas por día para ida
    for day in day_map:
        if 'outward' in config['schedules'] and day in config['schedules']['outward']:
            env_content += f"OUTWARD_TIME_{day_map[day]}={config['schedules']['outward'][day]}\n"
        else:
            env_content += f"OUTWARD_TIME_{day_map[day]}=\n"
    
    env_content += "\n# ====== HORARIOS DE VUELTA ======\n"
    
    # Añadir hora por defecto para vuelta
    if 'return' in config['schedules'] and 'default' in config['schedules']['return']:
        env_content += f"RETURN_TIME_DEFAULT={config['schedules']['return']['default']}\n"
    else:
        env_content += "RETURN_TIME_DEFAULT=\n"
        
    # Añadir horas específicas por día para vuelta
    for day in day_map:
        if 'return' in config['schedules'] and day in config['schedules']['return']:
            env_content += f"RETURN_TIME_{day_map[day]}={config['schedules']['return'][day]}\n"
        else:
            env_content += f"RETURN_TIME_{day_map[day]}=\n"
    
    # Añadir IDs de trayectos
    if 'trip_ids' in config and config['trip_ids']:
        env_content += "\n# ====== IDs DE TRAYECTOS ======\n"
        
        # IDs para ida
        if 'outward' in config['trip_ids']:
            if 'default' in config['trip_ids']['outward']:
                env_content += f"OUTWARD_TRIP_ID_DEFAULT={config['trip_ids']['outward']['default']}\n"
                
            for day in day_map:
                if day in config['trip_ids']['outward']:
                    env_content += f"OUTWARD_TRIP_ID_{day_map[day]}={config['trip_ids']['outward'][day]}\n"
        
        # IDs para vuelta
        if 'return' in config['trip_ids']:
            if 'default' in config['trip_ids']['return']:
                env_content += f"RETURN_TRIP_ID_DEFAULT={config['trip_ids']['return']['default']}\n"
                
            for day in day_map:
                if day in config['trip_ids']['return']:
                    env_content += f"RETURN_TRIP_ID_{day_map[day]}={config['trip_ids']['return'][day]}\n"
    
    # Añadir minutos de antelación para notificaciones
    env_content += "\n# Minutos de antelación para notificar antes del viaje\n"
    env_content += f"NOTIFICATION_ADVANCE={config['schedules'].get('notification_advance', '75')}\n"
    
    # Añadir ID de bono
    env_content += "\n# ID numérico del bono de transporte a utilizar\n"
    env_content += f"BONUS_ID={config['bonus_id']}\n"
    
    with open('.env', 'w') as f:
        f.write(env_content)
    
    print("Archivo .env generado correctamente")
    print("\nSugerencia: si necesitas ajustar algún valor, edita directamente el archivo .env")

def main():
    print_header("Asistente de configuración de HIFE Bot")
    print("Bienvenido al asistente de configuración. Este programa te ayudará a configurar el bot para comprar billetes en HIFE.es automáticamente.")
    
    print("\n⚠️ IMPORTANTE: Este bot está diseñado para funcionar EXCLUSIVAMENTE con cuentas de HIFE configuradas en inglés.")
    print("Por favor, asegúrate de que tu cuenta de HIFE.es está configurada en inglés antes de continuar.")
    print("Para cambiar el idioma de tu cuenta HIFE, inicia sesión y selecciona 'English' en el selector de idioma.")
    
    config = {}
    
    # 1. Obtener información de Telegram
    config['telegram_token'], config['telegram_user_id'] = get_telegram_info()
    
    # 2. Obtener credenciales de HIFE
    config['hife_email'], config['hife_password'] = get_hife_credentials()
    
    # 3. Iniciar sesión y mantener la sesión para todas las peticiones
    session = requests.Session()
    session.headers.update(HEADERS)  # Establecer headers base
    
    if not login_hife(session, config['hife_email'], config['hife_password']):
        print("Error al iniciar sesión en HIFE")
        return
    
    # 4. Obtener información de estaciones
    origin_name, dest_name = get_stations()
    
    # 5. Obtener IDs de estaciones usando la misma sesión
    origin_id, dest_id = get_station_ids(session, origin_name, dest_name)
    if not origin_id or not dest_id:
        print("Error al obtener IDs de estaciones")
        return
        
    config['origin_id'] = origin_id
    config['destination_id'] = dest_id
    config['origin_name'] = origin_name
    config['destination_name'] = dest_name
    
    # 6. Configurar horarios
    config['schedules'] = get_schedule()
    
    # 7. Obtener IDs de viajes usando la misma sesión
    config['trip_ids'] = get_trip_ids(session, origin_id, dest_id, config['schedules'], origin_name, dest_name)
    if not config['trip_ids']:
        print("Error al obtener IDs de viajes")
        return
    
    # 8. Obtener ID del bono usando la misma sesión
    config['bonus_id'] = get_bonus_id(session)
    if not config['bonus_id']:
        print("Advertencia: No se pudo obtener ID del bono. Tendrás que configurarlo manualmente en el archivo .env")
        config['bonus_id'] = ""
    
    # 9. Generar archivo .env
    generate_env_file(config)
    
    print("\n¡Configuración completada!")
    print("\nPara ejecutar el bot, usa: python main.py")
    print("\nEl bot enviará notificaciones a través de Telegram para preguntar si quieres comprar billetes.")

if __name__ == "__main__":
    main() 