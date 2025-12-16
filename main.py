import os
import sys
import warnings
import traceback


if getattr(sys, 'frozen', False):
    warnings.filterwarnings("ignore")
    os.environ["QT_LOGGING_RULES"] = "*.debug=false;*.warning=false;*.critical=false"
else:

    warnings.filterwarnings("ignore", message=".*QApplication.*main.*thread.*")
    warnings.filterwarnings("ignore", message=".*created in.*thread.*")
    warnings.filterwarnings("ignore", category=UserWarning)
    warnings.filterwarnings("ignore", category=DeprecationWarning)


os.environ["QT_LOGGING_RULES"] = "qt.*.debug=false;qt.*.warning=false"
os.environ["QT_LOGGING_RULES"] = "*=false" 


try:
    from PySide6.QtCore import qInstallMessageHandler
    def qt_silent_handler(msg_type, context, message):
        pass 
    qInstallMessageHandler(qt_silent_handler)
except:
    pass

from pathlib import Path
from core.widget_manager import WidgetManager
from core.tray import TrayApp

def main():
    try:
        docs = Path.home() / "Documents" / "ChronoDash"
        docs.mkdir(parents=True, exist_ok=True)
        config_path = docs / "widgets.json"

        wm = WidgetManager(config_path)
        tray = TrayApp(wm)
        tray.run()  # ← Блокирует главный поток — как и должно быть
    except Exception as e:
        print(f"ПИЗДЕЦ: {e}")
        traceback.print_exc()
        input("Нажми Enter чтобы выйти...")

if __name__ == "__main__":
    main()