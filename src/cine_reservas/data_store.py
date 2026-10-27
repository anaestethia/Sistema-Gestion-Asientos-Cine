"""Persistencia y validación de los datos de las salas de cine."""

import copy
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

DEFAULT_DATA = {
    "salas": [
        {
            "id": "SALA-1",
            "nombre": "Sala 1 - Principal",
            "pelicula": "Inception",
            "filas": 5,
            "asientos_por_fila": 8,
            "reservas": {},
        }
    ]
}

MAX_FILAS = 30
MAX_ASIENTOS_POR_FILA = 30


class CineDataStore:
    """Carga, valida y persiste el estado completo del cine en JSON."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        if self.path.exists():
            self.data = self._load()
        else:
            self.data = copy.deepcopy(DEFAULT_DATA)
            self.save()

    @staticmethod
    def _validate(data: Any) -> None:
        if not isinstance(data, dict) or not isinstance(data.get("salas"), list):
            raise ValueError("El archivo debe contener una lista 'salas'.")

        ids = set()
        for sala in data["salas"]:
            if not isinstance(sala, dict):
                raise ValueError("Cada sala debe ser un objeto JSON.")
            required = ("id", "nombre", "pelicula", "filas", "asientos_por_fila", "reservas")
            if any(key not in sala for key in required):
                raise ValueError("Una sala no contiene todos los campos requeridos.")
            if not all(isinstance(sala[key], str) and sala[key].strip() for key in required[:3]):
                raise ValueError("El ID, el nombre y la película de cada sala son obligatorios.")
            if sala["id"] in ids:
                raise ValueError(f"El ID de sala '{sala['id']}' está duplicado.")
            ids.add(sala["id"])
            for key, maximum in (
                ("filas", MAX_FILAS),
                ("asientos_por_fila", MAX_ASIENTOS_POR_FILA),
            ):
                value = sala[key]
                if (
                    isinstance(value, bool)
                    or not isinstance(value, int)
                    or not 1 <= value <= maximum
                ):
                    raise ValueError(f"'{key}' debe ser un entero entre 1 y {maximum}.")
            if not isinstance(sala["reservas"], dict):
                raise ValueError("Las reservas de cada sala deben ser un objeto JSON.")
            for position, reservation in sala["reservas"].items():
                match = re.fullmatch(r"(\d+)_(\d+)", position)
                if not match or not isinstance(reservation, dict):
                    raise ValueError(f"La reserva '{position}' no tiene un formato válido.")
                row, seat = map(int, match.groups())
                if row >= sala["filas"] or seat >= sala["asientos_por_fila"]:
                    raise ValueError(
                        f"La reserva '{position}' está fuera de los límites de la sala."
                    )
                if (
                    not isinstance(reservation.get("ticket"), str)
                    or not reservation["ticket"].strip()
                ):
                    raise ValueError(f"La reserva '{position}' no tiene un ticket válido.")
                if not isinstance(reservation.get("usuario", ""), str):
                    raise ValueError(f"El usuario de la reserva '{position}' no es válido.")

    def _load(self) -> dict[str, Any]:
        try:
            with self.path.open("r", encoding="utf-8") as file:
                data = json.load(file)
            self._validate(data)
            return data
        except (OSError, json.JSONDecodeError, ValueError) as error:
            raise ValueError(f"No se pudo cargar '{self.path}': {error}") from error

    def save(self) -> None:
        temporary_path = None
        try:
            self._validate(self.data)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.path.parent,
                prefix=f".{self.path.name}.",
                suffix=".tmp",
                delete=False,
            ) as file:
                temporary_path = Path(file.name)
                json.dump(self.data, file, ensure_ascii=False, indent=2)
                file.write("\n")
            os.replace(temporary_path, self.path)
        except (OSError, TypeError, ValueError) as error:
            if temporary_path and temporary_path.exists():
                temporary_path.unlink()
            raise OSError(f"No se pudieron guardar los datos en '{self.path}': {error}") from error

    def add_room(self, room: dict[str, Any]) -> None:
        old_data = copy.deepcopy(self.data)
        self.data["salas"].append(room)
        try:
            self.save()
        except OSError:
            self.data = old_data
            raise

    def update_room(self, room_id: str, changes: dict[str, Any]) -> None:
        room = self.get_room(room_id)
        if room is None:
            raise ValueError("La sala seleccionada ya no existe.")
        old_data = copy.deepcopy(self.data)
        room.update(changes)
        try:
            self.save()
        except OSError:
            self.data = old_data
            raise

    def set_reservation(
        self,
        room_id: str,
        position: str,
        reservation: dict[str, str] | None,
    ) -> None:
        room = self.get_room(room_id)
        if room is None:
            raise ValueError("La sala seleccionada ya no existe.")
        old_data = copy.deepcopy(self.data)
        if reservation is None:
            room["reservas"].pop(position, None)
        else:
            room["reservas"][position] = reservation
        try:
            self.save()
        except OSError:
            self.data = old_data
            raise

    def set_reservations(self, room_id: str, reservations: dict[str, dict[str, str]]) -> None:
        room = self.get_room(room_id)
        if room is None:
            raise ValueError("La sala seleccionada ya no existe.")
        occupied = room["reservas"].keys() & reservations.keys()
        if occupied:
            raise ValueError(f"El asiento '{next(iter(occupied))}' ya está reservado.")
        old_data = copy.deepcopy(self.data)
        room["reservas"].update(reservations)
        try:
            self.save()
        except OSError:
            self.data = old_data
            raise

    def get_room(self, room_id: str | None) -> dict[str, Any] | None:
        return next((room for room in self.data["salas"] if room["id"] == room_id), None)
