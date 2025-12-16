# core/tray.py
from PIL import Image, ImageDraw
import pystray
from pystray import MenuItem as Item, Menu
from dashboard.dashboard import run_widgets_editor
from core.qt_worker import QtWorker

class TrayApp:
    def __init__(self, widget_manager):
        self.wm = widget_manager
        self.qt_worker = QtWorker(widget_manager)
        self.icon = None
        self._create_icon()

    def _create_icon(self):
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.ellipse((8, 8, 56, 56), fill=(10, 120, 200))
        d.rectangle((18, 28, 46, 36), fill="white")
        self.img = img

    def _menu(self):
        return Menu(
            Item("Показать виджеты", lambda: self.qt_worker.start()),
            Item("Перезапустить виджеты", self._restart_qt),
            Item("Настройки", lambda: run_widgets_editor(self.wm)),
            Item("Выход", self.stop),
        )

    def _restart_qt(self):
        print("Перезапуск виджетов...")
        self.qt_worker.stop()
        import time; time.sleep(0.5)
        self.qt_worker.start()

    def run(self):
        self.qt_worker.start()  # Автозапуск при старте
        self.icon = pystray.Icon("ChronoDash", self.img, "ChronoDash", self._menu())
        self.icon.run()

    def stop(self):
        print("Выход из приложения...")
        self.qt_worker.stop()
        if self.icon:
            self.icon.stop()