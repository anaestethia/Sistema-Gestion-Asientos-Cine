@echo off
set "APP_DIR=%~dp0dist"
set "APP_EXE=%APP_DIR%\GestionAsientosCine.exe"

if exist "%APP_EXE%" (
    start "" "%APP_EXE%"
    exit /b 0
)

where python >nul 2>nul
if errorlevel 1 (
    echo No se encontro Python. Instala Python 3 o compila el ejecutable con build.ps1.
    pause
    exit /b 1
)

set "PYTHONPATH=%~dp0src"
python -m cine_reservas
