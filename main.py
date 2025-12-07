# main.py
import sys
import os
from pathlib import Path
from PySide6.QtWidgets import QApplication
from core.tray import TrayApp
from core.widget_manager import WidgetManager

app = QApplication(sys.argv)


def main():
    # Путь к конфигу в Documents/ChronoDash
    documents_path = Path.home() / "Documents" / "ChronoDash"
    documents_path.mkdir(exist_ok=True, parents=True)
    config_path = documents_path / "widgets.json"

    print(f"📂 Конфигурационный файл: {config_path}")

    wm = WidgetManager(config_path)

    from PySide6.QtCore import QTimer

    def delayed_load():
        wm.load_and_create_all_widgets()

    QTimer.singleShot(500, delayed_load)

    tray = TrayApp(widget_manager=wm)
    tray.run()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
