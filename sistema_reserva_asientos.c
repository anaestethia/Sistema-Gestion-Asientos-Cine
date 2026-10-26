#include <stdio.h>
#include <stdlib.h>

#define FILAS 5
#define COLUMNAS 8

/*
 * Función: leerEntero
 * Descripción: lee una línea y valida que contenga un número entero.
 * Entrada: mensaje para el usuario y dirección donde guardar el valor.
 * Salida: devuelve 1 si leyó un entero válido o 0 si se terminó la entrada.
 */
int leerEntero(const char *mensaje, int *valor) {
    char linea[100];
    char *fin;
    long numero;
    int indice;
    int tieneNuevaLinea = 0;

    while (1) {
        printf("%s", mensaje);
        fflush(stdout);

        if (fgets(linea, sizeof(linea), stdin) == NULL) {
            return 0;
        }

        for (indice = 0; linea[indice] != '\0'; indice++) {
            if (linea[indice] == '\n') {
                tieneNuevaLinea = 1;
                break;
            }
        }

        if (!tieneNuevaLinea && !feof(stdin)) {
            int caracter;
            while ((caracter = getchar()) != '\n' && caracter != EOF) {
                /* Descarta el resto de una línea demasiado larga. */
            }
            printf("Entrada demasiado larga. Intente nuevamente.\n");
            tieneNuevaLinea = 0;
            continue;
        }

        numero = strtol(linea, &fin, 10);
        while (*fin == ' ' || *fin == '\t' || *fin == '\n' || *fin == '\r') {
            fin++;
        }

        if (fin == linea || *fin != '\0' || numero < -30000L || numero > 30000L) {
            printf("Entrada inválida. Ingrese un número entero.\n");
            tieneNuevaLinea = 0;
            continue;
        }

        *valor = (int) numero;
        return 1;
    }
}

/*
 * Función: inicializarSala
 * Descripción: inicializa la sala con todos los asientos disponibles.
 * Entrada: matriz 2D de caracteres que representa la sala.
 * Salida: no retorna valor, pero deja la sala con '[L]' en cada posición.
 */
void inicializarSala(char sala[FILAS][COLUMNAS]) {
    int fila, columna;

    for (fila = 0; fila < FILAS; fila++) {
        for (columna = 0; columna < COLUMNAS; columna++) {
            sala[fila][columna] = 'L';
        }
    }
}

/*
 * Función: mostrarSala
 * Descripción: imprime el mapa de la sala con índices de filas y columnas.
 * Entrada: matriz 2D de caracteres que representa la sala.
 * Salida: muestra el estado actual de los asientos por consola.
 */
void mostrarSala(char sala[FILAS][COLUMNAS]) {
    int fila, columna;

    printf("\n==============================");
    printf("\n     MAPA DE LA SALA\n");
    printf("==============================\n");
    printf("      ");

    for (columna = 0; columna < COLUMNAS; columna++) {
        printf("%3d ", columna + 1);
    }
    printf("\n");

    for (fila = 0; fila < FILAS; fila++) {
        printf("Fila %2d |", fila + 1);

        for (columna = 0; columna < COLUMNAS; columna++) {
            if (sala[fila][columna] == 'L') {
                printf(" [L]");
            } else {
                printf(" [X]");
            }
        }

        printf("\n");
    }

    printf("\nLeyenda: [L] = libre, [X] = ocupado\n");
    printf("==============================\n");
}

/*
 * Función: reservarAsiento
 * Descripción: intenta reservar un asiento validando fila, columna y disponibilidad.
 * Entrada: matriz 2D, fila y columna elegidas por el usuario.
 * Salida: devuelve 1 si la reserva fue exitosa, 0 si falló por validación o asiento ocupado.
 */
int reservarAsiento(char sala[FILAS][COLUMNAS], int fila, int columna) {
    if (fila < 1 || fila > FILAS || columna < 1 || columna > COLUMNAS) {
        printf("Error: la fila y la columna deben estar dentro del rango de la sala.\n");
        return 0;
    }

    if (sala[fila - 1][columna - 1] == 'X') {
        printf("Error: el asiento seleccionado ya está ocupado.\n");
        return 0;
    }

    sala[fila - 1][columna - 1] = 'X';
    printf("Reserva realizada con éxito. Asiento Fila %d, Columna %d reservado.\n",
           fila, columna);
    return 1;
}

/*
 * Función: liberarAsiento
 * Descripción: libera un asiento ocupado validando la ubicación ingresada.
 * Entrada: matriz 2D, fila y columna seleccionadas por el usuario.
 * Salida: devuelve 1 si se liberó correctamente, 0 si la validación falla o el asiento ya estaba libre.
 */
int liberarAsiento(char sala[FILAS][COLUMNAS], int fila, int columna) {
    if (fila < 1 || fila > FILAS || columna < 1 || columna > COLUMNAS) {
        printf("Error: la fila y la columna deben estar dentro del rango de la sala.\n");
        return 0;
    }

    if (sala[fila - 1][columna - 1] == 'L') {
        printf("Error: el asiento seleccionado ya está libre.\n");
        return 0;
    }

    sala[fila - 1][columna - 1] = 'L';
    printf("Asiento liberado con éxito. Fila %d, Columna %d ahora está disponible.\n",
           fila, columna);
    return 1;
}

/*
 * Función: mostrarMenu
 * Descripción: muestra las opciones del menú principal del sistema.
 * Entrada: ninguna.
 * Salida: imprime el menú por consola.
 */
void mostrarMenu(void) {
    printf("\n===== SISTEMA DE RESERVA DE ASIENTOS =====\n");
    printf("1. Ver mapa de la sala\n");
    printf("2. Reservar asiento\n");
    printf("3. Liberar asiento\n");
    printf("4. Salir\n");
    printf("========================================\n");
    printf("Seleccione una opción: ");
}

/*
 * Función: main
 * Descripción: controla el flujo principal del programa, ejecutando un menú iterativo.
 * Entrada: argumentos estándar del programa.
 * Salida: código de terminación del programa.
 */
int main(void) {
    char sala[FILAS][COLUMNAS];
    int opcion = 0;
    int fila, columna;
    int continuar = 1;

    inicializarSala(sala);

    printf("Bienvenido al sistema de reserva de asientos.\n");

    while (continuar) {
        mostrarMenu();
        if (!leerEntero("", &opcion)) {
            printf("\nFin de la entrada. El sistema se cerrará.\n");
            break;
        }

        switch (opcion) {
            case 1:
                mostrarSala(sala);
                break;

            case 2:
                if (!leerEntero("Ingrese la fila (1-5): ", &fila) ||
                    !leerEntero("Ingrese la columna (1-8): ", &columna)) {
                    printf("\nFin de la entrada. El sistema se cerrará.\n");
                    continuar = 0;
                    break;
                }
                reservarAsiento(sala, fila, columna);
                break;

            case 3:
                if (!leerEntero("Ingrese la fila (1-5): ", &fila) ||
                    !leerEntero("Ingrese la columna (1-8): ", &columna)) {
                    printf("\nFin de la entrada. El sistema se cerrará.\n");
                    continuar = 0;
                    break;
                }
                liberarAsiento(sala, fila, columna);
                break;

            case 4:
                printf("Gracias por usar el sistema de reservas. Hasta pronto.\n");
                continuar = 0;
                break;

            default:
                printf("Opción inválida. Intente nuevamente.\n");
                break;
        }
    }

    return 0;
}
