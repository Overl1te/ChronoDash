# core/edit_overlay.py

from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtCore import Qt, Signal, QRect
from PySide6.QtGui import QColor, QPainter, QBrush

class EditOverlay(QWidget):
    stop_edit_signal = Signal() 

    def __init__(self):
        super().__init__()
        
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self._resize_to_screen()
        
        # 💡 Устанавливаем Policy для обработки ESC
        self.setFocusPolicy(Qt.StrongFocus) 
        self.grabKeyboard() # Перехватываем ввод с клавиатуры
        self.show()
        self.activateWindow()
        self.raise_()

    def _resize_to_screen(self):
        total_rect = QRect()
        for screen in QApplication.screens():
            # Используем availableGeometry чтобы избежать перекрытия панели задач
            total_rect = total_rect.united(screen.availableGeometry())
        
        # Используем geometry для всей площади виртуального рабочего стола
        self.setGeometry(QApplication.primaryScreen().geometry().united(*[s.geometry() for s in QApplication.screens()]))


    def paintEvent(self, event):
        painter = QPainter(self)
        # Черный цвет с прозрачностью 150 (из 255)
        painter.setBrush(QBrush(QColor(0, 0, 0, 150))) 
        painter.setPen(Qt.NoPen) 
        painter.drawRect(self.rect())

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.stop_edit_signal.emit()
            # Важно: Не закрываем здесь! Закрытие в WM после сохранения.
        
    def mousePressEvent(self, event):
        # Клик по затемнению тоже выключает режим
        # Мы хотим, чтобы клик по виджету его не закрывал. 
        # Если клик попадает на оверлей, значит, это клик мимо виджета.
        if self.childAt(event.pos()) is None:
            self.stop_edit_signal.emit()