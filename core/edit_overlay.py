# ChronoDash - Desktop Widgets
# Copyright (C) 2025 Overl1te
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from PySide6.QtWidgets import QWidget, QApplication, QLabel
from PySide6.QtCore import Qt, Signal, QRect
from PySide6.QtGui import QColor, QPainter, QBrush, QFont

class EditOverlay(QWidget):
    stop_edit_signal = Signal()

    def __init__(self, editing_widget):
        super().__init__()

        self.editing_widget = editing_widget  # Сохраняем ссылку на редактируемый виджет

        print("[OVERLAY] Создание EditOverlay")

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
        self.hint_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)

        self._position_hint_label()
        self.hint_label.show()

        self.setFocusPolicy(Qt.StrongFocus)
        self.grabKeyboard()
        self.show()
        # НЕ поднимаем оверлей через raise_() — виджет будет поднят отдельно

        print(f"[OVERLAY] EditOverlay показан. Geometry: {self.geometry()}, visible={self.isVisible()}")

    def _resize_to_screen(self):
        total_rect = QRect()
        app = QApplication.instance()
        for screen in app.screens():
            total_rect = total_rect.united(screen.availableGeometry())

        if total_rect.isEmpty():
            total_rect = app.primaryScreen().availableGeometry()

        self.setGeometry(total_rect)

    def _position_hint_label(self):
        label_width = 500
        label_height = 60
        screen_geo = QApplication.primaryScreen().availableGeometry()

        x = (screen_geo.width() - label_width) // 2
        y = 20

        self.hint_label.setGeometry(x, y, label_width, label_height)

    def resizeEvent(self, event):
        self._position_hint_label()
        super().resizeEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setBrush(QBrush(QColor(0, 0, 0, 150)))
        painter.setPen(Qt.NoPen)
        painter.drawRect(self.rect())

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            print("[OVERLAY] Нажата ESC — эмитируем stop_edit_signal")
            self.stop_edit_signal.emit()

    def mousePressEvent(self, event):
        # Важно: пропускаем клики, чтобы они попадали в редактируемый виджет под оверлеем
        self.editing_widget.activateWindow()
    
    def closeEvent(self, event):
        print("[OVERLAY] EditOverlay закрывается (closeEvent)")
        super().closeEvent(event)