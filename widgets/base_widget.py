# widgets/base_widget.py
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtCore import Qt

class BaseDesktopWidget(QWidget):
    def __init__(self, cfg=None):
        super().__init__()
        self.cfg = cfg or {}
        # print(f"Создается виджет: {self.cfg.get('id', 'no-id')}")

        self._apply_flags()
        self._apply_opacity()  # если добавил из прошлого ответа

        self.resize(max(self.cfg.get("width", 320), 10),
                    max(self.cfg.get("height", 180), 10))
        self.move(self.cfg.get("x", 100), self.cfg.get("y", 100))

        self.drag_pos = None

        # УДАЛЯЕМ ВСЁ ЭТО:
        # self.timer = QTimer(self)
        # self.timer.timeout.connect(self.update)
        # self.timer.start(1000)

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

    def _apply_opacity(self):
        opacity = self.cfg.get("opacity", 255) / 255.0
        self.setWindowOpacity(opacity)

    def _apply_flags(self):
        flags = Qt.FramelessWindowHint | Qt.Tool
        if self.cfg.get("always_on_top", True):
            flags |= Qt.WindowStaysOnTopHint
        if self.cfg.get("click_through", True):
            flags |= Qt.WindowTransparentForInput

        self.setWindowFlags(flags)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, self.cfg.get("click_through", True))

    def update_config(self, new_cfg):
        self.cfg = new_cfg.copy()
        self._apply_flags()
        self._apply_opacity()
        self.resize(max(self.cfg.get("width", 320), 10),
                    max(self.cfg.get("height", 180), 10))
        self.move(self.cfg.get("x", 100), self.cfg.get("y", 100))
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