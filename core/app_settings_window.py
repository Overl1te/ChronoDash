import sys
import os
import platform
import subprocess
import time
import shutil
import webbrowser
import traceback
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QCheckBox, QPushButton, 
    QLabel, QGroupBox, QMessageBox, QHBoxLayout, QTextEdit
)
from PySide6.QtCore import Qt, QObject, Signal
from PySide6.QtGui import QColor, QPalette, QTextCursor

from core.version import APP_VERSION, REPO_OWNER, REPO_NAME

class UpdateWindows(QWidget):
    """
    При наличии обновления показывает окно
    (В будущем: Сделать автоматическое скачивание и установку обновлений)
    """
    def __init__(self, widget_manager):
        super().__init__()
        self.setWindowTitle("Доступно обновление!")
        self.resize(200, 100)
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)

        # --- Консоль логов ---
        layout.addWidget(QLabel("Внимание! Доступно обновление приложения \nПожалуйста обновитесь до актуальной версии"))
        
        btn_update = QPushButton("Установить обновление")
        btn_update.clicked.connect(lambda: webbrowser.open(f"https://github.com/{REPO_OWNER}/{REPO_NAME}/releases"))
        layout.addWidget(btn_update)

        btn_close = QPushButton("Позже")
        btn_close.clicked.connect(self.close)
        layout.addWidget(btn_close)



# === Класс для перехвата логов ===
class LogStream(QObject):
    """
    Перехватывает stdout/stderr.
    1. Пишет в реальную консоль (print работает как обычно).
    2. Отправляет сигнал с текстом для отображения в GUI.
    """
    append_log = Signal(str)

    def __init__(self):
        super().__init__()
        # Сохраняем оригинальный поток вывода (консоль)
        self.terminal = sys.stdout

    def write(self, message):
        # 1. Пишем в реальную консоль (чтобы лог был виден в терминале)
        try:
            self.terminal.write(message)
            self.terminal.flush()
        except Exception:
            pass
        
        # 2. Отправляем в GUI
        self.append_log.emit(str(message))

    def flush(self):
        try:
            self.terminal.flush()
        except Exception:
            pass

# ==========================================
# Окно инструментов разработчика (DevTools)
# ==========================================
class Dev_menu(QWidget):
    def __init__(self, widget_manager):
        super().__init__()
        self.wm = widget_manager
        self.setWindowTitle("Меню разработчика (DevTools)")
        self.resize(700, 500)
        self._init_ui()
        self._init_logger()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # --- Панель инструментов ---
        tools_layout = QHBoxLayout()
        
        # 1. Границы
        self.btn_borders = QPushButton("Wireframe (Debug Borders)")
        self.btn_borders.setCheckable(True)
        self.btn_borders.setChecked(getattr(self.wm, "debug_borders", False))
        self.btn_borders.clicked.connect(self._toggle_borders)
        tools_layout.addWidget(self.btn_borders)
        
        # 2. Кэш
        btn_cache = QPushButton("Сброс кэша")
        btn_cache.clicked.connect(self._clear_cache)
        tools_layout.addWidget(btn_cache)
        
        # 3. Тест ошибки
        btn_crash = QPushButton("Simulate Error")
        btn_crash.setStyleSheet("background-color: #AA4400; color: white; font-weight: bold;")
        btn_crash.clicked.connect(self._force_crash)
        tools_layout.addWidget(btn_crash)
        
        layout.addLayout(tools_layout)

        # --- Экспериментальные функции ---
        grp_exp = QGroupBox("Experimental Features")
        v_exp = QVBoxLayout()
        
        self.cb_builder = QCheckBox("Использовать Visual Builder (Alpha)")
        self.cb_builder.setToolTip("Активирует новый визуальный конструктор виджетов (в разработке)")
        is_builder = self.wm.get_global_setting("use_builder", False)
        self.cb_builder.setChecked(is_builder)
        self.cb_builder.toggled.connect(lambda v: self.wm.set_global_setting("use_builder", v))
        v_exp.addWidget(self.cb_builder)
        
        grp_exp.setLayout(v_exp)
        layout.addWidget(grp_exp)

        # --- Консоль логов ---
        layout.addWidget(QLabel("Live Console Output:"))
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setLineWrapMode(QTextEdit.NoWrap)
        self.log_view.setStyleSheet("""
            QTextEdit {
                background-color: #0e0e0e; 
                color: #00ff00; 
                font-family: Consolas, 'Courier New', monospace;
                font-size: 11px;
                border: 1px solid #333;
            }
        """)
        layout.addWidget(self.log_view)
        
        btn_close = QPushButton("Закрыть")
        btn_close.clicked.connect(self.close)
        layout.addWidget(btn_close)

    def _init_logger(self):
        # Перехватываем stdout только если это еще не сделано
        if not hasattr(sys.stdout, "append_log"):
            self.stream = LogStream()
            sys.stdout = self.stream
            sys.stderr = self.stream 
        else:
            self.stream = sys.stdout
            
        # FIX: Убрали disconnect, так как при создании окна сигнал всегда чист.
        # Это убирает RuntimeWarning.
        self.stream.append_log.connect(self._append_log_safe)

    def _append_log_safe(self, text):
        """Безопасное добавление текста в консоль."""
        cursor = self.log_view.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(text)
        self.log_view.setTextCursor(cursor)
        self.log_view.ensureCursorVisible()

    def _toggle_borders(self, checked):
        self.wm.debug_borders = checked
        print(f"[DEV] Wireframe Mode: {'ON' if checked else 'OFF'}")
        for w in self.wm.widgets.values():
            w.update()

    def _clear_cache(self):
        count = 0
        for name in ["weather_icons_cache.json", "weather_location_cache.json"]:
            p = self.wm.config_path.parent / name
            if p.exists():
                try:
                    p.unlink()
                    count += 1
                except Exception as e:
                    print(f"[DEV] Error deleting {name}: {e}")
        print(f"[DEV] Cache cleared. Files deleted: {count}")

    def _force_crash(self):
        print("[DEV] Simulating critical error...")
        try:
            x = 1 / 0 
        except Exception:
            traceback.print_exc()
            print("[DEV] Error caught safely.")


# ==========================================
# Лейбл с "пасхалкой"
# ==========================================
class VersionLabel(QLabel):
    def __init__(self, text, widget_manager, parent_window):
        super().__init__(text, parent_window)
        self.wm = widget_manager
        self.parent_window = parent_window 
        self.clicks = []
        
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("color: gray; font-size: 11px;")
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("Нажми меня 10 раз быстро!")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            now = time.time()
            self.clicks.append(now)
            self.clicks = [t for t in self.clicks if now - t <= 3.0]
            
            if len(self.clicks) >= 10: 
                self.clicks.clear()
                self._toggle_dev_mode()
        super().mousePressEvent(event)

    def _toggle_dev_mode(self):
        current_state = self.wm.get_global_setting("dev_mode", False)
        new_state = not current_state
        self.wm.set_global_setting("dev_mode", new_state)
        
        status = "АКТИВИРОВАН" if new_state else "ДЕАКТИВИРОВАН"
        QMessageBox.information(self.window(), "Developer Mode", f"Режим разработчика <b>{status}</b>!")
        
        if hasattr(self.parent_window, "refresh_dev_button"):
            self.parent_window.refresh_dev_button()


# ==========================================
# Главное окно настроек приложения
# ==========================================
class AppSettingsWindow(QWidget):
    def __init__(self, widget_manager):
        super().__init__()
        self.wm = widget_manager
        self.dev_window = None 
        self.setWindowTitle("Настройки приложения")
        self.resize(420, 400)
        self._init_ui()

    def _init_ui(self):
        self.main_layout = QVBoxLayout(self)

        # === 1. Система ===
        grp_sys = QGroupBox("Система")
        v_sys = QVBoxLayout()

        self.cb_autostart = QCheckBox("Запускать вместе с системой")
        self.cb_autostart.setChecked(self.wm.get_global_setting("autostart", False))
        self.cb_autostart.toggled.connect(self._toggle_autostart)
        v_sys.addWidget(self.cb_autostart)
        
        btn_open_conf = QPushButton("📂 Открыть папку с конфигами")
        btn_open_conf.clicked.connect(self._open_config_folder)
        v_sys.addWidget(btn_open_conf)

        grp_sys.setLayout(v_sys)
        self.main_layout.addWidget(grp_sys)

        # === 2. Графика ===
        grp_gfx = QGroupBox("Графика и Совместимость")
        v_gfx = QVBoxLayout()
        
        lbl_hint = QLabel("⚠️ Изменения требуют перезапуска приложения!")
        lbl_hint.setStyleSheet("color: #FF8800; font-size: 10px; font-weight: bold;")
        v_gfx.addWidget(lbl_hint)

        self.cb_x11 = QCheckBox("Принудительно использовать X11 (Linux)")
        self.cb_x11.setToolTip("Исправляет прозрачность на GNOME/Wayland")
        self.cb_x11.setChecked(self.wm.get_global_setting("force_x11", True))
        self.cb_x11.toggled.connect(lambda v: self.wm.set_global_setting("force_x11", v))
        v_gfx.addWidget(self.cb_x11)
        
        self.cb_gpu = QCheckBox("Аппаратное ускорение (GPU)")
        self.cb_gpu.setChecked(self.wm.get_global_setting("gpu_acceleration", True))
        self.cb_gpu.toggled.connect(lambda v: self.wm.set_global_setting("gpu_acceleration", v))
        v_gfx.addWidget(self.cb_gpu)

        grp_gfx.setLayout(v_gfx)
        self.main_layout.addWidget(grp_gfx)

        self.main_layout.addStretch()
        
        # === 3. Кнопка Dev Mode ===
        self.btn_dev = QPushButton("🛠 Открыть меню разработчика")
        self.btn_dev.setStyleSheet("""
            QPushButton {
                background-color: #2D2D2D; 
                color: #FFAA00; 
                border: 1px solid #444; 
                padding: 5px;
            }
            QPushButton:hover { background-color: #3D3D3D; }
        """)
        self.btn_dev.clicked.connect(self.open_dev_menu)
        self.main_layout.addWidget(self.btn_dev)
        
        self.refresh_dev_button()

        # === 4. Версия ===
        self.lbl_ver = VersionLabel(f"ChronoDash {APP_VERSION}", self.wm, self)
        self.main_layout.addWidget(self.lbl_ver)
        
        btn_gh = QPushButton("GitHub")
        btn_gh.setFlat(True)
        btn_gh.setStyleSheet("color: #44AAFF; text-decoration: underline;")
        btn_gh.setCursor(Qt.PointingHandCursor)
        btn_gh.clicked.connect(lambda: webbrowser.open("https://github.com/Overl1te/ChronoDash"))
        self.main_layout.addWidget(btn_gh)

        btn_close = QPushButton("Закрыть")
        btn_close.clicked.connect(self.close)
        self.main_layout.addWidget(btn_close)

    def refresh_dev_button(self):
        is_dev = self.wm.get_global_setting("dev_mode", False)
        self.btn_dev.setVisible(is_dev)

    def open_dev_menu(self):
        if not self.dev_window:
            self.dev_window = Dev_menu(self.wm)
        self.dev_window.show()
        self.dev_window.activateWindow()

    def _open_config_folder(self):
        path = str(self.wm.config_path.parent)
        try:
            if platform.system() == "Windows":
                os.startfile(path)
            elif platform.system() == "Linux":
                subprocess.Popen(["xdg-open", path])
        except Exception as e:
            print(f"Error opening folder: {e}")

    def _toggle_autostart(self, checked):
        self.wm.set_global_setting("autostart", checked)
        if platform.system() == "Linux":
            autostart_dir = Path.home() / ".config" / "autostart"
            autostart_dir.mkdir(parents=True, exist_ok=True)
            desktop_file = autostart_dir / "chronodash.desktop"
            
            if checked:
                exe = sys.executable
                script = str(Path(sys.argv[0]).resolve())
                content = f"""[Desktop Entry]\nType=Application\nName=ChronoDash\nExec={exe} "{script}"\nIcon=utilities-terminal\nComment=Desktop Widgets\nX-GNOME-Autostart-enabled=true\n"""
                try:
                    with open(desktop_file, "w") as f: f.write(content)
                except: pass
            else:
                if desktop_file.exists(): desktop_file.unlink()