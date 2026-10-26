# Sistema de Reserva de Asientos

Este proyecto implementa un sistema interactivo de reserva de asientos para una sala de cine o teatro, desarrollado en lenguaje C y orientado a consola (CLI). El programa permite visualizar la sala, reservar asientos disponibles y liberar asientos ocupados.

## Características

- Sala representada como una matriz de 5 filas por 8 columnas.
- Los asientos libres se muestran como `[L]`.
- Los asientos ocupados se muestran como `[X]`.
- Menú interactivo en consola con las siguientes opciones:
  1. Ver mapa de la sala.
  2. Reservar asiento.
  3. Liberar asiento.
  4. Salir.
- Validaciones de rango y disponibilidad.
- Mensajes claros para confirmar acciones o informar errores.
- Programación estructurada con funciones modularizadas.

## Estructura del código

El programa está dividido en funciones principales:

- `inicializarSala`: crea la sala con todos los asientos libres.
- `mostrarSala`: imprime el estado actual de la sala con índices.
- `reservarAsiento`: valida y reserva un asiento disponible.
- `liberarAsiento`: valida y libera un asiento ocupado.
- `main`: controla el menú principal y la lógica general del programa.

## Requisitos

- Compilador de C (por ejemplo, GCC).
- Sistema operativo con consola o terminal.

## Compilación

Ejecuta el siguiente comando desde la carpeta del proyecto:

```bash
gcc -std=c11 -Wall -Wextra -pedantic sistema_reserva_asientos.c -o sistema_reserva_asientos
```

Si el compilador no está instalado en Ubuntu/Debian, puedes instalarlo con:

```bash
sudo apt update
sudo apt install build-essential
```

## Ejecución

En Linux y macOS:

```bash
./sistema_reserva_asientos
```

En Windows (con GCC/MinGW), compila con:

```bash
gcc -std=c11 -Wall -Wextra -pedantic sistema_reserva_asientos.c -o sistema_reserva_asientos.exe
```

Y luego inicia el programa con:

```text
sistema_reserva_asientos.exe
```

## Uso

Al ejecutar el programa aparecerá un menú con las opciones disponibles. Puedes:

- ver el mapa completo de la sala,
- seleccionar una fila y columna para reservar un asiento,
- liberar un asiento previamente ocupado,
- o salir del sistema.

Los números deben ingresarse como enteros. Si se recibe una entrada inválida o se termina la entrada estándar, el programa informa el problema y permite reintentar o finaliza ordenadamente.

## Ejemplo de salida

```text
===== SISTEMA DE RESERVA DE ASIENTOS =====
1. Ver mapa de la sala
2. Reservar asiento
3. Liberar asiento
4. Salir
========================================
Seleccione una opción: 1

==============================
     MAPA DE LA SALA
==============================
      1   2   3   4   5   6   7   8
Fila  1 | [L] [L] [L] [L] [L] [L] [L] [L]
...
```

## Nota

Este proyecto usa únicamente las librerías estándar `stdio.h` y `stdlib.h`. Las reservas se mantienen en memoria mientras el programa está abierto; al cerrarlo, todos los asientos vuelven a estar libres.
