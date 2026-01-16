import requests
import datetime
import logging
import asyncio
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackQueryHandler, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.logging import RichHandler
from config import Config

# Configurar logging con Rich
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True, show_path=False, markup=True)])
logger = logging.getLogger(__name__)

console = Console()

# Timeout for all HTTP requests (in seconds)
# Prevents requests from hanging indefinitely
REQUEST_TIMEOUT = 10

# Retry configuration for server errors
MAX_RETRIES = 3
RETRY_DELAY_BASE = 2  # Base delay in seconds for exponential backoff


class HifeAutomator:

	def __init__(self):
		self.api_url = Config.HIFE_API_URL
		self.headers = Config.get_headers()

	def get_trip_id(self, origin, dest, date_str, target_time):
		url = f"{self.api_url}/route/{origin}/{dest}/{date_str}/trips"
		params = {
		    'pmrsr':
		    0,
		    'client_id':
		    Config.HIFE_CLIENT_ID_VALIDATED
		    if Config.HIFE_CLIENT_ID_VALIDATED is not None else 33798,
		    'trip_main_info[adults_num]':
		    1,
		    'trip_main_info[operation_type_id]':
		    0,
		    'trip_main_info[going_date]':
		    date_str.replace('-', '/')
		}

		# Retry logic for server errors (5xx)
		for attempt in range(MAX_RETRIES):
			try:
				res = requests.get(url,
				                   headers=self.headers,
				                   params=params,
				                   timeout=REQUEST_TIMEOUT)

				# Handle different HTTP status codes
				if res.status_code == 500:
					# Server error - retry with exponential backoff
					if attempt < MAX_RETRIES - 1:
						delay = RETRY_DELAY_BASE * (2**attempt)
						console.print(
						    f"[yellow]⚠[/yellow] Error 500 del servidor (intento {attempt + 1}/{MAX_RETRIES}). "
						    f"Reintentando en {delay}s...")
						logger.warning(
						    f"Server error 500 al buscar viaje (intento {attempt + 1}/{MAX_RETRIES}): {res.url}"
						)
						time.sleep(delay)
						continue
					else:
						# Last attempt failed
						console.print(
						    f"[red]✗[/red] Error 500 del servidor después de {MAX_RETRIES} intentos"
						)
						logger.error(
						    f"Server error 500 persistente después de {MAX_RETRIES} intentos: {res.url}"
						)
						return {'error': 'server_error', 'status_code': 500}

				# Raise for other HTTP errors (4xx, etc.)
				res.raise_for_status()

				# Success - parse response
				trips = res.json()

				for trip in trips:
					if trip.get('departure_time') == target_time:
						console.print(
						    f"[green]✓[/green] Viaje encontrado: [cyan]{target_time}[/cyan] -> ID: [magenta]{trip['id']}[/magenta]"
						)
						return trip['id']

				# Trip not found in response
				console.print(
				    f"[yellow]⚠[/yellow] No se encontró viaje para [cyan]{target_time}[/cyan] el [cyan]{date_str}[/cyan]"
				)
				return None

			except requests.exceptions.HTTPError as e:
				# Handle other HTTP errors (4xx, etc.)
				status_code = e.response.status_code if hasattr(
				    e, 'response') and e.response else None
				console.print(
				    f"[red]✗[/red] Error HTTP {status_code} al buscar viaje: [red]{e}[/red]"
				)
				logger.error(f"HTTP error {status_code} al buscar viaje: {e}")
				return {'error': 'http_error', 'status_code': status_code}

			except requests.exceptions.Timeout as e:
				console.print(
				    f"[red]✗[/red] Timeout al buscar viaje: [red]{e}[/red]")
				logger.error(f"Timeout al buscar viaje: {e}")
				return {'error': 'timeout'}

			except requests.exceptions.ConnectionError as e:
				console.print(
				    f"[red]✗[/red] Error de conexión al buscar viaje: [red]{e}[/red]"
				)
				logger.error(f"Connection error al buscar viaje: {e}")
				return {'error': 'connection_error'}

			except requests.exceptions.RequestException as e:
				console.print(
				    f"[red]✗[/red] Error de red al buscar viaje: [red]{e}[/red]"
				)
				logger.error(f"Request exception al buscar viaje: {e}")
				return {'error': 'request_error'}

			except Exception as e:
				console.print(
				    f"[red]✗[/red] Error inesperado al buscar viaje: [red]{e}[/red]"
				)
				logger.exception("Error inesperado al buscar viaje")
				return {'error': 'unknown_error'}

		# Should not reach here, but just in case
		return {'error': 'max_retries_exceeded'}

	def buy_ticket(self, schedule_id, date_str, trip_type):
		try:
			console.print(
			    f"[cyan]🔄[/cyan] Iniciando compra de billete: [yellow]{trip_type}[/yellow] para [cyan]{date_str}[/cyan]"
			)
			# Use YYYY-MM-DD format (same as used in bonus API)
			op_data = {
			    "quantity": 1,
			    "quantity_childs": 0,
			    "quantity_childs_without_seat": 0,
			    "insurance": 0,
			    "pmrsr": 0,
			    "origin_schedule": str(schedule_id),
			    "goingTripDay": date_str,
			    "goingPrice": "512",
			    "operation_type": 0
			}
			try:
				op_res = requests.post(f"{self.api_url}/route/operation",
				                       headers=self.headers,
				                       json=op_data,
				                       timeout=REQUEST_TIMEOUT)
			except requests.exceptions.RequestException as e:
				console.print(
				    f"[red]✗[/red] Error de red/timeout en operación: [red]{e}[/red]"
				)
				logger.error(
				    f"Request exception al crear operación: {e}, op_data: {op_data}"
				)
				return False

			if op_res.status_code != 200:
				console.print(
				    f"[red]✗[/red] Error en operación: Status [red]{op_res.status_code}[/red]"
				)
				console.print(f"[red]Request data:[/red] {op_data}")
				try:
					console.print(f"[red]Response:[/red] {op_res.text}")
				except UnicodeDecodeError as e:
					logger.error(
					    f"Error decodificando respuesta: {e}, status_code: {op_res.status_code}"
					)
					console.print(
					    f"[red]Response (raw):[/red] {op_res.content[:200] if hasattr(op_res, 'content') else 'N/A'}"
					)
			op_res.raise_for_status()
			op_data = op_res.json()
			token_id = op_data['token_id']
			# Extract token_id from list if it's a list
			if isinstance(token_id, list):
				token_id = token_id[0]
			console.print(
			    f"[green]✓[/green] Operación creada: token_id=[magenta]{token_id}[/magenta]"
			)

			if trip_type == "ida":
				origin_stop_code = Config.ORIGIN_STOP_CODE
				destination_stop_code = Config.DESTINATION_STOP_CODE
			else:  # vuelta
				origin_stop_code = Config.DESTINATION_STOP_CODE
				destination_stop_code = Config.ORIGIN_STOP_CODE

			bonus_url = (f"{self.api_url}/bonus/available?"
			             f"bonus_id={Config.BONUS_ID}&"
			             f"trip_date={date_str}&"
			             f"origin_stop_code={origin_stop_code}&"
			             f"destination_stop_code={destination_stop_code}")
			bonus_res = requests.get(bonus_url,
			                         headers=self.headers,
			                         timeout=REQUEST_TIMEOUT)
			bonus_res.raise_for_status()
			bonus_data = bonus_res.json()

			if not bonus_data or len(bonus_data) == 0:
				console.print("[red]✗[/red] No se encontró bono disponible")
				return False

			bonus_item_id = bonus_data[0]['id']
			console.print(
			    f"[green]✓[/green] Bono disponible: ID=[magenta]{bonus_item_id}[/magenta]"
			)

			traveler_data = {
			    "travelers": {
			        "1": {
			            "1": {
			                "form_bonus": str(bonus_item_id)
			            }
			        }
			    },
			    "_method": "PATCH"
			}
			traveler_res = requests.post(
			    f"{self.api_url}/route/operation/{token_id}/travelers",
			    headers=self.headers,
			    json=traveler_data,
			    timeout=REQUEST_TIMEOUT)
			traveler_res.raise_for_status()
			console.print("[green]✓[/green] Viajero asignado")

			reservation_res = requests.post(
			    f"{self.api_url}/route/operation/{token_id}/proceed-reservation",
			    headers=self.headers,
			    json={
			        "payment_method_id": 7,
			        "_method": "PATCH"
			    },
			    timeout=REQUEST_TIMEOUT)
			reservation_res.raise_for_status()
			console.print("[green]✓[/green] Reserva confirmada")

			pay_res = requests.post(
			    f"{self.api_url}/route/operation/{token_id}/payment/bonus-item",
			    headers=self.headers,
			    json={"_method": "PATCH"},
			    timeout=REQUEST_TIMEOUT)
			pay_res.raise_for_status()
			pay_data = pay_res.json()

			success = pay_data.get('success', False)
			if success:
				console.print("[green]✅ Billete comprado con éxito[/green]")
			else:
				console.print(f"[red]✗[/red] Error en el pago: {pay_data}")

			return success
		except requests.exceptions.RequestException as e:
			console.print(f"[red]✗[/red] Error HTTP en compra: [red]{e}[/red]")
			return False
		except Exception as e:
			console.print(f"[red]✗[/red] Error en compra: [red]{e}[/red]")
			logger.exception("Error en compra")
			return False


automator = HifeAutomator()


async def ask_confirmation(context: ContextTypes.DEFAULT_TYPE):
	job = context.job
	data = job.data

	# Formatear fecha de forma legible
	trip_date = datetime.datetime.strptime(data['date'], "%Y-%m-%d")
	date_formatted = trip_date.strftime("%d/%m/%Y")
	day_name = trip_date.strftime("%A").lower()
	day_names_es = {
	    'monday': 'Lunes',
	    'tuesday': 'Martes',
	    'wednesday': 'Miércoles',
	    'thursday': 'Jueves',
	    'friday': 'Viernes',
	    'saturday': 'Sábado',
	    'sunday': 'Domingo'
	}
	day_display = day_names_es.get(day_name, day_name.capitalize())

	# Determinar estaciones según el tipo de viaje
	if data['type'] == "ida":
		origin = Config.ORIGIN_NAME or f"Estación {Config.ORIGIN_ID}"
		destination = Config.DESTINATION_NAME or f"Estación {Config.DESTINATION_ID}"
	else:
		origin = Config.DESTINATION_NAME or f"Estación {Config.DESTINATION_ID}"
		destination = Config.ORIGIN_NAME or f"Estación {Config.ORIGIN_ID}"

	keyboard = [[
	    InlineKeyboardButton(
	        "✅ Sí, comprar",
	        callback_data=f"buy|{data['type']}|{data['time']}|{data['date']}"),
	    InlineKeyboardButton("❌ No, ignorar", callback_data="cancel")
	]]
	reply_markup = InlineKeyboardMarkup(keyboard)

	message_text = (f"🚌 *Notificación de Viaje*\n\n"
	                f"📅 *Fecha:* {day_display}, {date_formatted}\n"
	                f"⏰ *Hora:* {data['time']}\n"
	                f"📍 *Ruta:* {origin} → {destination}\n"
	                f"🎫 *Tipo:* {data['type'].capitalize()}\n\n"
	                f"¿Deseas que compre el billete ahora?")

	await context.bot.send_message(Config.TELEGRAM_USER_ID,
	                               text=message_text,
	                               reply_markup=reply_markup,
	                               parse_mode='Markdown')
	console.print(
	    f"[cyan]📱[/cyan] Notificación enviada: [yellow]{data['type']}[/yellow] a las [cyan]{data['time']}[/cyan]"
	)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
	query = update.callback_query
	await query.answer()

	if query.data == "cancel":
		await query.edit_message_text(
		    "❌ *Operación cancelada*\n\n"
		    "No se realizará ninguna compra.",
		    parse_mode='Markdown')
		return

	_, t_type, t_time, t_date = query.data.split('|')

	# Formatear fecha
	trip_date = datetime.datetime.strptime(t_date, "%Y-%m-%d")
	date_formatted = trip_date.strftime("%d/%m/%Y")

	await query.edit_message_text(
	    f"⏳ *Procesando compra...*\n\n"
	    f"📅 Fecha: {date_formatted}\n"
	    f"⏰ Hora: {t_time}\n"
	    f"🎫 Tipo: {t_type.capitalize()}\n\n"
	    f"Por favor, espera un momento...",
	    parse_mode='Markdown')

	if t_type == "ida":
		origin = Config.ORIGIN_ID
		dest = Config.DESTINATION_ID
	else:
		origin = Config.DESTINATION_ID
		dest = Config.ORIGIN_ID

	date_search = datetime.datetime.strptime(t_date,
	                                         "%Y-%m-%d").strftime("%d-%m-%Y")
	schedule_id = automator.get_trip_id(origin, dest, date_search, t_time)

	# Formatear fecha para mensajes
	trip_date = datetime.datetime.strptime(t_date, "%Y-%m-%d")
	date_formatted = trip_date.strftime("%d/%m/%Y")

	# Determinar estaciones según el tipo de viaje
	if t_type == "ida":
		origin_name = Config.ORIGIN_NAME or f"Estación {Config.ORIGIN_ID}"
		dest_name = Config.DESTINATION_NAME or f"Estación {Config.DESTINATION_ID}"
	else:
		origin_name = Config.DESTINATION_NAME or f"Estación {Config.DESTINATION_ID}"
		dest_name = Config.ORIGIN_NAME or f"Estación {Config.ORIGIN_ID}"

	# Handle different return types from get_trip_id
	if isinstance(schedule_id, dict) and 'error' in schedule_id:
		# Error occurred
		error_type = schedule_id.get('error')
		status_code = schedule_id.get('status_code')

		if error_type == 'server_error':
			error_message = (
			    f"⚠️ *Error del servidor*\n\n"
			    f"📅 Fecha: {date_formatted}\n"
			    f"⏰ Hora solicitada: {t_time}\n"
			    f"🎫 Tipo: {t_type.capitalize()}\n\n"
			    f"El servidor de HIFE está experimentando problemas temporales.\n\n"
			    f"*Se intentó {MAX_RETRIES} veces sin éxito.*\n\n"
			    f"*Recomendaciones:*\n"
			    f"• Espera unos minutos e intenta de nuevo\n"
			    f"• Verifica manualmente en la app de HIFE\n"
			    f"• El bot seguirá intentando automáticamente\n\n"
			    f"Si el problema persiste, puede ser un problema temporal del servidor."
			)
		elif error_type == 'timeout':
			error_message = (f"⏱️ *Timeout en la solicitud*\n\n"
			                 f"📅 Fecha: {date_formatted}\n"
			                 f"⏰ Hora solicitada: {t_time}\n"
			                 f"🎫 Tipo: {t_type.capitalize()}\n\n"
			                 f"La solicitud tardó demasiado en responder.\n\n"
			                 f"*Posibles causas:*\n"
			                 f"• Problemas de conexión\n"
			                 f"• El servidor está sobrecargado\n\n"
			                 f"Por favor, intenta de nuevo en unos momentos.")
		elif error_type == 'connection_error':
			error_message = (
			    f"🔌 *Error de conexión*\n\n"
			    f"📅 Fecha: {date_formatted}\n"
			    f"⏰ Hora solicitada: {t_time}\n"
			    f"🎫 Tipo: {t_type.capitalize()}\n\n"
			    f"No se pudo conectar con el servidor de HIFE.\n\n"
			    f"*Posibles causas:*\n"
			    f"• Problemas de red\n"
			    f"• El servidor está temporalmente fuera de línea\n\n"
			    f"Verifica tu conexión e intenta de nuevo.")
		else:
			# Generic error
			error_message = (
			    f"❌ *Error al buscar viaje*\n\n"
			    f"📅 Fecha: {date_formatted}\n"
			    f"⏰ Hora solicitada: {t_time}\n"
			    f"🎫 Tipo: {t_type.capitalize()}\n\n"
			    f"Ocurrió un error inesperado al buscar el viaje.\n\n"
			    f"Por favor, intenta de nuevo más tarde.")

		await context.bot.send_message(Config.TELEGRAM_USER_ID,
		                               text=error_message,
		                               parse_mode='Markdown')
	elif schedule_id:
		# Valid trip ID found
		success = automator.buy_ticket(schedule_id, t_date, t_type)
		if success:
			success_message = (f"✅ *¡Billete comprado con éxito!*\n\n"
			                   f"📅 *Fecha:* {date_formatted}\n"
			                   f"⏰ *Hora:* {t_time}\n"
			                   f"📍 *Ruta:* {origin_name} → {dest_name}\n"
			                   f"🎫 *Tipo:* {t_type.capitalize()}\n\n"
			                   f"Tu billete está listo. ¡Buen viaje! 🚌")
			await context.bot.send_message(Config.TELEGRAM_USER_ID,
			                               text=success_message,
			                               parse_mode='Markdown')
		else:
			error_message = (
			    f"⚠️ *Error al procesar la compra*\n\n"
			    f"📅 Fecha: {date_formatted}\n"
			    f"⏰ Hora: {t_time}\n"
			    f"🎫 Tipo: {t_type.capitalize()}\n\n"
			    f"No se pudo completar el pago del billete.\n\n"
			    f"*Posibles causas:*\n"
			    f"• Saldo insuficiente en el bono\n"
			    f"• Bono expirado\n"
			    f"• Problema temporal con la API\n\n"
			    f"Por favor, intenta comprar manualmente o revisa tu bono.")
			await context.bot.send_message(Config.TELEGRAM_USER_ID,
			                               text=error_message,
			                               parse_mode='Markdown')
	else:
		# schedule_id is None - trip not found
		not_found_message = (
		    f"❌ *Horario no encontrado*\n\n"
		    f"📅 Fecha: {date_formatted}\n"
		    f"⏰ Hora solicitada: {t_time}\n"
		    f"🎫 Tipo: {t_type.capitalize()}\n\n"
		    f"No se encontró un viaje disponible para este horario.\n\n"
		    f"*Posibles causas:*\n"
		    f"• El horario no existe para esta fecha\n"
		    f"• Cambios en los horarios de la línea\n"
		    f"• El viaje ya no está disponible\n\n"
		    f"Por favor, verifica los horarios disponibles.")
		await context.bot.send_message(Config.TELEGRAM_USER_ID,
		                               text=not_found_message,
		                               parse_mode='Markdown')


def check_immediate_notification(app):
	"""Verifica si estamos dentro de la ventana de 2 horas y pregunta inmediatamente"""
	now = datetime.datetime.now()
	weekday = now.weekday()
	schedule = Config.get_schedule()

	if weekday not in schedule:
		return False

	times = schedule[weekday]
	buy_date_str = now.strftime("%Y-%m-%d")
	advance_minutes = Config.NOTIFICATION_ADVANCE_MINUTES

	for trip_type in ['ida', 'vuelta']:
		if trip_type not in times:
			continue

		time_value = times[trip_type]
		# Validar que el valor no sea None, 'None', o vacío
		if not time_value or time_value == 'None' or time_value is None:
			# No mostrar warning - es normal que algunos días no tengan horarios configurados
			continue

		trip_time = datetime.datetime.strptime(time_value, "%H:%M").time()
		trip_dt = datetime.datetime.combine(now.date(), trip_time)
		diff_minutes = (trip_dt - now).total_seconds() / 60

		# Si estamos dentro de la ventana de 2 horas (0 a advance_minutes minutos antes)
		if 0 < diff_minutes <= advance_minutes:
			console.print(
			    f"[yellow]⚠[/yellow] Inicio tardío detectado: viaje [yellow]{trip_type}[/yellow] a las [cyan]{time_value}[/cyan] "
			    f"(faltan [magenta]{diff_minutes:.1f}[/magenta] minutos) - Preguntando inmediatamente"
			)
			app.job_queue.run_once(ask_confirmation,
			                       when=0,
			                       data={
			                           'type': trip_type,
			                           'time': time_value,
			                           'date': buy_date_str
			                       })
			return True

	return False


def schedule_checker(app):
	now = datetime.datetime.now()
	weekday = now.weekday()
	schedule = Config.get_schedule()

	if weekday not in schedule:
		return

	times = schedule[weekday]
	buy_date_str = now.strftime("%Y-%m-%d")

	advance_minutes = Config.NOTIFICATION_ADVANCE_MINUTES
	window_start = advance_minutes - 5
	window_end = advance_minutes + 5

	for trip_type in ['ida', 'vuelta']:
		if trip_type not in times:
			continue

		time_value = times[trip_type]
		# Validar que el valor no sea None, 'None', o vacío
		if not time_value or time_value == 'None' or time_value is None:
			# No mostrar warning - es normal que algunos días no tengan horarios configurados
			continue

		trip_time = datetime.datetime.strptime(time_value, "%H:%M").time()
		trip_dt = datetime.datetime.combine(now.date(), trip_time)
		diff_minutes = (trip_dt - now).total_seconds() / 60

		if window_start <= diff_minutes <= window_end:
			console.print(
			    f"[cyan]🔔[/cyan] Notificando sobre viaje [yellow]{trip_type}[/yellow] a las [cyan]{time_value}[/cyan] "
			    f"(faltan [magenta]{diff_minutes:.1f}[/magenta] minutos)")
			app.job_queue.run_once(ask_confirmation,
			                       when=0,
			                       data={
			                           'type': trip_type,
			                           'time': time_value,
			                           'date': buy_date_str
			                       })


def show_startup_banner():
	"""Muestra un banner de inicio con información de configuración"""
	schedule = Config.get_schedule()

	# Crear tabla con información de configuración
	config_table = Table(show_header=False, box=None, padding=(0, 1))
	config_table.add_column(style="cyan", width=25)
	config_table.add_column(style="green")

	config_table.add_row("📱 Notificaciones a:", Config.TELEGRAM_USER_ID)
	origin_display = f"{Config.ORIGIN_NAME} (ID: {Config.ORIGIN_ID})" if Config.ORIGIN_NAME else f"ID: {Config.ORIGIN_ID}"
	config_table.add_row("🚉 Estación Origen:", origin_display)
	dest_display = f"{Config.DESTINATION_NAME} (ID: {Config.DESTINATION_ID})" if Config.DESTINATION_NAME else f"ID: {Config.DESTINATION_ID}"
	config_table.add_row("🚉 Estación Destino:", dest_display)
	config_table.add_row("🎫 Bono ID:", Config.BONUS_ID)
	config_table.add_row("⏰ Intervalo de revisión:",
	                     f"{Config.CHECK_INTERVAL_MINUTES} minutos")
	config_table.add_row("🔔 Antelación notificación:",
	                     f"{Config.NOTIFICATION_ADVANCE_MINUTES} minutos")

	# Mostrar horarios configurados
	day_names = {
	    0: 'Lunes',
	    1: 'Martes',
	    2: 'Miércoles',
	    3: 'Jueves',
	    4: 'Viernes'
	}

	schedule_text = ""
	for day, day_name in day_names.items():
		if day in schedule:
			times = schedule[day]
			ida_time = times.get('ida') or 'N/A'
			vuelta_time = times.get('vuelta') or 'N/A'
			schedule_text += f"\n[cyan]{day_name}:[/cyan] Ida: [yellow]{ida_time}[/yellow] | Vuelta: [yellow]{vuelta_time}[/yellow]"

	console.print()
	console.print(
	    Panel.fit(f"[bold cyan]🤖 HIFE Bot está en marcha[/bold cyan]",
	              border_style="cyan",
	              title="🚀 Bot Iniciado"))
	console.print(config_table)
	console.print(
	    Panel(f"[cyan]📅 Horarios configurados:[/cyan]{schedule_text}",
	          border_style="cyan"))
	console.print()


def main():
	is_valid, errors = Config.validate()
	if not is_valid:
		console.print()
		error_panel = Panel("\n".join(
		    [f"[red]✗[/red] {error}" for error in errors]),
		                    title="[red]❌ Errores en la configuración[/red]",
		                    border_style="red")
		console.print(error_panel)
		console.print()
		console.print(
		    Panel(
		        "[yellow]💡 Solución:[/yellow]\n\n"
		        "Por favor, configura las variables de entorno en el archivo .env\n\n"
		        "Puedes usar '[cyan]python setup_wizard.py[/cyan]' para configurarlo automáticamente",
		        border_style="yellow",
		        title="💡 Ayuda"))
		return

	console.print("[green]✅ Configuración validada correctamente[/green]")

	# Función que se ejecuta después de que la aplicación se inicializa
	async def post_init(app: Application) -> None:
		# Pequeño delay para asegurar que todo esté listo
		await asyncio.sleep(2)
		# Verificar si estamos dentro de la ventana de 2 horas al iniciar
		immediate_notification = check_immediate_notification(app)
		if immediate_notification:
			console.print(
			    "[cyan]⏰[/cyan] Notificación inmediata enviada - esperando respuesta del usuario..."
			)

	# Usar post_init como callback del builder
	application = Application.builder().token(
	    Config.TELEGRAM_TOKEN).post_init(post_init).build()
	application.add_handler(CallbackQueryHandler(handle_callback))

	scheduler = BackgroundScheduler()
	check_interval = Config.CHECK_INTERVAL_MINUTES
	scheduler.add_job(lambda: schedule_checker(application),
	                  'interval',
	                  minutes=check_interval)
	scheduler.start()

	console.print(
	    f"[cyan]🤖[/cyan] Bot iniciado - Revisando horarios cada [magenta]{check_interval}[/magenta] minutos"
	)

	# Mostrar banner de inicio
	show_startup_banner()

	application.run_polling()


if __name__ == '__main__':
	main()
