import os
import re
import requests
from getpass import getpass
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.text import Text
import questionary
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

console = Console()


def print_header(text, icon="📋"):
	"""
    Imprime un encabezado formateado para las secciones del asistente usando Rich.

    Args:
        text (str): Texto a mostrar como encabezado
        icon (str): Icono a mostrar junto al título
    """
	console.print()
	console.print(
	    Panel(f"[cyan]{text}[/cyan]",
	          border_style="cyan",
	          title=f"{icon} {text}",
	          title_align="left"))


def validate_time_format(time_str):
	"""Valida que el formato de hora sea HH:MM"""
	if not time_str:
		return True  # Permitir vacío para valores opcionales
	pattern = r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$'
	return bool(re.match(pattern, time_str))


def validate_email(email_str):
	"""Valida formato básico de email"""
	if not email_str:
		return False
	pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
	return bool(re.match(pattern, email_str))


def get_telegram_info():
	"""
    Solicita al usuario información sobre su bot de Telegram usando Questionary.

    Returns:
        tuple: (token del bot, ID de usuario)
    """
	print_header("Configuración de Telegram", "📱")

	info_text = ("[yellow]Para obtener el token de tu bot:[/yellow]\n"
	             "1. Habla con [cyan]@BotFather[/cyan] en Telegram\n"
	             "2. Usa el comando [cyan]/newbot[/cyan]\n"
	             "3. Sigue las instrucciones y copia el token que te da")
	console.print(Panel(info_text, border_style="yellow"))

	token = questionary.text(
	    "Introduce el token de tu bot:",
	    validate=lambda text: True
	    if text.strip() else "El token no puede estar vacío").ask()

	user_id = questionary.text(
	    "Introduce tu ID de usuario de Telegram (puedes obtenerlo hablando con @userinfobot):",
	    validate=lambda text: True
	    if text.strip() else "El ID de usuario no puede estar vacío").ask()

	return token, user_id


def get_jwt_token():
	"""Obtiene el token JWT automáticamente usando las credenciales de HIFE"""
	print_header("Autenticación en HIFE", "🔐")

	info_text = (
	    "[yellow]Introduce tus credenciales de HIFE para obtener el token de acceso automáticamente.[/yellow]"
	)
	console.print(Panel(info_text, border_style="yellow"))

	email = questionary.text(
	    "Email de HIFE:",
	    validate=lambda text: validate_email(text)
	    if text.strip() else "El email no puede estar vacío").ask()

	password = questionary.password("Contraseña de HIFE:").ask()

	# Get client_secret from environment variable or prompt user
	client_secret = os.getenv('HIFE_CLIENT_SECRET')
	if not client_secret:
		console.print(
		    Panel(
		        "[yellow]⚠️ HIFE_CLIENT_SECRET no encontrado en variables de entorno.[/yellow]\n"
		        "Por favor, introduce el client_secret de HIFE.",
		        border_style="yellow",
		        title="⚠️ Advertencia"))
		client_secret = questionary.password("Client Secret de HIFE:").ask()
		if not client_secret:
			console.print("[red]❌ Error: Client Secret es requerido[/red]")
			return None

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
	    'client_secret': client_secret,
	    'grant_type': 'password',
	    'username': email,
	    'password': password
	}

	with console.status("[cyan]Obteniendo token de acceso...", spinner="dots"):
		try:
			response = requests.post('https://middleware.hife.es/oauth/token',
			                         headers=headers,
			                         json=data,
			                         timeout=10)
			response.raise_for_status()
			result = response.json()

			access_token = result.get('access_token')
			if not access_token:
				console.print(
				    "[red]❌ Error: No se recibió el token de acceso[/red]")
				return None

			refresh_token = result.get('refresh_token')
			expires_in = result.get('expires_in', 0)
			days = expires_in // 86400 if expires_in > 0 else 0

			console.print(
			    f"[green]✅ Token obtenido correctamente (expira en {days} días)[/green]"
			)

			return f'Bearer {access_token}'

		except requests.exceptions.Timeout:
			error_panel = Panel(
			    "[red]Error: Timeout al conectar con el servidor de HIFE[/red]\n"
			    "Por favor, verifica tu conexión a internet e intenta de nuevo.",
			    title="[red]❌ Error de Timeout[/red]",
			    border_style="red")
			console.print(error_panel)
			return None
		except requests.exceptions.RequestException as e:
			error_panel = Panel(
			    f"[red]Error de red al obtener token:[/red]\n{str(e)}",
			    title="[red]❌ Error de Red[/red]",
			    border_style="red")
			console.print(error_panel)
			return None
		except requests.exceptions.HTTPError as e:
			if e.response.status_code == 401:
				console.print("[red]❌ Error: Credenciales incorrectas[/red]")
			else:
				error_panel = Panel(
				    f"[red]Error HTTP {e.response.status_code}[/red]\n"
				    f"Mensaje: {e.response.text[:200] if hasattr(e.response, 'text') else 'Error desconocido'}",
				    title="[red]❌ Error[/red]",
				    border_style="red")
				console.print(error_panel)
			return None
		except Exception as e:
			error_panel = Panel(
			    f"[red]Error al obtener token:[/red]\n{str(e)}",
			    title="[red]❌ Error[/red]",
			    border_style="red")
			console.print(error_panel)
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

	with console.status(
	    "[cyan]Obteniendo lista de paradas de la API de HIFE...",
	    spinner="dots"):
		try:
			response = requests.get('https://middleware.hife.es/api/stops',
			                        headers=headers,
			                        timeout=10)
			response.raise_for_status()
			try:
				return response.json()
			except ValueError as e:
				error_panel = Panel(
				    f"[red]Error al decodificar respuesta JSON:[/red]\n{str(e)}\n"
				    f"Status code: {response.status_code}",
				    title="[red]❌ Error de Decodificación[/red]",
				    border_style="red")
				console.print(error_panel)
				return None
		except requests.exceptions.RequestException as e:
			error_panel = Panel(
			    f"[red]Error de red/HTTP al obtener paradas:[/red]\n{str(e)}",
			    title="[red]❌ Error de Red[/red]",
			    border_style="red")
			console.print(error_panel)
			return None
		except Exception as e:
			error_panel = Panel(
			    f"[red]Error inesperado al obtener paradas:[/red]\n{str(e)}",
			    title="[red]❌ Error[/red]",
			    border_style="red")
			console.print(error_panel)
			return None


def get_available_bonuses(auth_token):
	"""Obtiene los bonos disponibles y activos de la API de HIFE"""
	headers = {
	    'accept': 'application/json; charset=utf-8',
	    'app-version': '2.0.8',
	    'authorization': auth_token,
	    'content-type': 'application/json; charset=utf-8',
	    'user-agent':
	    'Dalvik/2.1.0 (Linux; U; Android 12; SM-S916U Build/9643478.0)',
	    'hife-locale': 'es'
	}

	with console.status(
	    "[cyan]Obteniendo bonos disponibles de la API de HIFE...",
	    spinner="dots"):
		try:
			response = requests.get('https://middleware.hife.es/api/bonus',
			                        headers=headers,
			                        timeout=10)
			response.raise_for_status()
			data = response.json()
			# Extraer arrays de bonos disponibles y activos
			available_bonuses = data.get('availableBonuses', [])
			bonus_items = data.get('bonusItems', [])

			# Identificar el bono activo (primer item de bonusItems)
			active_bonus = None
			if bonus_items and len(bonus_items) > 0:
				first_item = bonus_items[0]
				active_bonus = {
				    'bonus_item_id':
				    first_item.get('id'),
				    'bonus_type_id':
				    first_item.get('bonus_type_id'),
				    'expired':
				    first_item.get('expired', False),
				    'current_funds_amount':
				    first_item.get('current_funds_amount', 0),
				    'initial_funds_amount':
				    first_item.get('initial_funds_amount', 0),
				    'bonus_name':
				    first_item.get('bonus', {}).get('current_language',
				                                    {}).get('name', '')
				}

			return {'available': available_bonuses, 'active': active_bonus}
		except requests.exceptions.Timeout:
			error_panel = Panel(
			    "[red]Error: Timeout al conectar con el servidor de HIFE[/red]\n"
			    "Por favor, verifica tu conexión a internet e intenta de nuevo.",
			    title="[red]❌ Error de Timeout[/red]",
			    border_style="red")
			console.print(error_panel)
			return None
		except requests.exceptions.RequestException as e:
			error_panel = Panel(
			    f"[red]Error de red/HTTP al obtener bonos:[/red]\n{str(e)}",
			    title="[red]❌ Error de Red[/red]",
			    border_style="red")
			console.print(error_panel)
			return None
		except Exception as e:
			error_panel = Panel(
			    f"[red]Error inesperado al obtener bonos:[/red]\n{str(e)}",
			    title="[red]❌ Error[/red]",
			    border_style="red")
			console.print(error_panel)
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
	"""Permite al usuario buscar y seleccionar una parada usando Questionary"""
	print_header(f"Configuración de Estación de {stop_type.capitalize()}", "🚉")

	search_term = questionary.text(
	    f"Buscar estación de {stop_type} (nombre):",
	    validate=lambda text: True
	    if text.strip() else "La búsqueda no puede estar vacía").ask()

	if not search_term:
		console.print("[yellow]⚠️ Búsqueda vacía[/yellow]")
		return None

	with console.status(
	    f"[cyan]Buscando estaciones que coincidan con '{search_term}'...",
	    spinner="dots"):
		matches = search_stop(stops_data, search_term)

	if not matches:
		console.print(
		    Panel(
		        f"[yellow]No se encontraron estaciones que coincidan con '{search_term}'[/yellow]",
		        border_style="yellow",
		        title="⚠️ Sin resultados"))
		return None

	if len(matches) == 1:
		selected = matches[0]
		console.print(
		    Panel(
		        f"[green]✓ Estación encontrada:[/green] [cyan]{selected['name']}[/cyan] ([yellow]{selected['city']}[/yellow])\n"
		        f"ID: [magenta]{selected['id']}[/magenta] | Código: [magenta]{selected['stop_code']}[/magenta]",
		        border_style="green",
		        title="✅ Estación encontrada"))
		return selected

	# Crear tabla para mostrar las estaciones
	table = Table(title=f"Estaciones encontradas ({len(matches)})",
	              show_header=True,
	              header_style="cyan")
	table.add_column("#", style="dim", width=3)
	table.add_column("Nombre", style="cyan")
	table.add_column("Ciudad", style="yellow")
	table.add_column("ID", style="magenta")
	table.add_column("Código", style="magenta")

	for i, match in enumerate(matches, 1):
		table.add_row(str(i), match['name'], match['city'], match['id'],
		              match['stop_code'])

	console.print(table)

	# Usar questionary para selección
	choices = [
	    f"{match['name']} ({match['city']}) - ID: {match['id']}, Código: {match['stop_code']}"
	    for match in matches
	]

	selected_text = questionary.select(
	    f"Selecciona la estación de {stop_type}:", choices=choices).ask()

	# Extraer el índice de la selección
	selected_index = choices.index(selected_text)
	return matches[selected_index]


def get_schedule():
	print_header("Configuración de Horarios", "⏰")

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

	# Define day_names at function scope so it's available to all loops
	day_names = {
	    'monday': 'lunes',
	    'tuesday': 'martes',
	    'wednesday': 'miércoles',
	    'thursday': 'jueves',
	    'friday': 'viernes'
	}

	console.print(Panel("[cyan]Horarios de IDA[/cyan]", border_style="cyan"))
	schedules['outward']['default'] = questionary.text(
	    "Hora por defecto (HH:MM):",
	    validate=lambda text: True if not text or validate_time_format(
	        text) else "Formato inválido. Usa HH:MM").ask() or None

	for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']:
		custom = questionary.text(
		    f"Hora específica para {day_names[day]} (Enter para usar default):",
		    validate=lambda text: True if not text or validate_time_format(
		        text) else "Formato inválido. Usa HH:MM").ask()
		if custom:
			schedules['outward'][day] = custom

	console.print()
	console.print(Panel("[cyan]Horarios de VUELTA[/cyan]",
	                    border_style="cyan"))
	default_return = questionary.text(
	    "Hora por defecto para vuelta (HH:MM, Enter para configurar por día):",
	    validate=lambda text: True if not text or validate_time_format(
	        text) else "Formato inválido. Usa HH:MM").ask()

	if default_return:
		schedules['return']['default'] = default_return

	for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']:
		if schedules['return'][day] is None:
			if schedules['return'].get('default'):
				custom = questionary.text(
				    f"Hora para {day_names[day]} (HH:MM, Enter para usar default {schedules['return']['default']}):",
				    validate=lambda text: True
				    if not text or validate_time_format(
				        text) else "Formato inválido. Usa HH:MM").ask()
				if custom:
					schedules['return'][day] = custom
			else:
				custom = questionary.text(
				    f"Hora para {day_names[day]} (HH:MM, requerido):",
				    validate=lambda text: validate_time_format(text)
				    if text else "Este campo es requerido").ask()
				schedules['return'][day] = custom

	# Minutos de antelación para notificaciones
	console.print()
	console.print(
	    Panel("[cyan]Configuración de notificaciones[/cyan]",
	          border_style="cyan"))
	advance = questionary.text(
	    "Minutos de antelación para notificar (default: 75):",
	    default="75",
	    validate=lambda text: True
	    if not text or text.isdigit() else "Debe ser un número").ask() or "75"
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

	console.print()
	console.print(
	    Panel(
	        "[green]✅ Archivo .env generado correctamente[/green]\n\n"
	        "[yellow]💡 Sugerencia:[/yellow] Si necesitas ajustar algún valor, edita directamente el archivo .env",
	        border_style="green",
	        title="✅ Archivo generado"))


def show_summary(config):
	"""Muestra un resumen de la configuración antes de guardar"""
	summary_table = Table(title="Resumen de Configuración",
	                      show_header=True,
	                      header_style="cyan")
	summary_table.add_column("Parámetro", style="cyan")
	summary_table.add_column("Valor", style="green")

	summary_table.add_row(
	    "Token Telegram", config['telegram_token'][:20] + "..."
	    if len(config['telegram_token']) > 20 else config['telegram_token'])
	summary_table.add_row("ID Usuario Telegram", config['telegram_user_id'])
	summary_table.add_row(
	    "Estación Origen",
	    f"{config['origin_name']} (ID: {config['origin_id']})")
	summary_table.add_row(
	    "Estación Destino",
	    f"{config['destination_name']} (ID: {config['destination_id']})")

	# Mostrar bono con nombre si está disponible
	bonus_id = config.get('bonus_id', '19')
	bonus_name = config.get('bonus_name', '')
	if bonus_name:
		summary_table.add_row("Bono", f"{bonus_name} (ID: {bonus_id})")
	else:
		summary_table.add_row("Bono ID", bonus_id)
	summary_table.add_row(
	    "Antelación Notificación",
	    f"{config['schedules'].get('notification_advance', '75')} minutos")

	console.print()
	console.print(summary_table)


def main():
	console.print()
	console.print(
	    Panel.fit(
	        "[bold cyan]HIFE BOT[/bold cyan]\n"
	        "[yellow]Asistente de configuración[/yellow]\n\n"
	        "Este programa te ayudará a configurar el bot para comprar billetes\n"
	        "en HIFE.es automáticamente.",
	        border_style="cyan",
	        title="🚀 Bienvenido"))

	config = {}

	# 1. Obtener información de Telegram
	config['telegram_token'], config['telegram_user_id'] = get_telegram_info()

	# 2. Obtener token JWT de HIFE
	config['hife_auth_token'] = get_jwt_token()
	if not config['hife_auth_token']:
		console.print()
		console.print(
		    Panel(
		        "[red]❌ No se pudo obtener el token de acceso. El proceso se detiene.[/red]",
		        border_style="red",
		        title="❌ Error"))
		return

	# 3. Obtener paradas de la API
	stops_data = get_stops_from_api(config['hife_auth_token'])
	if not stops_data:
		console.print()
		console.print(
		    Panel(
		        "[yellow]⚠️ No se pudieron obtener las paradas de la API.[/yellow]\n"
		        "Puedes introducir la información manualmente:",
		        border_style="yellow",
		        title="⚠️ Advertencia"))
		origin_name = questionary.text(
		    "Nombre de la estación de origen:").ask()
		origin_id = questionary.text(
		    "ID de la estación de origen (sin ceros iniciales):").ask()
		origin_stop_code = questionary.text(
		    f"Código de parada de origen (default: {origin_id.zfill(4) if origin_id else '0012'}):"
		).ask()

		dest_name = questionary.text("Nombre de la estación de destino:").ask()
		dest_id = questionary.text(
		    "ID de la estación de destino (sin ceros iniciales):").ask()
		dest_stop_code = questionary.text(
		    f"Código de parada de destino (default: {dest_id.zfill(4) if dest_id else '0007'}):"
		).ask()

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
			console.print(
			    Panel(
			        "[red]Error: No se seleccionó una estación de origen[/red]",
			        border_style="red",
			        title="❌ Error"))
			return

		config['origin_id'] = origin_stop['id']
		config['origin_stop_code'] = origin_stop['stop_code']
		config['origin_name'] = origin_stop['name']

		# Seleccionar estación de destino
		dest_stop = select_stop(stops_data, "destino")
		if not dest_stop:
			console.print(
			    Panel(
			        "[red]Error: No se seleccionó una estación de destino[/red]",
			        border_style="red",
			        title="❌ Error"))
			return

		config['destination_id'] = dest_stop['id']
		config['destination_stop_code'] = dest_stop['stop_code']
		config['destination_name'] = dest_stop['name']

	# 4. Configurar horarios
	config['schedules'] = get_schedule()

	# 5. Configurar bono
	print_header("Configuración de Bono", "🎫")

	# Obtener bonos disponibles y activos de la API
	bonuses_data = get_available_bonuses(config['hife_auth_token'])

	if bonuses_data and bonuses_data.get('available') and len(
	    bonuses_data['available']) > 0:
		available_bonuses = bonuses_data['available']
		active_bonus = bonuses_data.get('active')

		# Mostrar información del bono activo si existe
		if active_bonus:
			status_text = "[green]✓ Activo[/green]" if not active_bonus[
			    'expired'] else "[red]✗ Expirado[/red]"
			funds_info = f"{active_bonus['current_funds_amount']}/{active_bonus['initial_funds_amount']}"
			active_panel = Panel(
			    f"[cyan]Bono activo detectado:[/cyan]\n"
			    f"Nombre: [yellow]{active_bonus['bonus_name']}[/yellow]\n"
			    f"Tipo ID: [magenta]{active_bonus['bonus_type_id']}[/magenta]\n"
			    f"Estado: {status_text}\n"
			    f"Fondos: [cyan]{funds_info}[/cyan]",
			    border_style="green"
			    if not active_bonus['expired'] else "yellow",
			    title="🎫 Bono Activo")
			console.print(active_panel)
			console.print()

		# Crear tabla para mostrar los bonos disponibles
		bonus_table = Table(title="Bonos disponibles",
		                    show_header=True,
		                    header_style="cyan")
		bonus_table.add_column("ID", style="magenta", width=5)
		bonus_table.add_column("Nombre", style="cyan")
		bonus_table.add_column("Código", style="yellow", width=10)
		bonus_table.add_column("Estado", style="green", width=12)

		# Preparar opciones para questionary
		bonus_choices = []
		for bonus in available_bonuses:
			bonus_id = str(bonus.get('id', ''))
			bonus_name = bonus.get('current_language',
			                       {}).get('name',
			                               bonus.get('name', 'Sin nombre'))
			bonus_code = bonus.get('external_bonus_code', '')

			# Verificar si este bono es el activo
			is_active = active_bonus and str(
			    active_bonus['bonus_type_id']) == bonus_id
			status = "[green]✓ Activo[/green]" if is_active else ""

			bonus_table.add_row(bonus_id, bonus_name, bonus_code, status)

			# Marcar el bono activo en las opciones
			choice_text = f"{bonus_id} - {bonus_name} (Código: {bonus_code})"
			if is_active:
				choice_text = f"⭐ {choice_text} [ACTIVO]"
			bonus_choices.append(choice_text)

		console.print(bonus_table)
		console.print()

		# Permitir seleccionar o ingresar manualmente
		selected_bonus = questionary.select("Selecciona el bono a utilizar:",
		                                    choices=bonus_choices +
		                                    ["Ingresar ID manualmente"]).ask()

		if selected_bonus == "Ingresar ID manualmente":
			bonus_id = questionary.text(
			    "ID del bono a utilizar:",
			    validate=lambda text: True
			    if text.strip() else "El ID no puede estar vacío").ask()
			config['bonus_id'] = bonus_id
		else:
			# Extraer el ID de la selección (formato: "⭐ ID - Nombre (Código: XXX) [ACTIVO]" o "ID - Nombre (Código: XXX)")
			bonus_id = selected_bonus.replace("⭐ ", "").split(' - ')[0].strip()
			bonus_name = selected_bonus.split(' - ')[1].split(' (')[0].strip()
			config['bonus_id'] = bonus_id
			config['bonus_name'] = bonus_name  # Guardar nombre para el resumen
			# Mostrar confirmación
			is_active_selected = active_bonus and str(
			    active_bonus['bonus_type_id']) == bonus_id
			active_note = " [ACTIVO]" if is_active_selected else ""
			console.print(
			    f"[green]✓[/green] Bono seleccionado: [cyan]{bonus_name}[/cyan] (ID: [magenta]{bonus_id}[/magenta]){active_note}"
			)
	else:
		# Si no se pueden obtener los bonos, usar entrada manual con default
		console.print(
		    Panel(
		        "[yellow]⚠️ No se pudieron obtener los bonos de la API.[/yellow]\n"
		        "Puedes ingresar el ID del bono manualmente.",
		        border_style="yellow",
		        title="⚠️ Advertencia"))
		# Si hay un bono activo pero no se pudieron obtener los disponibles, sugerir el activo
		if bonuses_data and bonuses_data.get('active'):
			active_bonus = bonuses_data['active']
			suggested_id = str(active_bonus['bonus_type_id'])
			console.print(
			    f"[cyan]💡 Sugerencia:[/cyan] Tu bono activo es [yellow]{active_bonus['bonus_name']}[/yellow] (ID: [magenta]{suggested_id}[/magenta])"
			)
			bonus_id = questionary.text(
			    f"ID del bono a utilizar (default: {suggested_id} para tu bono activo):",
			    default=suggested_id).ask()
			config['bonus_id'] = bonus_id if bonus_id else suggested_id
			config['bonus_name'] = active_bonus['bonus_name']
		else:
			bonus_id = questionary.text(
			    "ID del bono a utilizar (default: 19 para MITMA Joven):",
			    default="19").ask()
			config['bonus_id'] = bonus_id if bonus_id else "19"

	# Los trip_ids no se obtienen automáticamente, el usuario puede configurarlos después si es necesario
	config['trip_ids'] = {}

	# Mostrar resumen
	show_summary(config)

	# Confirmar antes de guardar
	console.print()
	if not questionary.confirm("¿Guardar esta configuración?",
	                           default=True).ask():
		console.print(
		    "[yellow]Configuración cancelada por el usuario[/yellow]")
		return

	# 6. Generar archivo .env
	generate_env_file(config)

	console.print()
	console.print(
	    Panel.fit(
	        "[green]✅ ¡Configuración completada![/green]\n\n"
	        "[cyan]📝[/cyan] Se ha generado el archivo .env con tu configuración.\n\n"
	        "[cyan]🚀[/cyan] Para ejecutar el bot, usa:\n"
	        "   [yellow]python main.py[/yellow]\n\n"
	        "[cyan]📱[/cyan] El bot enviará notificaciones a través de Telegram\n"
	        "   para preguntarte si quieres comprar billetes.\n\n"
	        "[cyan]💡[/cyan] Si necesitas ajustar algún valor, edita el archivo .env",
	        border_style="green",
	        title="✅ Completado"))


if __name__ == "__main__":
	main()
