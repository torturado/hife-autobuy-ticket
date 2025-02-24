@echo off
:: ==============================================
:: HIFE Bot - Script de inicio para Windows
:: ==============================================
:: Este script permite ejecutar el bot en segundo plano
:: en sistemas Windows, redirigiendo los logs a un archivo.
:: ==============================================

setlocal enabledelayedexpansion

:: Configuración
set LOG_FILE=bot_output.log
set PID_FILE=bot.pid

:: Verificar argumentos
if "%1"=="" goto :usage
if "%1"=="start" goto :start_bot
if "%1"=="stop" goto :stop_bot
if "%1"=="status" goto :status
if "%1"=="log" goto :show_log
goto :usage

:usage
echo Uso: %0 {start^|stop^|status^|log}
echo.
echo   start  - Inicia el bot en segundo plano
echo   stop   - Detiene el bot
echo   status - Muestra el estado del bot
echo   log    - Muestra los últimos logs
echo.
goto :end

:start_bot
echo Iniciando HIFE Bot...

:: Verificar si el entorno virtual existe y activarlo
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
    echo Entorno virtual activado
) else (
    echo Advertencia: Entorno virtual no encontrado, utilizando Python del sistema
)

:: Verificar si el archivo .env existe
if not exist .env (
    echo Error: Archivo .env no encontrado. Por favor ejecuta primero setup_wizard.py
    echo   python setup_wizard.py
    goto :end
)

:: Verificar si el bot ya está en ejecución
if exist %PID_FILE% (
    for /f %%i in (%PID_FILE%) do set pid=%%i
    
    :: Comprobar si el proceso sigue activo
    tasklist /fi "PID eq !pid!" /NH | findstr "!pid!" > nul
    if not errorlevel 1 (
        echo Error: El bot ya está en ejecución (PID: !pid!)
        echo Usa '%0 stop' para detenerlo primero
        goto :end
    ) else (
        echo Advertencia: Archivo PID encontrado pero el proceso no existe, eliminando archivo PID obsoleto
        del %PID_FILE% > nul
    )
)

:: Iniciar el bot en segundo plano usando start
echo Ejecutando main.py...
start /B pythonw main.py > %LOG_FILE% 2>&1

:: Obtener el PID del proceso
for /f "tokens=2" %%a in ('tasklist /nh /fi "IMAGENAME eq pythonw.exe" ^| findstr /i "pythonw.exe"') do (
    set pid=%%a
    goto :got_pid
)

:got_pid
:: Guardar el PID en el archivo
echo !pid! > %PID_FILE%
echo Bot iniciado exitosamente con PID !pid!
echo Los logs se están guardando en %LOG_FILE%
echo Usa '%0 log' para ver los logs
goto :end

:stop_bot
if not exist %PID_FILE% (
    echo El bot no está en ejecución (no se encontró archivo PID)
    goto :end
)

for /f %%i in (%PID_FILE%) do set pid=%%i
echo Deteniendo bot (PID: !pid!)...

:: Intentar cerrar el proceso
taskkill /PID !pid! /F > nul 2>&1
if errorlevel 1 (
    echo Error: No se pudo detener el bot
) else (
    echo Bot detenido exitosamente
    del %PID_FILE% > nul
)
goto :end

:status
if not exist %PID_FILE% (
    echo El bot no está en ejecución
    goto :end
)

for /f %%i in (%PID_FILE%) do set pid=%%i
tasklist /fi "PID eq !pid!" /NH | findstr "!pid!" > nul
if errorlevel 1 (
    echo El bot no está en ejecución, pero se encontró un archivo PID obsoleto
    del %PID_FILE% > nul
) else (
    echo El bot está en ejecución con PID !pid!
)
goto :end

:show_log
if not exist %LOG_FILE% (
    echo No se encontró el archivo de log %LOG_FILE%
    goto :end
)
type %LOG_FILE%
goto :end

:end
endlocal 