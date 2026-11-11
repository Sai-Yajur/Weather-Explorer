import os
import random
import threading
import tkinter as tk
from datetime import datetime, timezone, timedelta
import requests
import customtkinter as ctk
from PIL import Image, ImageTk, ImageSequence
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from tkintermapview import TkinterMapView
from config import API_KEY

# OpenStreetMap tile request identification
original_get = requests.get

def weather_explorer_get(url, *args, **kwargs):
    if isinstance(url, str) and "tile.openstreetmap.org" in url:
        headers = dict(kwargs.get("headers") or {})
        headers["User-Agent"] = "WeatherExplorer/1.0"
        kwargs["headers"] = headers

    return original_get(url, *args, **kwargs)

requests.get = weather_explorer_get
# THEME

BG = "#0C1624"
PANEL = "#152235"
PANEL_LIGHT = "#21344F"
ACCENT = "#67E8F9"
ACCENT_DARK = "#22D3EE"
TEXT = "#F1F5F9"
MUTED = "#94A3B8"
BORDER = "#334155"
FONT_MAIN = "Segoe UI"
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")
# CONSTANTS
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_LAT, DEFAULT_LON, DEFAULT_ZOOM = 20.5937, 78.9629, 5
CARD_H, CARD_W, CARD_GAP = 46, 260, 8
CARD_START_Y = 175
CARD_STEP = CARD_H + CARD_GAP
WEATHER_ANIM_MS = 80
STAR_ANIM_MS = 40
STAR_COUNT = 80
CONDITION_EMOJI = {
    "Clear": "\u2600\ufe0f",
    "Clouds": "\u2601\ufe0f",
    "Rain": "\U0001F327\ufe0f",
    "Drizzle": "\U0001F326\ufe0f",
    "Thunderstorm": "\u26c8\ufe0f",
    "Snow": "\u2744\ufe0f",
    "Mist": "\U0001F32B\ufe0f",
    "Fog": "\U0001F32B\ufe0f",
    "Haze": "\U0001F32B\ufe0f",
}
CONDITION_BACKGROUNDS = {
    "Clear": "weather/clear.gif",
    "Clouds": "weather/clouds.gif",
    "Rain": "weather/rain.gif",
    "Thunderstorm": "weather/thunder.gif",
    "Snow": "weather/snow.gif",
    "Mist": "weather/mist.gif",
}
# GLOBAL STATE
stars = []
stars_running = False
weather_frames = []
weather_job = None
clock_offset = 0
current_lat = current_lon = None
current_lat_map, current_lon_map = DEFAULT_LAT, DEFAULT_LON
selected_marker = None
# HELPERS
def run_async(fn, *args):
    threading.Thread(target=fn, args=args, daemon=True).start()
def bg_path(name):
    return os.path.join(BASE_DIR, name)
# API: GEOCODING
def get_lat_lon(query):
    try:
        r = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"format": "json", "q": query, "limit": 1},
            headers={"User-Agent": "WeatherExplorerApp/1.0"},
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        if not data:
            return None
        return float(data[0]["lat"]), float(data[0]["lon"])
    except (requests.RequestException, ValueError, KeyError, IndexError) as err:
        print("Geocoding failed:", err)
        return None
# API: WEATHER
def get_weather(lat, lon):
    url = (
        "https://api.openweathermap.org/data/2.5/weather"
        f"?lat={lat}&lon={lon}&appid={API_KEY}&units=metric"
    )
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        if r.status_code != 200:
            print("Weather API error:", data)
            return None
        main, wind, clouds = data["main"], data["wind"], data["clouds"]
        tz = data["timezone"]
        return {
            "city": data.get("name", "Unknown"),
            "country": data["sys"]["country"],
            "temp": main["temp"],
            "humidity": main["humidity"],
            "wind": wind["speed"],
            "clouds": clouds["all"],
            "condition": data["weather"][0]["main"],
            "local_time": (datetime.now(timezone.utc) + timedelta(seconds=tz)).strftime("%I:%M %p"),
            "tz": tz,
        }
    except (requests.RequestException, ValueError, KeyError, IndexError) as err:
        print("Weather fetch failed:", err)
        return None
def get_forecast(lat, lon):
    url = (
        "https://api.openweathermap.org/data/2.5/forecast"
        f"?lat={lat}&lon={lon}&appid={API_KEY}&units=metric"
    )
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        if r.status_code != 200:
            print("Forecast API error:", data)
            return
        daily = [
            (item["dt_txt"][:10], item["main"]["temp"])
            for item in data.get("list", [])
            if "12:00:00" in item["dt_txt"]
        ][:5]
    except (requests.RequestException, ValueError, KeyError) as err:
        print("Forecast failed:", err)
        return
    if not daily:
        return
    days, temps = [], []
    for day, temp in daily:
        dt = datetime.strptime(day, "%Y-%m-%d")
        days.append(dt.strftime("%a"))
        temps.append(temp)
    # 
    window.after(0, lambda: animate_graph(days, temps))
    window.after(0, lambda: _update_forecast_labels(daily))
def _update_forecast_labels(daily):
    for i, (day, temp) in enumerate(daily):
        dt = datetime.strptime(day, "%Y-%m-%d")
        forecast_labels[i].config(
            text=f"{dt.strftime('%a')} ({dt.strftime('%d %b')})   {temp:.1f}°C"
        )
# NAVIGATION
def show_frame(frame):
    for f in (welcome_frame, map_frame, about_frame):
        f.pack_forget()
    frame.pack(fill="both", expand=True)
def open_about():
    global stars_running
    show_frame(about_frame)
    stars_running = True
    about_frame.after(200, create_stars)
    about_frame.after(400, animate_stars)
def open_menufa():
    global stars_running
    stars_running = False
    show_frame(welcome_frame)
def open_menufm():
    clock_label.place_forget()
    show_frame(welcome_frame)
def open_map():
    global current_lat_map, current_lon_map
    show_frame(map_frame)
    current_lat_map, current_lon_map = DEFAULT_LAT, DEFAULT_LON
    right_frame.update_idletasks()
    load_weather_background("weather/clear.gif")
    window.after(100, lambda: map_widget.set_position(DEFAULT_LAT, DEFAULT_LON))
    window.after(150, lambda: map_widget.set_zoom(DEFAULT_ZOOM))
def show_current():
    forecast_frame.pack_forget()
    current_frame.pack(fill="both", expand=True)
def show_forecast():
    current_frame.pack_forget()
    forecast_frame.pack(fill="both", expand=True)
    if current_lat is not None and current_lon is not None:
        run_async(get_forecast, current_lat, current_lon)
# ANIMATIONS
def animate_webp(i=0):
    try:
        if not window.winfo_exists():
            return
        if not frames:
            window.after(100, animate_webp, i)
            return
        earth_label.config(image=frames[i])
        window.after(30, animate_webp, (i + 1) % len(frames))
    except tk.TclError:
        pass
def animate_weather(i=0):
    global weather_job
    try:
        if not window.winfo_exists() or not weather_frames:
            return
        weather_bg.config(image=weather_frames[i])
        weather_bg.image = weather_frames[i]
        weather_job = window.after(
            WEATHER_ANIM_MS, animate_weather, (i + 1) % len(weather_frames)
        )
    except tk.TclError:
        weather_job = None
def load_weather_background(name):
    global weather_frames, weather_job
    if weather_job:
        try:
            window.after_cancel(weather_job)
        except tk.TclError:
            pass
        weather_job = None
    weather_frames.clear()
    path = bg_path(name)
    if not os.path.exists(path):
        print(f"Missing background asset: {name}")
        return
    right_frame.update_idletasks()
    w = right_frame.winfo_width() or int(W * 0.28)
    h = right_frame.winfo_height() or H
    img = Image.open(path)
    for frame in ImageSequence.Iterator(img):
        frame = frame.copy().resize((w, h), Image.LANCZOS)
        weather_frames.append(ImageTk.PhotoImage(frame))
    animate_weather()
def animate_number(label, prefix, end, suffix="", current=0):
    if current < end:
        label.configure(text=f"{prefix}{current}{suffix}")
        step = max(1, int((end - current) / 8))
        window.after(15, animate_number, label, prefix, end, suffix, current + step)
    else:
        label.configure(text=f"{prefix}{end}{suffix}")
def animate_graph(days, temps, i=1):
    ax.clear()
    ax.set_facecolor(BG)
    fig.patch.set_facecolor(BG)
    ax.tick_params(colors="white")
    for side in ("bottom", "left"):
        ax.spines[side].set_color("white")
    for side in ("top", "right"):
        ax.spines[side].set_color(BG)
    ax.set_title("Temperature Trend", color="white")
    ax.set_xlabel("Day", color="white")
    ax.set_ylabel("°C", color="white")
    ax.grid(True, alpha=0.3)
    ax.plot(days[:i], temps[:i], marker="o", color="cyan", linewidth=3)
    canvas.draw()
    if i < len(days):
        window.after(300, animate_graph, days, temps, i + 1)
def create_stars():
    for s in stars:
        s.destroy()
    stars.clear()
    about_frame.update_idletasks()
    w = about_frame.winfo_width() or W
    h = about_frame.winfo_height() or H
    for _ in range(STAR_COUNT):
        star = tk.Label(about_bg, text="✦", fg="white", bg="black", font=("Arial", 10))
        star.speed = random.randint(1, 3)
        star.place(x=random.randint(0, w), y=random.randint(0, h))
        stars.append(star)
def animate_stars():
    if not stars_running:
        return
    w = about_frame.winfo_width()
    h = about_frame.winfo_height()
    for s in stars:
        x, y = s.winfo_x(), s.winfo_y() + s.speed
        if y > h:
            y, x = 0, random.randint(0, max(w, 1))
        s.place(x=x, y=y)
    window.after(STAR_ANIM_MS, animate_stars)
def draw_clock():
    now = datetime.now(timezone.utc) + timedelta(seconds=clock_offset)
    clock_label.config(text=now.strftime("%H:%M:%S"))
    window.after(1000, draw_clock)
# MAP
def drop_marker(lat, lon, city, country):
    global selected_marker
    if selected_marker is not None:
        try:
            selected_marker.delete()
        except tk.TclError:
            pass
    selected_marker = map_widget.set_marker(lat, lon, text=f"{city}, {country}")
def smooth_zoom(target):
    cur = map_widget.zoom
    if abs(cur - target) < 0.2:
        map_widget.set_zoom(target)
        return
    map_widget.set_zoom(cur + (0.2 if cur < target else -0.2))
    window.after(30, smooth_zoom, target)
def fly_to_location(start_lat, start_lon, end_lat, end_lon):
    global current_lat_map, current_lon_map
    steps = 25
    dlat = (end_lat - start_lat) / steps
    dlon = (end_lon - start_lon) / steps
    def step(i=0):
        global current_lat_map, current_lon_map
        if i < steps:
            current_lat_map += dlat
            current_lon_map += dlon
            map_widget.set_position(current_lat_map, current_lon_map)
            window.after(20, step, i + 1)
        else:
            current_lat_map, current_lon_map = end_lat, end_lon
            map_widget.set_position(end_lat, end_lon)
            smooth_zoom(6)
    step()
# SEARCH PIPELINE
def search_city():
    query = search_entry.get().strip()
    if not query:
        return
    # Direct "lat,lon" or "lat lon"
    try:
        parts = query.replace(",", " ").split()
        if len(parts) == 2:
            lat, lon = float(parts[0]), float(parts[1])
            get_coords((lat, lon))
            return
    except ValueError:
        pass
    def worker():
        coords = get_lat_lon(query)
        window.after(0, lambda: get_coords(coords) if coords
                     else loading_label.config(text="Location not found"))
    run_async(worker)
def get_coords(coords):
    global current_lat, current_lon
    if not coords:
        return
    current_lat, current_lon = coords
    loading_label.config(text="Loading weather...")
    loading_label.place(x=20, y=10)
    def worker():
        result = get_weather(*coords)
        window.after(0, _on_weather_loaded, coords[0], coords[1], result)
    run_async(worker)
def _on_weather_loaded(lat, lon, result):
    global clock_offset
    if not result:
        loading_label.config(text="API Error")
        return
    loading_label.place_forget()
    clock_offset = result["tz"]
    load_weather_background(
        CONDITION_BACKGROUNDS.get(result["condition"], "weather/clear.gif")
    )
    icon = CONDITION_EMOJI.get(result["condition"], "\U0001F324\ufe0f")
    hero_icon.configure(text=icon)
    hero_temp.configure(text=f"{int(result['temp'])}\u00b0")
    hero_condition.configure(
        text=f"{result['condition']} \u00b7 {result['city']}, {result['country']}"
    )
    hero_frame.place(x=30, y=15)
    fly_to_location(current_lat_map, current_lon_map, lat, lon)
    drop_marker(lat, lon, result["city"], result["country"])
    location_label.configure(text=f"Location: {result['country']}, {result['city']}")
    time_label.configure(text=f"Local Time: {result['local_time']}")
    condition_label.configure(text=f"{icon}  Condition: {result['condition']}")
    # Slide-in cards, staggered
    cards = [location_card, time_card, temp_card, humidity_card,
             wind_card, cloud_card, condition_card]
    for i, card in enumerate(cards):
        window.after(i * 80, slide_widget, card, 30, CARD_START_Y + CARD_STEP * i)
    # Number animations
    window.after(800, animate_number, temp_label, "Temp: ", int(result["temp"]), " °C")
    window.after(900, animate_number, humidity_label, "Humidity: ", int(result["humidity"]), "%")
    window.after(1000, animate_number, wind_label, "Wind: ", int(result["wind"]), " m/s")
    window.after(1100, animate_number, cloud_label, "Clouds: ", int(result["clouds"]), "%")
    if forecast_frame.winfo_ismapped():
        run_async(get_forecast, lat, lon)
    clock_label.place(x=30, y=CARD_START_Y + CARD_STEP * 7 - 15)
# UI HELPERS
def slide_widget(widget, target_x, y, current_x=-120):
    if current_x == -120:
        widget.place(x=current_x, y=y)
    if current_x < target_x:
        window.after(15, slide_widget, widget, target_x, y, current_x + 5)
    else:
        widget.place(x=target_x, y=y)
def create_card(parent, y, title):
    card = ctk.CTkFrame(
        parent, width=CARD_W, height=CARD_H,
        fg_color=PANEL, corner_radius=12,
        border_width=1, border_color=BORDER,
    )
    card.place(x=-250, y=y)
    label = ctk.CTkLabel(
        card, text=title, text_color=TEXT, fg_color="transparent",
        font=(FONT_MAIN, 13, "bold"), anchor="w",
    )
    label.pack(expand=True, fill="both", padx=16)
    return card, label
def make_button(parent, text, command, fg=ACCENT, text_color="black", width=160, height=44, font_size=16):
    return ctk.CTkButton(
        parent, text=text, command=command,
        fg_color=fg, hover_color=ACCENT_DARK,
        text_color=text_color, font=(FONT_MAIN, font_size, "bold" if text_color == "black" else "normal"),
        corner_radius=10, width=width, height=height, cursor="hand2",
    )
# MAIN WINDOW
window = ctk.CTk()
window.title("Weather Explorer")
window.state("zoomed")
window.update()
W, H = window.winfo_screenwidth(), window.winfo_screenheight()
# WELCOME
welcome_frame = tk.Frame(window, bg="black")
welcome_frame.pack(fill="both", expand=True)
EARTH_WEBP = os.path.join(BASE_DIR, "earth.webp")
if not os.path.exists(EARTH_WEBP):
    raise FileNotFoundError(
        "earth.webp not found. Place it next to Weather Explorer.py."
    )
webp = Image.open(EARTH_WEBP)
earth_original_frames = [
    f.copy().convert("RGB")
    for f in ImageSequence.Iterator(webp)
]
frames = []
earth_frame_size = (0, 0)
def resize_earth_frames():
    global frames, earth_frame_size
    W, H = welcome_frame.winfo_width(), welcome_frame.winfo_height()
    if W <= 1 or H <= 1:
        window.after(100, resize_earth_frames)
        return
    if (W, H) == earth_frame_size:
        return
    earth_frame_size = (W, H)
    frames = [
        ImageTk.PhotoImage(
            f.resize((W, H), Image.LANCZOS), master=window
        )
        for f in earth_original_frames
    ]
def on_welcome_resize(event):
    if event.widget is welcome_frame:
        resize_earth_frames()
earth_label = tk.Label(welcome_frame, bg="black", borderwidth=0)
earth_label.place(relwidth=1, relheight=1)
welcome_frame.bind("<Configure>", on_welcome_resize)

title_panel = ctk.CTkFrame(welcome_frame, fg_color=PANEL, corner_radius=16)
title_panel.place(x=80, y=90)
ctk.CTkLabel(
    title_panel, text="WEATHER EXPLORER", text_color=TEXT,
    font=(FONT_MAIN, 32, "bold"),
).pack(padx=28, pady=(18, 4))
ctk.CTkLabel(
    title_panel, text="Live weather, forecasts & interactive maps",
    text_color=MUTED, font=(FONT_MAIN, 12),
).pack(padx=28, pady=(0, 18))
make_button(welcome_frame, "ENTER", open_map).place(x=80, y=230)
make_button(welcome_frame, "ABOUT", open_about,
            fg=PANEL_LIGHT, text_color=TEXT, font_size=16).place(x=80, y=290)
#  MAP SCREEN
map_frame = tk.Frame(window, bg="black")
left_frame = tk.Frame(map_frame, bg="black")
left_frame.pack(side="left", fill="both", expand=True)
right_frame = tk.Frame(map_frame, bg=BG, width=int(W * 0.28))
right_frame.pack(side="right", fill="y", anchor="e")
right_frame.pack_propagate(False)
weather_bg = tk.Label(right_frame, bd=0, bg=BG)
weather_bg.place(x=0, y=0, relwidth=1, height=175)
map_widget = TkinterMapView(left_frame)
map_widget.set_tile_server("https://tile.openstreetmap.org/{z}/{x}/{y}.png")
map_widget.pack(fill="both", expand=True)
map_widget.set_position(DEFAULT_LAT, DEFAULT_LON)
map_widget.set_zoom(DEFAULT_ZOOM)
map_widget.add_left_click_map_command(get_coords)
   # RIGHT PANEL
tk.Label(
    right_frame, text="WEATHER DASHBOARD", fg=TEXT, bg=BG,
    font=(FONT_MAIN, 16, "bold"),
).pack(pady=(16, 10))
search_frame = tk.Frame(right_frame, bg=BG)
search_frame.pack(pady=(0, 10))
search_entry = ctk.CTkEntry(
    search_frame, width=170, height=34, font=(FONT_MAIN, 12),
    fg_color=PANEL, text_color=TEXT, border_color=BORDER,
    corner_radius=8, placeholder_text="Enter City or lat,lon",
)
search_entry.pack(side="left", padx=(0, 6))
ctk.CTkButton(
    search_frame, text="Search", font=(FONT_MAIN, 11, "bold"),
    fg_color=ACCENT, hover_color=ACCENT_DARK, text_color="black",
    corner_radius=8, width=70, height=34, cursor="hand2",
    command=search_city,
).pack(side="left")
button_frame = tk.Frame(right_frame, bg=BG)
button_frame.pack(pady=(0, 10))
ctk.CTkButton(
    button_frame, text="CURRENT", command=show_current,
    font=(FONT_MAIN, 11, "bold"), fg_color=PANEL_LIGHT, hover_color=PANEL,
    text_color=TEXT, border_width=1, border_color=ACCENT,
    corner_radius=8, width=100, height=32, cursor="hand2",
).pack(side="left", padx=5)
ctk.CTkButton(
    button_frame, text="FORECAST", command=show_forecast,
    font=(FONT_MAIN, 11, "bold"), fg_color=PANEL_LIGHT, hover_color=PANEL,
    text_color=TEXT, border_width=1, border_color=BORDER,
    corner_radius=8, width=100, height=32, cursor="hand2",
).pack(side="left", padx=5)
   # CURRENT VIEW
current_frame = tk.Frame(right_frame, bg=BG)
hero_frame = tk.Frame(current_frame, bg=BG)
hero_frame.place(x=-250, y=-100)
hero_icon = ctk.CTkLabel(hero_frame, text="\u2600\ufe0f",
                         font=(FONT_MAIN, 40), fg_color="transparent", text_color=TEXT)
hero_icon.pack()
hero_temp = ctk.CTkLabel(hero_frame, text="--\u00b0",
                         font=(FONT_MAIN, 54, "bold"), fg_color="transparent", text_color=ACCENT)
hero_temp.pack()
hero_condition = ctk.CTkLabel(hero_frame, text="Search a city to begin",
                              font=(FONT_MAIN, 13), fg_color="transparent", text_color=MUTED)
hero_condition.pack(pady=(0, 4))
loading_label = tk.Label(right_frame, text="", fg=ACCENT, bg=BG,
                         font=(FONT_MAIN, 11, "bold"))
loading_label.place(x=20, y=10)
current_frame.pack(fill="both", expand=True)
# Cards
location_card, location_label = create_card(current_frame, CARD_START_Y + CARD_STEP * 0, "Location: --")
time_card, time_label = create_card(current_frame, CARD_START_Y + CARD_STEP * 1, "Local Time: --")
temp_card, temp_label = create_card(current_frame, CARD_START_Y + CARD_STEP * 2, "Temp: --")
humidity_card, humidity_label = create_card(current_frame, CARD_START_Y + CARD_STEP * 3, "Humidity: --")
wind_card, wind_label = create_card(current_frame, CARD_START_Y + CARD_STEP * 4, "Wind: --")
cloud_card, cloud_label = create_card(current_frame, CARD_START_Y + CARD_STEP * 5, "Clouds: --")
condition_card, condition_label = create_card(current_frame, CARD_START_Y + CARD_STEP * 6, "Condition: --")
clock_label = tk.Label(current_frame, text="--:--:--", fg=ACCENT, bg=BG,
                       font=(FONT_MAIN, 34, "bold"))
clock_label.place_forget()
  # FORECAST VIEW 
forecast_frame = tk.Frame(right_frame, bg=BG)
tk.Label(forecast_frame, text="WEEKLY FORECAST", fg=TEXT, bg=BG,
         font=(FONT_MAIN, 16, "bold")).pack(pady=(20, 10))
forecast_labels = []
for _ in range(5):
    lbl = tk.Label(forecast_frame, text="--", fg=MUTED, bg=BG, font=(FONT_MAIN, 12))
    lbl.pack(pady=4)
    forecast_labels.append(lbl)
graph_frame = tk.Frame(forecast_frame, bg=BG)
graph_frame.pack(fill="both", expand=False)
fig = Figure(figsize=(5, 3), dpi=100)
ax = fig.add_subplot(111)
ax.set_facecolor(BG)
fig.patch.set_facecolor(BG)
ax.tick_params(colors="white")
ax.spines["bottom"].set_color("white")
ax.spines["left"].set_color("white")
ax.spines["top"].set_color(BG)
ax.spines["right"].set_color(BG)
ax.set_title("Temperature Trend", color="white", fontsize=12)
ax.set_xlabel("Day", color="white")
ax.set_ylabel("°C", color="white")
ax.grid(True, color="gray", linestyle="--", alpha=0.3)
canvas = FigureCanvasTkAgg(fig, master=graph_frame)
canvas.get_tk_widget().pack(fill="both", expand=True)
   # ABOUT  
about_frame = tk.Frame(window, bg="black")
about_bg = tk.Frame(about_frame, bg="black")
about_bg.place(relwidth=1, relheight=1)
about_txt_frame = tk.Frame(about_frame, bg="black")
about_txt_frame.place(relx=0.5, rely=0.5, anchor="center")
tk.Label(
    about_txt_frame, bg="black", fg=TEXT, justify="center",
    text=(
        "Hello, my name is Sai Yajur.\n"
        "This is my class 12 project (using Python) that uses python libraries\n"
        "and an API to integrate weather forecasting and mapping.\n"
        "Modules used: tkinter, PIL, requests, datetime,\n"
        "matplotlib.backends.backend_tkagg, random.\n"
        "APIs used: OpenWeatherMap and OpenStreetMap.\n"
        "Features:\n"
        "  - Integrated search bar\n"
        "  - Temperature and atmospheric conditions\n"
        "  - Weekly Forecast\n"
        "Thank you for visiting....."
    ),
    font=(FONT_MAIN, 13),
).pack()
make_button(about_frame, "\u2190 BACK", open_menufa,
            fg=PANEL, text_color=TEXT, width=90, height=36, font_size=12).place(x=20, y=20)
make_button(map_frame, "\u2190 BACK", open_menufm,
            fg=PANEL, text_color=TEXT, width=90, height=36, font_size=12).place(x=W - 110, y=H - 90)
# START
window.after(100, resize_earth_frames)
window.after(150, animate_webp)
draw_clock()
window.mainloop()
