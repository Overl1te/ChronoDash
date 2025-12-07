# main.py
import sys
from PySide6.QtWidgets import QApplication
from core.tray import TrayApp
from core.widget_manager import WidgetManager
from core.qt_bridge import get_qt_bridge
from pathlib import Path

app = QApplication(sys.argv)

def main():
    documents_path = Path.home() / "Documents" / "ChronoDash"
    documents_path.mkdir(exist_ok=True, parents=True)
    config_path = documents_path / "widgets.json"

    print(f"Конфигурационный файл: {config_path}")

    wm = WidgetManager(config_path)
    
    # Создаем мост для общения с Qt
    qt_bridge = get_qt_bridge(wm)
    
    # Создаем виджеты
    wm.load_and_create_all_widgets()

    tray = TrayApp(widget_manager=wm)
    tray.run()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()