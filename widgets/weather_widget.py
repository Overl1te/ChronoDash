import threading
import requests
import json
from pathlib import Path
from PySide6.QtGui import QPainter, QFont, QColor, QPixmap
from PySide6.QtCore import Qt, QTimer, QDateTime, QByteArray
from PySide6.QtWidgets import QMessageBox
from widgets.base_widget import BaseDesktopWidget

OPENMETEO_URL = "https://api.open-meteo.com/v1/forecast"
NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"
ICONIFY_URL = "https://api.iconify.design"

class WeatherWidget(BaseDesktopWidget):
    def __init__(self, cfg=None, is_preview=False):
        super().__init__(cfg, is_preview=is_preview)

        self.current_temp = "Загрузка..."
        self.feels_like = ""
        self.condition = "—"
        self.location_str = ""
        self.current_weather_code = 0
        self.hourly_data = []
        self.daily_data = []
        self.error_message = None

        # Кеши теперь в папке с конфигом (обычно ~/Documents/ChronoDash)
        config_dir = Path(self.cfg.get("config_dir", str(Path.home() / "Documents" / "ChronoDash")))
        config_dir.mkdir(parents=True, exist_ok=True)

        self.icon_cache = {}
        self.location_cache = {}
        self.icon_cache_file = config_dir / "weather_icons_cache.json"
        self.location_cache_file = config_dir / "weather_location_cache.json"

        self._load_disk_caches()
        self._apply_content_settings()

        if not self.is_preview:
            DEFAULT_LAT = 56.267
            DEFAULT_LON = 44.0217

            is_manual_location = (abs(self.latitude - DEFAULT_LAT) > 0.001 or
                                  abs(self.longitude - DEFAULT_LON) > 0.001)

            if is_manual_location:
                print(f"[WEATHER] Ручные координаты: {self.latitude}, {self.longitude}")
                self._load_weather_data_blocking()
            else:
                print("[WEATHER] Автоопределение местоположения...")
                self._auto_detect_location()

            self._start_update_timer()
            self.show()

    def update_config(self, new_cfg: dict):
        """Переопределяем — просто копируем конфиг"""
        self.cfg = new_cfg.copy()
        self._apply_content_settings()
        self.update()

    def _load_disk_caches(self):
        # Иконки (храним SVG как base64)
        if self.icon_cache_file.exists():
            try:
                with open(self.icon_cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for name, b64_str in data.items():
                        svg_bytes = QByteArray.fromBase64(b64_str.encode("utf-8"))
                        pix = QPixmap()
                        if pix.loadFromData(svg_bytes, "SVG"):
                            self.icon_cache[name] = (svg_bytes, pix)
            except Exception as e:
                print(f"[WEATHER] Ошибка загрузки кеша иконок: {e}")

        # Локация
        if self.location_cache_file.exists():
            try:
                with open(self.location_cache_file, "r", encoding="utf-8") as f:
                    raw_data = json.load(f)
                    for key_str, loc in raw_data.items():
                        lat, lon = map(float, key_str.split(","))
                        self.location_cache[(lat, lon)] = loc
            except Exception as e:
                print(f"[WEATHER] Ошибка загрузки кеша локации: {e}")

    def _save_disk_caches(self):
        # Иконки
        try:
            icon_data = {}
            for name, (svg_bytes, _) in self.icon_cache.items():
                icon_data[name] = svg_bytes.toBase64().data().decode("utf-8")
            with open(self.icon_cache_file, "w", encoding="utf-8") as f:
                json.dump(icon_data, f, ensure_ascii=False)
        except Exception as e:
            print(f"[WEATHER] Ошибка сохранения кеша иконок: {e}")

        # Локация
        try:
            loc_data = {f"{lat:.6f},{lon:.6f}": loc for (lat, lon), loc in self.location_cache.items()}
            with open(self.location_cache_file, "w", encoding="utf-8") as f:
                json.dump(loc_data, f, ensure_ascii=False)
        except Exception as e:
            print(f"[WEATHER] Ошибка сохранения кеша локации: {e}")

    def _apply_content_settings(self):
        content = self.cfg.get("content", {})
        self.latitude = float(content.get("latitude", 56.267))
        self.longitude = float(content.get("longitude", 44.0217))
        self.temp_unit = content.get("temp_unit", "celsius")
        self.hours_back = content.get("hours_back", 3)
        self.hours_forward = content.get("hours_forward", 6)
        self.forecast_days = content.get("forecast_days", 7)
        self.update_interval_min = max(5, content.get("update_interval_min", 15))  # минимум 5 мин
        self.compact_mode = content.get("compact_mode", False)
        self.show_details = content.get("show_details", True)

    def _start_update_timer(self):
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._load_weather_data_blocking)
        self.update_timer.start(1000 * 60 * self.update_interval_min)

    def _auto_detect_location(self):
        def run_detection():
            services = [
                "https://ipapi.co/json/",
                "https://reallyfreegeoip.org/json/",
                "https://ip.imoz.io/",
                "https://geoip.vuiz.net/geoip",
                "https://apip.cc/json",
            ]
            for url in services:
                try:
                    resp = requests.get(url, timeout=7)
                    if resp.status_code != 200:
                        continue
                    d = resp.json()
                    lat = d.get("latitude") or d.get("lat")
                    lon = d.get("longitude") or d.get("lon")
                    city = d.get("city") or d.get("name") or "Неизвестно"
                    if lat is not None and lon is not None:
                        self._finalize_location_update(lat, lon, f"Авто: {city}")
                        return
                except:
                    continue
            self._show_error("Не удалось определить местоположение по IP")

        threading.Thread(target=run_detection, daemon=True).start()

    def _manual_ip_detect(self):
        """Вызывается из настроек"""
        self._auto_detect_location()  # теперь используем одну и ту же логику

    def _finalize_location_update(self, lat, lon, source):
        lat = round(float(lat), 6)
        lon = round(float(lon), 6)
        self.latitude = lat
        self.longitude = lon
        self.cfg["content"]["latitude"] = lat
        self.cfg["content"]["longitude"] = lon
        print(f"[WEATHER] Локация обновлена ({source}): {lat}, {lon}")
        self._load_weather_data_blocking()

    def _show_error(self, text):
        QMessageBox.critical(self, "Ошибка", text)

    def _show_info(self, title, text):
        QMessageBox.information(self, title, text)

    def _search_city(self, city_name: str):
        if not city_name.strip():
            return None
        params = {
            "q": city_name,
            "format": "json",
            "limit": 1,
            "accept-language": "ru"
        }
        headers = {"User-Agent": "ChronoDash/2.1 (your@email.com)"}
        try:
            response = requests.get(NOMINATIM_SEARCH_URL, params=params, headers=headers, timeout=6)
            response.raise_for_status()
            results = response.json()
            if results:
                return float(results[0]["lat"]), float(results[0]["lon"])
        except Exception as e:
            print(f"[WEATHER] Ошибка поиска города: {e}")
        return None

    def _get_location_name(self):
        key = (self.latitude, self.longitude)
        if key in self.location_cache:
            return self.location_cache[key]

        params = {
            "lat": self.latitude,
            "lon": self.longitude,
            "format": "json",
            "zoom": 10,
            "accept-language": "ru",
            "addressdetails": 1
        }
        headers = {"User-Agent": "ChronoDash/2.1 (your@email.com)"}

        try:
            response = requests.get(NOMINATIM_REVERSE_URL, params=params, headers=headers, timeout=6)
            response.raise_for_status()
            data = response.json()
            address = data.get("address", {})

            city = address.get("city") or address.get("town") or address.get("village") or ""
            state = address.get("state") or address.get("region") or address.get("province") or ""
            country = address.get("country") or ""

            parts = [p for p in [city, state, country] if p]
            location_str = ", ".join(parts) if parts else "Неизвестно"

            self.location_cache[key] = location_str
            self._save_disk_caches()
            return location_str
        except Exception as e:
            print(f"[WEATHER] Ошибка обратного геокодинга: {e}")
            return "Неизвестно"

    def _load_weather_data_blocking(self):
        params = {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "current": "temperature_2m,apparent_temperature,weather_code",
            "hourly": "temperature_2m,weather_code",
            "daily": "temperature_2m_max,temperature_2m_min,weather_code,sunrise,sunset",
            "timezone": "auto",
            "forecast_days": self.forecast_days,
            "temperature_unit": self.temp_unit,
        }

        try:
            response = requests.get(OPENMETEO_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            curr = data.get("current", {})
            t = curr.get("temperature_2m")
            self.current_temp = f"{round(t)}°" if t is not None else "—"
            at = curr.get("apparent_temperature")
            self.feels_like = f"Ощущается {round(at)}°" if at is not None else ""
            self.current_weather_code = curr.get("weather_code", 0)
            self.condition = self._get_condition_name(self.current_weather_code)

            self.location_str = self._get_location_name()

            # Hourly
            hourly = data.get("hourly", {})
            times = hourly.get("time", [])
            temps = hourly.get("temperature_2m", [])
            now_str = QDateTime.currentDateTime().toString("yyyy-MM-ddThh:00")
            try:
                now_idx = times.index(now_str)
            except ValueError:
                now_idx = next((i for i, t in enumerate(times) if t >= now_str), 0)

            start = max(0, now_idx - self.hours_back)
            end = min(len(times), now_idx + self.hours_forward + 1)
            self.hourly_data = [f"{times[i][-5:-3]}:00 {round(temps[i])}°" for i in range(start, end)]

            # Daily
            daily = data.get("daily", {})
            self.daily_data = []
            for i in range(len(daily.get("time", []))):
                day_date = daily["time"][i][5:10].replace("-", ".")
                max_t = round(daily["temperature_2m_max"][i])
                min_t = round(daily["temperature_2m_min"][i])
                sunrise = daily["sunrise"][i][-5:]
                sunset = daily["sunset"][i][-5:]
                self.daily_data.append({
                    "day": day_date,
                    "max": max_t,
                    "min": min_t,
                    "sunrise": sunrise,
                    "sunset": sunset
                })

            self.error_message = None

        except Exception as e:
            print(f"[WEATHER] Ошибка загрузки погоды: {e}")
            self.error_message = "Нет связи"
            self.current_temp = "—"
            self.feels_like = ""
            self.condition = "—"
            self.location_str = ""

        self.update()

    def _get_condition_name(self, code: int) -> str:
        names = {
            0: "Ясно", 1: "Малооблачно", 2: "Переменная облачность", 3: "Пасмурно",
            45: "Туман", 48: "Густой туман",
            51: "Морось", 53: "Морось", 55: "Сильная морось",
            61: "Дождь", 63: "Дождь", 65: "Ливень",
            71: "Снег", 73: "Снег", 75: "Сильный снег",
            80: "Ливневый дождь", 81: "Ливень", 82: "Сильный ливень",
            95: "Гроза", 96: "Гроза с градом", 99: "Сильная гроза с градом",
        }
        return names.get(code, "—")

    def _get_icon_pixmap(self, code: int) -> QPixmap:
        is_night = QDateTime.currentDateTime().time().hour() < 6 or QDateTime.currentDateTime().time().hour() > 20

        ICON_MAP = {
            0: "wi:night-clear" if is_night else "wi:day-sunny",
            1: "wi:day-sunny-overcast" if not is_night else "wi:night-alt-cloudy",
            2: "wi:day-cloudy" if not is_night else "wi:night-alt-cloudy",
            3: "wi:cloudy",
            45: "wi:fog", 48: "wi:fog",
            51: "wi:day-sprinkle" if not is_night else "wi:night-alt-sprinkle",
            53: "wi:day-sprinkle" if not is_night else "wi:night-alt-sprinkle",
            55: "wi:sprinkle",
            61: "wi:day-rain" if not is_night else "wi:night-alt-rain",
            63: "wi:rain", 65: "wi:rain",
            71: "wi:day-snow" if not is_night else "wi:night-alt-snow",
            73: "wi:snow", 75: "wi:snow",
            80: "wi:day-showers" if not is_night else "wi:night-alt-showers",
            81: "wi:showers", 82: "wi:rain",
            95: "wi:thunderstorm", 96: "wi:thunderstorm", 99: "wi:thunderstorm",
        }

        icon_name = ICON_MAP.get(code, "wi:cloud")
        if icon_name in self.icon_cache:
            return self.icon_cache[icon_name][1]

        content = self.cfg.get("content", {})
        color_hex = content.get("color", "#FFFFFF").lstrip("#")
        url = f"{ICONIFY_URL}/{icon_name}.svg?height=100&color=%23{color_hex}"

        try:
            response = requests.get(url, timeout=7)
            response.raise_for_status()
            svg_bytes = QByteArray(response.content)
            pixmap = QPixmap()
            if pixmap.loadFromData(svg_bytes, "SVG"):
                self.icon_cache[icon_name] = (svg_bytes, pixmap)
                self._save_disk_caches()
                return pixmap
        except Exception as e:
            print(f"[WEATHER] Не удалось загрузить иконку {icon_name}: {e}")

        return QPixmap()

    def draw_widget(self, painter: QPainter):
        rect = self.rect()
        painter.setRenderHint(QPainter.Antialiasing)

        painter.setBrush(QColor(20, 20, 30, 200))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(rect, 20, 20)

        content = self.cfg.get("content", {})
        text_color = QColor(content.get("color", "#FFFFFF"))
        font_family = content.get("font_family", "Segoe UI")
        base_size = content.get("font_size", 36)

        painter.setPen(text_color)

        # Большая температура
        big_font = QFont(font_family, base_size + 28, QFont.Bold)
        painter.setFont(big_font)
        painter.drawText(20, 20, 250, 100, Qt.AlignLeft | Qt.AlignVCenter, self.current_temp)

        # Локация
        location_font = QFont(font_family, base_size - 10)
        painter.setFont(location_font)
        painter.drawText(20, 107, 500, 40, Qt.AlignLeft | Qt.AlignVCenter, self.location_str)

        # Иконка
        icon_pixmap = self._get_icon_pixmap(self.current_weather_code)
        if not icon_pixmap.isNull():
            scaled = icon_pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            painter.drawPixmap(self.width() - 120, 30, scaled)

        # Ощущается + условие
        normal_font = QFont(font_family, base_size)
        painter.setFont(normal_font)
        painter.drawText(20, 180, self.feels_like)
        painter.drawText(20, 220, self.condition)

        # Подробности
        if self.show_details and not self.compact_mode and self.hourly_data:
            small_font = QFont(font_family, base_size - 10)
            painter.setFont(small_font)
            y = 260
            painter.drawText(20, y, "Ближайшие часы: " + "  ".join(self.hourly_data[:7]))
            y += 40
            for day in self.daily_data[:5]:
                painter.drawText(20, y, f"{day['day']}  {day['min']}°…{day['max']}°  ↑{day['sunrise']} ↓{day['sunset']}")
                y += 32

        elif self.compact_mode and self.hourly_data:
            painter.setFont(normal_font)
            painter.drawText(20, 160, "→ " + "  ".join([h.split()[-1] for h in self.hourly_data]))

        if self.error_message:
            painter.setPen(QColor("#FF5555"))
            painter.setFont(big_font)
            painter.drawText(rect, Qt.AlignCenter, self.error_message)


# ==============================================================================
# Дефолтная конфигурация и настройки UI остаются без изменений (кроме одной правки ниже)
# ==============================================================================

def get_default_config():
    return {
        "type": "weather",
        "name": "Погода",
        "width": 1420,
        "height": 460,
        "content": {
            "color": "#FFFFFF",
            "font_family": "Segoe UI",
            "font_size": 36,
            "latitude": 56.267,
            "longitude": 44.0217,
            "hours_back": 3,
            "hours_forward": 6,
            "forecast_days": 7,
            "update_interval_min": 15,
            "compact_mode": False,
            "show_details": True,
            "temp_unit": "celsius"
        }
    }

def render_settings_ui(parent, cfg, on_update):
    """
    Полные настройки погоды — без полей широты/долготы, с новыми опциями и пересозданием виджета
    """
    import customtkinter as ctk
    import tkinter as tk
    import threading
    import requests
    from core.qt_bridge import get_qt_bridge

    content = cfg.get("content", {})
    widget_id = cfg.get("id")

    def recreate_widget():
        bridge = get_qt_bridge()
        if bridge and widget_id:
            bridge.recreate_widget_signal.emit(widget_id)

    # ===================================================================
    # 1. МЕСТОПОЛОЖЕНИЕ (только поиск и автоопределение)
    # ===================================================================
    ctk.CTkLabel(parent, text="Местоположение", font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=20, pady=(10, 5))

    search_frame = ctk.CTkFrame(parent, fg_color="transparent")
    search_frame.pack(fill="x", padx=20, pady=5)

    search_var = tk.StringVar()
    search_entry = ctk.CTkEntry(search_frame, textvariable=search_var, placeholder_text="Введите город (например: Москва)")
    search_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

    status_text = tk.StringVar(value="Введите город и нажмите Enter")
    status_label = ctk.CTkLabel(search_frame, textvariable=status_text, text_color="gray")
    status_label.pack(side="right")

    def search_location():
        query = search_var.get().strip()
        if not query:
            status_text.set("Введите название")
            return

        status_text.set("Поиск...")
        search_entry.configure(state="disabled")

        def run():
            try:
                url = f"{NOMINATIM_SEARCH_URL}?q={query}&format=json&limit=1&addressdetails=1"
                headers = {"User-Agent": "ChronoDash/1.0"}
                resp = requests.get(url, headers=headers, timeout=12)
                resp.raise_for_status()
                data = resp.json()
                if not data:
                    status_text.set("Не найдено")
                    return

                lat = round(float(data[0]["lat"]), 6)
                lon = round(float(data[0]["lon"]), 6)
                city = data[0].get("display_name", "").split(",")[0]

                on_update("content.latitude", lat)
                on_update("content.longitude", lon)
                status_text.set(f"Найдено: {city}")
                recreate_widget()

            except Exception as e:
                print(f"[WEATHER] Ошибка поиска: {e}")
                status_text.set("Ошибка")
            finally:
                search_entry.configure(state="normal")

        threading.Thread(target=run, daemon=True).start()

    search_entry.bind("<Return>", lambda e: search_location())
    ctk.CTkButton(search_frame, text="Найти", width=100, command=search_location).pack(side="right")

    # Кнопка автоопределения по IP
    def auto_detect_ip():
        status_text.set("Определяю по IP...")
        search_entry.configure(state="disabled")

        def run():
            try:
                resp = requests.get("https://ipapi.co/json/", timeout=12)
                resp.raise_for_status()
                data = resp.json()
                lat = round(float(data["latitude"]), 6)
                lon = round(float(data["longitude"]), 6)
                city = data.get("city", "Неизвестно")

                on_update("content.latitude", lat)
                on_update("content.longitude", lon)
                status_text.set(f"По IP: {city}")
                recreate_widget()

            except Exception as e:
                status_text.set("Не удалось")
            finally:
                search_entry.configure(state="normal")

        threading.Thread(target=run, daemon=True).start()

    ctk.CTkButton(parent, text="Определить по IP", fg_color="#2E6B2E", height=36,
                  command=auto_detect_ip).pack(fill="x", padx=20, pady=(10, 20))

    # ===================================================================
    # 2. ПАРАМЕТРЫ ОТОБРАЖЕНИЯ
    # ===================================================================
    ctk.CTkLabel(parent, text="Отображение", font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=20, pady=(10, 5))

    grid_frame = ctk.CTkFrame(parent, fg_color="transparent")
    grid_frame.pack(fill="x", padx=20, pady=5)

    ctk.CTkLabel(grid_frame, text="Часов назад:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
    back_combo = ctk.CTkComboBox(grid_frame, values=[str(i) for i in range(0, 13)], width=80)
    back_combo.set(str(content.get("hours_back", 3)))
    back_combo.grid(row=0, column=1, padx=10, pady=5)
    back_combo.configure(command=lambda v: (on_update("content.hours_back", int(v)), recreate_widget()))

    ctk.CTkLabel(grid_frame, text="Часов вперёд:").grid(row=0, column=2, sticky="w", padx=5, pady=5)
    fwd_combo = ctk.CTkComboBox(grid_frame, values=[str(i) for i in range(0, 25)], width=80)
    fwd_combo.set(str(content.get("hours_forward", 6)))
    fwd_combo.grid(row=0, column=3, padx=10, pady=5)
    fwd_combo.configure(command=lambda v: (on_update("content.hours_forward", int(v)), recreate_widget()))

    ctk.CTkLabel(grid_frame, text="Обновление (мин):").grid(row=1, column=0, sticky="w", padx=5, pady=5)
    interval_combo = ctk.CTkComboBox(grid_frame, values=[str(i*5) for i in range(1, 25)], width=80)
    interval_combo.set(str(content.get("update_interval_min", 15)))
    interval_combo.grid(row=1, column=1, padx=10, pady=5)
    interval_combo.configure(command=lambda v: (on_update("content.update_interval_min", int(v)), recreate_widget()))

    # ===================================================================
    # 3. ВНЕШНИЙ ВИД И ПОВЕДЕНИЕ
    # ===================================================================
    ctk.CTkLabel(parent, text="Внешний вид и поведение", font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=20, pady=(20, 5))

    # compact_var = tk.BooleanVar(value=content.get("compact_mode", False))
    # ctk.CTkCheckBox(parent, text="Компактный режим", variable=compact_var,
    #                 command=lambda: (on_update("content.compact_mode", compact_var.get()), recreate_widget())).pack(anchor="w", padx=20, pady=5)

    units_var = tk.StringVar(value=content.get("temp_unit", "celsius"))
    units_frame = ctk.CTkFrame(parent, fg_color="transparent")
    units_frame.pack(fill="x", padx=20, pady=5)
    ctk.CTkLabel(units_frame, text="Единицы:").pack(side="left")
    ctk.CTkRadioButton(units_frame, text="°C", variable=units_var, value="celsius",
                       command=lambda: (on_update("content.temp_unit", "celsius"), recreate_widget())).pack(side="left", padx=15)
    ctk.CTkRadioButton(units_frame, text="°F", variable=units_var, value="fahrenheit",
                       command=lambda: (on_update("content.temp_unit", "fahrenheit"), recreate_widget())).pack(side="left")

    ctk.CTkLabel(parent, text="Цвет текста (HEX):").pack(anchor="w", padx=20, pady=(10, 0))
    color_entry = ctk.CTkEntry(parent)
    color_entry.pack(fill="x", padx=20, pady=5)
    color_entry.insert(0, content.get("color", "#FFFFFF"))
    color_entry.bind("<KeyRelease>", lambda e: (on_update("content.color", color_entry.get().strip()), recreate_widget()))

    ctk.CTkLabel(parent, text="Размер шрифта:").pack(anchor="w", padx=20, pady=(10, 0))
    size_slider = ctk.CTkSlider(parent, from_=16, to=72, number_of_steps=56,
                                command=lambda v: (on_update("content.font_size", int(v)), recreate_widget()))
    size_slider.pack(fill="x", padx=20, pady=5)
    size_slider.set(content.get("font_size", 36))

    # Новые глобальные опции виджета
    ctk.CTkLabel(parent, text="Поведение окна", font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=20, pady=(20, 5))

    always_top_var = tk.BooleanVar(value=cfg.get("always_on_top", False))
    ctk.CTkCheckBox(parent, text="Поверх всех окон", variable=always_top_var,
                    command=lambda: (on_update("always_on_top", always_top_var.get()), recreate_widget())).pack(anchor="w", padx=20, pady=5)

    click_through_var = tk.BooleanVar(value=cfg.get("click_through", False))
    ctk.CTkCheckBox(parent, text="Клик насквозь", variable=click_through_var,
                    command=lambda: (on_update("click_through", click_through_var.get()), recreate_widget())).pack(anchor="w", padx=20, pady=5)

# Экспорт класса
WidgetClass = WeatherWidget