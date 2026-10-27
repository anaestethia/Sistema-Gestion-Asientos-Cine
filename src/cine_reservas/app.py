import re
import sys
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, ttk

from .data_store import MAX_ASIENTOS_POR_FILA, MAX_FILAS, CineDataStore


class CineApp:
    COLORS = {
        "background": "#111116",
        "surface": "#18181f",
        "surface_alt": "#202029",
        "border": "#2b2b36",
        "text": "#f4f3fa",
        "muted": "#92919f",
        "purple": "#7d70e8",
        "purple_light": "#a59bff",
        "green": "#15d6a0",
        "green_dark": "#123a32",
        "red": "#fa3f72",
        "red_dark": "#461c2b",
        "blue": "#4c8dff",
        "blue_dark": "#203b68",
    }
    FREE_COLOR = "#123a32"
    OCCUPIED_COLOR = "#461c2b"
    SELECTED_COLOR = "#203b68"

    def __init__(self, root, data_path=None):
        self.root = root
        self.closed = False
        self.root.title("CineManager | Operaciones de cine")
        self.root.geometry("1440x900")
        self.root.minsize(1080, 700)
        self.root.configure(background=self.COLORS["background"])
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
        self.selected_seats = set()
        self.current_view = "asientos"
        self.activity_entries = []
        self._configure_styles()
        self._build_ui()
        self._refresh_rooms()

    def _configure_styles(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(
            "Dark.TCombobox",
            fieldbackground=self.COLORS["surface_alt"],
            background=self.COLORS["surface_alt"],
            foreground=self.COLORS["text"],
            arrowcolor=self.COLORS["muted"],
            bordercolor=self.COLORS["border"],
            lightcolor=self.COLORS["border"],
            darkcolor=self.COLORS["border"],
            padding=8,
        )
        style.configure("TFrame", background=self.COLORS["surface"])
        style.configure(
            "TLabel",
            background=self.COLORS["surface"],
            foreground=self.COLORS["text"],
            font=("Segoe UI", 9),
        )
        style.configure(
            "TEntry",
            fieldbackground=self.COLORS["surface_alt"],
            foreground=self.COLORS["text"],
            insertcolor=self.COLORS["text"],
            bordercolor=self.COLORS["border"],
            lightcolor=self.COLORS["border"],
            darkcolor=self.COLORS["border"],
            padding=7,
        )
        style.configure(
            "TButton",
            background=self.COLORS["surface_alt"],
            foreground=self.COLORS["text"],
            bordercolor=self.COLORS["border"],
            padding=(12, 7),
            font=("Segoe UI", 9),
        )
        style.map(
            "TButton",
            background=[("active", "#30303c")],
            foreground=[("disabled", "#686875")],
        )
        style.configure("TSeparator", background=self.COLORS["border"])
        style.configure("TLabelframe", background=self.COLORS["surface"])
        style.configure(
            "TLabelframe.Label",
            background=self.COLORS["surface"],
            foreground=self.COLORS["muted"],
        )
        style.map(
            "Dark.TCombobox",
            fieldbackground=[("readonly", self.COLORS["surface_alt"])],
            foreground=[("readonly", self.COLORS["text"])],
            selectbackground=[("readonly", self.COLORS["surface_alt"])],
            selectforeground=[("readonly", self.COLORS["text"])],
        )
        style.configure(
            "Dark.Treeview",
            background=self.COLORS["surface"],
            fieldbackground=self.COLORS["surface"],
            foreground=self.COLORS["text"],
            borderwidth=0,
            rowheight=36,
            font=("Segoe UI", 10),
        )
        style.configure(
            "Dark.Treeview.Heading",
            background=self.COLORS["surface_alt"],
            foreground=self.COLORS["muted"],
            borderwidth=0,
            font=("Segoe UI", 9, "bold"),
            padding=(10, 9),
        )
        style.map(
            "Dark.Treeview",
            background=[("selected", "#302b55")],
            foreground=[("selected", self.COLORS["text"])],
        )
        style.configure(
            "Dark.Vertical.TScrollbar",
            background=self.COLORS["surface_alt"],
            troughcolor=self.COLORS["background"],
            bordercolor=self.COLORS["background"],
            arrowcolor=self.COLORS["muted"],
        )
        style.configure(
            "Dark.Horizontal.TScrollbar",
            background=self.COLORS["surface_alt"],
            troughcolor=self.COLORS["background"],
            bordercolor=self.COLORS["background"],
            arrowcolor=self.COLORS["muted"],
        )

    def _label(self, parent, text="", *, size=10, color=None, bold=False, **kwargs):
        return tk.Label(
            parent,
            text=text,
            bg=kwargs.pop("bg", self.COLORS["surface"]),
            fg=color or self.COLORS["text"],
            font=("Segoe UI", size, "bold" if bold else "normal"),
            **kwargs,
        )

    def _button(self, parent, text, command, *, primary=False, danger=False, compact=False):
        if primary:
            background, foreground = self.COLORS["purple"], "white"
            active = self.COLORS["purple_light"]
        elif danger:
            background, foreground = self.COLORS["red"], "white"
            active = "#ff6289"
        else:
            background, foreground = self.COLORS["surface_alt"], self.COLORS["text"]
            active = "#30303c"
        return tk.Button(
            parent,
            text=text,
            command=command,
            background=background,
            foreground=foreground,
            activebackground=active,
            activeforeground=foreground,
            disabledforeground="#686875",
            relief="flat",
            borderwidth=0,
            padx=12 if compact else 16,
            pady=7 if compact else 10,
            font=("Segoe UI", 9, "bold"),
            cursor="hand2",
        )

    def _build_ui(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=0)
        self.root.rowconfigure(1, weight=1)
        self.root.rowconfigure(2, weight=0)
        self.root.columnconfigure(0, weight=1)

        self.header = tk.Frame(
            self.root,
            bg=self.COLORS["background"],
            padx=22,
            pady=12,
            highlightbackground=self.COLORS["border"],
            highlightthickness=1,
        )
        self.header.grid(row=0, column=0, sticky="ew")
        self.header.columnconfigure(1, weight=1)
        brand = tk.Frame(self.header, bg=self.COLORS["background"])
        brand.grid(row=0, column=0, sticky="w")
        tk.Label(
            brand,
            text="C",
            bg=self.COLORS["purple"],
            fg="white",
            font=("Segoe UI", 12, "bold"),
            width=2,
            height=1,
            pady=5,
        ).pack(side="left", padx=(0, 9))
        self._label(brand, "CineManager", size=12, bold=True, bg=self.COLORS["background"]).pack(
            side="left"
        )
        self._label(
            brand,
            "  ·  CENTRO DE OPERACIONES",
            size=8,
            color=self.COLORS["muted"],
            bg=self.COLORS["background"],
        ).pack(side="left")

        navigation = tk.Frame(self.header, bg=self.COLORS["background"])
        navigation.grid(row=0, column=1)
        self.nav_buttons = {}
        for key, title in (
            ("asientos", "Asientos"),
            ("reservas", "Reservas"),
            ("actividad", "Actividad"),
        ):
            button = tk.Button(
                navigation,
                text=title,
                command=lambda selected=key: self._show_view(selected),
                bg=self.COLORS["background"],
                fg=self.COLORS["muted"],
                activebackground=self.COLORS["background"],
                activeforeground=self.COLORS["text"],
                relief="flat",
                borderwidth=0,
                padx=16,
                pady=9,
                font=("Segoe UI", 9, "bold"),
                cursor="hand2",
            )
            button.pack(side="left", padx=3)
            self.nav_buttons[key] = button

        status = tk.Frame(self.header, bg=self.COLORS["background"])
        status.grid(row=0, column=2, sticky="e")
        self._label(
            status,
            "●  Sistema activo",
            size=8,
            color=self.COLORS["green"],
            bg=self.COLORS["background"],
        ).pack(side="left", padx=(0, 12))
        tk.Label(
            status,
            text="AM",
            bg=self.COLORS["surface_alt"],
            fg=self.COLORS["text"],
            font=("Segoe UI", 8, "bold"),
            width=3,
            pady=5,
        ).pack(side="left")

        self.content = tk.Frame(self.root, bg=self.COLORS["background"], padx=18, pady=16)
        self.content.grid(row=1, column=0, sticky="nsew")
        self.content.columnconfigure(0, weight=0, minsize=310)
        self.content.columnconfigure(1, weight=1)
        self.content.rowconfigure(0, weight=1)
        self._build_room_overview()
        self._build_seat_view()
        self._build_reservations_view()
        self._build_activity_view()

        self.footer = tk.Frame(
            self.root,
            bg=self.COLORS["background"],
            padx=18,
            pady=9,
            highlightbackground=self.COLORS["border"],
            highlightthickness=1,
        )
        self.footer.grid(row=2, column=0, sticky="ew")
        self._label(
            self.footer,
            "●  Cambios guardados automáticamente",
            size=8,
            color=self.COLORS["green"],
            bg=self.COLORS["background"],
        ).pack(side="left")
        self.footer_time = self._label(
            self.footer, "", size=8, color=self.COLORS["muted"], bg=self.COLORS["background"]
        )
        self.footer_time.pack(side="right")
        self._show_view("asientos")

    def _card(self, parent, *, padding=14):
        return tk.Frame(
            parent,
            bg=self.COLORS["surface"],
            padx=padding,
            pady=padding,
            highlightbackground=self.COLORS["border"],
            highlightthickness=1,
        )

    def _build_room_overview(self):
        self.overview = self._card(self.content, padding=14)
        self.overview.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        self.overview.columnconfigure(0, weight=1)
        self.overview.rowconfigure(13, weight=1)
        heading = tk.Frame(self.overview, bg=self.COLORS["surface"])
        heading.grid(row=0, column=0, sticky="ew")
        self._label(heading, "Resumen de sala", size=12, bold=True).pack(side="left")
        self.room_count_label = self._label(heading, "", size=8, color=self.COLORS["muted"])
        self.room_count_label.pack(side="right")

        self._label(self.overview, "SALA ACTUAL", size=8, color=self.COLORS["muted"]).grid(
            row=1, column=0, sticky="w", pady=(18, 6)
        )
        self.room_combo = ttk.Combobox(
            self.overview, state="readonly", style="Dark.TCombobox", font=("Segoe UI", 9)
        )
        self.room_combo.grid(row=2, column=0, sticky="ew")
        self.room_combo.bind("<<ComboboxSelected>>", self._on_room_selected)

        self.poster = tk.Canvas(self.overview, height=142, bg="#111821", highlightthickness=0)
        self.poster.grid(row=3, column=0, sticky="ew", pady=(14, 10))
        self.poster.bind("<Configure>", self._draw_poster)

        self._label(self.overview, "CAPACIDAD TOTAL", size=8, color=self.COLORS["muted"]).grid(
            row=4, column=0, sticky="w"
        )
        self.capacity_label = self._label(self.overview, "", size=10, bold=True)
        self.capacity_label.grid(row=5, column=0, sticky="w", pady=(3, 10))
        ttk.Separator(self.overview).grid(row=6, column=0, sticky="ew", pady=4)
        self._label(self.overview, "Disponibilidad en tiempo real", size=9, bold=True).grid(
            row=7, column=0, sticky="w", pady=(8, 8)
        )

        metrics = tk.Frame(self.overview, bg=self.COLORS["surface"])
        metrics.grid(row=8, column=0, sticky="ew")
        for index in range(3):
            metrics.columnconfigure(index, weight=1)
        self.available_metric = self._metric(metrics, 0, "LIBRES", self.COLORS["green"])
        self.selected_metric = self._metric(metrics, 1, "SELECCIONADOS", self.COLORS["blue"])
        self.occupied_metric = self._metric(metrics, 2, "OCUPADOS", self.COLORS["red"])
        self.availability_bar = tk.Canvas(
            self.overview, height=5, bg=self.COLORS["surface_alt"], highlightthickness=0
        )
        self.availability_bar.grid(row=9, column=0, sticky="ew", pady=(12, 12))
        self.availability_bar.bind("<Configure>", self._draw_availability)

        self._button(self.overview, "＋  Agregar sala", self._add_room, primary=True).grid(
            row=10, column=0, sticky="ew", pady=(3, 6)
        )
        self._button(self.overview, "⚙  Editar configuración", self._edit_room).grid(
            row=11, column=0, sticky="ew"
        )
        self._label(
            self.overview,
            "Selecciona un asiento libre para añadirlo a la reserva.",
            size=8,
            color=self.COLORS["muted"],
            wraplength=250,
            justify="left",
        ).grid(row=12, column=0, sticky="w", pady=(12, 2))

    def _metric(self, parent, column, title, color):
        box = tk.Frame(parent, bg=self.COLORS["surface"])
        box.grid(row=0, column=column, sticky="w", padx=(0, 3))
        value = self._label(box, "0", size=18, color=color, bold=True)
        value.pack(anchor="w")
        self._label(box, title, size=7, color=self.COLORS["muted"]).pack(anchor="w")
        return value

    def _draw_poster(self, _event=None):
        self.poster.delete("all")
        width = max(self.poster.winfo_width(), 240)
        height = 142
        self.poster.create_rectangle(0, 0, width, height, fill="#131b28", outline="")
        self.poster.create_rectangle(0, 0, width, height // 2, fill="#202738", outline="")
        self.poster.create_oval(width * 0.62, 16, width * 0.78, 70, fill="#343753", outline="")
        for index, height_offset in enumerate((30, 52, 40, 65, 34, 55, 42)):
            x = index * width / 6
            self.poster.create_rectangle(
                x,
                94 - height_offset / 2,
                x + width / 6 + 1,
                height,
                fill=("#1c2934" if index % 2 else "#25333b"),
                outline="",
            )
            for window_y in range(99, 132, 10):
                self.poster.create_rectangle(
                    x + 5, window_y, x + 8, window_y + 3, fill="#47535b", outline=""
                )
        self.poster.create_rectangle(
            0, 78, width, height, fill="#0b1018", stipple="gray50", outline=""
        )
        room = self.store.get_room(self.active_room_id) if self.active_room_id else None
        movie = room["pelicula"] if room else "Sin película asignada"
        room_name = room["nombre"] if room else "Agrega una sala para comenzar"
        self.poster.create_text(
            14,
            18,
            anchor="nw",
            text="EN CARTELERA",
            fill="#c6bfdc",
            font=("Segoe UI", 7, "bold"),
        )
        self.poster.create_text(
            14,
            78,
            anchor="sw",
            text=movie,
            fill="white",
            font=("Segoe UI", 17, "bold"),
        )
        self.poster.create_text(
            14,
            99,
            anchor="nw",
            text=f"{room_name}  ·  Función de hoy",
            fill="#c1c2cc",
            font=("Segoe UI", 8),
        )

    def _draw_availability(self, _event=None):
        self.availability_bar.delete("all")
        room = self.store.get_room(self.active_room_id) if self.active_room_id else None
        if room is None:
            return
        width = self.availability_bar.winfo_width()
        total = room["filas"] * room["asientos_por_fila"]
        occupied = len(room["reservas"])
        occupied_width = width * occupied / total if total else 0
        self.availability_bar.create_rectangle(
            0, 0, width - occupied_width, 5, fill=self.COLORS["green"], outline=""
        )
        self.availability_bar.create_rectangle(
            width - occupied_width, 0, width, 5, fill=self.COLORS["red"], outline=""
        )

    def _build_seat_view(self):
        self.seat_view = tk.Frame(self.content, bg=self.COLORS["background"])
        self.seat_view.grid(row=0, column=1, sticky="nsew")
        self.seat_view.columnconfigure(0, weight=1)
        self.seat_view.rowconfigure(1, weight=1)

        top = tk.Frame(self.seat_view, bg=self.COLORS["background"])
        top.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        top.columnconfigure(0, weight=1)
        left = tk.Frame(top, bg=self.COLORS["background"])
        left.grid(row=0, column=0, sticky="w")
        self._label(
            left, "Distribución de asientos", size=17, bold=True, bg=self.COLORS["background"]
        ).pack(anchor="w")
        self.map_subtitle = self._label(
            left, "", size=9, color=self.COLORS["muted"], bg=self.COLORS["background"]
        )
        self.map_subtitle.pack(anchor="w", pady=(3, 0))
        self.dimensions_badge = self._label(
            top,
            "",
            size=8,
            color=self.COLORS["muted"],
            bg=self.COLORS["surface"],
            padx=10,
            pady=7,
        )
        self.dimensions_badge.grid(row=0, column=1, sticky="e")

        self.map_card = self._card(self.seat_view, padding=12)
        self.map_card.grid(row=1, column=0, sticky="nsew")
        self.map_card.columnconfigure(0, weight=1)
        self.map_card.rowconfigure(1, weight=1)
        self.screen_canvas = tk.Canvas(
            self.map_card, height=42, bg=self.COLORS["surface"], highlightthickness=0
        )
        self.screen_canvas.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        self.screen_canvas.bind("<Configure>", self._draw_screen)

        map_area = tk.Frame(self.map_card, bg=self.COLORS["surface"])
        map_area.grid(row=1, column=0, sticky="nsew")
        map_area.columnconfigure(0, weight=1)
        map_area.rowconfigure(0, weight=1)
        self.canvas = tk.Canvas(map_area, highlightthickness=0, background=self.COLORS["surface"])
        vertical_scroll = ttk.Scrollbar(
            map_area,
            orient="vertical",
            command=self.canvas.yview,
            style="Dark.Vertical.TScrollbar",
        )
        horizontal_scroll = ttk.Scrollbar(
            map_area,
            orient="horizontal",
            command=self.canvas.xview,
            style="Dark.Horizontal.TScrollbar",
        )
        self.canvas.configure(
            yscrollcommand=vertical_scroll.set, xscrollcommand=horizontal_scroll.set
        )
        self.canvas.grid(row=0, column=0, sticky="nsew")
        vertical_scroll.grid(row=0, column=1, sticky="ns")
        horizontal_scroll.grid(row=1, column=0, sticky="ew")
        self.seat_grid = tk.Frame(self.canvas, bg=self.COLORS["surface"], padx=14, pady=10)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.seat_grid, anchor="nw")
        self.seat_grid.bind("<Configure>", self._update_scroll_region)

        selection_bar = tk.Frame(self.map_card, bg=self.COLORS["surface_alt"], padx=12, pady=10)
        selection_bar.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        selection_bar.columnconfigure(0, weight=1)
        self.selection_summary = self._label(
            selection_bar,
            "Ningún asiento seleccionado",
            size=9,
            color=self.COLORS["muted"],
            bg=self.COLORS["surface_alt"],
        )
        self.selection_summary.grid(row=0, column=0, sticky="w")
        self.clear_selection_button = self._button(
            selection_bar, "Limpiar", self._clear_selection, compact=True
        )
        self.clear_selection_button.grid(row=0, column=1, padx=(8, 6))
        self.reserve_button = self._button(
            selection_bar, "✓  Reservar asientos", self._reserve_selected, primary=True
        )
        self.reserve_button.grid(row=0, column=2)

        legend = tk.Frame(self.map_card, bg=self.COLORS["surface"])
        legend.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        self._legend_item(legend, self.COLORS["green"], "Disponible").pack(
            side="left", padx=(0, 16)
        )
        self._legend_item(legend, self.COLORS["blue"], "Seleccionado").pack(side="left", padx=16)
        self._legend_item(legend, self.COLORS["red"], "Ocupado").pack(side="left", padx=16)

    def _legend_item(self, parent, color, text):
        item = tk.Frame(parent, bg=self.COLORS["surface"])
        tk.Label(item, text="●", bg=self.COLORS["surface"], fg=color, font=("Segoe UI", 9)).pack(
            side="left", padx=(0, 5)
        )
        self._label(item, text, size=8, color=self.COLORS["muted"]).pack(side="left")
        return item

    def _draw_screen(self, event=None):
        self.screen_canvas.delete("all")
        width = event.width if event else self.screen_canvas.winfo_width()
        if width < 40:
            return
        center = width / 2
        self.screen_canvas.create_arc(
            center - width * 0.34,
            6,
            center + width * 0.34,
            63,
            start=8,
            extent=164,
            style="arc",
            outline="#8579ed",
            width=2,
        )
        self.screen_canvas.create_text(
            center,
            25,
            text="P A N T A L L A",
            fill=self.COLORS["muted"],
            font=("Segoe UI", 7, "bold"),
        )

    def _build_reservations_view(self):
        self.reservations_view = tk.Frame(self.content, bg=self.COLORS["background"])
        self.reservations_view.grid(row=0, column=1, sticky="nsew")
        self.reservations_view.columnconfigure(0, weight=1)
        self.reservations_view.rowconfigure(1, weight=1)
        heading = tk.Frame(self.reservations_view, bg=self.COLORS["background"])
        heading.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        self._label(heading, "Reservas", size=17, bold=True, bg=self.COLORS["background"]).pack(
            anchor="w"
        )
        self._label(
            heading,
            "Entradas registradas para la sala seleccionada.",
            size=9,
            color=self.COLORS["muted"],
            bg=self.COLORS["background"],
        ).pack(anchor="w", pady=(3, 0))
        card = self._card(self.reservations_view, padding=10)
        card.grid(row=1, column=0, sticky="nsew")
        card.columnconfigure(0, weight=1)
        card.rowconfigure(0, weight=1)
        columns = ("fila", "asiento", "ticket", "sala")
        self.reservations_table = ttk.Treeview(
            card, columns=columns, show="headings", style="Dark.Treeview"
        )
        for column, title, width in (
            ("fila", "FILA", 90),
            ("asiento", "ASIENTO", 100),
            ("ticket", "NÚMERO DE ENTRADA", 220),
            ("sala", "SALA", 220),
        ):
            self.reservations_table.heading(column, text=title)
            self.reservations_table.column(column, width=width, anchor="w")
        self.reservations_table.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(
            card,
            orient="vertical",
            command=self.reservations_table.yview,
            style="Dark.Vertical.TScrollbar",
        )
        scroll.grid(row=0, column=1, sticky="ns")
        self.reservations_table.configure(yscrollcommand=scroll.set)
        self.reservations_table.bind("<Double-1>", self._release_from_table)

    def _build_activity_view(self):
        self.activity_view = tk.Frame(self.content, bg=self.COLORS["background"])
        self.activity_view.grid(row=0, column=1, sticky="nsew")
        self.activity_view.columnconfigure(0, weight=1)
        self.activity_view.rowconfigure(1, weight=1)
        heading = tk.Frame(self.activity_view, bg=self.COLORS["background"])
        heading.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        self._label(
            heading, "Actividad reciente", size=17, bold=True, bg=self.COLORS["background"]
        ).pack(anchor="w")
        self._label(
            heading,
            "Historial de operaciones de esta sesión.",
            size=9,
            color=self.COLORS["muted"],
            bg=self.COLORS["background"],
        ).pack(anchor="w", pady=(3, 0))
        self.activity_card = self._card(self.activity_view, padding=12)
        self.activity_card.grid(row=1, column=0, sticky="nsew")
        self.activity_card.columnconfigure(0, weight=1)
        self.activity_card.rowconfigure(0, weight=1)
        self.activity_list = tk.Listbox(
            self.activity_card,
            bg=self.COLORS["surface"],
            fg=self.COLORS["text"],
            selectbackground="#302b55",
            selectforeground=self.COLORS["text"],
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            font=("Segoe UI", 10),
            activestyle="none",
        )
        self.activity_list.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(
            self.activity_card,
            orient="vertical",
            command=self.activity_list.yview,
            style="Dark.Vertical.TScrollbar",
        )
        scroll.grid(row=0, column=1, sticky="ns")
        self.activity_list.configure(yscrollcommand=scroll.set)

    def _show_view(self, view):
        self.current_view = view
        for name, frame in (
            ("asientos", self.seat_view),
            ("reservas", self.reservations_view),
            ("actividad", self.activity_view),
        ):
            frame.grid_remove()
            button = self.nav_buttons[name]
            button.configure(
                fg=self.COLORS["text"] if name == view else self.COLORS["muted"],
                highlightthickness=0,
                underline=0,
            )
            if name == view:
                button.configure(
                    fg=self.COLORS["purple_light"],
                    highlightthickness=0,
                    relief="flat",
                )
            if name == view:
                frame.grid()
        self.overview.grid()
        if view == "asientos":
            self._render_room()

    def _record_activity(self, text):
        timestamp = datetime.now().strftime("%H:%M")
        self.activity_entries.insert(0, f"{timestamp}   ·   {text}")
        self.activity_list.delete(0, tk.END)
        for entry in self.activity_entries:
            self.activity_list.insert(tk.END, entry)
        self.footer_time.configure(
            text=f"Última actualización: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        )

    def _update_scroll_region(self, _event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _refresh_rooms(self):
        self.room_ids_by_label.clear()
        labels = []
        for room in self.store.data["salas"]:
            label = f"{room['id']}  ·  {room['nombre']}"
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
        self.room_count_label.configure(text=f"{len(self.store.data['salas']):02d} SALA(S)")
        self._refresh_reservations()
        self._render_room()

    def _refresh_reservations(self):
        for item in self.reservations_table.get_children():
            self.reservations_table.delete(item)
        for room in self.store.data["salas"]:
            if room["id"] != self.active_room_id:
                continue
            for position, reservation in sorted(room["reservas"].items()):
                row, seat = map(int, position.split("_"))
                self.reservations_table.insert(
                    "",
                    tk.END,
                    values=(f"F{row + 1}", f"C{seat + 1}", reservation["ticket"], room["nombre"]),
                )

    def _on_room_selected(self, _event=None):
        self.active_room_id = self.room_ids_by_label.get(self.room_combo.get())
        self.selected_seats.clear()
        self._render_room()
        self._refresh_reservations()

    def _render_room(self):
        for child in self.seat_grid.winfo_children():
            child.destroy()
        room = self.store.get_room(self.active_room_id) if self.active_room_id else None
        if room is None:
            self.capacity_label.configure(text="Sin sala")
            self.map_subtitle.configure(text="Agrega una sala para administrar sus asientos.")
            self.dimensions_badge.configure(text="SIN SALA")
            self._update_metrics(0, 0, 0)
            self._draw_poster()
            self._draw_availability()
            return

        total = room["filas"] * room["asientos_por_fila"]
        occupied = len(room["reservas"])
        selected = sum(
            1
            for row, seat in self.selected_seats
            if f"{row}_{seat}" not in room["reservas"]
            and row < room["filas"]
            and seat < room["asientos_por_fila"]
        )
        available = total - occupied
        self.capacity_label.configure(text=f"{total} asientos  ·  Formato estándar")
        self.map_subtitle.configure(text=f"{room['nombre']}  ·  Función de hoy, 19:30")
        self.dimensions_badge.configure(
            text=f"{room['filas']} FILAS  ×  {room['asientos_por_fila']} COLUMNAS"
        )
        self._update_metrics(available, selected, occupied)
        self._draw_poster()

        columns = room["asientos_por_fila"]
        self._label(self.seat_grid, "", size=7, color=self.COLORS["muted"]).grid(
            row=0, column=0, padx=(0, 8)
        )
        for column in range(columns):
            self._label(
                self.seat_grid, f"C{column + 1:02d}", size=7, color=self.COLORS["muted"]
            ).grid(row=0, column=column + 1, padx=4, pady=(0, 8))
        self.seat_buttons = {}
        for row in range(room["filas"]):
            self._label(self.seat_grid, f"F{row + 1:02d}", size=8, color=self.COLORS["muted"]).grid(
                row=row + 1, column=0, padx=(0, 8), pady=4, sticky="e"
            )
            for seat in range(columns):
                position = f"{row}_{seat}"
                reservation = room["reservas"].get(position)
                is_selected = (row, seat) in self.selected_seats and not reservation
                color = (
                    self.OCCUPIED_COLOR
                    if reservation
                    else self.SELECTED_COLOR
                    if is_selected
                    else self.FREE_COLOR
                )
                foreground = "#ff8aa8" if reservation else "#a9c5ff" if is_selected else "#78e4c4"
                button = tk.Button(
                    self.seat_grid,
                    text=f"{seat + 1:02d}",
                    width=4,
                    padx=2,
                    pady=5,
                    relief="flat",
                    borderwidth=0,
                    background=color,
                    foreground=foreground,
                    activebackground=color,
                    activeforeground="white",
                    font=("Segoe UI", 8, "bold"),
                    cursor="hand2",
                    command=lambda r=row, s=seat: self._on_seat_click(r, s),
                )
                button.grid(row=row + 1, column=seat + 1, padx=3, pady=3)
                self.seat_buttons[(row, seat)] = button
        self.selection_summary.configure(
            text=(
                f"{selected} asiento(s) seleccionado(s)  ·  "
                "el mismo número de entrada se asignará a todos"
                if selected
                else "Selecciona uno o varios asientos disponibles"
            ),
            fg=self.COLORS["blue"] if selected else self.COLORS["muted"],
        )
        self.reserve_button.configure(state="normal" if selected else "disabled")
        self.clear_selection_button.configure(state="normal" if selected else "disabled")
        self.seat_grid.update_idletasks()
        self._update_scroll_region()
        self._draw_availability()

    def _update_metrics(self, available, selected, occupied):
        self.available_metric.configure(text=f"{available:02d}")
        self.selected_metric.configure(text=f"{selected:02d}")
        self.occupied_metric.configure(text=f"{occupied:02d}")

    def _on_seat_click(self, row, seat):
        room = self.store.get_room(self.active_room_id)
        if room is None:
            return
        position = f"{row}_{seat}"
        reservation = room["reservas"].get(position)
        if reservation:
            self._show_reservation(room, position, row, seat, reservation)
            return
        coordinate = (row, seat)
        if coordinate in self.selected_seats:
            self.selected_seats.remove(coordinate)
        else:
            self.selected_seats.add(coordinate)
        self._render_room()

    def _clear_selection(self):
        self.selected_seats.clear()
        self._render_room()

    def _reserve_selected(self):
        room = self.store.get_room(self.active_room_id)
        if room is None or not self.selected_seats:
            return
        ticket = self._ticket_dialog(len(self.selected_seats))
        if ticket is None:
            return
        reservations = {
            f"{row}_{seat}": {"ticket": ticket, "usuario": ""} for row, seat in self.selected_seats
        }
        try:
            self.store.set_reservations(room["id"], reservations)
        except (OSError, ValueError) as error:
            messagebox.showerror("Error al reservar", str(error), parent=self.root)
            self.selected_seats.clear()
            self._refresh_rooms()
            return
        reserved_count = len(self.selected_seats)
        self.selected_seats.clear()
        self._record_activity(
            f"{reserved_count} asiento(s) reservado(s) · Entrada {ticket} · {room['nombre']}"
        )
        self._refresh_rooms()

    def _ticket_dialog(self, seat_count):
        dialog = tk.Toplevel(self.root)
        dialog.title("Confirmar reserva")
        dialog.configure(bg=self.COLORS["background"])
        dialog.transient(self.root)
        dialog.resizable(False, False)
        dialog.grab_set()
        dialog.geometry("440x280")
        dialog.columnconfigure(0, weight=1)
        card = self._card(dialog, padding=22)
        card.grid(row=0, column=0, sticky="nsew", padx=14, pady=14)
        self._label(card, "Confirmar reserva", size=15, bold=True).pack(anchor="w")
        self._label(
            card,
            f"Vas a reservar {seat_count} asiento(s). Escribe el número de entrada.",
            size=9,
            color=self.COLORS["muted"],
            wraplength=350,
            justify="left",
        ).pack(anchor="w", pady=(8, 18))
        self._label(card, "NÚMERO DE ENTRADA", size=8, color=self.COLORS["muted"]).pack(anchor="w")
        entry = tk.Entry(
            card,
            bg=self.COLORS["surface_alt"],
            fg=self.COLORS["text"],
            insertbackground=self.COLORS["text"],
            relief="flat",
            font=("Segoe UI", 10),
            highlightthickness=1,
            highlightbackground=self.COLORS["border"],
            highlightcolor=self.COLORS["purple"],
            bd=0,
        )
        entry.pack(fill="x", ipady=9, pady=(6, 14))
        result = {"ticket": None}

        def confirm():
            ticket = entry.get().strip()
            if not ticket:
                messagebox.showwarning(
                    "Entrada obligatoria",
                    "Escribe un número de entrada para continuar.",
                    parent=dialog,
                )
                entry.focus_set()
                return
            result["ticket"] = ticket
            dialog.destroy()

        buttons = tk.Frame(card, bg=self.COLORS["surface"])
        buttons.pack(fill="x")
        self._button(buttons, "Cancelar", dialog.destroy).pack(side="right")
        self._button(buttons, "✓  Confirmar reserva", confirm, primary=True).pack(
            side="right", padx=(0, 8)
        )
        dialog.bind("<Return>", lambda _event: confirm())
        dialog.bind("<Escape>", lambda _event: dialog.destroy())
        entry.focus_set()
        self.root.wait_window(dialog)
        return result["ticket"]

    def _show_reservation(self, room, position, row, seat, reservation):
        dialog = tk.Toplevel(self.root)
        dialog.title("Detalle del asiento")
        dialog.configure(bg=self.COLORS["background"])
        dialog.transient(self.root)
        dialog.resizable(False, False)
        dialog.grab_set()
        card = self._card(dialog, padding=20)
        card.pack(fill="both", expand=True, padx=14, pady=14)
        self._label(card, f"Asiento F{row + 1} · C{seat + 1}", size=15, bold=True).pack(anchor="w")
        self._label(card, room["nombre"], size=9, color=self.COLORS["muted"]).pack(
            anchor="w", pady=(3, 16)
        )
        self._label(card, "NÚMERO DE ENTRADA", size=8, color=self.COLORS["muted"]).pack(anchor="w")
        self._label(card, reservation["ticket"], size=12, bold=True).pack(anchor="w", pady=(4, 18))
        actions = tk.Frame(card, bg=self.COLORS["surface"])
        actions.pack(fill="x")

        def release():
            try:
                self.store.set_reservation(room["id"], position, None)
            except (OSError, ValueError) as error:
                messagebox.showerror("Error al liberar", str(error), parent=dialog)
                return
            dialog.destroy()
            self._record_activity(f"Asiento F{row + 1} · C{seat + 1} liberado · {room['nombre']}")
            self._refresh_rooms()

        self._button(actions, "Cerrar", dialog.destroy).pack(side="right")
        self._button(actions, "Liberar asiento", release, danger=True).pack(
            side="right", padx=(0, 8)
        )
        dialog.bind("<Escape>", lambda _event: dialog.destroy())

    def _release_from_table(self, _event=None):
        selection = self.reservations_table.selection()
        if not selection:
            return
        values = self.reservations_table.item(selection[0], "values")
        room = self.store.get_room(self.active_room_id) if self.active_room_id else None
        if room is None:
            return
        row, seat = int(values[0][1:]) - 1, int(values[1][1:]) - 1
        position = f"{row}_{seat}"
        reservation = room["reservas"].get(position)
        if reservation:
            self._show_reservation(room, position, row, seat, reservation)

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
        self._record_activity(f"Sala agregada · {values['nombre']}")
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
        self._record_activity(f"Configuración actualizada · {room['nombre']}")
        self._refresh_rooms()

    def _room_dialog(self, title, room=None):
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.configure(bg=self.COLORS["background"])
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
