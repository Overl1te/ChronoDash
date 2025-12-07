from PIL import Image, ImageDraw
import pystray
from pystray import MenuItem as Item, Menu
from core.widget_manager import WidgetManager
from dashboard.dashboard import run_dashboard_window
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

class TrayApp:
    def __init__(self, widget_manager: WidgetManager):
        self.wm = widget_manager
        self.icon = None
        self._create_icon_image()

    def _create_icon_image(self):
        img = Image.new('RGBA', (64,64), (0,0,0,0))
        d = ImageDraw.Draw(img)
        d.ellipse((8,8,56,56), fill=(10,120,200,255))
        d.rectangle((18,28,46,36), fill=(255,255,255,255))
        self._img = img

    def _build_menu(self):
        items = [
            Item('Новый виджет', lambda _: run_dashboard_window(self.wm)),
            Item('Конструктор (Dashboard)', lambda _: run_dashboard_window(self.wm)),
            Item('Мои виджеты', self._menu_my_widgets),
            Item('Выход', self.stop)
        ]
        return Menu(*items)

    def _menu_my_widgets(self):
        run_dashboard_window(self.wm)

    def run(self):
        menu = self._build_menu()
        self.icon = pystray.Icon("DesktopWidgetsPro", self._img, "DesktopWidgetsPro", menu)
        self.icon.run()

    def stop(self):
        print("Завершение приложения...")
        
        if self.icon:
            self.icon.stop()

        if hasattr(self.wm, 'widgets'):
            for widget in self.wm.widgets.values():
                try:
                    widget.close()
                except:
                    pass
            self.wm.widgets.clear()

        QTimer.singleShot(100, QApplication.quit)