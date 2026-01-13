import os
from dotenv import load_dotenv
from typing import Dict, Optional

try:
	load_dotenv()
except (UnicodeDecodeError, Exception) as e:
	# Intentar cargar con diferentes codificaciones si UTF-8 falla
	try:
		load_dotenv(encoding='latin-1')
	except:
		try:
			load_dotenv(encoding='cp1252')
		except:
			# Si todo falla, continuar sin .env (usará valores por defecto)
			pass


class Config:

	# Telegram
	TELEGRAM_TOKEN: str = os.getenv('TELEGRAM_TOKEN', '')
	TELEGRAM_USER_ID: str = os.getenv('TELEGRAM_USER_ID', '')

	# HIFE API
	HIFE_API_URL: str = os.getenv('HIFE_API_URL',
	                              'https://middleware.hife.es/api')
	HIFE_AUTH_TOKEN: str = os.getenv('HIFE_AUTH_TOKEN', '')
	HIFE_CLIENT_ID: int = int(os.getenv('HIFE_CLIENT_ID', '33798'))
	HIFE_APP_VERSION: str = os.getenv('HIFE_APP_VERSION', '2.0.8')

	# Estaciones
	ORIGIN_ID: str = os.getenv('ORIGIN_ID', '')
	ORIGIN_STOP_CODE: str = os.getenv('ORIGIN_STOP_CODE', '')
	DESTINATION_ID: str = os.getenv('DESTINATION_ID', '')
	DESTINATION_STOP_CODE: str = os.getenv('DESTINATION_STOP_CODE', '')

	# Bono
	BONUS_ID: str = os.getenv('BONUS_ID', '19')

	# Horarios - Ida
	OUTWARD_TIME_DEFAULT: Optional[str] = os.getenv(
	    'OUTWARD_TIME_DEFAULT') or None
	OUTWARD_TIME_MONDAY: Optional[str] = os.getenv(
	    'OUTWARD_TIME_MONDAY') or None
	OUTWARD_TIME_TUESDAY: Optional[str] = os.getenv(
	    'OUTWARD_TIME_TUESDAY') or None
	OUTWARD_TIME_WEDNESDAY: Optional[str] = os.getenv(
	    'OUTWARD_TIME_WEDNESDAY') or None
	OUTWARD_TIME_THURSDAY: Optional[str] = os.getenv(
	    'OUTWARD_TIME_THURSDAY') or None
	OUTWARD_TIME_FRIDAY: Optional[str] = os.getenv(
	    'OUTWARD_TIME_FRIDAY') or None

	# Horarios - Vuelta
	RETURN_TIME_DEFAULT: Optional[str] = os.getenv(
	    'RETURN_TIME_DEFAULT') or None
	RETURN_TIME_MONDAY: Optional[str] = os.getenv('RETURN_TIME_MONDAY') or None
	RETURN_TIME_TUESDAY: Optional[str] = os.getenv(
	    'RETURN_TIME_TUESDAY') or None
	RETURN_TIME_WEDNESDAY: Optional[str] = os.getenv(
	    'RETURN_TIME_WEDNESDAY') or None
	RETURN_TIME_THURSDAY: Optional[str] = os.getenv(
	    'RETURN_TIME_THURSDAY') or None
	RETURN_TIME_FRIDAY: Optional[str] = os.getenv('RETURN_TIME_FRIDAY') or None

	# Notificaciones
	NOTIFICATION_ADVANCE_MINUTES: int = int(
	    os.getenv('NOTIFICATION_ADVANCE_MINUTES', '120'))
	CHECK_INTERVAL_MINUTES: int = int(os.getenv('CHECK_INTERVAL_MINUTES',
	                                            '10'))

	@classmethod
	def get_schedule(cls) -> Dict[int, Dict[str, str]]:
		schedule = {}
		day_map = {
		    0: ('OUTWARD_TIME_MONDAY', 'RETURN_TIME_MONDAY'),
		    1: ('OUTWARD_TIME_TUESDAY', 'RETURN_TIME_TUESDAY'),
		    2: ('OUTWARD_TIME_WEDNESDAY', 'RETURN_TIME_WEDNESDAY'),
		    3: ('OUTWARD_TIME_THURSDAY', 'RETURN_TIME_THURSDAY'),
		    4: ('OUTWARD_TIME_FRIDAY', 'RETURN_TIME_FRIDAY'),
		}

		for day, (outward_key, return_key) in day_map.items():
			outward_time = getattr(cls,
			                       outward_key) or cls.OUTWARD_TIME_DEFAULT
			return_time = getattr(cls, return_key) or cls.RETURN_TIME_DEFAULT

			if outward_time and return_time:
				schedule[day] = {"ida": outward_time, "vuelta": return_time}

		return schedule

	@classmethod
	def get_headers(cls) -> Dict[str, str]:
		return {
		    'accept':
		    'application/json; charset=utf-8',
		    'app-version':
		    cls.HIFE_APP_VERSION,
		    'authorization':
		    cls.HIFE_AUTH_TOKEN,
		    'content-type':
		    'application/json; charset=utf-8',
		    'user-agent':
		    'Dalvik/2.1.0 (Linux; U; Android 12; SM-S916U Build/9643478.0)'
		}

	@classmethod
	def validate(cls):
		errors = []

		if not cls.TELEGRAM_TOKEN:
			errors.append("TELEGRAM_TOKEN no configurado")
		if not cls.TELEGRAM_USER_ID:
			errors.append("TELEGRAM_USER_ID no configurado")
		if not cls.HIFE_AUTH_TOKEN:
			errors.append("HIFE_AUTH_TOKEN no configurado")
		if not cls.ORIGIN_ID:
			errors.append("ORIGIN_ID no configurado")
		if not cls.ORIGIN_STOP_CODE:
			errors.append("ORIGIN_STOP_CODE no configurado")
		if not cls.DESTINATION_ID:
			errors.append("DESTINATION_ID no configurado")
		if not cls.DESTINATION_STOP_CODE:
			errors.append("DESTINATION_STOP_CODE no configurado")
		if not cls.BONUS_ID:
			errors.append("BONUS_ID no configurado")

		schedule = cls.get_schedule()
		if not schedule:
			errors.append("No hay horarios configurados")

		return len(errors) == 0, errors
