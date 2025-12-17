# ChronoDash - Desktop Widgets
# Copyright (C) 2025 Overl1te
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

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