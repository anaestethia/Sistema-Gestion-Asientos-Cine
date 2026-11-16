import ast
import json
from pathlib import Path

import pytest

from cine_reservas.data_store import (
    add_room,
    create_store,
    get_room,
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


def test_creates_default_data_when_file_is_missing(tmp_path):
    path = tmp_path / "cine_data.json"

    store = create_store(path)

    assert path.exists()
    assert store["data"]["salas"][0]["id"] == "SALA-1"
    assert json.loads(path.read_text(encoding="utf-8")) == store["data"]


def test_room_and_reservation_changes_survive_reload(tmp_path):
    path = tmp_path / "cine_data.json"
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
    update_room(store, "SALA-2", {"pelicula": "Dune: Parte Dos"})
    set_reservation(store, "SALA-2", "3_5", {"ticket": "T-1002", "usuario": ""})

    loaded = create_store(path)
    assert get_room(loaded, "SALA-2")["pelicula"] == "Dune: Parte Dos"
    assert get_room(loaded, "SALA-2")["reservas"]["3_5"]["ticket"] == "T-1002"

    set_reservation(loaded, "SALA-2", "3_5", None)
    assert get_room(create_store(path), "SALA-2")["reservas"] == {}


def test_multiple_reservations_are_saved_together_and_occupied_seats_are_preserved(
    tmp_path,
):
    store = create_store(tmp_path / "cine_data.json")
    room_id = store["data"]["salas"][0]["id"]

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


def test_rejects_malformed_json(tmp_path):
    path = tmp_path / "cine_data.json"
    path.write_text("{", encoding="utf-8")

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
    store = create_store(tmp_path / "cine_data.json")

    with pytest.raises(OSError):
        add_room(store, room)

    assert len(store["data"]["salas"]) == 1


def test_rejects_reservations_outside_room_dimensions(tmp_path):
    path = tmp_path / "cine_data.json"
    data = {
        "salas": [
            {
                "id": "SALA-1",
                "nombre": "Sala 1",
                "pelicula": "Film",
                "filas": 1,
                "asientos_por_fila": 1,
                "reservas": {"1_0": {"ticket": "T-1", "usuario": ""}},
            }
        ]
    }
    path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ValueError, match="fuera de los límites"):
        create_store(path)
