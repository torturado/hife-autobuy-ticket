# ⚠️⚠️ BOT EN PRUEBAS

# HIFE Bot Personalizable

Bot para compra automática de billetes en HIFE.es

## Descripción

Este bot permite la compra automática de billetes de autobús en la página web de HIFE, personalizando horarios, rutas y bonos según las necesidades del usuario. El bot se conecta a Telegram para preguntar si deseas comprar los billetes según los horarios configurados.

## Características

- Configurable para cualquier ruta disponible en HIFE.es
- Horarios personalizables por día de la semana
- Soporte para diferentes tipos de bonos
- Notificaciones a través de Telegram
- Compra automática con confirmación del usuario
- Reintentos automáticos en caso de fallos
- Logs detallados para diagnosticar problemas

## Requisitos previos

- Python 3.7 o superior
- Cuenta en HIFE.es con un bono activo
- Bot de Telegram (creado a través de @BotFather)
- Acceso a internet estable
- Sistema operativo: Windows, Linux o macOS

## ⚠️ IMPORTANTE: Configuración de idioma HIFE ⚠️

Este bot está diseñado para funcionar EXCLUSIVAMENTE con cuentas de HIFE configuradas en inglés. 
Por favor, asegúrate de que tu cuenta de HIFE.es está configurada en inglés antes de usar este bot.

Para cambiar el idioma de tu cuenta HIFE:
1. Inicia sesión en la web de HIFE.es
2. Haz clic en el selector de idioma (normalmente en la esquina superior derecha)
3. Selecciona "English"
4. Verifica que la URL de navegación ha cambiado a incluir "/en/" y que la interfaz está en inglés

![image](https://github.com/user-attachments/assets/b3613df8-aa89-4a2a-8097-c6e136b248de)


El bot NO funcionará correctamente si tu cuenta está configurada en español o catalán.

## Instalación

### 1. Clonar el repositorio o descargar los archivos

```bash
git clone https://github.com/torturado/hife-autobuy-ticket.git
cd hife-autobuy-ticket
```

### 2. Crear un entorno virtual (recomendado)

```bash
# En Windows
python -m venv venv
venv\Scripts\activate

# En Linux/macOS
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalar las dependencias

```bash
pip install -r requirements.txt
```

### 4. Crear un bot de Telegram con BotFather

1. Abre Telegram y busca @BotFather
2. Envía el comando `/newbot`
3. Sigue las instrucciones para crear un nuevo bot
4. Guarda el token que te proporciona BotFather
5. Envía un mensaje a tu nuevo bot y luego habla con @userinfobot para obtener tu ID de usuario

![image](https://github.com/user-attachments/assets/3866d58c-78ee-4076-8033-750b1d606dcf)


### 5. Ejecutar el asistente de configuración

```bash
python setup_wizard.py
```

Sigue las instrucciones del asistente para configurar:
- Tu bot de Telegram
- Tus credenciales de HIFE
- Estaciones de origen y destino
- Horarios para cada día de la semana
- Bono a utilizar

## Uso

### Iniciar el bot

```bash
python main.py
```

El bot se ejecutará en segundo plano y te enviará notificaciones a través de Telegram en los horarios configurados para preguntarte si quieres comprar billetes.

### Ejemplo de configuración

Para un usuario que viaja de Madrid a Barcelona:

- **Ida**: Lunes a viernes a las 8:00
- **Vuelta**: 
  - Lunes, martes, miércoles, jueves: 18:30
  - Viernes: 16:00

El asistente de configuración te ayudará a encontrar los IDs de las estaciones y los viajes correspondientes.

### Comandos de Telegram

- `/start` - Inicia la conversación con el bot
- `/si_ida` - Compra un billete de ida para hoy inmediatamente
- `/si_vuelta` - Compra un billete de vuelta para hoy inmediatamente
- `/horarios` - Muestra los horarios configurados actualmente
- `/estado` - Comprueba el estado de la conexión con HIFE
- `/ayuda` - Muestra la lista de comandos disponibles

## Configuración manual

Si necesitas ajustar la configuración manualmente, puedes editar el archivo `.env` generado por el asistente. Las principales opciones incluyen:

- Credenciales (TELEGRAM_TOKEN, HIFE_EMAIL, etc.)
- IDs de estaciones (ORIGIN_ID, DESTINATION_ID)
- Horarios de ida y vuelta (OUTWARD_TIME_*, RETURN_TIME_*)
- IDs de los viajes (OUTWARD_TRIP_ID_*, RETURN_TRIP_ID_*)
- ID del bono (BONUS_ID)

## Solución de problemas

Si encuentras algún problema:

1. Verifica que tu cuenta en HIFE.es esté activa y configurada en INGLÉS
2. Comprueba que tienes un bono válido con saldo suficiente
3. Revisa las credenciales en el archivo `.env`
4. Consulta los logs en la carpeta `logs/`
5. Si los IDs de viaje cambian, actualiza el archivo .env con los nuevos valores
6. Usa el comando `/estado` en Telegram para verificar la conexión

## Archivos principales

- `main.py` - Aplicación principal del bot
- `setup_wizard.py` - Asistente de configuración interactivo
- `.env` - Archivo de configuración con variables personalizadas
- `requirements.txt` - Dependencias del proyecto

## Contribuciones

Las contribuciones son bienvenidas. Si deseas mejorar este bot:

1. Haz un fork del repositorio
2. Crea una rama para tu característica (`git checkout -b feature/amazing-feature`)
3. Haz commit de tus cambios (`git commit -m 'Add some amazing feature'`)
4. Haz push a la rama (`git push origin feature/amazing-feature`)
5. Abre un Pull Request

## Limitaciones conocidas

- Los IDs de viaje pueden cambiar con el tiempo, requiriendo actualización manual
- Solo funciona con bonos gratuitos de HIFE
- No gestiona cambios en los horarios o cancelaciones de rutas
- Solo compatible con cuentas HIFE configuradas en inglés

## Licencia

Este software es de código abierto, distribuido bajo licencia MIT.

## Descargo de responsabilidad

Este bot es un proyecto no oficial y no está afiliado de ninguna manera con HIFE.es. Úsalo bajo tu propia responsabilidad. Los autores no se hacen responsables de cualquier problema derivado del uso de esta herramienta. 
