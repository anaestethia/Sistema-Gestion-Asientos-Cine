# Sistema de Gestión y Reserva de Cine

Aplicación de escritorio multiplataforma, desarrollada en Python y Tkinter, para administrar salas de cine y gestionar reservas de asientos.

## Funcionalidades

- Mapa visual e interactivo con pantalla, filas y columnas.
- Reservar asientos disponibles con número de ticket.
- Consultar y liberar reservas existentes.
- Crear salas y editar película, filas y asientos por fila.
- Evitar reducciones de sala que eliminarían asientos reservados.
- Persistencia automática en JSON y validación de los datos al cargar.
- Ejecutable independiente para Windows mediante PyInstaller.

## Requisitos

- Python 3.10 o posterior.
- Tkinter, incluido en las instalaciones estándar de Python para Windows y macOS. En Linux puede requerir el paquete del sistema `python3-tk`.

## Ejecutar desde el código fuente

Desde la carpeta del proyecto:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
python -m cine_reservas
```

En Linux o macOS, activa el entorno con `source .venv/bin/activate`. También puedes iniciar la versión fuente en Windows haciendo doble clic en `ejecutar.bat`.

La aplicación no necesita paquetes de terceros para funcionar desde Python. La primera ejecución crea `cine_data.json` con una sala de ejemplo.

## Ejecutar pruebas y lint

Instala las herramientas de desarrollo y ejecuta las validaciones:

```powershell
python -m pip install -e ".[dev]"
ruff check .
pytest
```

La integración continua ejecuta lint y pruebas en Windows y Ubuntu, con Python 3.10, 3.12 y 3.13.

## Crear el ejecutable de Windows

Con Python instalado, ejecuta desde PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\build.ps1
```

El script instala PyInstaller dentro del entorno virtual y produce `dist\GestionAsientosCine.exe`. La primera compilación requiere conexión a Internet. El ejecutable no requiere que Python esté instalado en el equipo de destino.

Inicia el ejecutable haciendo doble clic o con `ejecutar.bat`.

## Datos y copias de seguridad

La aplicación guarda salas y reservas en `cine_data.json`, junto al directorio del proyecto en modo fuente o junto al ejecutable dentro de `dist`. El JSON se excluye de Git para no publicar datos locales. Conserva una copia de ese archivo para respaldar las reservas.

## Estructura del proyecto

```text
.
├── .github/workflows/ci.yml
├── launcher.py
├── pyproject.toml
├── src/cine_reservas/
│   ├── __init__.py
│   ├── __main__.py
│   ├── app.py
│   └── data_store.py
└── tests/
    └── test_data_store.py
```

## Límites de configuración

Cada sala permite entre 1 y 30 filas y entre 1 y 30 asientos por fila. Una sala no se puede reducir si conserva reservas fuera de las nuevas dimensiones.
