import json

import pytest

from cine_reservas.data_store import CineDataStore


def test_creates_default_data_when_file_is_missing(tmp_path):
    path = tmp_path / "cine_data.json"

    store = CineDataStore(path)

    assert path.exists()
    assert store.data["salas"][0]["id"] == "SALA-1"
    assert json.loads(path.read_text(encoding="utf-8")) == store.data


def test_room_and_reservation_changes_survive_reload(tmp_path):
    path = tmp_path / "cine_data.json"
    store = CineDataStore(path)

    store.add_room(
        {
            "id": "SALA-2",
            "nombre": "Sala 2",
            "pelicula": "Dune",
            "filas": 4,
            "asientos_por_fila": 6,
            "reservas": {},
        }
    )
    store.update_room("SALA-2", {"pelicula": "Dune: Parte Dos"})
    store.set_reservation("SALA-2", "3_5", {"ticket": "T-1002", "usuario": ""})

    loaded = CineDataStore(path)
    assert loaded.get_room("SALA-2")["pelicula"] == "Dune: Parte Dos"
    assert loaded.get_room("SALA-2")["reservas"]["3_5"]["ticket"] == "T-1002"

    loaded.set_reservation("SALA-2", "3_5", None)
    assert CineDataStore(path).get_room("SALA-2")["reservas"] == {}


def test_rejects_malformed_json(tmp_path):
    path = tmp_path / "cine_data.json"
    path.write_text("{", encoding="utf-8")

    with pytest.raises(ValueError, match="No se pudo cargar"):
        CineDataStore(path)


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
    store = CineDataStore(tmp_path / "cine_data.json")

    with pytest.raises(OSError):
        store.add_room(room)

    assert len(store.data["salas"]) == 1


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
        CineDataStore(path)
