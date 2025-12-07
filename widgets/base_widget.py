# widgets/base_widget.py
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtCore import Qt, QTimer, QMetaObject


class BaseDesktopWidget(QWidget):
    def __init__(self, cfg=None):
        super().__init__()
        self.cfg = cfg or {}
        self.buffer = None

        flags = Qt.FramelessWindowHint | Qt.Tool
        if self.cfg.get("always_on_top", True):
            flags |= Qt.WindowStaysOnTopHint
        if self.cfg.get("click_through", True):
            flags |= Qt.WindowTransparentForInput

        self.setWindowFlags(flags)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, self.cfg.get("click_through", True))

        self.resize(max(self.cfg.get("width", 320), 10),
                    max(self.cfg.get("height", 180), 10))
        self.move(self.cfg.get("x", 100), self.cfg.get("y", 100))

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(1000)

        self.drag_pos = None

    @staticmethod
    def render_to_pixmap(cfg: dict) -> QPixmap:
        """Возвращает готовый QPixmap с отрисованным виджетом (без создания окна)"""
        width = max(cfg.get("width", 320), 50)
        height = max(cfg.get("height", 180), 50)

        pixmap = QPixmap(width, height)
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        # Создаём временный виджет БЕЗ родителя и БЕЗ show()
        if cfg.get("type") == "clock":
            from widgets.clock_widget import ClockWidget
            temp_widget = ClockWidget(cfg.copy())
        else:
            temp_widget = BaseDesktopWidget(cfg.copy())

        temp_widget.resize(width, height)
        temp_widget.draw_widget(painter)        # прямой вызов

        painter.end()
        return pixmap

    def _apply_flags(self):
        """Применяет флаги на основе текущего cfg — безопасно и надёжно"""
        flags = Qt.FramelessWindowHint | Qt.Tool

        if self.cfg.get("always_on_top", True):
            flags |= Qt.WindowStaysOnTopHint

        if self.cfg.get("click_through", True):
            flags |= Qt.WindowTransparentForInput

        # Это главное: используем Qt internals, чтобы переприменить флаги без глюков
        self.setWindowFlags(flags)

        # Дополнительная страховка от мыши
        self.setAttribute(Qt.WA_TransparentForMouseEvents, self.cfg.get("click_through", True))

        # Пересоздаём нативное окно (без мерцания!)
        if self.isVisible():
            QMetaObject.invokeMethod(self, "show", Qt.QueuedConnection)

    def update_config(self, new_cfg):
        """Вызывается извне при изменении настроек"""
        changed_flags = False

        for key in ["always_on_top", "click_through"]:
            if self.cfg.get(key) != new_cfg.get(key):
                changed_flags = True

        # Обновляем конфиг
        self.cfg.update(new_cfg)

        # Обновляем позицию/размер
        self.move(self.cfg["x"], self.cfg["y"])
        self.resize(self.cfg["width"], self.cfg["height"])

        # Если изменились флаги — переприменяем
        if changed_flags:
            self._apply_flags()

        self.update()  # перерисовываем

    def paintEvent(self, event):
        if not self.buffer or self.buffer.size() != self.size():
            self.buffer = QPixmap(self.size())

        self.buffer.fill(Qt.transparent)
        painter = QPainter(self.buffer)
        painter.setRenderHint(QPainter.Antialiasing)
        self.draw_widget(painter)
        painter.end()

        painter = QPainter(self)
        painter.drawPixmap(0, 0, self.buffer)
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