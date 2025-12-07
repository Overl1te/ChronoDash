# tray.py — РАБОТАЕТ ПО ТВОЕЙ ЛОГИКЕ НА 100%
from PIL import Image, ImageDraw
import pystray
from pystray import MenuItem as Item, Menu
from core.widget_manager import WidgetManager
from dashboard.dashboard import run_widgets_editor
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
import threading


class TrayApp:
    def __init__(self, widget_manager: WidgetManager):
        self.wm = widget_manager
        self.icon = None
        self._create_icon_image()

    def _create_icon_image(self):
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.ellipse((8, 8, 56, 56), fill=(10, 120, 200, 255))
        d.rectangle((18, 28, 46, 36), fill=(255, 255, 255, 255))
        self._img = img

    def _build_menu(self):
        return Menu(
            Item("Мои виджеты", lambda: self._safe_open_editor()),
            Item("Выход", self.stop),
        )

    def _safe_open_editor(self):
        """Открывает редактор БЕЗ КОНФЛИКТА С pystray"""
        QTimer.singleShot(50, lambda: run_widgets_editor(self.wm))

    def run(self):
        menu = self._build_menu()
        self.icon = pystray.Icon("ChronoDash", self._img, "ChronoDash", menu)
        
        # ГЛАВНЫЙ ПОТОК — ТОЛЬКО ТРЕЙ, НИЧЕГО БОЛЬШЕ!
        self.icon.run()

    def stop(self):
        print("Завершение приложения...")

        if self.icon:
            self.icon.stop()

        # Закрываем все виджеты
        for widget in getattr(self.wm, "widgets", {}).values():
            try:
                widget.close()
            except:
                pass
        self.wm.widgets.clear()

        # Важно: даём Qt завершить работу через очередь
        QTimer.singleShot(100, QApplication.quit)