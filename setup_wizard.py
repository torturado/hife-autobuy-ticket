import os
import requests
from getpass import getpass
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
	print("\n" + "=" * 50)
	print(text)
	print("=" * 50 + "\n")


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
	user_id = input(
	    "Introduce tu ID de usuario de Telegram (puedes obtenerlo hablando con @userinfobot): "
	)

	return token, user_id


def get_jwt_token():
	"""Obtiene el token JWT automáticamente usando las credenciales de HIFE"""
	print_header("Autenticación en HIFE")
	print(
	    "Introduce tus credenciales de HIFE para obtener el token de acceso automáticamente."
	)

	email = input("Email de HIFE: ").strip()
	password = getpass("Contraseña de HIFE: ")

	print("\nObteniendo token de acceso...")

	headers = {
	    'accept':
	    'application/json; charset=utf-8',
	    'app-version':
	    '2.0.8',
	    'content-type':
	    'application/json; charset=utf-8',
	    'user-agent':
	    'Dalvik/2.1.0 (Linux; U; Android 12; SM-S916U Build/9643478.0)'
	}

	data = {
	    'client_id': 2,
	    'client_secret': 'SBZD2UnizBSnrZfPReiipqwfGPEHFpPOdAU4uiYN',
	    'grant_type': 'password',
	    'username': email,
	    'password': password
	}

	try:
		response = requests.post('https://middleware.hife.es/oauth/token',
		                         headers=headers,
		                         json=data)
		response.raise_for_status()
		result = response.json()

		access_token = result.get('access_token')
		if not access_token:
			print("❌ Error: No se recibió el token de acceso")
			return None

		refresh_token = result.get('refresh_token')
		expires_in = result.get('expires_in', 0)
		days = expires_in // 86400 if expires_in > 0 else 0

		print(f"✅ Token obtenido correctamente (expira en {days} días)")

		return f'Bearer {access_token}'

	except requests.exceptions.HTTPError as e:
		if e.response.status_code == 401:
			print("❌ Error: Credenciales incorrectas")
		else:
			print(f"❌ Error HTTP {e.response.status_code}")
			try:
				error_data = e.response.json()
				print(
				    f"   Mensaje: {error_data.get('message', 'Error desconocido')}"
				)
			except:
				pass
		return None
	except Exception as e:
		print(f"❌ Error al obtener token: {e}")
		return None


def get_stops_from_api(auth_token):
	"""Obtiene todas las paradas de la API de HIFE"""
	headers = {
	    'accept':
	    'application/json; charset=utf-8',
	    'app-version':
	    '2.0.8',
	    'authorization':
	    auth_token,
	    'content-type':
	    'application/json; charset=utf-8',
	    'user-agent':
	    'Dalvik/2.1.0 (Linux; U; Android 12; SM-S916U Build/9643478.0)'
	}

	try:
		response = requests.get('https://middleware.hife.es/api/stops',
		                        headers=headers)
		response.raise_for_status()
		return response.json()
	except Exception as e:
		print(f"Error al obtener paradas de la API: {e}")
		return None


def search_stop(stops_data, search_term):
	"""Busca una parada por nombre en los datos de la API"""
	if not stops_data:
		return None

	search_term = search_term.upper().strip()
	matches = []

	for city_data in stops_data:
		for stop in city_data.get('stops', []):
			stop_name = stop.get('name', '').upper()

			# Buscar en el nombre principal
			if search_term in stop_name or stop_name in search_term:
				stop_id = str(stop.get('id', ''))
				stop_code = None

				# Obtener el stop_code de los synonyms (todos tienen el mismo)
				if stop.get('synonyms') and len(stop.get('synonyms', [])) > 0:
					stop_code = stop['synonyms'][0].get('stop_code', '')

				matches.append({
				    'id': stop_id,
				    'stop_code': stop_code or stop_id.zfill(4),
				    'name': stop.get('name', ''),
				    'city': city_data.get('city', ''),
				    'address': stop.get('adress', '')
				})

	return matches


def select_stop(stops_data, stop_type="origen"):
	"""Permite al usuario buscar y seleccionar una parada"""
	print_header(f"Configuración de Estación de {stop_type.capitalize()}")

	search_term = input(f"Buscar estación de {stop_type} (nombre): ").strip()
	if not search_term:
		print("Búsqueda vacía")
		return None

	matches = search_stop(stops_data, search_term)

	if not matches:
		print(
		    f"No se encontraron estaciones que coincidan con '{search_term}'")
		return None

	if len(matches) == 1:
		selected = matches[0]
		print(
		    f"\n✓ Estación encontrada: {selected['name']} ({selected['city']})"
		)
		print(f"  ID: {selected['id']}, Código: {selected['stop_code']}")
		return selected

	print(f"\nSe encontraron {len(matches)} estaciones:")
	for i, match in enumerate(matches, 1):
		print(
		    f"{i}. {match['name']} ({match['city']}) - ID: {match['id']}, Código: {match['stop_code']}"
		)

	while True:
		try:
			choice = input(
			    f"\nSelecciona el número de la estación (1-{len(matches)}): "
			).strip()
			index = int(choice) - 1
			if 0 <= index < len(matches):
				return matches[index]
			else:
				print(
				    f"Por favor, introduce un número entre 1 y {len(matches)}")
		except ValueError:
			print("Por favor, introduce un número válido")


def get_schedule():
	print_header("Configuración de Horarios")

	schedules = {
	    'outward': {
	        'default': None
	    },
	    'return': {
	        'monday': None,
	        'tuesday': None,
	        'wednesday': None,
	        'thursday': None,
	        'friday': None
	    }
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
		custom = input(
		    f"Hora específica para {day_names[day]} (Enter para usar default): "
		)
		if custom:
			schedules['outward'][day] = custom

	print("\nHorarios de VUELTA:")
	default_return = input(
	    "Hora por defecto para vuelta (HH:MM, Enter para configurar por día): "
	).strip()
	if default_return:
		schedules['return']['default'] = default_return

	for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']:
		if schedules['return'][day] is None:
			if schedules['return'].get('default'):
				custom = input(
				    f"Hora para {day_names[day]} (HH:MM, Enter para usar default {schedules['return']['default']}): "
				).strip()
				if custom:
					schedules['return'][day] = custom
				# Si está vacío, no guardar nada - usará el default
			else:
				# Si no hay default, requerir un valor
				custom = ""
				while not custom:
					custom = input(
					    f"Hora para {day_names[day]} (HH:MM, requerido): "
					).strip()
				schedules['return'][day] = custom

	# Minutos de antelación para notificaciones
	print("\nConfiguración de notificaciones:")
	advance = input(
	    "Minutos de antelación para notificar (default: 75): ") or "75"
	schedules['notification_advance'] = advance

	return schedules


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

	env_content = f"""# ============================================
# CONFIGURACIÓN DE TELEGRAM
# ============================================
# Token de acceso del bot de Telegram
TELEGRAM_TOKEN={config['telegram_token']}

# ID del usuario autorizado en Telegram
TELEGRAM_USER_ID={config['telegram_user_id']}

# ============================================
# CONFIGURACIÓN DE HIFE API
# ============================================
# URL base de la API de HIFE (normalmente no cambiar)
HIFE_API_URL=https://middleware.hife.es/api

# Token JWT de autenticación (obtener de los logs de la app móvil)
HIFE_AUTH_TOKEN={config.get('hife_auth_token', '')}

# Client ID de HIFE (normalmente 33798)
HIFE_CLIENT_ID=33798

# Versión de la app (normalmente 2.0.8)
HIFE_APP_VERSION=2.0.8

# ============================================
# CONFIGURACIÓN DE ESTACIONES
# ============================================
# ID numérico de la estación de origen (sin ceros iniciales)
ORIGIN_ID={config['origin_id']}

# Código de parada de origen (con ceros iniciales, ej: 0012)
ORIGIN_STOP_CODE={config.get('origin_stop_code', config['origin_id'].zfill(4))}

# Nombre de la estación de origen
ORIGIN_NAME={config['origin_name']}

# ID numérico de la estación de destino (sin ceros iniciales)
DESTINATION_ID={config['destination_id']}

# Código de parada de destino (con ceros iniciales, ej: 0007)
DESTINATION_STOP_CODE={config.get('destination_stop_code', config['destination_id'].zfill(4))}

# Nombre de la estación de destino
DESTINATION_NAME={config['destination_name']}

# ====== HORARIOS DE IDA ======
"""

	# Añadir hora por defecto para ida
	if 'outward' in config['schedules'] and 'default' in config['schedules'][
	    'outward']:
		env_content += f"OUTWARD_TIME_DEFAULT={config['schedules']['outward']['default']}\n"
	else:
		env_content += "OUTWARD_TIME_DEFAULT=\n"

	# Añadir horas específicas por día para ida
	for day in day_map:
		if 'outward' in config['schedules'] and day in config['schedules'][
		    'outward']:
			env_content += f"OUTWARD_TIME_{day_map[day]}={config['schedules']['outward'][day]}\n"
		else:
			env_content += f"OUTWARD_TIME_{day_map[day]}=\n"

	env_content += "\n# ====== HORARIOS DE VUELTA ======\n"

	# Añadir hora por defecto para vuelta
	if 'return' in config['schedules'] and 'default' in config['schedules'][
	    'return']:
		env_content += f"RETURN_TIME_DEFAULT={config['schedules']['return']['default']}\n"
	else:
		env_content += "RETURN_TIME_DEFAULT=\n"

	# Añadir horas específicas por día para vuelta
	for day in day_map:
		if 'return' in config['schedules'] and day in config['schedules'][
		    'return']:
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

	# Añadir ID de bono
	env_content += "\n# ============================================\n"
	env_content += "# CONFIGURACIÓN DE BONO\n"
	env_content += "# ============================================\n"
	env_content += "# ID del bono a utilizar (19 = MITMA Joven, pero puede variar)\n"
	env_content += f"BONUS_ID={config.get('bonus_id', '19')}\n"

	# Añadir minutos de antelación para notificaciones
	env_content += "\n# ============================================\n"
	env_content += "# CONFIGURACIÓN DE NOTIFICACIONES\n"
	env_content += "# ============================================\n"
	env_content += "# Minutos de antelación para notificar antes del viaje (default: 120 = 2 horas)\n"
	env_content += f"NOTIFICATION_ADVANCE_MINUTES={config['schedules'].get('notification_advance', '120')}\n"

	# Intervalo de revisión
	env_content += "\n# Intervalo en minutos para revisar horarios (default: 10)\n"
	env_content += "CHECK_INTERVAL_MINUTES=10\n"

	with open('.env', 'w', encoding='utf-8') as f:
		f.write(env_content)

	print("Archivo .env generado correctamente")
	print(
	    "\nSugerencia: si necesitas ajustar algún valor, edita directamente el archivo .env"
	)


def main():
	print_header("Asistente de configuración de HIFE Bot")
	print(
	    "Bienvenido al asistente de configuración. Este programa te ayudará a configurar el bot para comprar billetes en HIFE.es automáticamente."
	)

	config = {}

	# 1. Obtener información de Telegram
	config['telegram_token'], config['telegram_user_id'] = get_telegram_info()

	# 2. Obtener token JWT de HIFE
	config['hife_auth_token'] = get_jwt_token()
	if not config['hife_auth_token']:
		print(
		    "\n❌ No se pudo obtener el token de acceso. El proceso se detiene."
		)
		return

	# 3. Obtener paradas de la API
	print("\nObteniendo lista de paradas de la API de HIFE...")
	stops_data = get_stops_from_api(config['hife_auth_token'])
	if not stops_data:
		print("⚠️ No se pudieron obtener las paradas de la API.")
		print("Puedes introducir la información manualmente:")
		origin_name = input("Nombre de la estación de origen: ").strip()
		origin_id = input(
		    "ID de la estación de origen (sin ceros iniciales): ").strip()
		origin_stop_code = input(
		    f"Código de parada de origen (default: {origin_id.zfill(4) if origin_id else '0012'}): "
		).strip()

		dest_name = input("\nNombre de la estación de destino: ").strip()
		dest_id = input(
		    "ID de la estación de destino (sin ceros iniciales): ").strip()
		dest_stop_code = input(
		    f"Código de parada de destino (default: {dest_id.zfill(4) if dest_id else '0007'}): "
		).strip()

		config['origin_id'] = origin_id
		config[
		    'origin_stop_code'] = origin_stop_code if origin_stop_code else (
		        origin_id.zfill(4) if origin_id else '0012')
		config['origin_name'] = origin_name
		config['destination_id'] = dest_id
		config[
		    'destination_stop_code'] = dest_stop_code if dest_stop_code else (
		        dest_id.zfill(4) if dest_id else '0007')
		config['destination_name'] = dest_name
	else:
		# Seleccionar estación de origen
		origin_stop = select_stop(stops_data, "origen")
		if not origin_stop:
			print("Error: No se seleccionó una estación de origen")
			return

		config['origin_id'] = origin_stop['id']
		config['origin_stop_code'] = origin_stop['stop_code']
		config['origin_name'] = origin_stop['name']

		# Seleccionar estación de destino
		dest_stop = select_stop(stops_data, "destino")
		if not dest_stop:
			print("Error: No se seleccionó una estación de destino")
			return

		config['destination_id'] = dest_stop['id']
		config['destination_stop_code'] = dest_stop['stop_code']
		config['destination_name'] = dest_stop['name']

	# 4. Configurar horarios
	config['schedules'] = get_schedule()

	# 5. Configurar bono
	print_header("Configuración de Bono")
	print("ID del bono a utilizar (default: 19 para MITMA Joven)")
	bonus_id = input("ID del bono: ").strip()
	config['bonus_id'] = bonus_id if bonus_id else "19"

	# Los trip_ids no se obtienen automáticamente, el usuario puede configurarlos después si es necesario
	config['trip_ids'] = {}

	# 6. Generar archivo .env
	generate_env_file(config)

	print("\n" + "=" * 50)
	print("✅ ¡Configuración completada!")
	print("=" * 50)
	print("\n📝 Se ha generado el archivo .env con tu configuración.")
	print("\n🚀 Para ejecutar el bot, usa:")
	print("   python main.py")
	print("\n📱 El bot enviará notificaciones a través de Telegram")
	print("   para preguntarte si quieres comprar billetes.")
	print("\n💡 Si necesitas ajustar algún valor, edita el archivo .env")
	print("=" * 50)


if __name__ == "__main__":
	main()
