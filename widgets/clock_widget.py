# widgets/clock_widget.py
from widgets.base_widget import BaseDesktopWidget
from PySide6.QtGui import QPainter, QFont, QColor
from PySide6.QtCore import Qt, QDateTime


class ClockWidget(BaseDesktopWidget):
    def __init__(self, cfg=None):
        super().__init__(cfg)
        self._apply_content_settings()  # ← читаем из cfg

        # Обновляем каждые 200 мс (для секунд)
        self.timer.stop()
        self.timer.start(200)

    def _apply_content_settings(self):
        """Читаем настройки контента из self.cfg"""
        content = self.cfg.get("content", {})
        self.format = content.get("format", "HH:mm:ss")
        self.color = QColor(content.get("color", "#00FF88"))
        if not self.color.isValid():
            self.color = QColor("#00FF88")

        self.font_family = content.get("font_family", "Consolas")
        self.font_size = int(content.get("font_size", 48))

    def update_config(self, new_cfg):
        print(f"🔄 ClockWidget.update_config() вызван")
        print(f"   Старый цвет: {getattr(self, 'color', 'НЕТ')}")
        print(f"   Новый цвет: {new_cfg.get('content', {}).get('color', 'НЕТ')}")
        
        # Обновляем конфиг
        self.cfg = new_cfg.copy()
        
        # Применяем настройки содержимого
        self._apply_content_settings()
        
        # Применяем настройки окна через родительский метод
        super().update_config(new_cfg)  # Это обновит размер, позицию, флаги
        
        print(f"✅ После обновления цвет: {self.color.name()}")
        print(f"   Формат: {self.format}")
        
        # Форсируем перерисовку
        self.update()

    def draw_widget(self, painter: QPainter):
        try:
            painter.setPen(self.color)
            font = QFont(self.font_family, self.font_size)
            font.setBold(True)
            painter.setFont(font)

            current_time = QDateTime.currentDateTime()
            text = current_time.toString(self.format)

            painter.drawText(self.rect(), Qt.AlignCenter, text)
        except Exception as e:
            print(f"Clock draw error: {e}")