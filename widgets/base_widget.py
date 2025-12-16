# widgets/base_widget.py
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtCore import Qt

class BaseDesktopWidget(QWidget):
    def __init__(self, cfg=None, is_preview=False): 
        super().__init__()
        self.cfg = cfg or {}
        self.is_preview = is_preview 

        # ⭐ ИСПРАВЛЕНИЕ ПРОЗРАЧНОСТИ: Принудительный прозрачный фон через CSS
        self.setStyleSheet("background: transparent;")
        
        self._apply_flags() 
        self._apply_opacity() 

        self.resize(max(self.cfg.get("width", 320), 10),
                    max(self.cfg.get("height", 180), 10))
        self.move(self.cfg.get("x", 100), self.cfg.get("y", 100))

        self.drag_pos = None
    
    # close_event() — реализация через метод closeEvent Qt
    def closeEvent(self, event):
        print(f"Виджет {self.cfg.get('name', self.cfg.get('id'))} закрывается.")
        event.accept()
    
    def _apply_opacity(self):
        opacity = self.cfg.get("opacity", 1.0)
        # setWindowOpacity должен работать теперь, когда фон прозрачен
        self.setWindowOpacity(max(0.01, min(1.0, opacity)))

    def _apply_flags(self):
        flags = Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint
        
        if not self.is_preview:
            # flags |= Qt.Tool  # <-- УДАЛИТЬ ЭТУ СТРОКУ
            
            if self.cfg.get("click_through", True):
                flags |= Qt.WindowTransparentForInput
        
        self.setWindowFlags(flags)
        
        # ОБЯЗАТЕЛЬНО: устанавливаем атрибут для полупрозрачного фона
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        
        # Устанавливаем атрибут для игнорирования кликов мышью 
        self.setAttribute(Qt.WA_TransparentForMouseEvents, self.cfg.get("click_through", True) and not self.is_preview)

    def update_config(self, new_cfg):
        self.cfg = new_cfg.copy()
        
        # Обновление флагов и прозрачности
        self._apply_flags() 
        self._apply_opacity()
        
        # Обновление размеров
        self.resize(max(self.cfg.get("width", 320), 10),
                    max(self.cfg.get("height", 180), 10))
        
        # Обновление позиции
        self.move(self.cfg.get("x", self.pos().x()), self.cfg.get("y", self.pos().y()))
        
        # Принудительная перерисовка
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        self.draw_widget(painter)
        painter.end()

    def draw_widget(self, painter: QPainter):
        pass

    # Перетаскивание правой кнопкой
    def mousePressEvent(self, event):
        if not self.is_preview and event.button() == Qt.RightButton and not self.cfg.get("click_through", True):
            self.drag_pos = event.globalPos()

    def mouseMoveEvent(self, event):
        if self.drag_pos and event.buttons() == Qt.RightButton and not self.cfg.get("click_through", True) and not self.is_preview:
            delta = event.globalPos() - self.drag_pos
            self.move(self.pos() + delta)
            self.drag_pos = event.globalPos()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.RightButton:
            self.drag_pos = None

    @staticmethod
    def render_to_pixmap(cfg: dict) -> QPixmap:
        """Статический метод для рендеринга превью"""
        width = max(cfg.get("width", 320), 50)
        height = max(cfg.get("height", 180), 50)
        
        pixmap = QPixmap(width, height)
        pixmap.fill(Qt.transparent)
        
        # Создаем временный виджет с флагом is_preview=True
        temp_widget = BaseDesktopWidget._create_instance_for_render(cfg, is_preview=True) 
        
        if not temp_widget:
            return pixmap
            
        temp_widget.resize(width, height) 
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        temp_widget.draw_widget(painter)
        painter.end()
        
        temp_widget.deleteLater() 
        return pixmap

    # ДОБАВЛЕНО: Вспомогательный статический метод для создания инстанса
    @staticmethod
    def _create_instance_for_render(cfg: dict, is_preview=False):
        from widgets.clock_widget import ClockWidget 
        if cfg.get("type") == "clock":
            return ClockWidget(cfg, is_preview=is_preview)
        
        return BaseDesktopWidget(cfg, is_preview=is_preview)