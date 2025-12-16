from PySide6.QtWidgets import QWidget, QApplication, QLabel
from PySide6.QtCore import Qt, Signal, QRect
from PySide6.QtGui import QColor, QPainter, QBrush, QFont


class EditOverlay(QWidget):
    stop_edit_signal = Signal()

    def __init__(self):
        super().__init__()

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self._resize_to_screen()

        self.hint_label = QLabel("Для выхода нажмите ESC", self)
        self.hint_label.setStyleSheet(
            """
            QLabel {
                color: white;
                background-color: rgba(128, 128, 128, 120);
                border-radius: 8px;
                padding: 12px 20px;
                font-size: 16px;
                font-family: Segoe UI, Arial;
            }
        """
        )
        self.hint_label.setFont(QFont("Segoe UI", 16, QFont.Bold))
        self.hint_label.setAlignment(Qt.AlignCenter)
        self.hint_label.setAttribute(
            Qt.WA_TransparentForMouseEvents, True
        )  # Чтобы не мешала кликам по виджету

        # Позиционируем вверху по центру
        self._position_hint_label()

        self.hint_label.show()

        self.setFocusPolicy(Qt.StrongFocus)
        self.grabKeyboard()
        self.show()
        self.activateWindow()
        self.raise_()

    def _resize_to_screen(self):
        total_rect = QRect()
        app = QApplication.instance()
        for screen in app.screens():
            total_rect = total_rect.united(screen.availableGeometry())

        if total_rect.isEmpty():
            total_rect = app.primaryScreen().availableGeometry()

        self.setGeometry(total_rect)

    def _position_hint_label(self):
        label_width = 400
        label_height = 60
        screen_geo = QApplication.primaryScreen().availableGeometry()

        x = (screen_geo.width() - label_width) // 2
        y = 20  # Отступ от верха

        self.hint_label.setGeometry(x, y, label_width, label_height)

    def resizeEvent(self, event):
        # При изменении размеров экрана (например, переключение мониторов) перепозиционируем
        self._position_hint_label()
        super().resizeEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        # Полупрозрачный чёрный фон
        painter.setBrush(QBrush(QColor(0, 0, 0, 150)))
        painter.setPen(Qt.NoPen)
        painter.drawRect(self.rect())

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.stop_edit_signal.emit()

    def mousePressEvent(self, event):
        # Клик мимо виджета — выход
        if (
            self.childAt(event.pos()) is None
        ):  # childAt учитывает QLabel, но у него WA_TransparentForMouseEvents
            self.stop_edit_signal.emit()
