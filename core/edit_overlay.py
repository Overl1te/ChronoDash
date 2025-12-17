# ChronoDash - Desktop Widgets
# Copyright (C) 2025 Overl1te
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

"""
Оверлей для режима редактирования виджета.

Полноэкранное прозрачное окно:
- Затемняет экран
- Показывает подсказку про ESC
- Перехватывает ESC
- Полностью пропускает клики мыши к виджету под собой
"""

from PySide6.QtWidgets import QWidget, QLabel, QApplication
from PySide6.QtCore import Qt, Signal, QRect
from PySide6.QtGui import QColor, QPainter, QBrush, QFont


class EditOverlay(QWidget):
    """
    Оверлей, активный только в режиме редактирования.
    Позволяет перемещать и изменять размер виджета под собой.
    """
    stop_edit_signal = Signal()

    def __init__(self, editing_widget: QWidget):
        super().__init__()

        self.editing_widget = editing_widget

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self._resize_to_all_screens()

        # Подсказка
        self.hint_label = QLabel("Для выхода нажмите ESC", self)
        self.hint_label.setStyleSheet("""
            QLabel {
                color: white;
                background-color: rgba(128, 128, 128, 120);
                border-radius: 8px;
                padding: 12px 20px;
                font-size: 16px;
                font-family: Segoe UI, Arial;
            }
        """)
        self.hint_label.setFont(QFont("Segoe UI", 16, QFont.Bold))
        self.hint_label.setAlignment(Qt.AlignCenter)
        self.hint_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)

        self._position_hint_label()
        self.hint_label.show()

        # Захват клавиатуры для ESC
        self.setFocusPolicy(Qt.StrongFocus)
        self.grabKeyboard()
        self.show()

    def _resize_to_all_screens(self):
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
        primary_geo = QApplication.primaryScreen().availableGeometry()

        x = (primary_geo.width() - label_width) // 2
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
            self.stop_edit_signal.emit()

    def mousePressEvent(self, event):
        """
        КЛЮЧЕВОЙ МЕТОД: пропускает клик к виджету под оверлеем.

        1. activateWindow() — заставляет Windows/Qt "знать", что клик предназначен виджету
        2. event.ignore() — позволяет событию пройти сквозь оверлей
        Без обоих — клики не доходят до BaseDesktopWidget!
        """
        self.editing_widget.activateWindow()
        event.ignore()  # Это обязательно!

    def closeEvent(self, event):
        print("[OVERLAY] EditOverlay закрывается (closeEvent)")
        super().closeEvent(event)
