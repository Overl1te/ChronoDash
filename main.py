from pathlib import Path
import sys
import traceback
from core.widget_manager import WidgetManager
from core.tray import TrayApp
from PySide6.QtWidgets import QApplication

def main():
    try:
        docs = Path.home() / "Documents" / "ChronoDash"
        docs.mkdir(parents=True, exist_ok=True)
        config_path = docs / "widgets.json"

        # 1. Создание QApplication в главном потоке
        app = QApplication.instance() or QApplication(sys.argv) 
        
        app.setQuitOnLastWindowClosed(False) 
        
        # 2. Создание менеджера виджетов
        wm = WidgetManager(config_path)
        
        # 3. Создание и запуск трея
        tray = TrayApp(wm)
        tray.run()

        # 4. После того как pystray.Icon.run() завершился (нажали "Выход")
        app.quit()
    except Exception as e:
        print(f"ERROR: {e}")
        traceback.print_exc()
        input("Нажми Enter чтобы выйти...")

if __name__ == "__main__":
    main()