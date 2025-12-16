# core/tray.py
from PIL import Image, ImageDraw
import pystray
from pystray import MenuItem as Item, Menu
from dashboard.dashboard import run_widgets_editor
from PySide6.QtWidgets import QApplication # Импортируем QApplication

class TrayApp:
    def __init__(self, widget_manager):
        self.wm = widget_manager
        # self.qt_worker = QtWorker(widget_manager) # УДАЛЯЕМ
        self.icon = None
        self._create_icon()
        
        # 1. Инициализация Qt
        self._init_qt_app()

    def _create_icon(self):
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.ellipse((8, 8, 56, 56), fill=(10, 120, 200))
        d.rectangle((18, 28, 46, 36), fill="white")
        self.img = img

    def _init_qt_app(self):
        app = QApplication.instance()
        if not app:
            print("Ошибка: QApplication не найден!")
            return

        # Создаем мост
        from core.qt_bridge import get_qt_bridge
        self.qt_bridge = get_qt_bridge(self.wm)

        # !!! ВАЖНО: УДАЛЯЕМ КОНФЛИКТУЮЩИЙ ПОСТОЯННЫЙ QTIMER !!!
        # from PySide6.QtCore import QTimer
        # self.timer = QTimer()
        # self.timer.timeout.connect(lambda: None) 
        # self.timer.start(1000)
        
        # Загружаем виджеты
        self.wm.load_and_create_all_widgets()
        
    def _menu(self):
        return Menu(
            # Теперь виджеты всегда видны после запуска _init_qt_app
            Item("Перезапустить виджеты", self._restart_qt),
            Item("Настройки", lambda: run_widgets_editor(self.wm)),
            Item("Выход", self.stop),
        )

    def _restart_qt(self):
        print("Перезапуск виджетов...")
        
        # 1. Останавливаем
        self.wm.stop_all_widgets() # Закрывает все окна и очищает
        
        # 2. Пересоздаем
        import time; time.sleep(0.5) 
        self._init_qt_app() # Пересоздаст мост, таймер и загрузит виджеты
        
    def run(self):
        # self.qt_worker.start() # УДАЛЯЕМ
        self.icon = pystray.Icon("ChronoDash", self.img, "ChronoDash", self._menu())
        self.icon.run() # Блокирует главный поток
        
    def stop(self):
        print("Выход из приложения...")
        self.wm.stop_all_widgets() # Закрываем виджеты
        
        if self.icon:
            self.icon.stop()
        
        # Если pystray.Icon.run() завершится, управление вернется в main.py, 
        # где будет вызван app.quit()