# ChronoDash - Desktop Widgets
# Copyright (C) 2025 Overl1te
#
# Системный трей для ChronoDash (кросс-платформенная версия)

import platform
from pathlib import Path
from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QApplication, QWidget, QVBoxLayout, QPushButton, QLabel
from PySide6.QtGui import QIcon, QAction
from PySide6.QtCore import QTimer, Qt
from dashboard.dashboard import run_widgets_editor
from core.qt_bridge import get_qt_bridge


class TrayApp:
    """
    Кросс-платформенный трей на базе Qt.
    Использует QSystemTrayIcon где доступен, иначе fallback-окно.
    """
    def __init__(self, widget_manager):
        self.wm = widget_manager
        self.qt_bridge = get_qt_bridge(self.wm)
        self.wm.load_and_create_all_widgets()
        
        # Пробуем использовать Qt System Tray
        self.tray_icon = QSystemTrayIcon()
        
        # Загружаем иконку
        icon_path = Path(__file__).parent.parent / "assets" / "icons" / "logo.ico"
        if icon_path.exists():
            self.tray_icon.setIcon(QIcon(str(icon_path)))
        else:
            # Создаём простую иконку
            from PySide6.QtGui import QPixmap, QPainter, QColor
            pixmap = QPixmap(64, 64)
            pixmap.fill(Qt.transparent)
            painter = QPainter(pixmap)
            painter.setBrush(QColor(10, 120, 200))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(8, 8, 48, 48)
            painter.drawRect(18, 28, 28, 8)
            painter.end()
            self.tray_icon.setIcon(QIcon(pixmap))
        
        self.tray_icon.setToolTip("ChronoDash")
        
        # Создаём меню
        menu = QMenu()
        
        action_restart = QAction("Перезапустить виджеты", menu)
        action_restart.triggered.connect(self._restart_widgets)
        menu.addAction(action_restart)
        
        action_editor = QAction("Мои виджеты", menu)
        action_editor.triggered.connect(self._open_editor)
        menu.addAction(action_editor)
        
        menu.addSeparator()
        
        action_quit = QAction("Выход", menu)
        action_quit.triggered.connect(self._quit_app)
        menu.addAction(action_quit)
        
        self.tray_icon.setContextMenu(menu)
        
        # Проверяем доступность системного трея
        self.system_tray_available = QSystemTrayIcon.isSystemTrayAvailable()
        
        if not self.system_tray_available:
            print("Системный трей недоступен. Запускаем fallback-окно...")
            self._create_fallback_window()
        else:
            print("Системный трей доступен, показываем иконку...")
            self.tray_icon.show()

    def _create_fallback_window(self):
        """Создаёт окно управления если трей недоступен"""
        self.control_window = QWidget()
        self.control_window.setWindowTitle("ChronoDash")
        self.control_window.setFixedSize(300, 180)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        
        label = QLabel("ChronoDash активен")
        label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(label)
        
        layout.addSpacing(10)
        
        btn_editor = QPushButton("Открыть редактор виджетов")
        btn_editor.clicked.connect(self._open_editor)
        layout.addWidget(btn_editor)
        
        btn_restart = QPushButton("Перезапустить все виджеты")
        btn_restart.clicked.connect(self._restart_widgets)
        layout.addWidget(btn_restart)
        
        layout.addSpacing(10)
        
        btn_minimize = QPushButton("Свернуть в трей" if self.system_tray_available else "Свернуть")
        btn_minimize.clicked.connect(self.control_window.hide)
        layout.addWidget(btn_minimize)
        
        btn_quit = QPushButton("Выйти из программы")
        btn_quit.clicked.connect(self._quit_app)
        btn_quit.setStyleSheet("background-color: #d32f2f; color: white;")
        layout.addWidget(btn_quit)
        
        self.control_window.setLayout(layout)
        self.control_window.show()
        
        # Подключаем событие закрытия окна
        self.control_window.closeEvent = lambda e: self._on_control_window_close(e)

    def _on_control_window_close(self, event):
        """При закрытии окна спрашиваем подтверждение"""
        from PySide6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self.control_window, 
            "Выход",
            "Закрыть ChronoDash полностью?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self._quit_app()
        else:
            event.ignore()
            self.control_window.hide()

    def _restart_widgets(self):
        """Перезапускает все виджеты"""
        self.wm.stop_all_widgets()
        QTimer.singleShot(300, self.wm.load_and_create_all_widgets)

    def _open_editor(self):
        """Открывает дашборд настроек"""
        run_widgets_editor(self.wm)

    def _quit_app(self):
        """Полностью завершает приложение"""
        self.wm.stop_all_widgets()
        self.tray_icon.hide()
        if hasattr(self, 'control_window'):
            self.control_window.close()
        QApplication.instance().quit()

    def run(self):
        """
        Запускает приложение.
        В Qt-версии это неблокирующий метод, просто возвращаем управление.
        """
        if not self.system_tray_available and hasattr(self, 'control_window'):
            # Если нет трея, но есть окно - возвращаем управление
            # Qt продолжит работать в фоне
            return
        
        # Если есть трей, он будет работать в фоне
        # Для блокировки можно использовать цикл событий,
        # но в нашем случае main.py уже запускает app.exec()
        pass