# 🚌 HIFE Bot

<div align="center">

**Automatización inteligente de compra de billetes de autobús en HIFE.es**

[![Python](https://img.shields.io/badge/Python-3.7+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Telegram](https://img.shields.io/badge/Telegram-Bot-blue.svg)](https://telegram.org/)

[Características](#-características) • [Instalación](#-instalación-rápida) • [Uso](#-uso) • [Configuración](#-configuración) • [Solución de Problemas](#-solución-de-problemas)

</div>

---

## 📋 Tabla de Contenidos

-   [Descripción](#-descripción)
-   [Características](#-características)
-   [Requisitos Previos](#-requisitos-previos)
-   [Instalación Rápida](#-instalación-rápida)
-   [Uso](#-uso)
-   [Configuración](#-configuración)
-   [Solución de Problemas](#-solución-de-problemas)
-   [Estructura del Proyecto](#-estructura-del-proyecto)
-   [Seguridad](#-seguridad)
-   [Contribuciones](#-contribuciones)

---

## 📖 Descripción

**HIFE Bot** es un bot de Telegram que automatiza completamente la compra de billetes de autobús en HIFE.es. El bot monitorea tus horarios configurados y te envía notificaciones cuando es momento de comprar un billete, permitiéndote confirmar o cancelar la compra con un simple clic desde Telegram.

### 🎯 ¿Por qué usar HIFE Bot?

-   ⏰ **Ahorra tiempo**: No más recordatorios manuales ni compras de último momento
-   🤖 **Totalmente automatizado**: Configúralo una vez y olvídate
-   📱 **Control desde Telegram**: Confirma o cancela compras desde tu móvil
-   🎫 **Soporte para bonos**: Compatible con bonos gratuitos (MITMA Joven, etc.)
-   🔔 **Notificaciones inteligentes**: Te avisa con suficiente antelación

---

## ✨ Características

| Característica                       | Descripción                                                 |
| ------------------------------------ | ----------------------------------------------------------- |
| 🤖 **Automatización completa**       | Monitorea horarios y notifica automáticamente               |
| 📱 **Integración con Telegram**      | Notificaciones y confirmaciones mediante bot                |
| ⏰ **Horarios personalizables**      | Configura diferentes horarios para cada día de la semana    |
| 🎫 **Soporte para bonos**            | Compatible con bonos gratuitos de HIFE (MITMA Joven, etc.)  |
| 🔄 **Reintentos automáticos**        | Manejo robusto de errores y reintentos                      |
| 📊 **Logs detallados**               | Sistema de logging completo con Rich para diagnóstico       |
| 🎨 **Interfaz mejorada**             | Asistente de configuración con interfaz de terminal moderna |
| 🔍 **Detección automática de bonos** | Obtiene y muestra bonos disponibles de la API               |

---

## 📋 Requisitos Previos

Antes de comenzar, asegúrate de tener:

-   ✅ **Python 3.7+** instalado
-   ✅ **Cuenta en HIFE.es** con un bono activo
-   ✅ **Bot de Telegram** creado a través de [@BotFather](https://t.me/BotFather)
-   ✅ **Acceso a internet** estable

---

## 🚀 Instalación Rápida

### Paso 1: Clonar el repositorio

```bash
git clone https://github.com/torturado/hife-autobuy-ticket.git
cd hife-autobuy-ticket
```

### Paso 2: Crear entorno virtual (recomendado)

<details>
<summary><strong>Windows</strong></summary>

```bash
python -m venv venv
venv\Scripts\activate
```

</details>

<details>
<summary><strong>Linux/macOS</strong></summary>

```bash
python3 -m venv venv
source venv/bin/activate
```

</details>

### Paso 3: Instalar dependencias

```bash
pip install -r requirements.txt
```

### Paso 4: Configurar el bot

Ejecuta el asistente de configuración interactivo:

```bash
python setup_wizard.py
```

El asistente te guiará paso a paso a través de toda la configuración necesaria.

---

## ⚙️ Configuración

### 🔧 Asistente Interactivo (Recomendado)

El asistente de configuración (`setup_wizard.py`) te guía a través de:

#### 1️⃣ Configuración de Telegram

-   Token del bot (obtener de [@BotFather](https://t.me/BotFather))
-   Tu ID de usuario (obtener de [@userinfobot](https://t.me/userinfobot))

#### 2️⃣ Autenticación en HIFE

-   Email y contraseña de tu cuenta HIFE
-   El sistema obtendrá automáticamente el token JWT necesario

#### 3️⃣ Selección de Estaciones

-   Busca y selecciona tu estación de origen de una lista interactiva
-   Busca y selecciona tu estación de destino de una lista interactiva
-   Los IDs y códigos de parada se obtienen automáticamente de la API

#### 4️⃣ Configuración de Horarios

-   Horarios de ida y vuelta para cada día de la semana
-   Puedes usar un horario por defecto o configurar horarios específicos por día
-   Minutos de antelación para notificaciones

#### 5️⃣ Configuración de Bono

-   **Nuevo**: El asistente obtiene automáticamente los bonos disponibles de la API
-   Selecciona tu bono de una lista interactiva o ingresa el ID manualmente
-   Detecta automáticamente tu bono activo y lo destaca en la selección

### 📝 Configuración Manual (Opcional)

Si prefieres configurar manualmente:

```bash
cp env.example .env
```

Edita el archivo `.env` con tus valores. Ver `env.example` para todas las variables disponibles.

---

## 📖 Uso

### Iniciar el bot

```bash
python main.py
```

El bot se ejecutará y mostrará un banner de inicio con toda tu configuración. El bot:

-   🔄 Revisará los horarios cada 10 minutos (configurable)
-   🔔 Te enviará notificaciones cuando falten ~2 horas para un viaje
-   ✅ Te permitirá confirmar o cancelar la compra desde Telegram

### 📱 Ejemplo de Flujo

```
1. ⏰ El bot detecta que faltan 2 horas para tu viaje de ida a las 06:45
   ↓
2. 📱 Te envía un mensaje en Telegram:
   "❓ ¿Compro el billete de ida para hoy a las 06:45?"
   ↓
3. 🎯 Tú respondes con "✅ Comprar" o "❌ Ignorar"
   ↓
4. 🤖 Si confirmas, el bot ejecuta la compra automáticamente
   ↓
5. ✅ Recibes confirmación del éxito o error de la compra
```

---

## 🔧 Configuración Avanzada

### Variables de Entorno

El bot usa variables de entorno desde el archivo `.env`. Aquí están las principales:

#### 📱 Telegram

| Variable           | Descripción                  | Ejemplo                                |
| ------------------ | ---------------------------- | -------------------------------------- |
| `TELEGRAM_TOKEN`   | Token del bot de Telegram    | `123456789:ABCdefGHIjklMNOpqrsTUVwxyz` |
| `TELEGRAM_USER_ID` | Tu ID de usuario de Telegram | `123456789`                            |

#### 🔐 HIFE API

| Variable           | Descripción                | Valor por Defecto                |
| ------------------ | -------------------------- | -------------------------------- |
| `HIFE_AUTH_TOKEN`  | Token JWT de autenticación | -                                |
| `HIFE_API_URL`     | URL base de la API         | `https://middleware.hife.es/api` |
| `HIFE_CLIENT_ID`   | Client ID                  | `33798`                          |
| `HIFE_APP_VERSION` | Versión de la app          | `2.0.8`                          |

#### 🚉 Estaciones

| Variable                | Descripción                             | Ejemplo   |
| ----------------------- | --------------------------------------- | --------- |
| `ORIGIN_ID`             | ID numérico de la estación de origen    | `12`      |
| `ORIGIN_STOP_CODE`      | Código de parada de origen (con ceros)  | `0012`    |
| `ORIGIN_NAME`           | Nombre de la estación de origen         | `VINARÒS` |
| `DESTINATION_ID`        | ID numérico de la estación de destino   | `7`       |
| `DESTINATION_STOP_CODE` | Código de parada de destino (con ceros) | `0007`    |
| `DESTINATION_NAME`      | Nombre de la estación de destino        | `AMPOSTA` |

#### ⏰ Horarios

**Horarios de Ida:**

-   `OUTWARD_TIME_DEFAULT`: Hora por defecto (formato: `HH:MM`)
-   `OUTWARD_TIME_MONDAY`, `OUTWARD_TIME_TUESDAY`, etc.: Horarios específicos por día

**Horarios de Vuelta:**

-   `RETURN_TIME_DEFAULT`: Hora por defecto (formato: `HH:MM`)
-   `RETURN_TIME_MONDAY`, `RETURN_TIME_TUESDAY`, etc.: Horarios específicos por día

#### 🔔 Notificaciones

| Variable                       | Descripción                          | Valor por Defecto |
| ------------------------------ | ------------------------------------ | ----------------- |
| `NOTIFICATION_ADVANCE_MINUTES` | Minutos de antelación para notificar | `120` (2 horas)   |
| `CHECK_INTERVAL_MINUTES`       | Intervalo de revisión en minutos     | `10`              |

#### 🎫 Bono

| Variable   | Descripción            | Valor por Defecto  |
| ---------- | ---------------------- | ------------------ |
| `BONUS_ID` | ID del bono a utilizar | `19` (MITMA Joven) |

### 🔑 Autenticación Automática

El bot obtiene automáticamente el token JWT necesario usando tus credenciales de HIFE a través de la API de OAuth. No necesitas obtener el token manualmente.

> **💡 Nota**: El token JWT tiene una validez de aproximadamente 30 días. Si el token expira, simplemente ejecuta `python setup_wizard.py` nuevamente para obtener uno nuevo.

---

## 🐛 Solución de Problemas

### ❌ El bot no inicia

**Síntomas**: El bot muestra errores al iniciar o no se ejecuta.

**Soluciones**:

-   ✅ Verifica que todas las variables en `.env` estén configuradas
-   ✅ Ejecuta `python main.py` para ver los errores específicos
-   ✅ Si el token JWT expiró, ejecuta `python setup_wizard.py` nuevamente
-   ✅ Verifica que tus credenciales de HIFE sean correctas

### 📱 No recibo notificaciones

**Síntomas**: El bot está ejecutándose pero no recibes notificaciones.

**Soluciones**:

-   ✅ Verifica que `TELEGRAM_USER_ID` sea correcto (habla con [@userinfobot](https://t.me/userinfobot))
-   ✅ Comprueba que el bot esté ejecutándose (`python main.py`)
-   ✅ Revisa los logs para ver si hay errores
-   ✅ Verifica que los horarios estén configurados correctamente

### 💳 Error al comprar billetes

**Síntomas**: El bot intenta comprar pero falla.

**Soluciones**:

-   ✅ Verifica que tengas saldo suficiente en tu bono
-   ✅ Comprueba que el `BONUS_ID` sea correcto
-   ✅ Asegúrate de que los códigos de parada (`ORIGIN_STOP_CODE`, `DESTINATION_STOP_CODE`) sean correctos
-   ✅ Revisa los logs para más detalles del error
-   ✅ Verifica que el bono no haya expirado

### ⏰ Los horarios no coinciden

**Síntomas**: El bot no encuentra los viajes en los horarios configurados.

**Soluciones**:

-   ✅ Los IDs de viaje pueden cambiar con el tiempo
-   ✅ Ejecuta `python setup_wizard.py` nuevamente para actualizar la configuración
-   ✅ O edita manualmente los valores en `.env`

### 🔄 Error: "Conflict: terminated by other getUpdates request"

**Síntomas**: Aparece un error de conflicto al iniciar el bot.

**Soluciones**:

-   ✅ Cierra todas las instancias del bot que estén ejecutándose
-   ✅ Asegúrate de que solo haya una instancia corriendo
-   ✅ Si usas webhooks, elimínalos ejecutando el bot con `deleteWebhook=True`

---

## 📁 Estructura del Proyecto

```
hife-bot/
├── 📄 main.py              # Punto de entrada principal
├── 🤖 androidapi.py        # Lógica principal del bot y API de HIFE
├── ⚙️  config.py            # Configuración centralizada
├── 🧙 setup_wizard.py      # Asistente de configuración interactivo
├── 📦 requirements.txt     # Dependencias de Python
├── 📋 env.example          # Ejemplo de archivo de configuración
├── 🚫 .gitignore          # Archivos ignorados por Git
├── 🔐 .env                # Archivo de configuración (no se incluye en Git)
└── 📖 README.md           # Este archivo
```

---

## 🔒 Seguridad

> ⚠️ **IMPORTANTE**: Sigue estas prácticas de seguridad

-   🔐 **NUNCA** compartas tu archivo `.env` o lo subas a Git
-   🔐 El archivo `.env` está en `.gitignore` por defecto
-   🔐 Mantén tu token JWT seguro y no lo compartas
-   🔐 Si comprometes tu token, cámbialo inmediatamente ejecutando `setup_wizard.py` nuevamente
-   🔐 No compartas capturas de pantalla que muestren tokens o credenciales

---

## 📝 Licencia

Este proyecto está bajo la licencia **MIT**. Ver el archivo [LICENSE](LICENSE) para más detalles.

---

## ⚠️ Descargo de Responsabilidad

Este bot es un proyecto **no oficial** y **no está afiliado** de ninguna manera con HIFE.es.

-   ⚠️ Úsalo bajo tu propia responsabilidad
-   ⚠️ Los autores no se hacen responsables de cualquier problema derivado del uso de esta herramienta
-   ⚠️ Este bot está diseñado para uso personal y educativo
-   ⚠️ Respeta los términos de servicio de HIFE.es

---

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Si deseas mejorar este bot:

1. 🍴 Haz un fork del repositorio
2. 🌿 Crea una rama para tu característica (`git checkout -b feature/amazing-feature`)
3. 💾 Haz commit de tus cambios (`git commit -m 'Add some amazing feature'`)
4. 📤 Haz push a la rama (`git push origin feature/amazing-feature`)
5. 🔄 Abre un Pull Request

### 🎯 Áreas donde puedes contribuir

-   🐛 Reportar bugs
-   💡 Sugerir nuevas características
-   📝 Mejorar la documentación
-   🔧 Optimizar el código
-   🎨 Mejorar la interfaz de terminal

---

## 📞 Soporte

Si encuentras algún problema o tienes preguntas:

1. 📖 Revisa la sección de [Solución de Problemas](#-solución-de-problemas)
2. 🐛 Abre un [Issue](https://github.com/torturado/hife-autobuy-ticket/issues) en GitHub
3. 📊 Revisa los logs del bot para más información

---

## 🙏 Agradecimientos

-   🙏 A la comunidad de **Python** y **Telegram** por las excelentes librerías

---

<div align="center">

**⭐ Si este proyecto te resulta útil, considera darle una estrella en GitHub**

Hecho con ❤️ para la comunidad

</div>
