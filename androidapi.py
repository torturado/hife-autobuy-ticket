import requests
import datetime
import logging
import asyncio
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

		try:
			res = requests.get(url,
			                   headers=self.headers,
			                   params=params,
			                   timeout=REQUEST_TIMEOUT)
			res.raise_for_status()
			trips = res.json()

			for trip in trips:
				if trip.get('departure_time') == target_time:
					console.print(
					    f"[green]✓[/green] Viaje encontrado: [cyan]{target_time}[/cyan] -> ID: [magenta]{trip['id']}[/magenta]"
					)
					return trip['id']

			console.print(
			    f"[yellow]⚠[/yellow] No se encontró viaje para [cyan]{target_time}[/cyan] el [cyan]{date_str}[/cyan]"
			)
			return None
		except requests.exceptions.RequestException as e:
			console.print(
			    f"[red]✗[/red] Error de red/timeout al buscar viaje: [red]{e}[/red]"
			)
			logger.error(f"Request exception al buscar viaje: {e}")
			return None
		except Exception as e:
			console.print(
			    f"[red]✗[/red] Error al buscar viaje: [red]{e}[/red]")
			logger.exception("Error inesperado al buscar viaje")
			return None

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

	keyboard = [[
	    InlineKeyboardButton(
	        "✅ Comprar",
	        callback_data=f"buy|{data['type']}|{data['time']}|{data['date']}"),
	    InlineKeyboardButton("❌ Ignorar", callback_data="cancel")
	]]
	reply_markup = InlineKeyboardMarkup(keyboard)
	await context.bot.send_message(
	    Config.TELEGRAM_USER_ID,
	    text=
	    f"❓ ¿Compro el billete de {data['type']} para hoy a las {data['time']}?",
	    reply_markup=reply_markup)
	console.print(
	    f"[cyan]📱[/cyan] Notificación enviada: [yellow]{data['type']}[/yellow] a las [cyan]{data['time']}[/cyan]"
	)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
	query = update.callback_query
	await query.answer()

	if query.data == "cancel":
		await query.edit_message_text("❌ Operación cancelada.")
		return

	_, t_type, t_time, t_date = query.data.split('|')
	await query.edit_message_text(
	    f"⏳ Procesando compra de {t_type} ({t_time})...")

	if t_type == "ida":
		origin = Config.ORIGIN_ID
		dest = Config.DESTINATION_ID
	else:
		origin = Config.DESTINATION_ID
		dest = Config.ORIGIN_ID

	date_search = datetime.datetime.strptime(t_date,
	                                         "%Y-%m-%d").strftime("%d-%m-%Y")
	schedule_id = automator.get_trip_id(origin, dest, date_search, t_time)
	if schedule_id:
		success = automator.buy_ticket(schedule_id, t_date, t_type)
		if success:
			await context.bot.send_message(
			    Config.TELEGRAM_USER_ID,
			    f"✅ ¡Billete de {t_type} comprado con éxito!")
		else:
			await context.bot.send_message(
			    Config.TELEGRAM_USER_ID,
			    f"⚠️ Error al procesar el pago del billete de {t_type}.")
	else:
		await context.bot.send_message(
		    Config.TELEGRAM_USER_ID,
		    f"❌ No se encontró el horario {t_time} para la fecha {t_date}.")


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
