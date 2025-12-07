from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtCore import Qt, QTimer

class BaseDesktopWidget(QWidget):
    def __init__(self, cfg=None):
        super().__init__()
        self.cfg = cfg or {}
        
        # Инициализируем буфер
        self.buffer = None
        
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool |
            Qt.WindowTransparentForInput
        )
        
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        
        # Размер и позиция
        self.resize(max(self.cfg.get("width", 320), 10), 
                   max(self.cfg.get("height", 180), 10))
        self.move(self.cfg.get("x", 100), self.cfg.get("y", 100))
        
        # Таймер для обновления
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._on_timer)
        self.timer.start(1000)
        
        self.drag_pos = None
    
    def _on_timer(self):
        """Вызывается по таймеру - обновляет виджет"""
        self.update()  # Запускает paintEvent
    
    def paintEvent(self):
        """Отрисовка виджета с очисткой буфера"""
        # Создаем или обновляем буфер если нужно
        if not self.buffer or self.buffer.size() != self.size():
            self.buffer = QPixmap(self.size())
        
        # ВАЖНО: Очищаем буфер перед рисованием!
        self.buffer.fill(Qt.transparent)
        
        # Рисуем в буфер
        painter = QPainter(self.buffer)
        painter.setRenderHint(QPainter.Antialiasing)
        self.draw_widget(painter)
        painter.end()
        
        # Рисуем буфер на окне
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self.buffer)
        painter.end()
    
    def draw_widget(self):
        """Метод для переопределения в дочерних классах"""
        pass
    
    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self.drag_pos = event.globalPos()
    
    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.RightButton and self.drag_pos:
            delta = event.globalPos() - self.drag_pos
            self.move(self.pos() + delta)
            self.drag_pos = event.globalPos()
            if self.cfg:
                self.cfg["x"] = self.x()
                self.cfg["y"] = self.y()
    
    def mouseReleaseEvent(self):
        self.drag_pos = None
    
    def resizeEvent(self, event):
        """При изменении размера сбрасываем буфер"""
        super().resizeEvent(event)
        self.buffer = None  # Сброс буфера, чтобы он пересоздался