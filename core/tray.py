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
Системный трей (systray) для ChronoDash.

Обеспечивает постоянное присутствие приложения в области уведомлений,
доступ к настройкам и безопасный выход.
Использует pystray + PIL для иконки.
"""

from pathlib import Path
from PIL import Image, ImageDraw
import pystray
from pystray import MenuItem, Menu
from dashboard.dashboard import run_widgets_editor
from core.qt_bridge import get_qt_bridge


class TrayApp:
    """
    Класс, управляющий иконкой в системном трее.

    Создаёт меню:
    - Перезапуск виджетов
    - Открытие редактора (дашборда)
    - Выход из приложения
    """

    def __init__(self, widget_manager):
        self.wm = widget_manager
        self.icon = None
        self._load_icon()

        # Инициализируем Qt-мост и загружаем все виджеты
        self.qt_bridge = get_qt_bridge(self.wm)
        self.wm.load_and_create_all_widgets()

    def _load_icon(self):
        """Загружает официальную иконку или создаёт fallback."""
        icon_path = Path(__file__).parent.parent / "assets" / "icons" / "logo.ico"

        if icon_path.exists():
            try:
                self.tray_image = Image.open(icon_path)
                return
            except Exception as e:
                print(f"Не удалось загрузить иконку {icon_path}: {e}")

        # Fallback: простая синяя иконка с белой полосой
        self._create_fallback_icon()

    def _create_fallback_icon(self):
        """Создаёт простую запасную иконку программно."""
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse((8, 8, 56, 56), fill=(10, 120, 200))
        draw.rectangle((18, 28, 46, 36), fill="white")
        self.tray_image = img

    def _restart_widgets(self):
        """Перезапускает все виджеты (полная очистка + повторная загрузка)."""
        self.wm.stop_all_widgets()

        # Небольшая пауза для завершения закрытия окон
        import time
        time.sleep(0.3)

        # Повторно инициализируем мост и загружаем виджеты
        self.qt_bridge = get_qt_bridge(self.wm)
        self.wm.load_and_create_all_widgets()

    def _open_editor(self):
        """Открывает дашборд настроек в отдельном потоке."""
        run_widgets_editor(self.wm)

    def _quit_app(self):
        """Полностью завершает приложение."""
        self.wm.stop_all_widgets()
        if self.icon:
            self.icon.stop()

    def _build_menu(self) -> Menu:
        """Создаёт контекстное меню трея."""
        return Menu(
            MenuItem("Перезапустить виджеты", self._restart_widgets),
            MenuItem("Мои виджеты", self._open_editor),
            MenuItem("Выход", self._quit_app),
        )

    def run(self):
        """Запускает иконку в трее. Блокирует поток до завершения."""
        menu = self._build_menu()
        self.icon = pystray.Icon(
            name="ChronoDash",
            icon=self.tray_image,
            title="ChronoDash",
            menu=menu,
        )
        self.icon.run()