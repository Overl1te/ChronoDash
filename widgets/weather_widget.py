# ChronoDash - Weather Widget (Fixes)
import threading
import requests
import json
from pathlib import Path

from PySide6.QtGui import QPainter, QFont, QColor, QPixmap
from PySide6.QtCore import Qt, QTimer, QDateTime, QByteArray, QStandardPaths
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QSpinBox, QCheckBox
)

from widgets.base_widget import BaseDesktopWidget

# FIX: Добавляем User-Agent, чтобы API не разрывал соединение
HEADERS = {"User-Agent": "ChronoDash/2.1 (github.com/Overl1te/ChronoDash)"}

OPENMETEO_URL = "https://api.open-meteo.com/v1/forecast"
NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"
ICONIFY_URL = "https://api.iconify.design"

class WeatherWidget(BaseDesktopWidget):
    def __init__(self, cfg=None, is_preview=False):
        super().__init__(cfg, is_preview=is_preview)

        # Данные погоды (Дефолтные значения — строки, чтобы drawText не падал)
        self.current_temp = "--"
        self.feels_like = ""
        self.condition = ""
        self.location_str = "Загрузка..."
        self.current_weather_code = 0
        self.hourly_data = []
        self.daily_data = []
        self.error_message = None

        std_path = Path(QStandardPaths.writableLocation(QStandardPaths.AppConfigLocation))
        config_dir = Path(self.cfg.get("config_dir", std_path))
        config_dir.mkdir(parents=True, exist_ok=True)

        self.icon_cache_file = config_dir / "weather_icons_cache.json"
        self.location_cache_file = config_dir / "weather_location_cache.json"
        self.icon_cache = {}
        self.location_cache = {}

        self._load_disk_caches()
        self._apply_content_settings()

        if not self.is_preview:
            # Задержка перед первой загрузкой, чтобы UI успел отрисоваться
            QTimer.singleShot(500, lambda: threading.Thread(target=self._load_weather_data_blocking, daemon=True).start())
            self._start_update_timer()

    def update_config(self, new_cfg: dict):
        self.cfg = new_cfg.copy()
        self._apply_content_settings()
        self.update()

    def _load_disk_caches(self):
        # Загрузка кэша (упрощена, чтобы не дублировать код, оставь как было или используй этот)
        if self.icon_cache_file.exists():
            try:
                with open(self.icon_cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for name, b64 in data.items():
                        bs = QByteArray.fromBase64(b64.encode())
                        px = QPixmap()
                        if px.loadFromData(bs, "SVG"): self.icon_cache[name] = (bs, px)
            except: pass

    def _save_disk_caches(self):
        try:
            d = {n: b.toBase64().data().decode() for n, (b, _) in self.icon_cache.items()}
            with open(self.icon_cache_file, "w") as f: json.dump(d, f)
        except: pass

    def _apply_content_settings(self):
        c = self.cfg.get("content", {})
        self.lat = float(c.get("latitude", 55.75))
        self.lon = float(c.get("longitude", 37.61))
        self.units = c.get("temp_unit", "celsius")
        self.interval = max(5, int(c.get("update_interval_min", 15)))
        self.show_details = c.get("show_details", True)
        self.compact_mode = c.get("compact_mode", False)

    def _start_update_timer(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(lambda: threading.Thread(target=self._load_weather_data_blocking, daemon=True).start())
        self.timer.start(self.interval * 60 * 1000)

    def _load_weather_data_blocking(self):
        params = {
            "latitude": self.lat, "longitude": self.lon,
            "current": "temperature_2m,apparent_temperature,weather_code",
            "hourly": "temperature_2m,weather_code",
            "daily": "temperature_2m_max,temperature_2m_min,sunrise,sunset",
            "timezone": "auto",
            "forecast_days": 3,
            "temperature_unit": self.units,
        }
        
        try:
            # FIX: Добавил headers и увеличил timeout
            response = requests.get(OPENMETEO_URL, params=params, headers=HEADERS, timeout=15)
            response.raise_for_status()
            data = response.json()

            curr = data.get("current", {})
            t = curr.get("temperature_2m")
            self.current_temp = f"{round(t)}°" if t is not None else "--"
            
            at = curr.get("apparent_temperature")
            self.feels_like = f"Ощущается {round(at)}°" if at is not None else ""
            
            self.current_weather_code = curr.get("weather_code", 0)
            self.condition = self._get_condition_name(self.current_weather_code)
            self.location_str = f"Lat: {self.lat:.2f}, Lon: {self.lon:.2f}"

            # Hourly
            hourly = data.get("hourly", {})
            times = hourly.get("time", [])
            temps = hourly.get("temperature_2m", [])
            now_idx = 0 
            # (Упрощенный поиск индекса времени)
            now_str = QDateTime.currentDateTime().toString("yyyy-MM-ddThh:00")
            for i, val in enumerate(times):
                if val >= now_str:
                    now_idx = i
                    break
            
            self.hourly_data = []
            for i in range(now_idx, min(len(times), now_idx + 6)):
                t_str = times[i][-5:]
                self.hourly_data.append(f"{t_str} {round(temps[i])}°")

            # Daily
            daily = data.get("daily", {})
            self.daily_data = []
            for i in range(min(3, len(daily.get("time", [])))):
                d_str = daily["time"][i][5:].replace("-", ".")
                mn = round(daily["temperature_2m_min"][i])
                mx = round(daily["temperature_2m_max"][i])
                self.daily_data.append(f"{d_str}: {mn}°..{mx}°")

            self.error_message = None

        except Exception as e:
            print(f"[Weather] Error: {e}")
            self.error_message = "Ошибка связи"
            self.current_temp = "?"
        
        QTimer.singleShot(0, self.update)

    def _get_condition_name(self, code):
        codes = {0:"Ясно", 1:"Перем. облачность", 2:"Облачно", 3:"Пасмурно", 45:"Туман", 61:"Дождь", 71:"Снег", 95:"Гроза"}
        return codes.get(code, codes.get(code//10*10, ""))

    def _get_icon_pixmap(self, code):
        is_night = QDateTime.currentDateTime().time().hour() < 6 or QDateTime.currentDateTime().time().hour() > 21
        mapping = {0: "night-clear" if is_night else "day-sunny", 1: "day-cloudy", 2: "day-cloudy", 3: "cloudy", 45: "fog", 61: "rain", 71: "snow", 95: "thunderstorm"}
        name = "wi:" + mapping.get(code, "cloud")
        
        if name in self.icon_cache: return self.icon_cache[name][1]
        
        # Загрузка (в основном потоке, если нет кэша - плохо, но допустимо для редких случаев)
        # Лучше вынести в тред, но для фикса оставим здесь с защитой
        try:
            c_hex = self.cfg.get("content", {}).get("color", "#FFFFFF").replace("#", "")
            url = f"{ICONIFY_URL}/{name}.svg?height=100&color=%23{c_hex}"
            r = requests.get(url, headers=HEADERS, timeout=2) # Короткий таймаут
            if r.status_code == 200:
                bs = QByteArray(r.content)
                px = QPixmap()
                if px.loadFromData(bs, "SVG"):
                    self.icon_cache[name] = (bs, px)
                    self._save_disk_caches()
                    return px
        except: pass
        return QPixmap()

    def draw_widget(self, painter: QPainter):
        # Если данных нет вообще - не рисуем детали, чтобы не упасть
        if not self.location_str: 
            return

        rect = self.rect()
        painter.setRenderHint(QPainter.Antialiasing)

        # Фон
        painter.setBrush(QColor(20, 20, 30, 200))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(rect, 20, 20)

        c = self.cfg.get("content", {})
        col = QColor(c.get("color", "#FFFFFF"))
        font_fam = c.get("font_family", "Segoe UI")
        base_size = int(c.get("font_size", 32))

        painter.setPen(col)
        
        # Temp
        painter.setFont(QFont(font_fam, base_size + 20, QFont.Bold))
        painter.drawText(20, 20, 200, 80, Qt.AlignLeft | Qt.AlignVCenter, str(self.current_temp))
        
        # Details
        painter.setFont(QFont(font_fam, base_size - 10))
        painter.drawText(20, 100, f"{self.condition} {self.feels_like}")
        
        # Hourly
        if self.hourly_data and self.show_details:
            painter.setFont(QFont("Consolas", base_size - 14))
            line = "  ".join(self.hourly_data[:5])
            painter.drawText(20, 140, line)

        # Icon
        pix = self._get_icon_pixmap(self.current_weather_code)
        if not pix.isNull():
            scaled = pix.scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            painter.drawPixmap(self.width() - 100, 20, scaled)

        if self.error_message:
            painter.setPen(QColor("#FF5555"))
            painter.setFont(QFont(font_fam, 12))
            painter.drawText(rect.adjusted(0,0,-10,-10), Qt.AlignBottom | Qt.AlignRight, self.error_message)

# ==============================================================================
# UI SETTINGS (Qt)
# ==============================================================================
def render_qt_settings(layout, cfg, on_update):
    c = cfg.get("content", {})

    # Поиск
    search_w = QWidget()
    sh = QHBoxLayout(search_w)
    sh.setContentsMargins(0,0,0,0)
    sed = QLineEdit()
    sed.setPlaceholderText("Город")
    sbtn = QPushButton("Найти")
    sres = QLabel()
    
    def do_search():
        q = sed.text()
        if not q: return
        sres.setText("...")
        def run():
            try:
                r = requests.get(f"{NOMINATIM_SEARCH_URL}?q={q}&format=json&limit=1", headers=HEADERS, timeout=5)
                d = r.json()
                if d:
                    lat, lon = float(d[0]["lat"]), float(d[0]["lon"])
                    QTimer.singleShot(0, lambda: apply(lat, lon, d[0]["display_name"][:15]))
                else:
                    QTimer.singleShot(0, lambda: sres.setText("Не найдено"))
            except:
                QTimer.singleShot(0, lambda: sres.setText("Ошибка"))
        
        def apply(lat, lon, name):
            on_update("content.latitude", lat)
            on_update("content.longitude", lon)
            sres.setText(f"OK: {name}")

        threading.Thread(target=run, daemon=True).start()

    sbtn.clicked.connect(do_search)
    sh.addWidget(sed)
    sh.addWidget(sbtn)
    sh.addWidget(sres)
    layout.addWidget(QLabel("Поиск:"))
    layout.addWidget(search_w)

    # Цвет
    layout.addWidget(QLabel("Цвет (HEX):"))
    ced = QLineEdit(c.get("color", "#FFFFFF"))
    ced.textChanged.connect(lambda v: on_update("content.color", v))
    layout.addWidget(ced)
    
    # Размер
    layout.addWidget(QLabel("Размер:"))
    sbox = QSpinBox()
    sbox.setRange(10, 100)
    sbox.setValue(int(c.get("font_size", 32)))
    sbox.valueChanged.connect(lambda v: on_update("content.font_size", v))
    layout.addWidget(sbox)

WidgetClass = WeatherWidget