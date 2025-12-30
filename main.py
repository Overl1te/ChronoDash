import sys
import os
import platform
import shutil
import traceback
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QStandardPaths

# Импортируем наши модули
from core.widget_manager import WidgetManager
from core.tray import TrayApp

def main():
    # === 1. Настройка окружения для Linux ===
    if platform.system() == "Linux":
            os.environ["QT_IM_MODULE"] = "simple"
            
            force_x11 = True # Default

            if force_x11:
                print("Force X11 mode enabled")
                os.environ["QT_QPA_PLATFORM"] = "xcb"
            else:
                # Если юзер отключил, даем Qt выбрать самому (xcb или wayland)
                if "QT_QPA_PLATFORM" in os.environ:
                    del os.environ["QT_QPA_PLATFORM"]

    try:
        # === 2. Настройка путей конфигурации ===
        # Windows: C:/Users/User/AppData/Local/ChronoDash/
        # Linux: /home/user/.config/ChronoDash/
        config_dir = Path(QStandardPaths.writableLocation(QStandardPaths.AppConfigLocation))
        config_dir.mkdir(parents=True, exist_ok=True)
        config_path = config_dir / "widgets.json"
        
        if config_path.exists():
            try:
                import json
                with open(config_path, 'r') as f:
                    d = json.load(f)
                    # Учитываем новую структуру { "global": ... }
                    if isinstance(d, dict):
                        g = d.get("global", {})
                        force_x11 = g.get("force_x11", True)
            except: pass

        # Миграция старого конфига (если был в Документах)
        old_path = Path.home() / "Documents" / "ChronoDash" / "widgets.json"
        if old_path.exists() and not config_path.exists():
            print(f"Migrating config from {old_path} to {config_path}")
            shutil.copy(old_path, config_path)

        # === 3. Запуск приложения ===
        app = QApplication.instance() or QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(False)
        app.setApplicationName("ChronoDash")
        app.setApplicationDisplayName("ChronoDash Desktop Widgets")

        # Менеджер виджетов
        wm = WidgetManager(config_path)

        # Трей и управление
        tray = TrayApp(wm)
        
        print(f"ChronoDash запущен. Конфиг: {config_path}")
        
        # Запуск главного цикла
        sys.exit(app.exec())

    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()