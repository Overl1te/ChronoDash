from PySide6.QtWidgets import QLabel
from PySide6.QtCore import QTimer, Qt, QTime
from widgets.base_widget import BaseDesktopWidget
from PySide6.QtGui import QFont

class ClockWidget(BaseDesktopWidget):
    def __init__(self, cfg=None):
        super().__init__(cfg=cfg)
        self.label = QLabel(self)
        fmt = cfg = cfg or {}
        self.format = fmt.get('content', {}).get('format', '%H:%M:%S')
        font_name = fmt.get('content', {}).get('font_family', 'Consolas')
        font_size = int(fmt.get('content', {}).get('font_size', 40))
        self.label.setFont(QFont(font_name, font_size))
        self.label.setAlignment(Qt.AlignCenter)
        self.resize(300, 100)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_time)
        self.timer.start(500)
        self.update_time()

    def update_time(self):
        from datetime import datetime
        now = datetime.now().strftime(self.format)
        self.label.setText(now)
        self.label.adjustSize()
