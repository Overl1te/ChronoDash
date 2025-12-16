# widgets/base_widget.py
from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtGui import QPainter, QPixmap, QColor, QPen, QCursor
from PySide6.QtCore import Qt, QRect

class BaseDesktopWidget(QWidget):
    def __init__(self, cfg=None, is_preview=False): 
        super().__init__()
        self.cfg = cfg or {}
        self.is_preview = is_preview 
        self.is_editing = False # <-- Добавляем этот атрибут

        # ⭐ НОВЫЕ АТРИБУТЫ ДЛЯ РЕДАКТИРОВАНИЯ
        self.resize_margin = 10     
        self.resize_mode = None     
        self.start_geometry = None  
        
        # ⭐ drag_pos уже был, оставляем
        self.drag_pos = None

        self.setStyleSheet("background: transparent;")
        
        self._apply_flags() 
        self._apply_opacity()

        self.resize(max(self.cfg.get("width", 320), 10),
                    max(self.cfg.get("height", 180), 10))
        self.move(self.cfg.get("x", 100), self.cfg.get("y", 100))

        self.drag_pos = None

    # Включаем/выключаем режим редактора
    def set_edit_mode(self, active: bool):
        self.is_editing = active
        
        if active:
            # В режиме редактирования: НЕ WindowTransparentForInput, ЛОВИТЬ МЫШЬ
            flags = Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool # Qt.Tool тут для управления Z-слоем
            self.setWindowFlags(flags)
            self.setAttribute(Qt.WA_TransparentForMouseEvents, False) 
            self.setMouseTracking(True)
            self.show()
            self.raise_()
        else:
            self.setMouseTracking(False)
            self._apply_flags() # Возвращаем обычный режим (click-through)
            self._apply_opacity()
            self.show()
        
        self.update() # Перерисовка для отображения рамки

    def closeEvent(self, event):
        event.accept()
    
    def _apply_opacity(self):
        opacity = self.cfg.get("opacity", 1.0)
        # В режиме редактирования делаем ПОЛНОСТЬЮ непрозрачным для удобства
        if self.is_editing:
             self.setWindowOpacity(1.0) 
        else:
             self.setWindowOpacity(max(0.01, min(1.0, opacity)))

    def _apply_flags(self):
        # Базовые флаги: Нет рамки + Поверх всех
        flags = Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint

        # ⭐ ГЛАВНОЕ ИСПРАВЛЕНИЕ: Добавляем Qt.Tool. 
        # Это убирает виджет из панели задач и Alt+Tab.
        # Это должно быть применено всегда, кроме, может быть, Preview.
        if not self.is_preview:
            flags |= Qt.Tool 
        
        # Если виджет не в режиме превью и не в режиме редактирования, применяем click-through
        ignore_mouse = False
        if not self.is_preview and not self.is_editing:
            if self.cfg.get("click_through", True):
                flags |= Qt.WindowTransparentForInput
                ignore_mouse = True
        
        # 1. Применяем флаги
        current_flags = self.windowFlags()
        if current_flags != flags:
            self.setWindowFlags(flags)
            # При смене флагов нужно вызвать show() для их активации
            if self.isVisible():
                 self.show() 

        # 2. Применяем атрибут мыши
        self.setAttribute(Qt.WA_TransparentForMouseEvents, ignore_mouse)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

    def update_config(self, new_cfg):
        # Если мы сейчас редактируем этот виджет, не обновляем позицию из конфига,
        # чтобы не сбить драг-н-дроп.
        if self.is_editing:
            # Обновляем только контент (цвет, формат)
            self.cfg.update(new_cfg)
            self.update()
            return

        self.cfg = new_cfg.copy()
        self._apply_flags() 
        self._apply_opacity()
        self.resize(max(self.cfg.get("width", 320), 10),
                    max(self.cfg.get("height", 180), 10))
        self.move(self.cfg.get("x", self.pos().x()), self.cfg.get("y", self.pos().y()))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        self.draw_widget(painter)
        
        # РИСУЕМ ИНТЕРФЕЙС РЕДАКТОРА ПОВЕРХ
        if self.is_editing:
            self._draw_edit_overlay(painter)
            
        painter.end()

    def _draw_edit_overlay(self, painter):
        rect = self.rect()
        # Пунктирная рамка
        pen = QPen(QColor("#0099FF"))
        pen.setWidth(2)
        pen.setStyle(Qt.DashLine)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        # Чуть отступаем внутрь, чтобы рамка была видна целиком
        painter.drawRect(rect.adjusted(1,1,-1,-1))

        # Рисуем "ручки" по углам
        handle_size = 8
        painter.setBrush(QColor("#0099FF"))
        painter.setPen(Qt.NoPen)
        
        # Правый нижний
        painter.drawRect(rect.width() - handle_size, rect.height() - handle_size, handle_size, handle_size)
        # Правый верхний
        painter.drawRect(rect.width() - handle_size, 0, handle_size, handle_size)
        # Левый нижний
        painter.drawRect(0, rect.height() - handle_size, handle_size, handle_size)
        # Левый верхний
        painter.drawRect(0, 0, handle_size, handle_size)

    def draw_widget(self, painter: QPainter):
        pass

    # --- ЛОГИКА ПЕРЕМЕЩЕНИЯ И РЕСАЙЗА ---

    def _get_resize_mode(self, pos):
        """Возвращает '' для перемещения или имя края/угла для ресайза."""
        w, h = self.width(), self.height()
        m = self.resize_margin
        x, y = pos.x(), pos.y()

        mode = ""
        
        # Вертикальные края
        if y < m: mode += "top"
        elif y > h - m: mode += "bottom"
        
        # Горизонтальные края
        if x < m: mode += "left"
        elif x > w - m: mode += "right"
        
        # Если mode == "", значит клик в центре (режим перемещения)
        return mode

    # --- ЛОГИКА ПЕРЕМЕЩЕНИЯ И РЕСАЙЗА ---

    def mousePressEvent(self, event):
        # Активируем только в режиме редактирования/превью и только ЛЕВОЙ кнопкой
        if (self.is_editing or self.is_preview) and event.button() == Qt.LeftButton:
            
            self.resize_mode = self._get_resize_mode(event.pos())
            
            # ⭐ КРИТИЧНО: Если mode == "", то мы в режиме перемещения.
            # Если mode != "", то мы в режиме ресайза.
            
            self.drag_pos = event.globalPos()
            self.start_geometry = self.geometry()

    def mouseMoveEvent(self, event):
        
        # 1. Меняем курсор при наведении (если не тащим)
        if (self.is_editing or self.is_preview) and not self.drag_pos:
            mode = self._get_resize_mode(event.pos())
            cursor = Qt.ArrowCursor
            if mode in ["left", "right"]: cursor = Qt.SizeHorCursor
            elif mode in ["top", "bottom"]: cursor = Qt.SizeVerCursor
            elif mode in ["topleft", "bottomright"]: cursor = Qt.SizeFDiagCursor
            elif mode in ["topright", "bottomleft"]: cursor = Qt.SizeBDiagCursor
            elif mode == "": cursor = Qt.SizeAllCursor # Курсор перемещения (ЗАХВАТ)
            self.setCursor(cursor)
            return
            
        # 2. Движение (кнопка зажата)
        if self.drag_pos and event.buttons() == Qt.LeftButton:
            
            delta = event.globalPos() - self.drag_pos
            geo = self.start_geometry

            if self.resize_mode == "": 
                # ⭐ ПЕРЕМЕЩЕНИЕ: Срабатывает, если клик не был на краю (mode == "")
                self.move(geo.topLeft() + delta)
            
            else: 
                # РЕСАЙЗ: Клик был на краю
                x, y, w, h = geo.x(), geo.y(), geo.width(), geo.height()
                dx = delta.x()
                dy = delta.y()

                min_w, min_h = 20, 20

                if "right" in self.resize_mode: w = max(min_w, w + dx)
                if "left" in self.resize_mode:
                    new_w = max(min_w, w - dx)
                    if new_w > min_w: x += dx; w -= dx
                
                if "bottom" in self.resize_mode: h = max(min_h, h + dy)
                if "top" in self.resize_mode:
                    new_h = max(min_h, h - dy)
                    if new_h > min_h: y += dy; h -= dy
                
                self.setGeometry(x, y, w, h)
                
            self.update()

    def mouseReleaseEvent(self, event):
        # Сбрасываем все состояния
        if self.drag_pos is not None:
             self.drag_pos = None
             self.resize_mode = None
        
             # Сохраняем геометрию, если мы в режиме редактирования
             if self.is_editing:
                self.setCursor(Qt.ArrowCursor) 
                # Здесь должен быть вызов _save_current_geometry(),
                # но его должен делать WidgetManager при exit_edit_mode

    def _save_current_geometry(self):
        # Обновляем конфиг локально
        self.cfg["x"] = self.x()
        self.cfg["y"] = self.y()
        self.cfg["width"] = self.width()
        self.cfg["height"] = self.height()
        
        # Отправляем сигнал менеджеру, что данные обновились (чтобы синхронизировать с dashboard)
        # Это потребует обратной связи, но пока просто обновим конфиг в памяти менеджера
        from core.widget_manager import WidgetManager 
        # Ха, мы не имеем доступа к WM напрямую отсюда легко. 
        # Но мы можем использовать QtBridge для отправки сигнала обратно?
        # Или проще: WidgetManager держит ссылку на виджет. 
        # Виджет сам обновил self.cfg. 
        # WidgetManager при выходе из режима редактора сохранит всё.
        pass

    @staticmethod
    def render_to_pixmap(cfg: dict) -> QPixmap:
        # Без изменений
        width = max(cfg.get("width", 320), 50)
        height = max(cfg.get("height", 180), 50)
        pixmap = QPixmap(width, height)
        pixmap.fill(Qt.transparent)
        temp_widget = BaseDesktopWidget._create_instance_for_render(cfg, is_preview=True) 
        if not temp_widget: return pixmap
        temp_widget.resize(width, height) 
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        temp_widget.draw_widget(painter)
        painter.end()
        temp_widget.deleteLater() 
        return pixmap

    @staticmethod
    def _create_instance_for_render(cfg: dict, is_preview=False):
        from widgets.clock_widget import ClockWidget 
        if cfg.get("type") == "clock":
            return ClockWidget(cfg, is_preview=is_preview)
        return BaseDesktopWidget(cfg, is_preview=is_preview)