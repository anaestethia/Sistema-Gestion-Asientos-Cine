import re
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, simpledialog, ttk

from .data_store import MAX_ASIENTOS_POR_FILA, MAX_FILAS, CineDataStore


class CineApp:
    FREE_COLOR = "#72c98b"
    OCCUPIED_COLOR = "#e76f6f"

    def __init__(self, root, data_path=None):
        self.root = root
        self.closed = False
        self.root.title("Sistema de Gestión y Reserva de Cine")
        self.root.geometry("1100x720")
        self.root.minsize(820, 560)
        if data_path:
            self.data_path = Path(data_path)
        else:
            app_directory = (
                Path(sys.executable).resolve().parent
                if getattr(sys, "frozen", False)
                else Path(__file__).resolve().parents[2]
            )
            self.data_path = app_directory / "cine_data.json"

        try:
            self.store = CineDataStore(self.data_path)
        except (OSError, ValueError) as error:
            messagebox.showerror("Error de datos", str(error), parent=self.root)
            self.closed = True
            self.root.destroy()
            return

        self.active_room_id = (
            self.store.data["salas"][0]["id"] if self.store.data["salas"] else None
        )
        self.room_ids_by_label = {}
        self._build_ui()
        self._refresh_rooms()

    def _build_ui(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main = ttk.Frame(self.root, padding=12)
        main.grid(row=0, column=0, sticky="nsew")
        main.columnconfigure(1, weight=1)
        main.rowconfigure(0, weight=1)

        controls = ttk.LabelFrame(main, text="Panel de control", padding=12)
        controls.grid(row=0, column=0, sticky="nsw", padx=(0, 12))
        ttk.Label(controls, text="Sala activa").grid(row=0, column=0, sticky="w")
        self.room_combo = ttk.Combobox(controls, state="readonly", width=27)
        self.room_combo.grid(row=1, column=0, sticky="ew", pady=(4, 14))
        self.room_combo.bind("<<ComboboxSelected>>", self._on_room_selected)

        self.room_info = ttk.Label(controls, text="", justify="left", wraplength=230)
        self.room_info.grid(row=2, column=0, sticky="w", pady=(0, 14))
        ttk.Button(controls, text="Agregar sala", command=self._add_room).grid(
            row=3, column=0, sticky="ew", pady=3
        )
        ttk.Button(controls, text="Editar sala activa", command=self._edit_room).grid(
            row=4, column=0, sticky="ew", pady=3
        )
        ttk.Separator(controls).grid(row=5, column=0, sticky="ew", pady=12)
        ttk.Label(
            controls,
            text="Asientos",
            font=("Segoe UI", 10, "bold"),
        ).grid(row=6, column=0, sticky="w")
        ttk.Label(controls, text="Verde: libre\nRojo: ocupado", justify="left").grid(
            row=7, column=0, sticky="w", pady=(5, 14)
        )
        self.seat_summary = ttk.Label(controls, text="")
        self.seat_summary.grid(row=8, column=0, sticky="w")

        map_frame = ttk.LabelFrame(main, text="Mapa de sala", padding=10)
        map_frame.grid(row=0, column=1, sticky="nsew")
        map_frame.columnconfigure(0, weight=1)
        map_frame.rowconfigure(1, weight=1)
        self.movie_title = ttk.Label(map_frame, text="", font=("Segoe UI", 15, "bold"))
        self.movie_title.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        map_area = ttk.Frame(map_frame)
        map_area.grid(row=1, column=0, sticky="nsew")
        map_area.columnconfigure(0, weight=1)
        map_area.rowconfigure(0, weight=1)
        self.canvas = tk.Canvas(map_area, highlightthickness=0, background="#f5f6f7")
        vertical_scroll = ttk.Scrollbar(map_area, orient="vertical", command=self.canvas.yview)
        horizontal_scroll = ttk.Scrollbar(map_area, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(
            yscrollcommand=vertical_scroll.set, xscrollcommand=horizontal_scroll.set
        )
        self.canvas.grid(row=0, column=0, sticky="nsew")
        vertical_scroll.grid(row=0, column=1, sticky="ns")
        horizontal_scroll.grid(row=1, column=0, sticky="ew")
        self.seat_grid = ttk.Frame(self.canvas, padding=16)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.seat_grid, anchor="nw")
        self.seat_grid.bind("<Configure>", self._update_scroll_region)

    def _update_scroll_region(self, _event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _refresh_rooms(self):
        self.room_ids_by_label.clear()
        labels = []
        for room in self.store.data["salas"]:
            label = f"{room['id']} — {room['nombre']}"
            labels.append(label)
            self.room_ids_by_label[label] = room["id"]
        self.room_combo["values"] = labels
        if self.active_room_id and self.store.get_room(self.active_room_id):
            selected = next(
                label
                for label, room_id in self.room_ids_by_label.items()
                if room_id == self.active_room_id
            )
            self.room_combo.set(selected)
        elif labels:
            self.active_room_id = self.room_ids_by_label[labels[0]]
            self.room_combo.set(labels[0])
        else:
            self.active_room_id = None
            self.room_combo.set("")
        self._render_room()

    def _on_room_selected(self, _event=None):
        self.active_room_id = self.room_ids_by_label.get(self.room_combo.get())
        self._render_room()

    def _render_room(self):
        for child in self.seat_grid.winfo_children():
            child.destroy()
        room = self.store.get_room(self.active_room_id) if self.active_room_id else None
        if room is None:
            self.room_info.configure(text="No hay salas. Agrega una para comenzar.")
            self.movie_title.configure(text="Sin sala seleccionada")
            self.seat_summary.configure(text="")
            return

        total = room["filas"] * room["asientos_por_fila"]
        occupied = len(room["reservas"])
        self.room_info.configure(
            text=(
                f"{room['nombre']}\n"
                f"Película: {room['pelicula']}\n"
                f"Dimensiones: {room['filas']} filas × "
                f"{room['asientos_por_fila']} asientos"
            )
        )
        self.movie_title.configure(text=f"{room['pelicula']}  ·  {room['nombre']}")
        self.seat_summary.configure(
            text=f"Libres: {total - occupied}\nOcupados: {occupied}\nTotal: {total}"
        )

        screen = tk.Label(
            self.seat_grid,
            text="P A N T A L L A",
            background="#263238",
            foreground="white",
            font=("Segoe UI", 10, "bold"),
            pady=8,
        )
        screen.grid(
            row=0, column=1, columnspan=room["asientos_por_fila"], sticky="ew", pady=(0, 14)
        )
        ttk.Label(self.seat_grid, text="").grid(row=1, column=0, padx=4)
        for column in range(room["asientos_por_fila"]):
            ttk.Label(self.seat_grid, text=f"C{column + 1}").grid(
                row=1, column=column + 1, padx=3, pady=(0, 5)
            )
        for row in range(room["filas"]):
            ttk.Label(self.seat_grid, text=f"F{row + 1}").grid(
                row=row + 2, column=0, padx=(0, 8), pady=3, sticky="e"
            )
            for seat in range(room["asientos_por_fila"]):
                position = f"{row}_{seat}"
                reservation = room["reservas"].get(position)
                button = tk.Button(
                    self.seat_grid,
                    text=f"{seat + 1:02}",
                    width=4,
                    padx=3,
                    pady=5,
                    relief="raised",
                    background=self.OCCUPIED_COLOR if reservation else self.FREE_COLOR,
                    activebackground=self.OCCUPIED_COLOR if reservation else self.FREE_COLOR,
                    command=lambda r=row, s=seat: self._on_seat_click(r, s),
                )
                button.grid(row=row + 2, column=seat + 1, padx=3, pady=3)
        self.seat_grid.update_idletasks()
        self._update_scroll_region()

    def _on_seat_click(self, row, seat):
        room = self.store.get_room(self.active_room_id)
        if room is None:
            return
        position = f"{row}_{seat}"
        reservation = room["reservas"].get(position)
        if reservation:
            self._show_reservation(room, position, row, seat, reservation)
        else:
            self._reserve_seat(room, position, row, seat)

    def _reserve_seat(self, room, position, row, seat):
        ticket = simpledialog.askstring(
            "Reservar asiento",
            f"Ingrese el número de entrada/ticket para F{row + 1}, C{seat + 1}:",
            parent=self.root,
        )
        if ticket is None:
            return
        ticket = ticket.strip()
        if not ticket:
            messagebox.showwarning(
                "Ticket obligatorio", "Debe ingresar un número de ticket.", parent=self.root
            )
            return
        try:
            self.store.set_reservation(room["id"], position, {"ticket": ticket, "usuario": ""})
        except (OSError, ValueError) as error:
            messagebox.showerror("Error al reservar", str(error), parent=self.root)
            return
        self._render_room()

    def _show_reservation(self, room, position, row, seat, reservation):
        release = messagebox.askyesno(
            "Asiento ocupado",
            (
                f"Fila: F{row + 1}\nAsiento: C{seat + 1}\n"
                f"Número de entrada: {reservation['ticket']}\n\n"
                "¿Desea liberar este asiento?"
            ),
            parent=self.root,
        )
        if not release:
            return
        try:
            self.store.set_reservation(room["id"], position, None)
        except (OSError, ValueError) as error:
            messagebox.showerror("Error al liberar", str(error), parent=self.root)
            return
        self._render_room()

    def _add_room(self):
        values = self._room_dialog("Agregar sala")
        if values is None:
            return
        numbers = [
            int(match.group(1))
            for room in self.store.data["salas"]
            if (match := re.fullmatch(r"SALA-(\d+)", room["id"]))
        ]
        room_id = f"SALA-{max(numbers, default=0) + 1}"
        room = {"id": room_id, **values, "reservas": {}}
        try:
            self.store.add_room(room)
        except (OSError, ValueError) as error:
            messagebox.showerror("Error al agregar sala", str(error), parent=self.root)
            return
        self.active_room_id = room_id
        self._refresh_rooms()

    def _edit_room(self):
        room = self.store.get_room(self.active_room_id) if self.active_room_id else None
        if room is None:
            messagebox.showinfo(
                "Editar sala", "Primero agrega o selecciona una sala.", parent=self.root
            )
            return
        values = self._room_dialog("Editar sala", room)
        if values is None:
            return
        removed = []
        for position in room["reservas"]:
            row, seat = map(int, position.split("_"))
            if row >= values["filas"] or seat >= values["asientos_por_fila"]:
                removed.append(position)
        if removed:
            messagebox.showwarning(
                "No se puede reducir la sala",
                (
                    f"Hay {len(removed)} reserva(s) en asientos que quedarían fuera "
                    "de las nuevas dimensiones. Libere esos asientos antes de reducir la sala."
                ),
                parent=self.root,
            )
            return
        try:
            self.store.update_room(room["id"], values)
        except (OSError, ValueError) as error:
            messagebox.showerror("Error al editar sala", str(error), parent=self.root)
            return
        self._refresh_rooms()

    def _room_dialog(self, title, room=None):
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.transient(self.root)
        dialog.resizable(False, False)
        dialog.grab_set()
        frame = ttk.Frame(dialog, padding=16)
        frame.grid(row=0, column=0, sticky="nsew")
        fields = (
            ("Nombre de la sala", "nombre", room["nombre"] if room else ""),
            ("Película asignada", "pelicula", room["pelicula"] if room else ""),
            ("Cantidad de filas (1–30)", "filas", str(room["filas"] if room else 5)),
            (
                "Asientos por fila (1–30)",
                "asientos_por_fila",
                str(room["asientos_por_fila"] if room else 8),
            ),
        )
        entries = {}
        for index, (label, key, initial) in enumerate(fields):
            ttk.Label(frame, text=label).grid(row=index, column=0, sticky="w", pady=5)
            entry = ttk.Entry(frame, width=32)
            entry.insert(0, initial)
            entry.grid(row=index, column=1, padx=(12, 0), pady=5)
            entries[key] = entry

        result = {"value": None}

        def submit():
            name = entries["nombre"].get().strip()
            movie = entries["pelicula"].get().strip()
            if not name or not movie:
                messagebox.showwarning(
                    "Datos obligatorios",
                    "El nombre de la sala y la película son obligatorios.",
                    parent=dialog,
                )
                return
            try:
                rows = int(entries["filas"].get().strip())
                seats = int(entries["asientos_por_fila"].get().strip())
            except ValueError:
                messagebox.showwarning(
                    "Dimensiones inválidas",
                    "Filas y asientos por fila deben ser números enteros.",
                    parent=dialog,
                )
                return
            if not 1 <= rows <= MAX_FILAS or not 1 <= seats <= MAX_ASIENTOS_POR_FILA:
                messagebox.showwarning(
                    "Dimensiones inválidas",
                    "Las filas y los asientos por fila deben estar entre 1 y 30.",
                    parent=dialog,
                )
                return
            result["value"] = {
                "nombre": name,
                "pelicula": movie,
                "filas": rows,
                "asientos_por_fila": seats,
            }
            dialog.destroy()

        buttons = ttk.Frame(frame)
        buttons.grid(row=len(fields), column=0, columnspan=2, sticky="e", pady=(12, 0))
        ttk.Button(buttons, text="Cancelar", command=dialog.destroy).grid(row=0, column=0, padx=4)
        ttk.Button(buttons, text="Guardar", command=submit).grid(row=0, column=1, padx=4)
        dialog.bind("<Return>", lambda _event: submit())
        dialog.bind("<Escape>", lambda _event: dialog.destroy())
        entries["nombre"].focus_set()
        self.root.wait_window(dialog)
        return result["value"]


def main():
    root = tk.Tk()
    app = CineApp(root)
    if not app.closed:
        root.mainloop()


if __name__ == "__main__":
    main()
