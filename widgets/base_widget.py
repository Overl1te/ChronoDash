# widgets/base_widget.py
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtCore import Qt, QTimer, QMetaObject
from streamlit import json


class BaseDesktopWidget(QWidget):
    def __init__(self, cfg=None):
        super().__init__()
        self.cfg = cfg or {}
        print(f"🧩 Создается виджет с cfg: {self.cfg.get('id', 'no-id')}")
        
        self._apply_flags()
        
        self.resize(max(self.cfg.get("width", 320), 10),
                    max(self.cfg.get("height", 180), 10))
        self.move(self.cfg.get("x", 100), self.cfg.get("y", 100))

        # Таймер обновления
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(1000)

        self.drag_pos = None

    @staticmethod
    def render_to_pixmap(cfg: dict) -> QPixmap:
        """Статический метод для рендеринга превью"""
        width = max(cfg.get("width", 320), 50)
        height = max(cfg.get("height", 180), 50)

        pixmap = QPixmap(width, height)
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        # Создаём временный виджет БЕЗ родителя
        if cfg.get("type") == "clock":
            from widgets.clock_widget import ClockWidget
            temp_widget = ClockWidget(cfg.copy())
        else:
            temp_widget = BaseDesktopWidget(cfg.copy())

        temp_widget.resize(width, height)
        temp_widget.draw_widget(painter)

        painter.end()
        return pixmap

    def _apply_flags(self):
        """Применяет флаги окна на основе cfg"""
        flags = Qt.FramelessWindowHint | Qt.Tool

        if self.cfg.get("always_on_top", True):
            flags |= Qt.WindowStaysOnTopHint

        if self.cfg.get("click_through", True):
            flags |= Qt.WindowTransparentForInput

        self.setWindowFlags(flags)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, 
                         self.cfg.get("click_through", True))

        # Показываем окно если оно было видимым
        if hasattr(self, 'isVisible') and self.isVisible():
            self.show()

    def update_config(self, new_cfg):
        """Обновляет конфигурацию виджета"""
        print(f"🔄 BaseDesktopWidget.update_config() вызван для {self.cfg.get('id', 'unknown')}")
        self.cfg = new_cfg.copy()
        
        # Обновляем флаги окна
        self._apply_flags()
        
        # Обновляем размер и позицию
        self.resize(max(self.cfg.get("width", 320), 10),
                    max(self.cfg.get("height", 180), 10))
        self.move(self.cfg.get("x", 100), self.cfg.get("y", 100))
        
        # Форсируем перерисовку
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        self.draw_widget(painter)
        painter.end()

    def draw_widget(self, painter: QPainter):
        pass

    # Перетаскивание правой кнопкой
    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton and not self.cfg.get("click_through", True):
            self.drag_pos = event.globalPos()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.RightButton and self.drag_pos:
            delta = event.globalPos() - self.drag_pos
            self.move(self.pos() + delta)
            self.drag_pos = event.globalPos()
            self.cfg["x"] = self.x()
            self.cfg["y"] = self.y()

    def mouseReleaseEvent(self):
        self.drag_pos = None