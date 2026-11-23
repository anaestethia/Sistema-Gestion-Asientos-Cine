import ast
from pathlib import Path

import pytest

from cine_reservas.data_store import (
    add_room,
    clear_room_reservations,
    create_store,
    get_room,
    list_rooms,
    set_reservation,
    set_reservations,
    update_room,
)


def test_application_modules_do_not_define_classes():
    package = Path(__file__).parents[1] / "src" / "cine_reservas"
    modules = (package / "app.py", package / "data_store.py")

    for module in modules:
        tree = ast.parse(module.read_text(encoding="utf-8"))
        assert not any(isinstance(node, ast.ClassDef) for node in ast.walk(tree)), module.name


def test_creates_default_data_when_database_is_missing(tmp_path):
    path = tmp_path / "cine_data.db"

    store = create_store(path)

    assert path.exists()
    rooms = list_rooms(store)
    assert rooms[0]["id"] == "SALA-1"
    assert rooms[0]["nombre"] == "Sala 1 - Principal"
    assert rooms[0]["pelicula"] == "Inception"
    assert rooms[0]["filas"] == 5
    assert rooms[0]["asientos_por_fila"] == 8


def test_room_and_reservation_changes_survive_reload(tmp_path):
    path = tmp_path / "cine_data.db"
    store = create_store(path)

    add_room(
        store,
        {
            "id": "SALA-2",
            "nombre": "Sala 2",
            "pelicula": "Dune",
            "filas": 4,
            "asientos_por_fila": 6,
            "reservas": {},
        },
    )
    update_room(
        store,
        "SALA-2",
        {"nombre": "Sala 2", "pelicula": "Dune: Parte Dos", "filas": 4, "asientos_por_fila": 6},
    )
    set_reservation(store, "SALA-2", "3_5", {"ticket": "T-1002", "usuario": ""})

    loaded = create_store(path)
    assert get_room(loaded, "SALA-2")["pelicula"] == "Dune: Parte Dos"
    assert get_room(loaded, "SALA-2")["reservas"]["3_5"]["ticket"] == "T-1002"

    set_reservation(loaded, "SALA-2", "3_5", None)
    assert get_room(create_store(path), "SALA-2")["reservas"] == {}


def test_multiple_reservations_are_saved_together_and_occupied_seats_are_preserved(
    tmp_path,
):
    store = create_store(tmp_path / "cine_data.db")
    room_id = list_rooms(store)[0]["id"]

    set_reservations(
        store,
        room_id,
        {
            "0_0": {"ticket": "T-1001", "usuario": ""},
            "0_1": {"ticket": "T-1001", "usuario": ""},
        },
    )

    with pytest.raises(ValueError, match="ya está reservado"):
        set_reservations(
            store,
            room_id,
            {
                "0_1": {"ticket": "T-2002", "usuario": ""},
                "0_2": {"ticket": "T-2002", "usuario": ""},
            },
        )

    reservations = get_room(create_store(store["path"]), room_id)["reservas"]
    assert reservations["0_0"]["ticket"] == "T-1001"
    assert reservations["0_1"]["ticket"] == "T-1001"
    assert "0_2" not in reservations


def test_rejects_malformed_database(tmp_path):
    path = tmp_path / "cine_data.db"
    path.write_text("esto no es sqlite", encoding="utf-8")

    with pytest.raises(ValueError, match="No se pudo cargar"):
        create_store(path)


@pytest.mark.parametrize(
    "room",
    [
        {
            "id": "SALA-1",
            "nombre": "Duplicada",
            "pelicula": "Film",
            "filas": 2,
            "asientos_por_fila": 2,
            "reservas": {},
        },
        {
            "id": "SALA-2",
            "nombre": "Invalida",
            "pelicula": "Film",
            "filas": 31,
            "asientos_por_fila": 2,
            "reservas": {},
        },
    ],
)
def test_rejects_invalid_rooms(tmp_path, room):
    store = create_store(tmp_path / "cine_data.db")

    with pytest.raises(OSError):
        add_room(store, room)

    assert len(list_rooms(store)) == 1


def test_rejects_reservations_outside_room_dimensions(tmp_path):
    store = create_store(tmp_path / "cine_data.db")
    room_id = list_rooms(store)[0]["id"]

    with pytest.raises(ValueError, match="fuera de los límites"):
        set_reservation(store, room_id, "99_0", {"ticket": "T-1", "usuario": ""})


def test_database_applies_normalized_schema(tmp_path):
    import sqlite3

    path = tmp_path / "cine_data.db"
    create_store(path)

    with sqlite3.connect(path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert {
            "salas",
            "peliculas",
            "filas",
            "asientos",
            "funciones",
            "funcion_asientos",
        }.issubset(tables)
        assert connection.execute("SELECT COUNT(*) FROM filas").fetchone()[0] == 5
        assert connection.execute("SELECT COUNT(*) FROM asientos").fetchone()[0] == 40
        assert connection.execute("SELECT COUNT(*) FROM funciones").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM funcion_asientos").fetchone()[0] == 40
        sala = connection.execute("SELECT codigo, nombre, habilitada FROM salas").fetchone()
        assert sala[0] == "SALA-1"
        assert sala[1] == "Sala 1 - Principal"
        assert sala[2] == 1
        funcion = connection.execute("SELECT estado, id_funcion_origen FROM funciones").fetchone()
        assert funcion[0] == "PROGRAMADA"
        assert funcion[1] is None


def test_variable_row_layout_create_and_update(tmp_path):
    path = tmp_path / "cine_data.db"
    store = create_store(path)

    add_room(
        store,
        {
            "id": "SALA-VAR",
            "nombre": "Sala Variable",
            "pelicula": "Dune",
            "filas_config": [3, 3, 3, 5, 5, 5, 5],
            "reservas": {},
        },
    )
    room = get_room(store, "SALA-VAR")
    assert room["filas"] == 7
    assert room["total_asientos"] == 29
    assert [row["asientos"] for row in room["filas_config"]] == [3, 3, 3, 5, 5, 5, 5]
    assert room["asientos_por_fila"] is None

    # reserve in second front row and in a back row
    set_reservation(store, "SALA-VAR", "1_2", {"ticket": "TICK-200", "usuario": ""})
    set_reservation(store, "SALA-VAR", "3_4", {"ticket": "TICK-201", "usuario": ""})

    room = get_room(store, "SALA-VAR")
    layout = room["filas_config"]
    # change an unaffected front row, add a row at the end,
    # and remove the last back row without occupied seats
    new_layout = [
        {"id_fila": layout[0]["id_fila"], "asientos": 4},
        {"id_fila": layout[1]["id_fila"], "asientos": 3},  # keeps occupied seat index 2
        {"id_fila": layout[2]["id_fila"], "asientos": 3},
        {"id_fila": layout[3]["id_fila"], "asientos": 5},  # keeps occupied seat index 4
        {"id_fila": layout[4]["id_fila"], "asientos": 6},
        {"id_fila": layout[5]["id_fila"], "asientos": 5},
        {"id_fila": None, "asientos": 2},
    ]
    update_room(
        store,
        "SALA-VAR",
        {"nombre": "Sala Variable", "pelicula": "Dune 2", "filas_config": new_layout},
    )

    room = get_room(store, "SALA-VAR")
    assert [row["asientos"] for row in room["filas_config"]] == [4, 3, 3, 5, 6, 5, 2]
    assert room["pelicula"] == "Dune 2"
    assert room["reservas"]["1_2"]["ticket"] == "TICK-200"
    assert room["reservas"]["3_4"]["ticket"] == "TICK-201"


def test_variable_row_update_blocks_affected_occupied_seats(tmp_path):
    path = tmp_path / "cine_data.db"
    store = create_store(path)

    add_room(
        store,
        {
            "id": "SALA-OCC",
            "nombre": "Sala Ocupada",
            "pelicula": "Alien",
            "filas_config": [4, 4, 4],
            "reservas": {},
        },
    )
    set_reservation(store, "SALA-OCC", "1_3", {"ticket": "TICK-300", "usuario": ""})
    room = get_room(store, "SALA-OCC")
    layout = room["filas_config"]

    # shrinking below occupied seat in that row must be blocked
    with pytest.raises(ValueError, match="reservas"):
        update_room(
            store,
            "SALA-OCC",
            {
                "nombre": "Sala Ocupada",
                "pelicula": "Alien",
                "filas_config": [
                    {"id_fila": layout[0]["id_fila"], "asientos": 4},
                    {"id_fila": layout[1]["id_fila"], "asientos": 3},
                    {"id_fila": layout[2]["id_fila"], "asientos": 4},
                ],
            },
        )

    # removing a row with occupied seats must be blocked
    with pytest.raises(ValueError, match="reservas|fila"):
        update_room(
            store,
            "SALA-OCC",
            {
                "nombre": "Sala Ocupada",
                "pelicula": "Alien",
                "filas_config": [
                    {"id_fila": layout[0]["id_fila"], "asientos": 4},
                    {"id_fila": layout[2]["id_fila"], "asientos": 4},
                ],
            },
        )

    room = get_room(store, "SALA-OCC")
    assert room["reservas"]["1_3"]["ticket"] == "TICK-300"
    assert [row["asientos"] for row in room["filas_config"]] == [4, 4, 4]


def test_clear_room_reservations_frees_all_occupied_seats(tmp_path):
    path = tmp_path / "cine_data.db"
    store = create_store(path)

    set_reservation(store, "SALA-1", "0_0", {"ticket": "TICK-1", "usuario": ""})
    set_reservation(store, "SALA-1", "1_2", {"ticket": "TICK-2", "usuario": ""})
    assert len(get_room(store, "SALA-1")["reservas"]) == 2

    cleared = clear_room_reservations(store, "SALA-1")

    assert cleared == 2
    assert get_room(store, "SALA-1")["reservas"] == {}
    assert clear_room_reservations(store, "SALA-1") == 0
