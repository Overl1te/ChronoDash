# widgets/clock_widget.py
from widgets.base_widget import BaseDesktopWidget
from PySide6.QtGui import QPainter, QFont, QColor
from PySide6.QtCore import Qt, QDateTime, QTimer

class ClockWidget(BaseDesktopWidget):
    def __init__(self, cfg=None):
        super().__init__(cfg)
        self._apply_content_settings()

        # Запускаем тикалку — безопасно, без постоянного QTimer
        self._start_clock()

    def _start_clock(self):
        self.update()  # сразу рисуем
        QTimer.singleShot(200, self._start_clock)  # рекурсивно каждые 200 мс

    def _apply_content_settings(self):
        content = self.cfg.get("content", {})
        self.format = content.get("format", "HH:mm:ss")
        self.color = QColor(content.get("color", "#00FF88"))
        if not self.color.isValid():
            self.color = QColor("#00FF88")

        self.font_family = content.get("font_family", "Consolas")
        self.font_size = int(content.get("font_size", 48))

    def update_config(self, new_cfg):
        # print(f"ClockWidget: обновление конфига")
        self.cfg = new_cfg.copy()
        self._apply_content_settings()
        super().update_config(new_cfg)  # вызывает resize, move, opacity и т.д.
        self.update()  # перерисовка

    def draw_widget(self, painter: QPainter):
        try:
            painter.setPen(self.color)
            font = QFont(self.font_family, self.font_size)
            font.setBold(True)
            painter.setFont(font)

            text = QDateTime.currentDateTime().toString(self.format)
            painter.drawText(self.rect(), Qt.AlignCenter, text)
        except Exception as e:
            print(f"Clock draw error: {e}")