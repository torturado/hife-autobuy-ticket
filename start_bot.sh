#!/bin/bash

# ==============================================
# HIFE Bot - Script de inicio
# ==============================================
# Este script permite ejecutar el bot en segundo plano
# en sistemas Linux/Unix, redirigiendo los logs a un archivo.
# Útil para iniciar el bot en servidores o instancias remotas.
# ==============================================

# Configuración
LOG_FILE="bot_output.log"
PID_FILE="bot.pid"

# Función para mostrar mensaje de uso
usage() {
    echo "Uso: $0 {start|stop|status|log}"
    echo ""
    echo "  start  - Inicia el bot en segundo plano"
    echo "  stop   - Detiene el bot"
    echo "  status - Muestra el estado del bot"
    echo "  log    - Muestra los últimos logs en tiempo real"
    echo ""
}

# Función para iniciar el bot
start_bot() {
    echo "Iniciando HIFE Bot..."
    
    # Verificar si el entorno virtual existe y activarlo
    if [ -d "venv" ]; then
        source venv/bin/activate
        echo "Entorno virtual activado"
    else
        echo "Advertencia: Entorno virtual no encontrado, utilizando Python del sistema"
    fi
    
    # Verificar si el archivo .env existe
    if [ ! -f ".env" ]; then
        echo "Error: Archivo .env no encontrado. Por favor ejecuta primero setup_wizard.py"
        echo "  python setup_wizard.py"
        exit 1
    fi
    
    # Verificar si el bot ya está en ejecución
    if [ -f "$PID_FILE" ]; then
        pid=$(cat "$PID_FILE")
        if ps -p "$pid" > /dev/null; then
            echo "Error: El bot ya está en ejecución (PID: $pid)"
            echo "Usa '$0 stop' para detenerlo primero"
            exit 1
        else
            echo "Advertencia: Archivo PID encontrado pero el proceso no existe, eliminando archivo PID obsoleto"
            rm "$PID_FILE"
        fi
    fi
    
    # Iniciar el bot en segundo plano
    echo "Ejecutando main.py..."
    nohup python main.py > "$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"
    sleep 2
    
    # Verificar si el proceso sigue en ejecución
    if ps -p "$(cat $PID_FILE)" > /dev/null; then
        echo "Bot iniciado exitosamente con PID $(cat $PID_FILE)"
        echo "Los logs se están guardando en $LOG_FILE"
        echo "Usa '$0 log' para ver los logs en tiempo real"
    else
        echo "Error: El bot se inició pero se detuvo inesperadamente"
        echo "Revisa los logs en $LOG_FILE para más información"
        rm -f "$PID_FILE"
        exit 1
    fi
}

# Función para detener el bot
stop_bot() {
    if [ -f "$PID_FILE" ]; then
        pid=$(cat "$PID_FILE")
        if ps -p "$pid" > /dev/null; then
            echo "Deteniendo bot (PID: $pid)..."
            kill "$pid"
            sleep 2
            
            # Verificar si se detuvo correctamente
            if ps -p "$pid" > /dev/null; then
                echo "El bot no respondió, forzando cierre..."
                kill -9 "$pid"
                sleep 1
            fi
            
            # Verificar el estado final
            if ps -p "$pid" > /dev/null; then
                echo "Error: No se pudo detener el bot"
            else
                echo "Bot detenido exitosamente"
                rm "$PID_FILE"
            fi
        else
            echo "El bot no está en ejecución, pero se encontró un archivo PID"
            rm "$PID_FILE"
        fi
    else
        echo "El bot no está en ejecución (no se encontró archivo PID)"
    fi
}

# Función para mostrar el estado
show_status() {
    if [ -f "$PID_FILE" ]; then
        pid=$(cat "$PID_FILE")
        if ps -p "$pid" > /dev/null; then
            echo "El bot está en ejecución con PID $pid"
            # Mostrar tiempo de ejecución
            ps -p "$pid" -o etime=
        else
            echo "El bot no está en ejecución, pero se encontró un archivo PID obsoleto"
            rm "$PID_FILE"
        fi
    else
        echo "El bot no está en ejecución"
    fi
}

# Función para mostrar logs
show_log() {
    if [ -f "$LOG_FILE" ]; then
        tail -f "$LOG_FILE"
    else
        echo "No se encontró el archivo de log $LOG_FILE"
    fi
}

# Procesar el comando
case "$1" in
    start)
        start_bot
        ;;
    stop)
        stop_bot
        ;;
    status)
        show_status
        ;;
    log)
        show_log
        ;;
    *)
        usage
        ;;
esac

exit 0 