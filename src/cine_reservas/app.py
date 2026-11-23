import re
import sys
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, ttk

from .data_store import (
    MAX_ASIENTOS_POR_FILA,
    MAX_FILAS,
    clear_room_reservations,
    create_store,
    get_room,
    list_rooms,
    set_reservation,
    set_reservations,
    update_room,
)
from .data_store import (
    add_room as save_room,
)

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


def create_app(root, data_path=None):
    app = {"root": root, "closed": False}
    root.title("CineManager | Operaciones de cine")
    root.geometry("1440x900")
    root.minsize(1080, 700)
    root.configure(background=COLORS["background"])
    if data_path:
        app["data_path"] = Path(data_path)
    else:
        app_directory = (
            Path(sys.executable).resolve().parent
            if getattr(sys, "frozen", False)
            else Path(__file__).resolve().parents[2]
        )
        app["data_path"] = app_directory / "cine_data.db"
    try:
        app["store"] = create_store(app["data_path"])
    except (OSError, ValueError) as error:
        messagebox.showerror("Error de datos", str(error), parent=root)
        app["closed"] = True
        root.destroy()
        return app
    rooms = list_rooms(app["store"])
    app["active_room_id"] = rooms[0]["id"] if rooms else None
    app["room_ids_by_label"] = {}
    app["selected_seats"] = set()
    app["current_view"] = "asientos"
    app["activity_entries"] = []
    configure_styles(app)
    build_ui(app)
    refresh_rooms(app)
    return app


def configure_styles(app):
    style = ttk.Style(app["root"])
    style.theme_use("clam")
    style.configure(
        "Dark.TCombobox",
        fieldbackground=COLORS["surface_alt"],
        background=COLORS["surface_alt"],
        foreground=COLORS["text"],
        arrowcolor=COLORS["muted"],
        bordercolor=COLORS["border"],
        lightcolor=COLORS["border"],
        darkcolor=COLORS["border"],
        padding=8,
    )
    style.configure("TFrame", background=COLORS["surface"])
    style.configure(
        "TLabel", background=COLORS["surface"], foreground=COLORS["text"], font=("Segoe UI", 9)
    )
    style.configure(
        "TEntry",
        fieldbackground=COLORS["surface_alt"],
        foreground=COLORS["text"],
        insertcolor=COLORS["text"],
        bordercolor=COLORS["border"],
        lightcolor=COLORS["border"],
        darkcolor=COLORS["border"],
        padding=7,
    )
    style.configure(
        "TButton",
        background=COLORS["surface_alt"],
        foreground=COLORS["text"],
        bordercolor=COLORS["border"],
        padding=(12, 7),
        font=("Segoe UI", 9),
    )
    style.map("TButton", background=[("active", "#30303c")], foreground=[("disabled", "#686875")])
    style.configure("TSeparator", background=COLORS["border"])
    style.configure("TLabelframe", background=COLORS["surface"])
    style.configure("TLabelframe.Label", background=COLORS["surface"], foreground=COLORS["muted"])
    style.map(
        "Dark.TCombobox",
        fieldbackground=[("readonly", COLORS["surface_alt"])],
        foreground=[("readonly", COLORS["text"])],
        selectbackground=[("readonly", COLORS["surface_alt"])],
        selectforeground=[("readonly", COLORS["text"])],
    )
    style.configure(
        "Dark.Treeview",
        background=COLORS["surface"],
        fieldbackground=COLORS["surface"],
        foreground=COLORS["text"],
        borderwidth=0,
        rowheight=36,
        font=("Segoe UI", 10),
    )
    style.configure(
        "Dark.Treeview.Heading",
        background=COLORS["surface_alt"],
        foreground=COLORS["muted"],
        borderwidth=0,
        font=("Segoe UI", 9, "bold"),
        padding=(10, 9),
    )
    style.map(
        "Dark.Treeview",
        background=[("selected", "#302b55")],
        foreground=[("selected", COLORS["text"])],
    )
    style.configure(
        "Dark.Vertical.TScrollbar",
        background=COLORS["surface_alt"],
        troughcolor=COLORS["background"],
        bordercolor=COLORS["background"],
        arrowcolor=COLORS["muted"],
    )
    style.configure(
        "Dark.Horizontal.TScrollbar",
        background=COLORS["surface_alt"],
        troughcolor=COLORS["background"],
        bordercolor=COLORS["background"],
        arrowcolor=COLORS["muted"],
    )


def label(app, parent, text="", *, size=10, color=None, bold=False, **kwargs):
    return tk.Label(
        parent,
        text=text,
        bg=kwargs.pop("bg", COLORS["surface"]),
        fg=color or COLORS["text"],
        font=("Segoe UI", size, "bold" if bold else "normal"),
        **kwargs,
    )


def button(app, parent, text, command, *, primary=False, danger=False, compact=False):
    if primary:
        background, foreground = (COLORS["purple"], "white")
        active = COLORS["purple_light"]
    elif danger:
        background, foreground = (COLORS["red"], "white")
        active = "#ff6289"
    else:
        background, foreground = (COLORS["surface_alt"], COLORS["text"])
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


def build_ui(app):
    app["root"].columnconfigure(0, weight=1)
    app["root"].rowconfigure(0, weight=1)
    app["root"].rowconfigure(0, weight=0)
    app["root"].rowconfigure(1, weight=1)
    app["root"].rowconfigure(2, weight=0)
    app["root"].columnconfigure(0, weight=1)
    app["header"] = tk.Frame(
        app["root"],
        bg=COLORS["background"],
        padx=22,
        pady=12,
        highlightbackground=COLORS["border"],
        highlightthickness=1,
    )
    app["header"].grid(row=0, column=0, sticky="ew")
    app["header"].columnconfigure(1, weight=1)
    brand = tk.Frame(app["header"], bg=COLORS["background"])
    brand.grid(row=0, column=0, sticky="w")
    tk.Label(
        brand,
        text="C",
        bg=COLORS["purple"],
        fg="white",
        font=("Segoe UI", 12, "bold"),
        width=2,
        height=1,
        pady=5,
    ).pack(side="left", padx=(0, 9))
    label(app, brand, "CineManager", size=12, bold=True, bg=COLORS["background"]).pack(side="left")
    label(
        app,
        brand,
        "  ·  CENTRO DE OPERACIONES",
        size=8,
        color=COLORS["muted"],
        bg=COLORS["background"],
    ).pack(side="left")
    navigation = tk.Frame(app["header"], bg=COLORS["background"])
    navigation.grid(row=0, column=1)
    app["nav_buttons"] = {}
    for key, title in (
        ("asientos", "Asientos"),
        ("reservas", "Reservas"),
        ("actividad", "Actividad"),
    ):
        button = tk.Button(
            navigation,
            text=title,
            command=lambda selected=key: show_view(app, selected),
            bg=COLORS["background"],
            fg=COLORS["muted"],
            activebackground=COLORS["background"],
            activeforeground=COLORS["text"],
            relief="flat",
            borderwidth=0,
            padx=16,
            pady=9,
            font=("Segoe UI", 9, "bold"),
            cursor="hand2",
        )
        button.pack(side="left", padx=3)
        app["nav_buttons"][key] = button
    status = tk.Frame(app["header"], bg=COLORS["background"])
    status.grid(row=0, column=2, sticky="e")
    label(
        app, status, "●  Sistema activo", size=8, color=COLORS["green"], bg=COLORS["background"]
    ).pack(side="left", padx=(0, 12))
    tk.Label(
        status,
        text="AM",
        bg=COLORS["surface_alt"],
        fg=COLORS["text"],
        font=("Segoe UI", 8, "bold"),
        width=3,
        pady=5,
    ).pack(side="left")
    app["content"] = tk.Frame(app["root"], bg=COLORS["background"], padx=18, pady=16)
    app["content"].grid(row=1, column=0, sticky="nsew")
    app["content"].columnconfigure(0, weight=0, minsize=310)
    app["content"].columnconfigure(1, weight=1)
    app["content"].rowconfigure(0, weight=1)
    build_room_overview(app)
    build_seat_view(app)
    build_reservations_view(app)
    build_activity_view(app)
    app["footer"] = tk.Frame(
        app["root"],
        bg=COLORS["background"],
        padx=18,
        pady=9,
        highlightbackground=COLORS["border"],
        highlightthickness=1,
    )
    app["footer"].grid(row=2, column=0, sticky="ew")
    label(
        app,
        app["footer"],
        "●  Cambios guardados automáticamente",
        size=8,
        color=COLORS["green"],
        bg=COLORS["background"],
    ).pack(side="left")
    app["footer_time"] = label(
        app, app["footer"], "", size=8, color=COLORS["muted"], bg=COLORS["background"]
    )
    app["footer_time"].pack(side="right")
    show_view(app, "asientos")


def card_panel(app, parent, *, padding=14):
    return tk.Frame(
        parent,
        bg=COLORS["surface"],
        padx=padding,
        pady=padding,
        highlightbackground=COLORS["border"],
        highlightthickness=1,
    )


def build_room_overview(app):
    app["overview"] = card_panel(app, app["content"], padding=14)
    app["overview"].grid(row=0, column=0, sticky="nsew", padx=(0, 14))
    app["overview"].columnconfigure(0, weight=1)
    app["overview"].rowconfigure(13, weight=1)
    heading = tk.Frame(app["overview"], bg=COLORS["surface"])
    heading.grid(row=0, column=0, sticky="ew")
    label(app, heading, "Resumen de sala", size=12, bold=True).pack(side="left")
    app["room_count_label"] = label(app, heading, "", size=8, color=COLORS["muted"])
    app["room_count_label"].pack(side="right")
    label(app, app["overview"], "SALA ACTUAL", size=8, color=COLORS["muted"]).grid(
        row=1, column=0, sticky="w", pady=(18, 6)
    )
    app["room_combo"] = ttk.Combobox(
        app["overview"], state="readonly", style="Dark.TCombobox", font=("Segoe UI", 9)
    )
    app["room_combo"].grid(row=2, column=0, sticky="ew")
    app["room_combo"].bind("<<ComboboxSelected>>", lambda *_args: on_room_selected(app, *_args))
    app["poster"] = tk.Canvas(app["overview"], height=142, bg="#111821", highlightthickness=0)
    app["poster"].grid(row=3, column=0, sticky="ew", pady=(14, 10))
    app["poster"].bind("<Configure>", lambda *_args: draw_poster(app, *_args))
    label(app, app["overview"], "CAPACIDAD TOTAL", size=8, color=COLORS["muted"]).grid(
        row=4, column=0, sticky="w"
    )
    app["capacity_label"] = label(app, app["overview"], "", size=10, bold=True)
    app["capacity_label"].grid(row=5, column=0, sticky="w", pady=(3, 10))
    ttk.Separator(app["overview"]).grid(row=6, column=0, sticky="ew", pady=4)
    label(app, app["overview"], "Disponibilidad en tiempo real", size=9, bold=True).grid(
        row=7, column=0, sticky="w", pady=(8, 8)
    )
    metrics = tk.Frame(app["overview"], bg=COLORS["surface"])
    metrics.grid(row=8, column=0, sticky="ew")
    for index in range(3):
        metrics.columnconfigure(index, weight=1)
    app["available_metric"] = metric(app, metrics, 0, "LIBRES", COLORS["green"])
    app["selected_metric"] = metric(app, metrics, 1, "SELECCIONADOS", COLORS["blue"])
    app["occupied_metric"] = metric(app, metrics, 2, "OCUPADOS", COLORS["red"])
    app["availability_bar"] = tk.Canvas(
        app["overview"], height=5, bg=COLORS["surface_alt"], highlightthickness=0
    )
    app["availability_bar"].grid(row=9, column=0, sticky="ew", pady=(12, 12))
    app["availability_bar"].bind("<Configure>", lambda *_args: draw_availability(app, *_args))
    button(
        app, app["overview"], "＋  Agregar sala", lambda *_args: add_room(app, *_args), primary=True
    ).grid(row=10, column=0, sticky="ew", pady=(3, 6))
    button(
        app, app["overview"], "⚙  Editar configuración", lambda *_args: edit_room(app, *_args)
    ).grid(row=11, column=0, sticky="ew")
    label(
        app,
        app["overview"],
        "Selecciona un asiento libre para añadirlo a la reserva.",
        size=8,
        color=COLORS["muted"],
        wraplength=250,
        justify="left",
    ).grid(row=12, column=0, sticky="w", pady=(12, 2))


def metric(app, parent, column, title, color):
    box = tk.Frame(parent, bg=COLORS["surface"])
    box.grid(row=0, column=column, sticky="w", padx=(0, 3))
    value = label(app, box, "0", size=18, color=color, bold=True)
    value.pack(anchor="w")
    label(app, box, title, size=7, color=COLORS["muted"]).pack(anchor="w")
    return value


def draw_poster(app, _event=None):
    app["poster"].delete("all")
    width = max(app["poster"].winfo_width(), 240)
    height = 142
    app["poster"].create_rectangle(0, 0, width, height, fill="#131b28", outline="")
    app["poster"].create_rectangle(0, 0, width, height // 2, fill="#202738", outline="")
    app["poster"].create_oval(width * 0.62, 16, width * 0.78, 70, fill="#343753", outline="")
    for index, height_offset in enumerate((30, 52, 40, 65, 34, 55, 42)):
        x = index * width / 6
        app["poster"].create_rectangle(
            x,
            94 - height_offset / 2,
            x + width / 6 + 1,
            height,
            fill="#1c2934" if index % 2 else "#25333b",
            outline="",
        )
        for window_y in range(99, 132, 10):
            app["poster"].create_rectangle(
                x + 5, window_y, x + 8, window_y + 3, fill="#47535b", outline=""
            )
    app["poster"].create_rectangle(
        0, 78, width, height, fill="#0b1018", stipple="gray50", outline=""
    )
    room = get_room(app["store"], app["active_room_id"]) if app["active_room_id"] else None
    movie = room["pelicula"] if room else "Sin película asignada"
    room_name = room["nombre"] if room else "Agrega una sala para comenzar"
    app["poster"].create_text(
        14, 18, anchor="nw", text="EN CARTELERA", fill="#c6bfdc", font=("Segoe UI", 7, "bold")
    )
    app["poster"].create_text(
        14, 78, anchor="sw", text=movie, fill="white", font=("Segoe UI", 17, "bold")
    )
    app["poster"].create_text(
        14,
        99,
        anchor="nw",
        text=f"{room_name}  ·  Función de hoy",
        fill="#c1c2cc",
        font=("Segoe UI", 8),
    )


def draw_availability(app, _event=None):
    app["availability_bar"].delete("all")
    room = get_room(app["store"], app["active_room_id"]) if app["active_room_id"] else None
    if room is None:
        return
    width = app["availability_bar"].winfo_width()
    total = int(room.get("total_asientos") or sum(r["asientos"] for r in room["filas_config"]))
    occupied = len(room["reservas"])
    occupied_width = width * occupied / total if total else 0
    app["availability_bar"].create_rectangle(
        0, 0, width - occupied_width, 5, fill=COLORS["green"], outline=""
    )
    app["availability_bar"].create_rectangle(
        width - occupied_width, 0, width, 5, fill=COLORS["red"], outline=""
    )


def build_seat_view(app):
    app["seat_view"] = tk.Frame(app["content"], bg=COLORS["background"])
    app["seat_view"].grid(row=0, column=1, sticky="nsew")
    app["seat_view"].columnconfigure(0, weight=1)
    app["seat_view"].rowconfigure(1, weight=1)
    top = tk.Frame(app["seat_view"], bg=COLORS["background"])
    top.grid(row=0, column=0, sticky="ew", pady=(0, 12))
    top.columnconfigure(0, weight=1)
    left = tk.Frame(top, bg=COLORS["background"])
    left.grid(row=0, column=0, sticky="w")
    label(app, left, "Distribución de asientos", size=17, bold=True, bg=COLORS["background"]).pack(
        anchor="w"
    )
    app["map_subtitle"] = label(
        app, left, "", size=9, color=COLORS["muted"], bg=COLORS["background"]
    )
    app["map_subtitle"].pack(anchor="w", pady=(3, 0))
    app["dimensions_badge"] = label(
        app, top, "", size=8, color=COLORS["muted"], bg=COLORS["surface"], padx=10, pady=7
    )
    app["dimensions_badge"].grid(row=0, column=1, sticky="e")
    app["map_card"] = card_panel(app, app["seat_view"], padding=12)
    app["map_card"].grid(row=1, column=0, sticky="nsew")
    app["map_card"].columnconfigure(0, weight=1)
    app["map_card"].rowconfigure(1, weight=1)
    app["screen_canvas"] = tk.Canvas(
        app["map_card"], height=42, bg=COLORS["surface"], highlightthickness=0
    )
    app["screen_canvas"].grid(row=0, column=0, sticky="ew", pady=(0, 8))
    app["screen_canvas"].bind("<Configure>", lambda *_args: draw_screen(app, *_args))
    map_area = tk.Frame(app["map_card"], bg=COLORS["surface"])
    map_area.grid(row=1, column=0, sticky="nsew")
    map_area.columnconfigure(0, weight=1)
    map_area.rowconfigure(0, weight=1)
    app["canvas"] = tk.Canvas(map_area, highlightthickness=0, background=COLORS["surface"])
    vertical_scroll = ttk.Scrollbar(
        map_area, orient="vertical", command=app["canvas"].yview, style="Dark.Vertical.TScrollbar"
    )
    horizontal_scroll = ttk.Scrollbar(
        map_area,
        orient="horizontal",
        command=app["canvas"].xview,
        style="Dark.Horizontal.TScrollbar",
    )
    app["canvas"].configure(
        yscrollcommand=vertical_scroll.set, xscrollcommand=horizontal_scroll.set
    )
    app["canvas"].grid(row=0, column=0, sticky="nsew")
    vertical_scroll.grid(row=0, column=1, sticky="ns")
    horizontal_scroll.grid(row=1, column=0, sticky="ew")
    app["seat_grid"] = tk.Frame(app["canvas"], bg=COLORS["surface"], padx=14, pady=10)
    app["canvas_window"] = app["canvas"].create_window((0, 0), window=app["seat_grid"], anchor="nw")
    app["seat_grid"].bind("<Configure>", lambda *_args: update_scroll_region(app, *_args))
    selection_bar = tk.Frame(app["map_card"], bg=COLORS["surface_alt"], padx=12, pady=10)
    selection_bar.grid(row=2, column=0, sticky="ew", pady=(10, 0))
    selection_bar.columnconfigure(0, weight=1)
    app["selection_summary"] = label(
        app,
        selection_bar,
        "Ningún asiento seleccionado",
        size=9,
        color=COLORS["muted"],
        bg=COLORS["surface_alt"],
    )
    app["selection_summary"].grid(row=0, column=0, sticky="w")
    app["clear_selection_button"] = button(
        app, selection_bar, "Limpiar", lambda *_args: clear_selection(app, *_args), compact=True
    )
    app["clear_selection_button"].grid(row=0, column=1, padx=(8, 6))
    app["reserve_button"] = button(
        app,
        selection_bar,
        "✓  Reservar asientos",
        lambda *_args: reserve_selected(app, *_args),
        primary=True,
    )
    app["reserve_button"].grid(row=0, column=2)
    app["clear_room_button"] = button(
        app,
        selection_bar,
        "Limpiar sala",
        lambda *_args: clear_room_reservations_action(app, *_args),
        compact=True,
    )
    app["clear_room_button"].grid(row=0, column=3, padx=(6, 0))
    legend = tk.Frame(app["map_card"], bg=COLORS["surface"])
    legend.grid(row=3, column=0, sticky="ew", pady=(10, 0))
    legend_item(app, legend, COLORS["green"], "Disponible").pack(side="left", padx=(0, 16))
    legend_item(app, legend, COLORS["blue"], "Seleccionado").pack(side="left", padx=16)
    legend_item(app, legend, COLORS["red"], "Ocupado").pack(side="left", padx=16)


def legend_item(app, parent, color, text):
    item = tk.Frame(parent, bg=COLORS["surface"])
    tk.Label(item, text="●", bg=COLORS["surface"], fg=color, font=("Segoe UI", 9)).pack(
        side="left", padx=(0, 5)
    )
    label(app, item, text, size=8, color=COLORS["muted"]).pack(side="left")
    return item


def draw_screen(app, event=None):
    app["screen_canvas"].delete("all")
    width = event.width if event else app["screen_canvas"].winfo_width()
    if width < 40:
        return
    center = width / 2
    app["screen_canvas"].create_arc(
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
    app["screen_canvas"].create_text(
        center, 25, text="P A N T A L L A", fill=COLORS["muted"], font=("Segoe UI", 7, "bold")
    )


def build_reservations_view(app):
    app["reservations_view"] = tk.Frame(app["content"], bg=COLORS["background"])
    app["reservations_view"].grid(row=0, column=1, sticky="nsew")
    app["reservations_view"].columnconfigure(0, weight=1)
    app["reservations_view"].rowconfigure(1, weight=1)
    heading = tk.Frame(app["reservations_view"], bg=COLORS["background"])
    heading.grid(row=0, column=0, sticky="ew", pady=(0, 12))
    label(app, heading, "Reservas", size=17, bold=True, bg=COLORS["background"]).pack(anchor="w")
    label(
        app,
        heading,
        "Entradas registradas para la sala seleccionada.",
        size=9,
        color=COLORS["muted"],
        bg=COLORS["background"],
    ).pack(anchor="w", pady=(3, 0))
    card = card_panel(app, app["reservations_view"], padding=10)
    card.grid(row=1, column=0, sticky="nsew")
    card.columnconfigure(0, weight=1)
    card.rowconfigure(0, weight=1)
    columns = ("fila", "asiento", "ticket", "sala")
    app["reservations_table"] = ttk.Treeview(
        card, columns=columns, show="headings", style="Dark.Treeview"
    )
    for column, title, width in (
        ("fila", "FILA", 90),
        ("asiento", "ASIENTO", 100),
        ("ticket", "NÚMERO DE ENTRADA", 220),
        ("sala", "SALA", 220),
    ):
        app["reservations_table"].heading(column, text=title)
        app["reservations_table"].column(column, width=width, anchor="w")
    app["reservations_table"].grid(row=0, column=0, sticky="nsew")
    scroll = ttk.Scrollbar(
        card,
        orient="vertical",
        command=app["reservations_table"].yview,
        style="Dark.Vertical.TScrollbar",
    )
    scroll.grid(row=0, column=1, sticky="ns")
    app["reservations_table"].configure(yscrollcommand=scroll.set)
    app["reservations_table"].bind("<Double-1>", lambda *_args: release_from_table(app, *_args))


def build_activity_view(app):
    app["activity_view"] = tk.Frame(app["content"], bg=COLORS["background"])
    app["activity_view"].grid(row=0, column=1, sticky="nsew")
    app["activity_view"].columnconfigure(0, weight=1)
    app["activity_view"].rowconfigure(1, weight=1)
    heading = tk.Frame(app["activity_view"], bg=COLORS["background"])
    heading.grid(row=0, column=0, sticky="ew", pady=(0, 12))
    label(app, heading, "Actividad reciente", size=17, bold=True, bg=COLORS["background"]).pack(
        anchor="w"
    )
    label(
        app,
        heading,
        "Historial de operaciones de esta sesión.",
        size=9,
        color=COLORS["muted"],
        bg=COLORS["background"],
    ).pack(anchor="w", pady=(3, 0))
    app["activity_card"] = card_panel(app, app["activity_view"], padding=12)
    app["activity_card"].grid(row=1, column=0, sticky="nsew")
    app["activity_card"].columnconfigure(0, weight=1)
    app["activity_card"].rowconfigure(0, weight=1)
    app["activity_list"] = tk.Listbox(
        app["activity_card"],
        bg=COLORS["surface"],
        fg=COLORS["text"],
        selectbackground="#302b55",
        selectforeground=COLORS["text"],
        relief="flat",
        borderwidth=0,
        highlightthickness=0,
        font=("Segoe UI", 10),
        activestyle="none",
    )
    app["activity_list"].grid(row=0, column=0, sticky="nsew")
    scroll = ttk.Scrollbar(
        app["activity_card"],
        orient="vertical",
        command=app["activity_list"].yview,
        style="Dark.Vertical.TScrollbar",
    )
    scroll.grid(row=0, column=1, sticky="ns")
    app["activity_list"].configure(yscrollcommand=scroll.set)


def show_view(app, view):
    app["current_view"] = view
    for name, frame in (
        ("asientos", app["seat_view"]),
        ("reservas", app["reservations_view"]),
        ("actividad", app["activity_view"]),
    ):
        frame.grid_remove()
        button = app["nav_buttons"][name]
        button.configure(
            fg=COLORS["text"] if name == view else COLORS["muted"],
            highlightthickness=0,
            underline=0,
        )
        if name == view:
            button.configure(fg=COLORS["purple_light"], highlightthickness=0, relief="flat")
        if name == view:
            frame.grid()
    app["overview"].grid()
    if view == "asientos":
        render_room(app)


def record_activity(app, text):
    timestamp = datetime.now().strftime("%H:%M")
    app["activity_entries"].insert(0, f"{timestamp}   ·   {text}")
    app["activity_list"].delete(0, tk.END)
    for entry in app["activity_entries"]:
        app["activity_list"].insert(tk.END, entry)
    app["footer_time"].configure(
        text=f"Última actualización: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    )


def update_scroll_region(app, _event=None):
    app["canvas"].configure(scrollregion=app["canvas"].bbox("all"))


def refresh_rooms(app):
    app["room_ids_by_label"].clear()
    labels = []
    rooms = list_rooms(app["store"])
    for room in rooms:
        label = f"{room['id']}  ·  {room['nombre']}"
        labels.append(label)
        app["room_ids_by_label"][label] = room["id"]
    app["room_combo"]["values"] = labels
    if app["active_room_id"] and get_room(app["store"], app["active_room_id"]):
        selected = next(
            (
                label
                for label, room_id in app["room_ids_by_label"].items()
                if room_id == app["active_room_id"]
            )
        )
        app["room_combo"].set(selected)
    elif labels:
        app["active_room_id"] = app["room_ids_by_label"][labels[0]]
        app["room_combo"].set(labels[0])
    else:
        app["active_room_id"] = None
        app["room_combo"].set("")
    app["room_count_label"].configure(text=f"{len(rooms):02d} SALA(S)")
    refresh_reservations(app)
    render_room(app)


def refresh_reservations(app):
    for item in app["reservations_table"].get_children():
        app["reservations_table"].delete(item)
    room = get_room(app["store"], app["active_room_id"]) if app["active_room_id"] else None
    if room is None:
        return
    for position, reservation in sorted(room["reservas"].items()):
        row, seat = map(int, position.split("_"))
        app["reservations_table"].insert(
            "",
            tk.END,
            values=(f"F{row + 1}", f"C{seat + 1}", reservation["ticket"], room["nombre"]),
        )


def on_room_selected(app, _event=None):
    app["active_room_id"] = app["room_ids_by_label"].get(app["room_combo"].get())
    app["selected_seats"].clear()
    render_room(app)
    refresh_reservations(app)


def _room_layout_payload(room):
    return {
        "nombre": room["nombre"],
        "pelicula": room["pelicula"],
        "filas_config": [
            {"id_fila": row["id_fila"], "asientos": int(row["asientos"])}
            for row in room.get("filas_config", [])
        ],
    }


def _apply_room_layout_change(app, room, filas_config, activity=None):
    try:
        update_room(
            app["store"],
            room["id"],
            {
                "nombre": room["nombre"],
                "pelicula": room["pelicula"],
                "filas_config": filas_config,
            },
        )
    except (OSError, ValueError) as error:
        messagebox.showerror("No se pudo modificar la sala", str(error), parent=app["root"])
        return
    if activity:
        record_activity(app, activity)
    refresh_rooms(app)


def add_seat_to_row(app, row_index):
    room = get_room(app["store"], app["active_room_id"]) if app["active_room_id"] else None
    if room is None:
        return
    layout = _room_layout_payload(room)["filas_config"]
    if row_index < 0 or row_index >= len(layout):
        return
    if layout[row_index]["asientos"] >= MAX_ASIENTOS_POR_FILA:
        messagebox.showinfo(
            "L?mite de asientos",
            f"Cada fila permite como m?ximo {MAX_ASIENTOS_POR_FILA} asientos.",
            parent=app["root"],
        )
        return
    layout[row_index]["asientos"] += 1
    _apply_room_layout_change(
        app, room, layout, f"Asiento agregado en F{row_index + 1:02d} ? {room['nombre']}"
    )


def remove_seat_from_row(app, row_index):
    room = get_room(app["store"], app["active_room_id"]) if app["active_room_id"] else None
    if room is None:
        return
    layout = _room_layout_payload(room)["filas_config"]
    if row_index < 0 or row_index >= len(layout):
        return
    if layout[row_index]["asientos"] <= 1:
        messagebox.showinfo(
            "L?mite de asientos",
            "Cada fila debe tener al menos 1 asiento.",
            parent=app["root"],
        )
        return
    layout[row_index]["asientos"] -= 1
    _apply_room_layout_change(
        app, room, layout, f"Asiento quitado en F{row_index + 1:02d} ? {room['nombre']}"
    )


def add_row_end(app):
    room = get_room(app["store"], app["active_room_id"]) if app["active_room_id"] else None
    if room is None:
        return
    layout = _room_layout_payload(room)["filas_config"]
    if len(layout) >= MAX_FILAS:
        messagebox.showinfo(
            "L?mite de filas",
            f"La sala permite como m?ximo {MAX_FILAS} filas.",
            parent=app["root"],
        )
        return
    default_seats = layout[-1]["asientos"] if layout else 8
    layout.append({"id_fila": None, "asientos": int(default_seats)})
    _apply_room_layout_change(app, room, layout, f"Fila agregada ? {room['nombre']}")


def remove_row(app, row_index):
    room = get_room(app["store"], app["active_room_id"]) if app["active_room_id"] else None
    if room is None:
        return
    layout = _room_layout_payload(room)["filas_config"]
    if row_index < 0 or row_index >= len(layout):
        return
    if len(layout) <= 1:
        messagebox.showinfo(
            "L?mite de filas",
            "La sala debe tener al menos una fila.",
            parent=app["root"],
        )
        return
    layout.pop(row_index)
    _apply_room_layout_change(
        app, room, layout, f"Fila F{row_index + 1:02d} quitada ? {room['nombre']}"
    )


def render_room(app):
    for child in app["seat_grid"].winfo_children():
        child.destroy()
    room = get_room(app["store"], app["active_room_id"]) if app["active_room_id"] else None
    if room is None:
        app["capacity_label"].configure(text="Sin sala")
        app["map_subtitle"].configure(text="Agrega una sala para administrar sus asientos.")
        app["dimensions_badge"].configure(text="SIN SALA")
        update_metrics(app, 0, 0, 0)
        draw_poster(app)
        draw_availability(app)
        return

    filas_config = room.get("filas_config") or []
    seat_counts = [int(row["asientos"]) for row in filas_config]
    total = int(room.get("total_asientos") or sum(seat_counts))
    occupied = len(room["reservas"])
    selected = 0
    for row, seat in list(app["selected_seats"]):
        if row < len(seat_counts) and seat < seat_counts[row]:
            if f"{row}_{seat}" not in room["reservas"]:
                selected += 1
    available = total - occupied
    formato = "Formato est?ndar" if len(set(seat_counts)) <= 1 else "Formato variable"
    app["capacity_label"].configure(text=f"{total} asientos  ?  {formato}")
    app["map_subtitle"].configure(
        text=(
            f"{room['nombre']}  ?  Funci?n de hoy, 19:30  ?  "
            "Usa +/? al final de cada fila para ajustar asientos"
        )
    )
    if seat_counts and len(set(seat_counts)) == 1:
        badge = f"{len(seat_counts)} FILAS  ?  {seat_counts[0]} ASIENTOS"
    elif seat_counts:
        badge = f"{len(seat_counts)} FILAS  ?  {min(seat_counts)}-{max(seat_counts)} ASIENTOS"
    else:
        badge = "SIN FILAS"
    app["dimensions_badge"].configure(text=badge)
    update_metrics(app, available, selected, occupied)
    draw_poster(app)

    max_columns = max(seat_counts) if seat_counts else 0
    label(app, app["seat_grid"], "", size=7, color=COLORS["muted"]).grid(
        row=0, column=0, padx=(0, 8)
    )
    for column in range(max_columns):
        label(app, app["seat_grid"], f"C{column + 1:02d}", size=7, color=COLORS["muted"]).grid(
            row=0, column=column + 1, padx=4, pady=(0, 8)
        )
    label(app, app["seat_grid"], "AJUSTES", size=7, color=COLORS["muted"]).grid(
        row=0, column=max_columns + 1, padx=(10, 4), pady=(0, 8), sticky="w"
    )
    app["seat_buttons"] = {}
    for row_index, row_info in enumerate(filas_config):
        row_seats = int(row_info["asientos"])
        offset = (max_columns - row_seats) // 2
        label(
            app,
            app["seat_grid"],
            f"F{row_index + 1:02d}",
            size=8,
            color=COLORS["muted"],
        ).grid(row=row_index + 1, column=0, padx=(0, 8), pady=4, sticky="e")
        for seat in range(row_seats):
            position = f"{row_index}_{seat}"
            reservation = room["reservas"].get(position)
            is_selected = (row_index, seat) in app["selected_seats"] and not reservation
            if reservation:
                color = OCCUPIED_COLOR
                foreground = "#ff8aa8"
            elif is_selected:
                color = SELECTED_COLOR
                foreground = "#a9c5ff"
            else:
                color = FREE_COLOR
                foreground = "#78e4c4"
            seat_button = tk.Button(
                app["seat_grid"],
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
                command=lambda r=row_index, s=seat: on_seat_click(app, r, s),
            )
            seat_button.grid(row=row_index + 1, column=offset + seat + 1, padx=3, pady=3)
            app["seat_buttons"][row_index, seat] = seat_button

        controls = tk.Frame(app["seat_grid"], bg=COLORS["surface"])
        controls.grid(row=row_index + 1, column=max_columns + 1, padx=(10, 4), pady=3, sticky="w")
        for text, command, bg, fg in (
            (
                "-",
                lambda r=row_index: remove_seat_from_row(app, r),
                COLORS["surface_alt"],
                COLORS["text"],
            ),
            (
                "+",
                lambda r=row_index: add_seat_to_row(app, r),
                COLORS["surface_alt"],
                COLORS["text"],
            ),
            (
                "Quitar fila",
                lambda r=row_index: remove_row(app, r),
                "#3a1f2a",
                "#ff8aa8",
            ),
        ):
            tk.Button(
                controls,
                text=text,
                command=command,
                relief="flat",
                borderwidth=0,
                padx=8 if text != "Quitar fila" else 10,
                pady=4,
                background=bg,
                foreground=fg,
                activebackground=COLORS["border"],
                activeforeground="white",
                font=("Segoe UI", 8, "bold"),
                cursor="hand2",
            ).pack(side="left", padx=2)

    add_row = tk.Button(
        app["seat_grid"],
        text="+ Agregar fila",
        command=lambda: add_row_end(app),
        relief="flat",
        borderwidth=0,
        padx=12,
        pady=6,
        background=COLORS["surface_alt"],
        foreground=COLORS["green"],
        activebackground=COLORS["border"],
        activeforeground="white",
        font=("Segoe UI", 9, "bold"),
        cursor="hand2",
    )
    add_row.grid(
        row=len(filas_config) + 1,
        column=1,
        columnspan=max(2, max_columns),
        pady=(14, 4),
        sticky="w",
    )

    app["selection_summary"].configure(
        text=(
            f"{selected} asiento(s) seleccionado(s)  ?  "
            "el mismo n?mero de entrada se asignar? a todos"
        )
        if selected
        else "Selecciona uno o varios asientos disponibles",
        fg=COLORS["blue"] if selected else COLORS["muted"],
    )
    app["reserve_button"].configure(state="normal" if selected else "disabled")
    app["clear_selection_button"].configure(state="normal" if selected else "disabled")
    if "clear_room_button" in app:
        app["clear_room_button"].configure(state="normal" if occupied > 0 else "disabled")
    app["seat_grid"].update_idletasks()
    update_scroll_region(app)
    draw_availability(app)


def update_metrics(app, available, selected, occupied):
    app["available_metric"].configure(text=f"{available:02d}")
    app["selected_metric"].configure(text=f"{selected:02d}")
    app["occupied_metric"].configure(text=f"{occupied:02d}")


def on_seat_click(app, row, seat):
    room = get_room(app["store"], app["active_room_id"])
    if room is None:
        return
    position = f"{row}_{seat}"
    reservation = room["reservas"].get(position)
    if reservation:
        show_reservation(app, room, position, row, seat, reservation)
        return
    coordinate = (row, seat)
    if coordinate in app["selected_seats"]:
        app["selected_seats"].remove(coordinate)
    else:
        app["selected_seats"].add(coordinate)
    render_room(app)


def clear_selection(app):
    app["selected_seats"].clear()
    render_room(app)


def clear_room_reservations_action(app):
    room = get_room(app["store"], app["active_room_id"]) if app["active_room_id"] else None
    if room is None:
        return
    if not room["reservas"]:
        messagebox.showinfo(
            "Limpiar sala",
            "No hay asientos ocupados en esta sala.",
            parent=app["root"],
        )
        return
    confirmed = messagebox.askyesno(
        "Limpiar sala",
        f"¿Deseas liberar todos los asientos ocupados de {room['nombre']}?\n\n"
        "Esta acción quitará todas las reservas de la sala.",
        parent=app["root"],
    )
    if not confirmed:
        return
    try:
        cleared = clear_room_reservations(app["store"], room["id"])
    except (OSError, ValueError) as error:
        messagebox.showerror("No se pudo limpiar la sala", str(error), parent=app["root"])
        return
    app["selected_seats"].clear()
    record_activity(
        app,
        f"Sala limpiada · {cleared} asiento(s) liberado(s) · {room['nombre']}",
    )
    refresh_rooms(app)


def reserve_selected(app):
    room = get_room(app["store"], app["active_room_id"])
    if room is None or not app["selected_seats"]:
        return
    ticket = ticket_dialog(app, len(app["selected_seats"]))
    if ticket is None:
        return
    reservations = {
        f"{row}_{seat}": {"ticket": ticket, "usuario": ""} for row, seat in app["selected_seats"]
    }
    try:
        set_reservations(app["store"], room["id"], reservations)
    except (OSError, ValueError) as error:
        messagebox.showerror("Error al reservar", str(error), parent=app["root"])
        app["selected_seats"].clear()
        refresh_rooms(app)
        return
    reserved_count = len(app["selected_seats"])
    app["selected_seats"].clear()
    record_activity(
        app, f"{reserved_count} asiento(s) reservado(s) · Entrada {ticket} · {room['nombre']}"
    )
    refresh_rooms(app)


def ticket_dialog(app, seat_count):
    dialog = tk.Toplevel(app["root"])
    dialog.title("Confirmar reserva")
    dialog.configure(bg=COLORS["background"])
    dialog.transient(app["root"])
    dialog.resizable(False, False)
    dialog.grab_set()
    dialog.geometry("440x280")
    dialog.columnconfigure(0, weight=1)
    card = card_panel(app, dialog, padding=22)
    card.grid(row=0, column=0, sticky="nsew", padx=14, pady=14)
    label(app, card, "Confirmar reserva", size=15, bold=True).pack(anchor="w")
    label(
        app,
        card,
        f"Vas a reservar {seat_count} asiento(s). Escribe el número de entrada.",
        size=9,
        color=COLORS["muted"],
        wraplength=350,
        justify="left",
    ).pack(anchor="w", pady=(8, 18))
    label(app, card, "NÚMERO DE ENTRADA", size=8, color=COLORS["muted"]).pack(anchor="w")
    entry = tk.Entry(
        card,
        bg=COLORS["surface_alt"],
        fg=COLORS["text"],
        insertbackground=COLORS["text"],
        relief="flat",
        font=("Segoe UI", 10),
        highlightthickness=1,
        highlightbackground=COLORS["border"],
        highlightcolor=COLORS["purple"],
        bd=0,
    )
    entry.pack(fill="x", ipady=9, pady=(6, 14))
    result = {"ticket": None}

    def confirm():
        ticket = entry.get().strip()
        if not ticket:
            messagebox.showwarning(
                "Entrada obligatoria", "Escribe un número de entrada para continuar.", parent=dialog
            )
            entry.focus_set()
            return
        result["ticket"] = ticket
        dialog.destroy()

    buttons = tk.Frame(card, bg=COLORS["surface"])
    buttons.pack(fill="x")
    button(app, buttons, "Cancelar", dialog.destroy).pack(side="right")
    button(app, buttons, "✓  Confirmar reserva", confirm, primary=True).pack(
        side="right", padx=(0, 8)
    )
    dialog.bind("<Return>", lambda _event: confirm())
    dialog.bind("<Escape>", lambda _event: dialog.destroy())
    entry.focus_set()
    app["root"].wait_window(dialog)
    return result["ticket"]


def show_reservation(app, room, position, row, seat, reservation):
    dialog = tk.Toplevel(app["root"])
    dialog.title("Detalle del asiento")
    dialog.configure(bg=COLORS["background"])
    dialog.transient(app["root"])
    dialog.resizable(False, False)
    dialog.grab_set()
    card = card_panel(app, dialog, padding=20)
    card.pack(fill="both", expand=True, padx=14, pady=14)
    label(app, card, f"Asiento F{row + 1} · C{seat + 1}", size=15, bold=True).pack(anchor="w")
    label(app, card, room["nombre"], size=9, color=COLORS["muted"]).pack(anchor="w", pady=(3, 16))
    label(app, card, "NÚMERO DE ENTRADA", size=8, color=COLORS["muted"]).pack(anchor="w")
    label(app, card, reservation["ticket"], size=12, bold=True).pack(anchor="w", pady=(4, 18))
    actions = tk.Frame(card, bg=COLORS["surface"])
    actions.pack(fill="x")

    def release():
        try:
            set_reservation(app["store"], room["id"], position, None)
        except (OSError, ValueError) as error:
            messagebox.showerror("Error al liberar", str(error), parent=dialog)
            return
        dialog.destroy()
        record_activity(app, f"Asiento F{row + 1} · C{seat + 1} liberado · {room['nombre']}")
        refresh_rooms(app)

    button(app, actions, "Cerrar", dialog.destroy).pack(side="right")
    button(app, actions, "Liberar asiento", release, danger=True).pack(side="right", padx=(0, 8))
    dialog.bind("<Escape>", lambda _event: dialog.destroy())


def release_from_table(app, _event=None):
    selection = app["reservations_table"].selection()
    if not selection:
        return
    values = app["reservations_table"].item(selection[0], "values")
    room = get_room(app["store"], app["active_room_id"]) if app["active_room_id"] else None
    if room is None:
        return
    row, seat = (int(values[0][1:]) - 1, int(values[1][1:]) - 1)
    position = f"{row}_{seat}"
    reservation = room["reservas"].get(position)
    if reservation:
        show_reservation(app, room, position, row, seat, reservation)


def add_room(app):
    values = room_dialog(app, "Agregar sala")
    if values is None:
        return
    rooms = list_rooms(app["store"])
    numbers = [
        int(match.group(1)) for room in rooms if (match := re.fullmatch(r"SALA-(\d+)", room["id"]))
    ]
    room_id = f"SALA-{max(numbers, default=0) + 1}"
    room = {"id": room_id, **values, "reservas": {}}
    try:
        save_room(app["store"], room)
    except (OSError, ValueError) as error:
        messagebox.showerror("Error al agregar sala", str(error), parent=app["root"])
        return
    app["active_room_id"] = room_id
    record_activity(app, f"Sala agregada ? {values['nombre']}")
    refresh_rooms(app)


def edit_room(app):
    room = get_room(app["store"], app["active_room_id"]) if app["active_room_id"] else None
    if room is None:
        messagebox.showinfo(
            "Editar sala", "Primero agrega o selecciona una sala.", parent=app["root"]
        )
        return
    values = room_dialog(app, "Editar sala", room)
    if values is None:
        return
    try:
        update_room(app["store"], room["id"], values)
    except (OSError, ValueError) as error:
        messagebox.showerror("Error al editar sala", str(error), parent=app["root"])
        return
    record_activity(app, f"Configuraci?n actualizada ? {room['nombre']}")
    refresh_rooms(app)


def room_dialog(app, title, room=None):
    dialog = tk.Toplevel(app["root"])
    dialog.title(title)
    dialog.configure(bg=COLORS["background"])
    dialog.transient(app["root"])
    dialog.resizable(True, True)
    dialog.grab_set()
    dialog.geometry("560x520")

    frame = ttk.Frame(dialog, padding=16)
    frame.pack(fill="both", expand=True)
    frame.columnconfigure(0, weight=1)
    frame.rowconfigure(4, weight=1)

    ttk.Label(frame, text="Nombre de la sala").grid(row=0, column=0, sticky="w", pady=(0, 4))
    name_entry = ttk.Entry(frame)
    name_entry.grid(row=1, column=0, sticky="ew", pady=(0, 10))
    name_entry.insert(0, room["nombre"] if room else "")

    ttk.Label(frame, text="Pel?cula asignada").grid(row=2, column=0, sticky="w", pady=(0, 4))
    movie_entry = ttk.Entry(frame)
    movie_entry.grid(row=3, column=0, sticky="ew", pady=(0, 12))
    movie_entry.insert(0, room["pelicula"] if room else "")

    editor = ttk.LabelFrame(frame, text="Filas de la sala (configuraci?n particular)")
    editor.grid(row=4, column=0, sticky="nsew")
    editor.columnconfigure(0, weight=1)
    editor.rowconfigure(0, weight=1)

    columns = ("fila", "asientos")
    tree = ttk.Treeview(editor, columns=columns, show="headings", height=10, style="Dark.Treeview")
    tree.heading("fila", text="FILA")
    tree.heading("asientos", text="ASIENTOS")
    tree.column("fila", width=140, anchor="w")
    tree.column("asientos", width=140, anchor="w")
    tree.grid(row=0, column=0, sticky="nsew", padx=(10, 0), pady=10)
    scroll = ttk.Scrollbar(
        editor, orient="vertical", command=tree.yview, style="Dark.Vertical.TScrollbar"
    )
    scroll.grid(row=0, column=1, sticky="ns", pady=10, padx=(0, 10))
    tree.configure(yscrollcommand=scroll.set)

    controls = ttk.Frame(editor)
    controls.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 10))
    ttk.Label(controls, text="Asientos de la fila (1?30):").pack(side="left")
    seats_var = tk.StringVar(value="8")
    seats_spin = tk.Spinbox(
        controls, from_=1, to=MAX_ASIENTOS_POR_FILA, width=6, textvariable=seats_var
    )
    seats_spin.pack(side="left", padx=(8, 12))

    row_state = {"rows": []}

    def refresh_tree():
        for item in tree.get_children():
            tree.delete(item)
        for index, row in enumerate(row_state["rows"], start=1):
            tree.insert("", tk.END, iid=str(index - 1), values=(f"F{index:02d}", row["asientos"]))

    def read_seats():
        try:
            value = int(seats_var.get().strip())
        except ValueError:
            return None
        if not 1 <= value <= MAX_ASIENTOS_POR_FILA:
            return None
        return value

    def add_row():
        if len(row_state["rows"]) >= MAX_FILAS:
            messagebox.showwarning(
                "L?mite de filas",
                f"La sala permite como m?ximo {MAX_FILAS} filas.",
                parent=dialog,
            )
            return
        seats = read_seats()
        if seats is None:
            messagebox.showwarning(
                "Valor inv?lido",
                "Ingresa una cantidad de asientos entre 1 y 30.",
                parent=dialog,
            )
            return
        row_state["rows"].append({"id_fila": None, "asientos": seats})
        refresh_tree()
        tree.selection_set(str(len(row_state["rows"]) - 1))

    def change_row():
        selection = tree.selection()
        if not selection:
            messagebox.showinfo(
                "Selecciona una fila", "Elige la fila que deseas cambiar.", parent=dialog
            )
            return
        seats = read_seats()
        if seats is None:
            messagebox.showwarning(
                "Valor inv?lido",
                "Ingresa una cantidad de asientos entre 1 y 30.",
                parent=dialog,
            )
            return
        index = int(selection[0])
        row_state["rows"][index]["asientos"] = seats
        refresh_tree()
        tree.selection_set(str(index))

    def remove_row():
        selection = tree.selection()
        if not selection:
            messagebox.showinfo(
                "Selecciona una fila", "Elige la fila que deseas quitar.", parent=dialog
            )
            return
        index = int(selection[0])
        row_state["rows"].pop(index)
        refresh_tree()

    buttons = ttk.Frame(editor)
    buttons.grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 10))
    ttk.Button(buttons, text="Agregar fila al final", command=add_row).pack(
        side="left", padx=(0, 6)
    )
    ttk.Button(buttons, text="Cambiar asientos", command=change_row).pack(side="left", padx=6)
    ttk.Button(buttons, text="Quitar fila seleccionada", command=remove_row).pack(
        side="left", padx=6
    )

    initial_rows = (
        [{"id_fila": r["id_fila"], "asientos": int(r["asientos"])} for r in room["filas_config"]]
        if room and room.get("filas_config")
        else [{"id_fila": None, "asientos": 8} for _ in range(5)]
    )
    row_state["rows"] = initial_rows
    refresh_tree()

    result = {"value": None}

    def submit():
        name = name_entry.get().strip()
        movie = movie_entry.get().strip()
        if not name or not movie:
            messagebox.showwarning(
                "Datos obligatorios",
                "El nombre de la sala y la pel?cula son obligatorios.",
                parent=dialog,
            )
            return
        if not row_state["rows"]:
            messagebox.showwarning(
                "Configuraci?n inv?lida",
                "La sala debe tener al menos una fila.",
                parent=dialog,
            )
            return
        result["value"] = {
            "nombre": name,
            "pelicula": movie,
            "filas_config": [dict(row) for row in row_state["rows"]],
        }
        dialog.destroy()

    footer = ttk.Frame(frame)
    footer.grid(row=5, column=0, sticky="e", pady=(12, 0))
    ttk.Button(footer, text="Cancelar", command=dialog.destroy).pack(side="left", padx=4)
    ttk.Button(footer, text="Guardar", command=submit).pack(side="left", padx=4)
    dialog.bind("<Escape>", lambda _event: dialog.destroy())
    name_entry.focus_set()
    app["root"].wait_window(dialog)
    return result["value"]


def main():
    root = tk.Tk()
    app = create_app(root)
    if not app["closed"]:
        root.mainloop()
