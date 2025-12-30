from widgets.base_widget import BaseDesktopWidget
from PySide6.QtGui import QPainter, QFont, QColor
from PySide6.QtCore import QDateTime, QTimer, Qt
from PySide6.QtWidgets import QLabel, QLineEdit, QSpinBox, QPushButton, QColorDialog, QHBoxLayout

class ClockWidget(BaseDesktopWidget):
    def __init__(self, cfg=None, is_preview=False):
        super().__init__(cfg, is_preview=is_preview)
        self._apply_content_settings()
        if not self.is_preview:
            self._start_clock()

    def _start_clock(self):
        self.update()
        interval = 100 if ".z" in self.format else 1000
        QTimer.singleShot(interval, self._start_clock)

    def _apply_content_settings(self):
        content = self.cfg.get("content", {})
        self.format = content.get("format", "HH:mm:ss")
        self.font_family = content.get("font_family", "Consolas")
        self.font_size = int(content.get("font_size", 48))
        
        col_str = content.get("color", "#00FF88")
        self.color = QColor(col_str)
        if not self.color.isValid(): self.color = QColor("#00FF88")

    def update_config(self, new_cfg):
        super().update_config(new_cfg)
        self._apply_content_settings()
        self.update()

    def draw_widget(self, painter: QPainter):
        try:
            current_time = QDateTime.currentDateTime().toString(self.format)
            font = QFont(self.font_family, self.font_size)
            font.setStyleStrategy(QFont.PreferAntialias)
            painter.setFont(font)
            painter.setPen(self.color)
            painter.drawText(self.rect(), Qt.AlignCenter, current_time)
        except Exception:
            pass

def get_default_config():
    return {
        "type": "clock",
        "name": "Часы",
        "width": 350,
        "height": 150,
        "opacity": 1.0,
        "always_on_top": True,
        "click_through": True,
        "content": {
            "format": "HH:mm:ss",
            "color": "#00FF88",
            "font_family": "Segoe UI",
            "font_size": 64
        }
    }

# === НОВЫЙ UI НАСТРОЕК (Qt) ===
def render_qt_settings(layout, cfg, on_update):
    content = cfg.get("content", {})

    # Формат
    layout.addWidget(QLabel("Формат времени (Python strftime):"))
    fmt_edit = QLineEdit(content.get("format", "HH:mm:ss"))
    fmt_edit.textChanged.connect(lambda v: on_update("content.format", v))
    layout.addWidget(fmt_edit)

    # Размер шрифта
    layout.addWidget(QLabel("Размер шрифта:"))
    sz_spin = QSpinBox()
    sz_spin.setRange(8, 500)
    sz_spin.setValue(int(content.get("font_size", 64)))
    sz_spin.valueChanged.connect(lambda v: on_update("content.font_size", v))
    layout.addWidget(sz_spin)

    # Цвет
    layout.addWidget(QLabel("Цвет текста:"))
    color_val = content.get("color", "#00FF88")
    
    col_layout = QHBoxLayout()
    col_edit = QLineEdit(color_val)
    col_btn = QPushButton("Выбрать")
    col_btn.setStyleSheet(f"background-color: {color_val}; color: black;")
    
    def pick_color():
        c = QColorDialog.getColor(QColor(color_val))
        if c.isValid():
            hex_c = c.name().upper()
            col_edit.setText(hex_c)
            col_btn.setStyleSheet(f"background-color: {hex_c}")
            on_update("content.color", hex_c)

    col_btn.clicked.connect(pick_color)
    col_edit.textChanged.connect(lambda v: on_update("content.color", v))
    
    col_layout.addWidget(col_edit)
    col_layout.addWidget(col_btn)
    layout.addLayout(col_layout)

    # Шрифт
    layout.addWidget(QLabel("Семейство шрифта:"))
    font_edit = QLineEdit(content.get("font_family", "Segoe UI"))
    font_edit.textChanged.connect(lambda v: on_update("content.font_family", v))
    layout.addWidget(font_edit)

WidgetClass = ClockWidget