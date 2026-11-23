"""Funciones de validación y persistencia usando SQLite (DER adaptado)."""

import sqlite3
from datetime import date
from pathlib import Path
from typing import Any

MAX_FILAS = 30
MAX_ASIENTOS_POR_FILA = 30
STORE_PATH = "path"

DEFAULT_ROOM_CODE = "SALA-1"
DEFAULT_ROOM_NAME = "Sala 1 - Principal"
DEFAULT_MOVIE = "Inception"
DEFAULT_ROWS = 5
DEFAULT_SEATS_PER_ROW = 8


def _connect(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _initialize_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS salas (
            id_sala INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo VARCHAR NOT NULL UNIQUE,
            nombre VARCHAR NOT NULL,
            habilitada BOOLEAN NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS peliculas (
            id_pelicula INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo VARCHAR NOT NULL UNIQUE
        );
        CREATE TABLE IF NOT EXISTS filas (
            id_fila INTEGER PRIMARY KEY AUTOINCREMENT,
            letra CHAR NOT NULL,
            id_sala INTEGER NOT NULL REFERENCES salas(id_sala) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS asientos (
            id_asiento INTEGER PRIMARY KEY AUTOINCREMENT,
            numero INTEGER NOT NULL,
            id_fila INTEGER NOT NULL REFERENCES filas(id_fila) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS funciones (
            id_funcion INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha DATE NOT NULL,
            hora_inicio TIME NOT NULL,
            hora_fin TIME NOT NULL,
            estado TEXT NOT NULL CHECK (estado IN ('PROGRAMADA', 'FINALIZADA', 'CANCELADA')),
            id_sala INTEGER NOT NULL REFERENCES salas(id_sala) ON DELETE CASCADE,
            id_pelicula INTEGER NOT NULL REFERENCES peliculas(id_pelicula),
            id_funcion_origen INTEGER NULL REFERENCES funciones(id_funcion)
        );
        CREATE TABLE IF NOT EXISTS funcion_asientos (
            id_funcion INTEGER NOT NULL REFERENCES funciones(id_funcion) ON DELETE CASCADE,
            id_asiento INTEGER NOT NULL REFERENCES asientos(id_asiento) ON DELETE CASCADE,
            estado TEXT NOT NULL CHECK (estado IN ('DISPONIBLE', 'OCUPADO')),
            ticket TEXT,
            PRIMARY KEY (id_funcion, id_asiento)
        );
        """
    )


def _row_label(index: int) -> str:
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    if index < 26:
        return letters[index]
    return letters[index // 26 - 1] + letters[index % 26]


def _ensure_pelicula(connection: sqlite3.Connection, titulo: str) -> int:
    row = connection.execute(
        "SELECT id_pelicula FROM peliculas WHERE titulo = ?",
        (titulo,),
    ).fetchone()
    if row:
        return int(row["id_pelicula"])
    cursor = connection.execute("INSERT INTO peliculas (titulo) VALUES (?)", (titulo,))
    return int(cursor.lastrowid)


def _create_seating(
    connection: sqlite3.Connection, sala_id: int, filas_asientos: list[int]
) -> list[int]:
    fila_ids: list[int] = []
    for row_index, asientos in enumerate(filas_asientos):
        cursor = connection.execute(
            "INSERT INTO filas (letra, id_sala) VALUES (?, ?)",
            (_row_label(row_index), sala_id),
        )
        fila_id = int(cursor.lastrowid)
        fila_ids.append(fila_id)
        connection.executemany(
            "INSERT INTO asientos (numero, id_fila) VALUES (?, ?)",
            [(seat + 1, fila_id) for seat in range(int(asientos))],
        )
    return fila_ids


def _active_function_id(connection: sqlite3.Connection, sala_id: int) -> int | None:
    row = connection.execute(
        """
        SELECT id_funcion
        FROM funciones
        WHERE id_sala = ? AND estado = 'PROGRAMADA'
        ORDER BY fecha DESC, hora_inicio DESC, id_funcion DESC
        LIMIT 1
        """,
        (sala_id,),
    ).fetchone()
    if row:
        return int(row["id_funcion"])
    row = connection.execute(
        """
        SELECT id_funcion
        FROM funciones
        WHERE id_sala = ?
        ORDER BY id_funcion DESC
        LIMIT 1
        """,
        (sala_id,),
    ).fetchone()
    return int(row["id_funcion"]) if row else None


def _ensure_active_function(connection: sqlite3.Connection, sala_id: int, pelicula_id: int) -> int:
    function_id = _active_function_id(connection, sala_id)
    if function_id is not None:
        return function_id
    today = date.today().isoformat()
    cursor = connection.execute(
        """
        INSERT INTO funciones
            (fecha, hora_inicio, hora_fin, estado, id_sala, id_pelicula, id_funcion_origen)
        VALUES (?, '19:30', '21:30', 'PROGRAMADA', ?, ?, NULL)
        """,
        (today, sala_id, pelicula_id),
    )
    function_id = int(cursor.lastrowid)
    connection.execute(
        """
        INSERT INTO funcion_asientos (id_funcion, id_asiento, estado, ticket)
        SELECT ?, a.id_asiento, 'DISPONIBLE', NULL
        FROM asientos a
        JOIN filas f ON f.id_fila = a.id_fila
        WHERE f.id_sala = ?
        ORDER BY f.id_fila, a.numero
        """,
        (function_id, sala_id),
    )
    return function_id


def _sync_function_seats(connection: sqlite3.Connection, function_id: int, sala_id: int) -> None:
    connection.execute(
        """
        INSERT INTO funcion_asientos (id_funcion, id_asiento, estado, ticket)
        SELECT ?, a.id_asiento, 'DISPONIBLE', NULL
        FROM asientos a
        JOIN filas f ON f.id_fila = a.id_fila
        WHERE f.id_sala = ?
          AND NOT EXISTS (
              SELECT 1 FROM funcion_asientos fa
              WHERE fa.id_funcion = ? AND fa.id_asiento = a.id_asiento
          )
        """,
        (function_id, sala_id, function_id),
    )


def _create_room(
    connection: sqlite3.Connection,
    codigo: str,
    nombre: str,
    pelicula: str,
    filas_asientos: list[int],
) -> int:
    pelicula_id = _ensure_pelicula(connection, pelicula)
    cursor = connection.execute(
        "INSERT INTO salas (codigo, nombre, habilitada) VALUES (?, ?, 1)",
        (codigo, nombre),
    )
    sala_id = int(cursor.lastrowid)
    _create_seating(connection, sala_id, filas_asientos)
    _ensure_active_function(connection, sala_id, pelicula_id)
    return sala_id


def _ensure_default_data(connection: sqlite3.Connection) -> None:
    count = connection.execute("SELECT COUNT(*) AS total FROM salas").fetchone()["total"]
    if int(count) == 0:
        _create_room(
            connection,
            DEFAULT_ROOM_CODE,
            DEFAULT_ROOM_NAME,
            DEFAULT_MOVIE,
            [DEFAULT_SEATS_PER_ROW] * DEFAULT_ROWS,
        )


def create_store(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        connection = _connect(path)
        _initialize_schema(connection)
        _ensure_default_data(connection)
        connection.commit()
        connection.close()
    except sqlite3.Error as error:
        raise ValueError(f"No se pudo cargar '{path}': {error}") from error
    return {STORE_PATH: path}


def _list_room_rows(connection: sqlite3.Connection) -> list[sqlite3.Row]:
    return connection.execute(
        "SELECT id_sala, codigo, nombre, habilitada FROM salas ORDER BY codigo"
    ).fetchall()


def _layout(connection: sqlite3.Connection, sala_id: int) -> list[dict[str, Any]]:
    filas_rows = connection.execute(
        "SELECT id_fila, letra FROM filas WHERE id_sala = ? ORDER BY id_fila",
        (sala_id,),
    ).fetchall()
    layout = []
    for row in filas_rows:
        count = connection.execute(
            "SELECT COUNT(*) AS total FROM asientos WHERE id_fila = ?",
            (int(row["id_fila"]),),
        ).fetchone()["total"]
        layout.append(
            {
                "id_fila": int(row["id_fila"]),
                "letra": str(row["letra"]),
                "asientos": int(count),
            }
        )
    return layout


def _room_view(connection: sqlite3.Connection, sala_row: sqlite3.Row) -> dict[str, Any] | None:
    sala_id = int(sala_row["id_sala"])
    filas_config = _layout(connection, sala_id)
    function_id = _active_function_id(connection, sala_id)
    pelicula = ""
    reservas: dict[str, dict[str, str]] = {}
    function_info = None
    if function_id is not None:
        _sync_function_seats(connection, function_id, sala_id)
        func = connection.execute(
            """
            SELECT f.id_funcion, f.fecha, f.hora_inicio, f.hora_fin, f.estado, p.titulo
            FROM funciones f
            JOIN peliculas p ON p.id_pelicula = f.id_pelicula
            WHERE f.id_funcion = ?
            """,
            (function_id,),
        ).fetchone()
        if func:
            pelicula = str(func["titulo"])
            function_info = {
                "id_funcion": int(func["id_funcion"]),
                "fecha": str(func["fecha"]),
                "hora_inicio": str(func["hora_inicio"]),
                "hora_fin": str(func["hora_fin"]),
                "estado": str(func["estado"]),
            }
            occupied = connection.execute(
                """
                SELECT fr.orden_fila, a.numero, fa.ticket
                FROM funcion_asientos fa
                JOIN asientos a ON a.id_asiento = fa.id_asiento
                JOIN (
                    SELECT id_fila, ROW_NUMBER() OVER (ORDER BY id_fila) - 1 AS orden_fila
                    FROM filas WHERE id_sala = ?
                ) fr ON fr.id_fila = a.id_fila
                WHERE fa.id_funcion = ? AND fa.estado = 'OCUPADO'
                """,
                (sala_id, function_id),
            ).fetchall()
            for row in occupied:
                position = f"{int(row['orden_fila'])}_{int(row['numero']) - 1}"
                reservas[position] = {"ticket": str(row["ticket"] or ""), "usuario": ""}
    asientos_lista = [row["asientos"] for row in filas_config]
    return {
        "id": str(sala_row["codigo"]),
        "id_sala": sala_id,
        "nombre": str(sala_row["nombre"]),
        "pelicula": pelicula,
        "habilitada": bool(sala_row["habilitada"]),
        "filas": len(filas_config),
        "asientos_por_fila": asientos_lista[0] if len(set(asientos_lista)) == 1 else None,
        "filas_config": filas_config,
        "total_asientos": sum(asientos_lista),
        "reservas": reservas,
        "funcion": function_info,
    }


def list_rooms(store: dict[str, Any]) -> list[dict[str, Any]]:
    path = store[STORE_PATH]
    with _connect(path) as connection:
        rooms = []
        for sala_row in _list_room_rows(connection):
            view = _room_view(connection, sala_row)
            if view is not None:
                rooms.append(view)
        return rooms


def get_room(store: dict[str, Any], room_id: str | None) -> dict[str, Any] | None:
    if room_id is None:
        return None
    path = store[STORE_PATH]
    with _connect(path) as connection:
        sala_row = connection.execute(
            "SELECT id_sala, codigo, nombre, habilitada FROM salas WHERE codigo = ?",
            (room_id,),
        ).fetchone()
        if sala_row is None:
            return None
        view = _room_view(connection, sala_row)
        connection.commit()
        return view


def _validate_room_input(
    nombre: str, pelicula: str, filas_asientos: list[int] | None = None
) -> list[int]:
    if not isinstance(nombre, str) or not nombre.strip():
        raise ValueError("El nombre de la sala es obligatorio.")
    if not isinstance(pelicula, str) or not pelicula.strip():
        raise ValueError("La película es obligatoria.")
    if filas_asientos is None:
        return []
    if not isinstance(filas_asientos, list) or not filas_asientos:
        raise ValueError("La sala debe tener al menos una fila.")
    if len(filas_asientos) > MAX_FILAS:
        raise ValueError(f"'filas' debe ser un entero entre 1 y {MAX_FILAS}.")
    normalized: list[int] = []
    for seats in filas_asientos:
        if isinstance(seats, bool) or not isinstance(seats, int):
            raise ValueError(
                f"'asientos_por_fila' debe ser un entero entre 1 y {MAX_ASIENTOS_POR_FILA}."
            )
        if not 1 <= seats <= MAX_ASIENTOS_POR_FILA:
            raise ValueError(
                f"'asientos_por_fila' debe ser un entero entre 1 y {MAX_ASIENTOS_POR_FILA}."
            )
        normalized.append(seats)
    return normalized


def _normalize_layout_input(room: dict[str, Any]) -> list[int]:
    if "filas_config" in room and room["filas_config"] is not None:
        config = room["filas_config"]
        if isinstance(config, list) and config and isinstance(config[0], dict):
            return [int(item.get("asientos", 0)) for item in config]
        if isinstance(config, list):
            return [int(item) for item in config]
    filas = room.get("filas")
    asientos = room.get("asientos_por_fila")
    if isinstance(asientos, list):
        return [int(value) for value in asientos]
    if filas is not None and asientos is not None:
        return [int(asientos)] * int(filas)
    return []


def add_room(store: dict[str, Any], room: dict[str, Any]) -> None:
    codigo = str(room.get("id", "")).strip()
    nombre = str(room.get("nombre", "")).strip()
    pelicula = str(room.get("pelicula", "")).strip()
    path = store[STORE_PATH]
    try:
        if not codigo:
            raise ValueError("El c?digo de la sala es obligatorio.")
        filas_asientos = _validate_room_input(nombre, pelicula, _normalize_layout_input(room))
        with _connect(path) as connection:
            existing = connection.execute(
                "SELECT 1 FROM salas WHERE codigo = ?", (codigo,)
            ).fetchone()
            if existing:
                raise ValueError(f"El ID de sala '{codigo}' est? duplicado.")
            _create_room(connection, codigo, nombre, pelicula, filas_asientos)
    except ValueError as error:
        raise OSError(f"No se pudieron guardar los datos en '{path}': {error}") from error
    except sqlite3.Error as error:
        raise OSError(f"No se pudieron guardar los datos en '{path}': {error}") from error


def _asiento_id_for_position(
    connection: sqlite3.Connection, sala_id: int, position: str
) -> int | None:
    parts = position.split("_")
    if len(parts) != 2 or not all(part.isdigit() for part in parts):
        return None
    row_index, seat_index = (int(parts[0]), int(parts[1]))
    filas_rows = connection.execute(
        "SELECT id_fila FROM filas WHERE id_sala = ? ORDER BY id_fila",
        (sala_id,),
    ).fetchall()
    if row_index < 0 or row_index >= len(filas_rows):
        return None
    fila_id = int(filas_rows[row_index]["id_fila"])
    seat_row = connection.execute(
        "SELECT id_asiento FROM asientos WHERE id_fila = ? AND numero = ?",
        (fila_id, seat_index + 1),
    ).fetchone()
    return int(seat_row["id_asiento"]) if seat_row else None


def update_room(store: dict[str, Any], room_id: str, changes: dict[str, Any]) -> None:
    path = store[STORE_PATH]
    try:
        with _connect(path) as connection:
            sala = connection.execute(
                "SELECT id_sala, codigo FROM salas WHERE codigo = ?",
                (room_id,),
            ).fetchone()
            if sala is None:
                raise ValueError("La sala seleccionada ya no existe.")
            sala_id = int(sala["id_sala"])
            current_layout = _layout(connection, sala_id)
            current_by_id = {row["id_fila"]: row for row in current_layout}

            nombre = str(changes.get("nombre", "")).strip()
            pelicula = str(changes.get("pelicula", "")).strip()

            if "filas_config" in changes and changes["filas_config"] is not None:
                raw_specs = changes["filas_config"]
            elif "asientos_por_fila" in changes or "filas" in changes:
                counts = _normalize_layout_input(changes)
                raw_specs = []
                for index, count in enumerate(counts):
                    fila_id = (
                        current_layout[index]["id_fila"] if index < len(current_layout) else None
                    )
                    raw_specs.append({"id_fila": fila_id, "asientos": count})
            else:
                raw_specs = [
                    {"id_fila": row["id_fila"], "asientos": row["asientos"]}
                    for row in current_layout
                ]

            if not isinstance(raw_specs, list) or not raw_specs:
                raise ValueError("La sala debe tener al menos una fila.")
            if len(raw_specs) > MAX_FILAS:
                raise ValueError(f"'filas' debe ser un entero entre 1 y {MAX_FILAS}.")

            target_specs: list[dict[str, int | None]] = []
            seen_ids: set[int] = set()
            for spec in raw_specs:
                if not isinstance(spec, dict):
                    raise ValueError("La configuraci?n de filas no es v?lida.")
                raw_id = spec.get("id_fila")
                fila_id = int(raw_id) if raw_id is not None else None
                asientos = spec.get("asientos")
                if isinstance(asientos, bool) or not isinstance(asientos, int):
                    raise ValueError(
                        f"'asientos_por_fila' debe ser un entero entre 1 y {MAX_ASIENTOS_POR_FILA}."
                    )
                if not 1 <= asientos <= MAX_ASIENTOS_POR_FILA:
                    raise ValueError(
                        f"'asientos_por_fila' debe ser un entero entre 1 y {MAX_ASIENTOS_POR_FILA}."
                    )
                if fila_id is not None:
                    if fila_id not in current_by_id:
                        raise ValueError("La fila seleccionada no existe en la sala.")
                    if fila_id in seen_ids:
                        raise ValueError("La configuraci?n de filas no es v?lida.")
                    seen_ids.add(fila_id)
                target_specs.append({"id_fila": fila_id, "asientos": asientos})

            _validate_room_input(nombre, pelicula, [int(s["asientos"]) for s in target_specs])

            pelicula_id = _ensure_pelicula(connection, pelicula)
            function_id = _ensure_active_function(connection, sala_id, pelicula_id)

            target_ids = {
                int(spec["id_fila"]) for spec in target_specs if spec["id_fila"] is not None
            }

            # Block removing rows that have occupied seats.
            for row in current_layout:
                if row["id_fila"] in target_ids:
                    continue
                occupied = connection.execute(
                    """
                    SELECT COUNT(*) AS total
                    FROM funcion_asientos fa
                    JOIN asientos a ON a.id_asiento = fa.id_asiento
                    WHERE fa.id_funcion = ? AND fa.estado = 'OCUPADO' AND a.id_fila = ?
                    """,
                    (function_id, int(row["id_fila"])),
                ).fetchone()["total"]
                if int(occupied) > 0:
                    raise ValueError(
                        "No se puede quitar una fila que tiene asientos reservados. "
                        "Libera esas reservas antes de continuar."
                    )

            # Block reducing seats in a row when affected seats are occupied.
            for spec in target_specs:
                fila_id = spec["id_fila"]
                if fila_id is None:
                    continue
                new_count = int(spec["asientos"])
                current_count = int(current_by_id[int(fila_id)]["asientos"])
                if new_count < current_count:
                    occupied = connection.execute(
                        """
                        SELECT COUNT(*) AS total
                        FROM funcion_asientos fa
                        JOIN asientos a ON a.id_asiento = fa.id_asiento
                        WHERE fa.id_funcion = ? AND fa.estado = 'OCUPADO'
                          AND a.id_fila = ? AND a.numero > ?
                        """,
                        (function_id, int(fila_id), new_count),
                    ).fetchone()["total"]
                    if int(occupied) > 0:
                        raise ValueError(
                            "No se puede reducir la cantidad de asientos porque hay "
                            "reservas en los asientos que quedar?an fuera. "
                            "Libera esas reservas antes de continuar."
                        )

            connection.execute(
                "UPDATE salas SET nombre = ? WHERE id_sala = ?",
                (nombre, sala_id),
            )
            connection.execute(
                "UPDATE funciones SET id_pelicula = ? WHERE id_funcion = ?",
                (pelicula_id, function_id),
            )

            # Remove rows not present in target.
            for row in current_layout:
                if row["id_fila"] not in target_ids:
                    connection.execute(
                        "DELETE FROM filas WHERE id_fila = ?",
                        (int(row["id_fila"]),),
                    )

            # Apply target layout in order.
            for index, spec in enumerate(target_specs):
                fila_id = spec["id_fila"]
                new_count = int(spec["asientos"])
                letra = _row_label(index)
                if fila_id is None:
                    cursor = connection.execute(
                        "INSERT INTO filas (letra, id_sala) VALUES (?, ?)",
                        (letra, sala_id),
                    )
                    fila_id = int(cursor.lastrowid)
                    connection.executemany(
                        "INSERT INTO asientos (numero, id_fila) VALUES (?, ?)",
                        [(seat + 1, fila_id) for seat in range(new_count)],
                    )
                else:
                    fila_id = int(fila_id)
                    connection.execute(
                        "UPDATE filas SET letra = ? WHERE id_fila = ?",
                        (letra, fila_id),
                    )
                    current_count = int(current_by_id[fila_id]["asientos"])
                    if new_count > current_count:
                        connection.executemany(
                            "INSERT INTO asientos (numero, id_fila) VALUES (?, ?)",
                            [(seat + 1, fila_id) for seat in range(current_count, new_count)],
                        )
                    elif new_count < current_count:
                        connection.execute(
                            "DELETE FROM asientos WHERE id_fila = ? AND numero > ?",
                            (fila_id, new_count),
                        )

            _sync_function_seats(connection, function_id, sala_id)
    except sqlite3.Error as error:
        raise OSError(f"No se pudieron guardar los datos en '{path}': {error}") from error


def set_reservation(
    store: dict[str, Any],
    room_id: str,
    position: str,
    reservation: dict[str, str] | None,
) -> None:
    path = store[STORE_PATH]
    try:
        with _connect(path) as connection:
            sala = connection.execute(
                "SELECT id_sala FROM salas WHERE codigo = ?", (room_id,)
            ).fetchone()
            if sala is None:
                raise ValueError("La sala seleccionada ya no existe.")
            sala_id = int(sala["id_sala"])
            function_id = _ensure_active_function(
                connection, sala_id, _ensure_pelicula(connection, DEFAULT_MOVIE)
            )
            # ensure function has correct pelicula context if exists
            current = connection.execute(
                "SELECT id_pelicula FROM funciones WHERE id_funcion = ?",
                (function_id,),
            ).fetchone()
            if current is not None:
                _ensure_active_function(connection, sala_id, int(current["id_pelicula"]))
                function_id = _active_function_id(connection, sala_id) or function_id
            _sync_function_seats(connection, function_id, sala_id)
            asiento_id = _asiento_id_for_position(connection, sala_id, position)
            if asiento_id is None:
                raise ValueError(f"La reserva '{position}' está fuera de los límites de la sala.")
            if reservation is None:
                connection.execute(
                    """
                    UPDATE funcion_asientos
                    SET estado = 'DISPONIBLE', ticket = NULL
                    WHERE id_funcion = ? AND id_asiento = ?
                    """,
                    (function_id, asiento_id),
                )
            else:
                ticket = str(reservation.get("ticket", "")).strip()
                if not ticket:
                    raise ValueError(f"La reserva '{position}' no tiene un ticket válido.")
                connection.execute(
                    """
                    UPDATE funcion_asientos
                    SET estado = 'OCUPADO', ticket = ?
                    WHERE id_funcion = ? AND id_asiento = ?
                    """,
                    (ticket, function_id, asiento_id),
                )
    except sqlite3.Error as error:
        raise OSError(f"No se pudieron guardar los datos en '{path}': {error}") from error


def set_reservations(
    store: dict[str, Any],
    room_id: str,
    reservations: dict[str, dict[str, str]],
) -> None:
    path = store[STORE_PATH]
    try:
        with _connect(path) as connection:
            sala = connection.execute(
                "SELECT id_sala FROM salas WHERE codigo = ?", (room_id,)
            ).fetchone()
            if sala is None:
                raise ValueError("La sala seleccionada ya no existe.")
            sala_id = int(sala["id_sala"])
            function_id = _active_function_id(connection, sala_id)
            if function_id is None:
                function_id = _ensure_active_function(
                    connection, sala_id, _ensure_pelicula(connection, DEFAULT_MOVIE)
                )
            _sync_function_seats(connection, function_id, sala_id)

            resolved = []
            for position, reservation in reservations.items():
                asiento_id = _asiento_id_for_position(connection, sala_id, position)
                if asiento_id is None:
                    raise ValueError(
                        f"La reserva '{position}' está fuera de los límites de la sala."
                    )
                ticket = str(reservation.get("ticket", "")).strip()
                if not ticket:
                    raise ValueError(f"La reserva '{position}' no tiene un ticket válido.")
                resolved.append((position, asiento_id, ticket))

            for position, asiento_id, _ in resolved:
                row = connection.execute(
                    "SELECT estado FROM funcion_asientos WHERE id_funcion = ? AND id_asiento = ?",
                    (function_id, asiento_id),
                ).fetchone()
                if row is not None and row["estado"] == "OCUPADO":
                    raise ValueError(f"El asiento '{position}' ya está reservado.")

            for _, asiento_id, ticket in resolved:
                connection.execute(
                    """
                    UPDATE funcion_asientos
                    SET estado = 'OCUPADO', ticket = ?
                    WHERE id_funcion = ? AND id_asiento = ?
                    """,
                    (ticket, function_id, asiento_id),
                )
    except sqlite3.Error as error:
        raise OSError(f"No se pudieron guardar los datos en '{path}': {error}") from error


def clear_room_reservations(store: dict[str, Any], room_id: str) -> int:
    path = store[STORE_PATH]
    try:
        with _connect(path) as connection:
            sala = connection.execute(
                "SELECT id_sala FROM salas WHERE codigo = ?",
                (room_id,),
            ).fetchone()
            if sala is None:
                raise ValueError("La sala seleccionada ya no existe.")
            sala_id = int(sala["id_sala"])
            function_id = _active_function_id(connection, sala_id)
            if function_id is None:
                function_id = _ensure_active_function(
                    connection, sala_id, _ensure_pelicula(connection, DEFAULT_MOVIE)
                )
            _sync_function_seats(connection, function_id, sala_id)
            count_row = connection.execute(
                """
                SELECT COUNT(*) AS total
                FROM funcion_asientos
                WHERE id_funcion = ? AND estado = 'OCUPADO'
                """,
                (function_id,),
            ).fetchone()
            cleared = int(count_row["total"]) if count_row else 0
            connection.execute(
                """
                UPDATE funcion_asientos
                SET estado = 'DISPONIBLE', ticket = NULL
                WHERE id_funcion = ? AND estado = 'OCUPADO'
                """,
                (function_id,),
            )
            return cleared
    except sqlite3.Error as error:
        raise OSError(f"No se pudieron guardar los datos en '{path}': {error}") from error
