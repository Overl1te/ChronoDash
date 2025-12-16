# widgets/clock_widget.py
from widgets.base_widget import BaseDesktopWidget
from PySide6.QtGui import QPainter, QFont, QColor
from PySide6.QtCore import Qt, QDateTime, QTimer

class ClockWidget(BaseDesktopWidget):
    # ИЗМЕНЕНИЕ: Принимаем и передаем is_preview
    def __init__(self, cfg=None, is_preview=False):
        super().__init__(cfg, is_preview=is_preview) 
        self._apply_content_settings()

        if not self.is_preview: 
            self._start_clock()

    def _start_clock(self):
        self.update()  # сразу рисуем
        # QTimer.singleShot - работает безопасно, так как вызывается только в потоке Qt
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
        self.cfg = new_cfg.copy()
        self._apply_content_settings()
        super().update_config(new_cfg) 
        # self.update()  # перерисовка

    def draw_widget(self, painter: QPainter):
        try:
            # 1. Текущее время
            current_time = QDateTime.currentDateTime().toString(self.format)

            # 2. Настройки шрифта
            font = QFont(self.font_family, self.font_size)
            painter.setFont(font)
            painter.setPen(self.color)

            # 3. Отрисовка
            rect = self.rect()
            
            # Находим размер текста
            metrics = painter.fontMetrics()
            text_rect = metrics.boundingRect(current_time)

            # Вычисляем позицию для центрирования
            x = (rect.width() - text_rect.width()) / 2
            y = (rect.height() - text_rect.height()) / 2 + metrics.ascent()

            # Рисуем текст
            painter.drawText(x, y, current_time)

        except Exception as e:
            pass