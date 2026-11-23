# Sistema de Gestión y Reserva de Cine

Aplicación de escritorio multiplataforma, desarrollada en Python y Tkinter, para administrar salas de cine y gestionar reservas de asientos. Está implementada con **programación estructurada**, mediante funciones y estado explícito en diccionarios; el código de la aplicación no define clases.

## Funcionalidades

- Mapa visual e interactivo con pantalla, filas y columnas adaptado a salas con distribuci?n variable por fila.
- Configuraci?n de salas con nombre, pel?cula y filas independientes: cada fila puede tener una cantidad distinta de asientos (por ejemplo, 3 filas delanteras de 20 asientos y 4 filas traseras de 30).
- Edici?n de la distribuci?n de filas: agregar filas al final, quitar una fila espec?fica y cambiar la cantidad de asientos de una fila existente.
- Selecci?n de uno o varios asientos y reserva con un mismo n?mero de entrada/ticket.
- Consulta y liberaci?n de reservas existentes.
- Panel oscuro con disponibilidad en tiempo real, resumen de sala y registro de actividad.
- Persistencia autom?tica en SQLite (`cine_data.db`) con esquema relacional aplicado y validaci?n de datos.
- Bloqueo de cambios que afecten reservas ocupadas (no se permite quitar una fila reservada ni reducirla dejando fuera asientos ocupados).
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

La aplicaci?n no necesita paquetes de terceros para funcionar desde Python. La primera ejecuci?n crea `cine_data.db` con una sala de ejemplo y el esquema de base de datos aplicado.

La interfaz ofrece las secciones **Asientos**, **Reservas** y **Actividad**. Selecciona uno o varios asientos verdes y confirma la reserva con un número de entrada; ese número se asigna a todos los asientos seleccionados. Los asientos ocupados se identifican en rojo y permiten consultar o liberar la reserva.

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

La aplicaci?n guarda la informaci?n en `cine_data.db` (SQLite), junto al directorio del proyecto en modo fuente o junto al ejecutable dentro de `dist`. La base de datos local se excluye de Git para no publicar datos reales. Conserva una copia de ese archivo para respaldar las reservas.

### Esquema de base de datos (DER aplicado)

La persistencia usa SQLite con las siguientes tablas, adaptadas del modelo entidad-relaci?n:

- `salas` (`id_sala` PK, `codigo` UNIQUE, `nombre`, `habilitada`).
- `peliculas` (`id_pelicula` PK, `titulo`).
- `filas` (`id_fila` PK, `letra`, `id_sala` FK): cada fila pertenece a una sala y define su propia cantidad de asientos.
- `asientos` (`id_asiento` PK, `numero`, `id_fila` FK).
- `funciones` (`id_funcion` PK, `fecha`, `hora_inicio`, `hora_fin`, `estado` PROGRAMADA/FINALIZADA/CANCELADA, `id_sala` FK, `id_pelicula` FK, `id_funcion_origen` FK opcional).
- `funcion_asientos` (`id_funcion` PK/FK, `id_asiento` PK/FK, `estado` DISPONIBLE/OCUPADO, `ticket`).

Cada sala mantiene su estructura f?sica en `filas` y `asientos` (permitiendo salas no rectangulares), y las reservas de la funci?n activa se registran en `funcion_asientos`.

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

La interfaz está organizada en funciones dentro de `app.py`. `data_store.py` contiene las funciones de validación y persistencia. El estado compartido de la interfaz y del almacenamiento se pasa explícitamente como diccionario.

## Límites de configuración

Cada sala permite entre 1 y 30 filas y entre 1 y 30 asientos por fila. Una sala no se puede reducir si conserva reservas fuera de las nuevas dimensiones.
