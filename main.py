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

"""
Точка входа приложения ChronoDash.

Запускает:
1. QApplication (главный Qt-поток)
2. WidgetManager — менеджер всех виджетов
3. TrayApp — иконку в трее + меню (перезапуск, настройки, выход)
4. Загружает и показывает все сохранённые виджеты

При выходе из трея (кнопка "Выход") — корректно закрывает все окна и завершает приложение.
"""

from pathlib import Path
import sys
import traceback
from core.widget_manager import WidgetManager
from core.tray import TrayApp
from PySide6.QtWidgets import QApplication


def main():
    """
    Главная функция запуска приложения.
    
    Порядок:
    1. Создаём папку Documents/ChronoDash (если нет)
    2. Создаём QApplication в главном потоке
    3. Создаём менеджер виджетов с путём к конфигу
    4. Запускаем системный трей (блокирует поток)
    5. При выходе из трея — завершаем Qt-приложение
    """
    try:
        # 1. Создаём папку для конфига (обычно ~/Documents/ChronoDash)
        docs = Path.home() / "Documents" / "ChronoDash"
        docs.mkdir(parents=True, exist_ok=True)
        config_path = docs / "widgets.json"

        # 2. Инициализируем QApplication (обязательно в главном потоке)
        app = QApplication.instance() or QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(False)  # Не закрывать приложение при закрытии окон

        # 3. Создаём менеджер виджетов (загружает конфиг, создаёт/удаляет виджеты)
        wm = WidgetManager(config_path)

        # 4. Запускаем трей — он блокирует поток до нажатия "Выход"
        tray = TrayApp(wm)
        tray.run()

        # 5. После выхода из трея — завершаем Qt-приложение
        app.quit()

    except Exception as e:
        # Если что-то пошло не так — показываем ошибку и ждём нажатия Enter
        print(f"ERROR: {e}")
        traceback.print_exc()
        input("Нажми Enter чтобы выйти...")


if __name__ == "__main__":
    main()