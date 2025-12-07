from widgets.base_widget import BaseDesktopWidget
from PySide6.QtGui import QPainter, QFont, QColor
from PySide6.QtCore import Qt, QDateTime

class ClockWidget(BaseDesktopWidget):
    def __init__(self, cfg=None):
        super().__init__(cfg)
        
        # Настройки из конфига
        content = cfg.get("content", {}) if cfg else {}
        self.format = content.get("format", "HH:mm:ss")
        self.color = content.get("color", "#00FF88")
        self.font_family = content.get("font_family", "Consolas")
        self.font_size = int(content.get("font_size", 48))
        
        # Устанавливаем частоту обновления для часов
        self.timer.stop()
        self.timer.start(200)  # Обновляем каждые 200 мс
    
    def draw_widget(self, painter: QPainter):
        """Отрисовка часов - ТОЛЬКО текст, фон уже прозрачный"""
        try:
            # Создаем QColor из строки
            color = QColor(self.color)
            if not color.isValid():
                color = QColor("#00FF88")  # Цвет по умолчанию
            
            # Получаем текущее время
            current_time = QDateTime.currentDateTime()
            text = current_time.toString(self.format)
            
            # Настраиваем шрифт
            font = QFont(self.font_family, self.font_size)
            font.setBold(True)
            painter.setFont(font)
            
            # Устанавливаем цвет
            painter.setPen(color)
            
            # Рисуем текст по центру
            # Используем флаг AlignCenter для выравнивания
            painter.drawText(self.rect(), Qt.AlignCenter, text)
            
        except Exception as e:
            print(f"Clock draw error: {e}")