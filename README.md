# 🚌 HIFE Bot - Automatización de Compra de Billetes

Bot de Telegram que automatiza la compra de billetes de autobús en HIFE.es usando la API oficial de middleware.

[![Python](https://img.shields.io/badge/Python-3.7+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## 📋 Descripción

Este bot te permite automatizar la compra de billetes de autobús en HIFE.es. El bot monitorea tus horarios configurados y te envía notificaciones a través de Telegram cuando es momento de comprar un billete, permitiéndote confirmar o cancelar la compra con un simple clic.

### ✨ Características

-   **Automatización completa**: Monitorea horarios y notifica automáticamente
-   **Integración con Telegram**: Notificaciones y confirmaciones mediante bot
-   **Horarios personalizables**: Configura diferentes horarios para cada día de la semana
-   **Soporte para bonos**: Compatible con bonos gratuitos de HIFE (MITMA Joven, etc.)
-   **Reintentos automáticos**: Manejo robusto de errores y reintentos
-   **Logs detallados**: Sistema de logging completo para diagnóstico
-   **Configuración fácil**: Asistente interactivo de configuración

## Requisitos Previos

-   Python 3.7 o superior
-   Cuenta en HIFE.es con un bono activo
-   Bot de Telegram (creado a través de [@BotFather](https://t.me/BotFather))
-   Acceso a internet estable

## 🚀 Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/tu-usuario/hife-bot.git
cd hife-bot
```

### 2. Crear entorno virtual (recomendado)

```bash
# En Windows
python -m venv venv
venv\Scripts\activate

# En Linux/macOS
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar el bot

Ejecuta el asistente de configuración interactivo:

```bash
python setup_wizard.py
```

El asistente te guiará a través de:

1. **Configuración de Telegram**

    - Token del bot (obtener de [@BotFather](https://t.me/BotFather))
    - Tu ID de usuario (obtener de [@userinfobot](https://t.me/userinfobot))

2. **Autenticación en HIFE**

    - Email y contraseña de tu cuenta HIFE
    - El sistema obtendrá automáticamente el token JWT necesario

3. **Selección de Estaciones**

    - Busca y selecciona tu estación de origen de una lista
    - Busca y selecciona tu estación de destino de una lista
    - Los IDs y códigos de parada se obtienen automáticamente de la API

4. **Configuración de Horarios**

    - Horarios de ida y vuelta para cada día de la semana
    - Puedes usar un horario por defecto o configurar horarios específicos por día
    - Minutos de antelación para notificaciones

5. **Configuración de Bono**
    - ID del bono a utilizar (default: 19 para MITMA Joven)

### 5. Configuración manual (opcional)

Si prefieres configurar manualmente, copia el archivo de ejemplo:

```bash
cp env.example .env
```

Edita el archivo `.env` con tus valores. Ver `env.example` para ver todas las variables disponibles.

## 📖 Uso

### Iniciar el bot

```bash
python main.py
```

El bot se ejecutará en segundo plano y:

-   Revisará los horarios cada 10 minutos (configurable)
-   Te enviará notificaciones cuando falten ~2 horas para un viaje
-   Te permitirá confirmar o cancelar la compra desde Telegram

### Ejemplo de flujo

1. El bot detecta que faltan 2 horas para tu viaje de ida a las 06:45
2. Te envía un mensaje en Telegram: "❓ ¿Compro el billete de ida para hoy a las 06:45?"
3. Tú respondes con "✅ Comprar" o "❌ Ignorar"
4. Si confirmas, el bot ejecuta la compra automáticamente
5. Recibes confirmación del éxito o error de la compra

## 🔧 Configuración Avanzada

### Variables de Entorno

El bot usa variables de entorno desde el archivo `.env`. Las principales son:

#### Telegram

-   `TELEGRAM_TOKEN`: Token del bot de Telegram
-   `TELEGRAM_USER_ID`: Tu ID de usuario de Telegram

#### HIFE API

-   `HIFE_AUTH_TOKEN`: Token JWT de autenticación (formato: `Bearer eyJ0eXAiOiJKV1Qi...`)
-   `HIFE_API_URL`: URL base de la API (default: `https://middleware.hife.es/api`)
-   `HIFE_CLIENT_ID`: Client ID (default: `33798`)
-   `HIFE_APP_VERSION`: Versión de la app (default: `2.0.8`)

#### Estaciones

-   `ORIGIN_ID`: ID numérico de la estación de origen (sin ceros iniciales)
-   `ORIGIN_STOP_CODE`: Código de parada de origen (con ceros iniciales, ej: `0012`)
-   `DESTINATION_ID`: ID numérico de la estación de destino
-   `DESTINATION_STOP_CODE`: Código de parada de destino (ej: `0007`)

#### Horarios

-   `OUTWARD_TIME_DEFAULT`: Hora por defecto para ida (formato: `HH:MM`)
-   `OUTWARD_TIME_MONDAY`, `OUTWARD_TIME_TUESDAY`, etc.: Horarios específicos por día
-   `RETURN_TIME_DEFAULT`: Hora por defecto para vuelta
-   `RETURN_TIME_MONDAY`, etc.: Horarios específicos por día

#### Notificaciones

-   `NOTIFICATION_ADVANCE_MINUTES`: Minutos de antelación para notificar (default: `120`)
-   `CHECK_INTERVAL_MINUTES`: Intervalo de revisión en minutos (default: `10`)

#### Bono

-   `BONUS_ID`: ID del bono a utilizar (default: `19` para MITMA Joven)

### Autenticación Automática

El bot obtiene automáticamente el token JWT necesario usando tus credenciales de HIFE a través de la API de OAuth. No necesitas obtener el token manualmente.

**Nota**: El token JWT tiene una validez de aproximadamente 30 días. Si el token expira, simplemente ejecuta `python setup_wizard.py` nuevamente para obtener uno nuevo.

## 🐛 Solución de Problemas

### El bot no inicia

-   Verifica que todas las variables en `.env` estén configuradas
-   Ejecuta `python main.py` para ver los errores específicos
-   Si el token JWT expiró, ejecuta `python setup_wizard.py` nuevamente para obtener uno nuevo
-   Verifica que tus credenciales de HIFE sean correctas

### No recibo notificaciones

-   Verifica que `TELEGRAM_USER_ID` sea correcto (habla con [@userinfobot](https://t.me/userinfobot))
-   Comprueba que el bot esté ejecutándose (`python main.py`)
-   Revisa los logs para ver si hay errores

### Error al comprar billetes

-   Verifica que tengas saldo suficiente en tu bono
-   Comprueba que el `BONUS_ID` sea correcto
-   Asegúrate de que los códigos de parada (`ORIGIN_STOP_CODE`, `DESTINATION_STOP_CODE`) sean correctos
-   Revisa los logs para más detalles del error

### Los horarios no coinciden

-   Los IDs de viaje pueden cambiar con el tiempo
-   Ejecuta `python setup_wizard.py` nuevamente para actualizar los IDs
-   O edita manualmente los valores en `.env`

## 📁 Estructura del Proyecto

```
hife-bot/
├── main.py              # Punto de entrada principal
├── androidapi.py        # Lógica principal del bot y API de HIFE
├── config.py            # Configuración centralizada
├── setup_wizard.py      # Asistente de configuración interactivo
├── requirements.txt     # Dependencias de Python
├── env.example          # Ejemplo de archivo de configuración
├── .gitignore          # Archivos ignorados por Git
├── .env                # Archivo de configuración (no se incluye en Git)
└── README.md           # Este archivo
```

## 🔒 Seguridad

-   **NUNCA** compartas tu archivo `.env` o lo subas a Git
-   El archivo `.env` está en `.gitignore` por defecto
-   Mantén tu token JWT seguro y no lo compartas
-   Si comprometes tu token, cámbialo inmediatamente

## 📝 Licencia

Este proyecto está bajo la licencia MIT. Ver el archivo [LICENSE](LICENSE) para más detalles.

## ⚠️ Descargo de Responsabilidad

Este bot es un proyecto **no oficial** y **no está afiliado** de ninguna manera con HIFE.es.

-   Úsalo bajo tu propia responsabilidad
-   Los autores no se hacen responsables de cualquier problema derivado del uso de esta herramienta
-   Este bot está diseñado para uso personal y educativo
-   Respeta los términos de servicio de HIFE.es

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Si deseas mejorar este bot:

1. Haz un fork del repositorio
2. Crea una rama para tu característica (`git checkout -b feature/amazing-feature`)
3. Haz commit de tus cambios (`git commit -m 'Add some amazing feature'`)
4. Haz push a la rama (`git push origin feature/amazing-feature`)
5. Abre un Pull Request

## 📞 Soporte

Si encuentras algún problema o tienes preguntas:

1. Revisa la sección de [Solución de Problemas](#-solución-de-problemas)
2. Abre un [Issue](https://github.com/tu-usuario/hife-bot/issues) en GitHub
3. Revisa los logs del bot para más información

## 🙏 Agradecimientos

-   A HIFE.es por proporcionar la API pública
-   A la comunidad de Python y Telegram por las excelentes librerías

---

⭐ Si este proyecto te resulta útil, considera darle una estrella en GitHub
