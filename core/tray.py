# ChronoDash - Base Widget
# Copyright (C) 2025 Overl1te

import platform
from pathlib import Path
from PySide6.QtWidgets import (
    QSystemTrayIcon, QMenu, QApplication, QWidget, 
    QVBoxLayout, QLabel, QPushButton, QMessageBox, QFrame
)
from PySide6.QtGui import QIcon, QAction, QFont, QPixmap, QColor, QPainter
from PySide6.QtCore import QTimer, Qt
from core.updater import UpdateChecker

# Импортируем наше окно настроек
from core.settings_window import SettingsWindow
from core.app_settings_window import UpdateWindows

class TrayApp:
    """
    Управляет жизненным циклом приложения:
    1. Если есть трей -> иконка + контекстное меню.
    2. Если трея нет -> маленькое окошко управления (Fallback).
    """
    def __init__(self, widget_manager):
        self.wm = widget_manager
        self.settings_window = None  # Окно настроек (ленивая загрузка)
        self.fallback_window = None  # Окно управления (если нет трея)
        
        # 1. Загружаем все виджеты
        self.wm.load_and_create_all_widgets()
        
        # 2. Проверяем наличие трея
        if QSystemTrayIcon.isSystemTrayAvailable():
            print("[TrayApp] Системный трей доступен. Запускаем иконку.")
            self._init_tray()
        else:
            print("[TrayApp] Трей НЕ доступен (Linux/GNOME?). Запускаем Fallback-окно.")
            self._init_fallback_window()

        # 3. Проверяем наличие обновления
        self.updater = UpdateChecker()
        self.updater.update_available.connect(self._on_update_found)
        self.updater.check_for_updates()

    def _open_app_settings(self):
        # Ленивая загрузка окна
        if not hasattr(self, 'app_settings_window') or self.app_settings_window is None:
            from core.app_settings_window import AppSettingsWindow
            self.app_settings_window = AppSettingsWindow(self.wm)
        
        self.app_settings_window.show()
        self.app_settings_window.activateWindow()

    def _init_tray(self):
        """Инициализация иконки в трее."""
        self.tray_icon = QSystemTrayIcon()
        self._load_icon(self.tray_icon)
        
        # Меню
        menu = QMenu()
        
        # Жирный шрифт для "Настроек" (как дефолтное действие)
        action_settings = QAction("Настройки виджетов", menu)
        font = action_settings.font()
        font.setBold(True)
        action_settings.setFont(font)
        action_settings.triggered.connect(self._open_settings)
        menu.addAction(action_settings)
        
        menu.addSeparator()
        
        action_restart = QAction("Перезагрузить виджеты", menu)
        action_restart.triggered.connect(self._restart_widgets)
        menu.addAction(action_restart)

        act_app_conf = QAction("Настройки приложения", menu)
        act_app_conf.triggered.connect(self._open_app_settings)
        menu.addAction(act_app_conf)
        
        action_quit = QAction("Выход", menu)
        action_quit.triggered.connect(self._quit_app)
        menu.addAction(action_quit)
        
        self.tray_icon.setContextMenu(menu)
        self.tray_icon.show()
        
        # Клик по иконке (левой кнопкой)
        self.tray_icon.activated.connect(self._on_tray_click)

    def _init_fallback_window(self):
        """Создает окно управления, если трея нет."""
        self.fallback_window = QWidget()
        self.fallback_window.setWindowTitle("ChronoDash")
        self.fallback_window.setFixedSize(280, 280)
        self._load_icon(self.fallback_window)
        
        layout = QVBoxLayout(self.fallback_window)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Заголовок
        lbl_status = QLabel("ChronoDash работает")
        lbl_status.setAlignment(Qt.AlignCenter)
        lbl_status.setStyleSheet("font-size: 14px; font-weight: bold; color: #44AAFF;")
        layout.addWidget(lbl_status)
        
        lbl_info = QLabel("Системный трей не обнаружен.\nИспользуйте это окно для управления.")
        lbl_info.setAlignment(Qt.AlignCenter)
        lbl_info.setWordWrap(True)
        lbl_info.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(lbl_info)
        
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)
        
        # Кнопки
        btn_settings = QPushButton("Настройки виджетов")
        btn_settings.setCursor(Qt.PointingHandCursor)
        btn_settings.setStyleSheet("padding: 6px;")
        btn_settings.clicked.connect(self._open_settings)
        layout.addWidget(btn_settings)
        
        btn_restart = QPushButton("Перезапустить виджеты")
        btn_restart.clicked.connect(self._restart_widgets)
        layout.addWidget(btn_restart)

        act_app_conf = QPushButton("Настройки приложения")
        act_app_conf.clicked.connect(self._open_app_settings)
        layout.addWidget(act_app_conf)
        
        btn_quit = QPushButton("Выход")
        btn_quit.setStyleSheet("background-color: #552222; color: white;")
        btn_quit.clicked.connect(self._quit_app)
        layout.addWidget(btn_quit)
        
        # Перехватываем закрытие окна (крестик), чтобы спросить выход
        # Используем monkey-patching метода closeEvent для экземпляра
        self.fallback_window.closeEvent = self._on_fallback_close
        
        self.fallback_window.show()

    def _on_fallback_close(self, event):
        """Обработчик нажатия на крестик в Fallback окне."""
        reply = QMessageBox.question(
            self.fallback_window, 
            "Выход", 
            "Закрыть ChronoDash и убрать все виджеты?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self._quit_app()
            event.accept()
        else:
            event.ignore()

    def _on_update_found(self):
        """Показывает уведомление об обновлении"""
        print("Запускаем окно обновлений")
        self.updatewindows = UpdateWindows(self.wm)
        
        self.updatewindows.show()
        self.updatewindows.activateWindow()

    def _open_update_link(self):
        if hasattr(self, 'update_url'):
            self.updater.open_url(self.update_url)

    def _load_icon(self, target_obj):
        """Загружает иконку для трея или окна."""
        if platform.system() == "Windows":
            icon_path = Path(__file__).parent.parent / "assets" / "icons" / "chronodash.ico"
        else:
            icon_path = Path(__file__).parent.parent / "assets" / "icons" / "chronodash.png"
            
        icon = None
        if icon_path.exists():
            icon = QIcon(str(icon_path))
        else:
            # Fallback (рисуем программно)
            pix = QPixmap(64, 64)
            pix.fill(Qt.transparent)
            p = QPainter(pix)
            p.setRenderHint(QPainter.Antialiasing)
            p.setBrush(QColor("#0078D7"))
            p.setPen(Qt.NoPen)
            p.drawEllipse(4, 4, 56, 56)
            p.setBrush(QColor("white"))
            p.drawRect(20, 20, 24, 24)
            p.end()
            icon = QIcon(pix)
            
        if isinstance(target_obj, QSystemTrayIcon):
            target_obj.setIcon(icon)
        elif isinstance(target_obj, QWidget):
            target_obj.setWindowIcon(icon)

    def _on_tray_click(self, reason):
        # На Linux Trigger срабатывает при клике ЛКМ
        if reason == QSystemTrayIcon.Trigger:
            self._open_settings()

    def _open_settings(self):
        if not self.settings_window:
            self.settings_window = SettingsWindow(self.wm)
        
        # Восстанавливаем окно, если свернуто, и поднимаем наверх
        self.settings_window.show()
        self.settings_window.activateWindow()
        self.settings_window.raise_()

    def _restart_widgets(self):
        self.wm.stop_all_widgets()
        # Небольшая задержка перед запуском
        QTimer.singleShot(500, self.wm.load_and_create_all_widgets)

    def _quit_app(self):
        print("Завершение работы...")
        self.wm.stop_all_widgets()
        
        if self.settings_window:
            self.settings_window.close()
            
        if self.fallback_window:
            # Отключаем событие закрытия, чтобы не спрашивал второй раз
            self.fallback_window.closeEvent = lambda e: e.accept()
            self.fallback_window.close()
            
        QApplication.quit()

    def run(self):
        """
        Метод для совместимости (если вызывается из main.py).
        В Qt loop запускается в main.py, здесь ничего блокировать не нужно.
        """
        pass