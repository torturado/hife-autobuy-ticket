import requests
import datetime
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackQueryHandler, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler
from config import Config

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)
logger = logging.getLogger(__name__)


class HifeAutomator:

	def __init__(self):
		self.api_url = Config.HIFE_API_URL
		self.headers = Config.get_headers()

	def get_trip_id(self, origin, dest, date_str, target_time):
		url = f"{self.api_url}/route/{origin}/{dest}/{date_str}/trips"
		params = {
		    'pmrsr': 0,
		    'client_id': Config.HIFE_CLIENT_ID,
		    'trip_main_info[adults_num]': 1,
		    'trip_main_info[operation_type_id]': 0,
		    'trip_main_info[going_date]': date_str.replace('-', '/')
		}

		try:
			res = requests.get(url, headers=self.headers, params=params)
			res.raise_for_status()
			trips = res.json()

			for trip in trips:
				if trip.get('departure_time') == target_time:
					logger.info(
					    f"Viaje encontrado: {target_time} -> ID: {trip['id']}")
					return trip['id']

			logger.warning(
			    f"No se encontró viaje para {target_time} el {date_str}")
			return None
		except Exception as e:
			logger.error(f"Error al buscar viaje: {e}")
			return None

	def buy_ticket(self, schedule_id, date_str, trip_type):
		try:
			logger.info(
			    f"Iniciando compra de billete: {trip_type} para {date_str}")
			op_data = {
			    "quantity": 1,
			    "pmrsr": 0,
			    "origin_schedule": str(schedule_id),
			    "goingTripDay": date_str,
			    "goingPrice": "512",
			    "operation_type": 0
			}
			op_res = requests.post(f"{self.api_url}/route/operation",
			                       headers=self.headers,
			                       json=op_data)
			op_res.raise_for_status()
			op_data = op_res.json()
			token_id = op_data['token_id']
			logger.info(f"Operación creada: token_id={token_id}")

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
			bonus_res = requests.get(bonus_url, headers=self.headers)
			bonus_res.raise_for_status()
			bonus_data = bonus_res.json()

			if not bonus_data or len(bonus_data) == 0:
				logger.error("No se encontró bono disponible")
				return False

			bonus_item_id = bonus_data[0]['id']
			logger.info(f"Bono disponible: ID={bonus_item_id}")

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
			    json=traveler_data)
			traveler_res.raise_for_status()
			logger.info("Viajero asignado")

			reservation_res = requests.post(
			    f"{self.api_url}/route/operation/{token_id}/proceed-reservation",
			    headers=self.headers,
			    json={
			        "payment_method_id": 7,
			        "_method": "PATCH"
			    })
			reservation_res.raise_for_status()
			logger.info("Reserva confirmada")

			pay_res = requests.post(
			    f"{self.api_url}/route/operation/{token_id}/payment/bonus-item",
			    headers=self.headers,
			    json={"_method": "PATCH"})
			pay_res.raise_for_status()
			pay_data = pay_res.json()

			success = pay_data.get('success', False)
			if success:
				logger.info("✅ Billete comprado con éxito")
			else:
				logger.error(f"Error en el pago: {pay_data}")

			return success
		except requests.exceptions.RequestException as e:
			logger.error(f"Error HTTP en compra: {e}")
			return False
		except Exception as e:
			logger.error(f"Error en compra: {e}", exc_info=True)
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
	logger.info(f"Notificación enviada: {data['type']} a las {data['time']}")


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


def schedule_checker(app):
	now = datetime.datetime.now()
	weekday = now.weekday()
	schedule = Config.get_schedule()

	if weekday not in schedule:
		return

	times = schedule[weekday]
	date_str = now.strftime("%d-%m-%Y")
	buy_date_str = now.strftime("%Y-%m-%d")

	advance_minutes = Config.NOTIFICATION_ADVANCE_MINUTES
	window_start = advance_minutes - 5
	window_end = advance_minutes + 5

	for trip_type in ['ida', 'vuelta']:
		if trip_type not in times:
			continue

		trip_time = datetime.datetime.strptime(times[trip_type],
		                                       "%H:%M").time()
		trip_dt = datetime.datetime.combine(now.date(), trip_time)
		diff_minutes = (trip_dt - now).total_seconds() / 60

		if window_start <= diff_minutes <= window_end:
			logger.info(
			    f"Notificando sobre viaje {trip_type} a las {times[trip_type]} "
			    f"(faltan {diff_minutes:.1f} minutos)")
			app.job_queue.run_once(ask_confirmation,
			                       when=0,
			                       data={
			                           'type': trip_type,
			                           'time': times[trip_type],
			                           'date': buy_date_str
			                       })


def main():
	is_valid, errors = Config.validate()
	if not is_valid:
		logger.error("❌ Errores en la configuración:")
		for error in errors:
			logger.error(f"  - {error}")
		logger.error(
		    "\nPor favor, configura las variables de entorno en el archivo .env"
		)
		logger.error(
		    "Puedes usar 'python setup_wizard.py' para configurarlo automáticamente"
		)
		return

	logger.info("✅ Configuración validada correctamente")

	application = Application.builder().token(Config.TELEGRAM_TOKEN).build()
	application.add_handler(CallbackQueryHandler(handle_callback))

	scheduler = BackgroundScheduler()
	check_interval = Config.CHECK_INTERVAL_MINUTES
	scheduler.add_job(lambda: schedule_checker(application),
	                  'interval',
	                  minutes=check_interval)
	scheduler.start()

	logger.info(
	    f"🤖 Bot iniciado - Revisando horarios cada {check_interval} minutos")
	print("\n" + "=" * 50)
	print("🤖 HIFE Bot está en marcha...")
	print("=" * 50)
	print(f"📱 Notificaciones a: {Config.TELEGRAM_USER_ID}")
	print(f"⏰ Revisando cada {check_interval} minutos")
	print(
	    f"🔔 Notificando {Config.NOTIFICATION_ADVANCE_MINUTES} minutos antes del viaje"
	)
	print("=" * 50 + "\n")

	application.run_polling()


if __name__ == '__main__':
	main()
