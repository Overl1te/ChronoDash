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
        
        # ОЧЕНЬ ВАЖНО: Отключаем завершение приложения при закрытии последнего виджета
        # Приложение будет блокировать только pystray.
        app.setQuitOnLastWindowClosed(False) 
        
        # 2. Создание менеджера виджетов
        wm = WidgetManager(config_path)
        
        # 3. Создание и запуск трея (БЛОКИРУЕТ ГЛАВНЫЙ ПОТОК)
        tray = TrayApp(wm)
        tray.run() # <- Запускает pystray и блокирует главный поток

        # 4. После того как pystray.Icon.run() завершился (нажали "Выход")
        app.quit()
    except Exception as e:
        print(f"ПИЗДЕЦ: {e}")
        traceback.print_exc()
        input("Нажми Enter чтобы выйти...")

if __name__ == "__main__":
    main()