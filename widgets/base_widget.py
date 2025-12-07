from PySide6.QtWidgets import QWidget, QApplication, QMenu
from PySide6.QtCore import Qt, QTimer, QRect
import sys, platform
try:
    import win32con, win32gui, win32api
except Exception:
    win32gui = None

class BaseDesktopWidget(QWidget):
    def __init__(self, cfg=None):
        super().__init__(flags=Qt.Tool)
        self.cfg = cfg or {}
        self.setup_window()

    def setup_window(self):
        self.setWindowFlag(Qt.FramelessWindowHint, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        if win32gui:
            try:
                hwnd = self.winId().__int__()
                ex = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
                ex = ex | win32con.WS_EX_LAYERED
                if self.cfg.get('click_through', True):
                    ex = ex | win32con.WS_EX_TRANSPARENT
                win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ex)
            except Exception:
                pass

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.addAction("Настроить", self.on_configure)
        menu.addAction("Удалить", self.on_delete)
        menu.exec(event.globalPos())

    def on_configure(self):
        print('configure requested')

    def on_delete(self):
        print('delete requested')
