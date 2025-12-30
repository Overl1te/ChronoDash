# ChronoDash - Base Widget
# Copyright (C) 2025 Overl1te

from pathlib import Path
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QPixmap, QColor, QPen, QIcon, QFont
from PySide6.QtCore import Qt, QTimer
import platform


class BaseDesktopWidget(QWidget):
    """
    Базовый класс, от которого наследуются все конкретные виджеты.
    """
    def __init__(self, cfg=None, is_preview=False):
        super().__init__()

        self.cfg = cfg or {}                # Конфигурация виджета
        self.is_preview = is_preview        # True — если это превью в дашборде
        self.is_editing = False             # True — в режиме редактирования
        self.resize_margin = 10             
        self.resize_mode = None             
        self.start_geometry = None          
        self.drag_pos = None                

        # Прозрачный фон
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setAutoFillBackground(False)
        self.setStyleSheet("background: transparent;")

        # Применяем флаги окна и прозрачность
        self.__apply_flags()
        self.__apply_opacity()

        # Устанавливаем размер и позицию
        self.resize(
            max(self.cfg.get("width", 320), 10),
            max(self.cfg.get("height", 180), 10)
        )
        self.move(self.cfg.get("x", 100), self.cfg.get("y", 100))

        # Иконка приложения
        self._load_icon()

    def _load_icon(self):
        if platform.system() == "Windows":
            icon_path = Path(__file__).parent.parent / "assets" / "icons" / "chronodash.ico"
        else:
            icon_path = Path(__file__).parent.parent / "assets" / "icons" / "chronodash.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

    def closeEvent(self, event):
        event.accept()

    def __apply_opacity(self):
        opacity = self.cfg.get("opacity", 1.0)
        if self.is_editing:
            self.setWindowOpacity(1.0)
        else:
            self.setWindowOpacity(max(0.01, min(1.0, opacity)))

    def showEvent(self, event):
        super().showEvent(event)
        if not self.is_editing and not self.is_preview:
            self.raise_()
            self.activateWindow()
            QTimer.singleShot(100, self.raise_)

    def __apply_flags(self):
        flags = Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        ignore_mouse = False

        if not self.is_preview and not self.is_editing:
            if self.cfg.get("click_through", True):
                flags |= Qt.WindowTransparentForInput
                ignore_mouse = True

            if platform.system() == "Windows":
                QTimer.singleShot(0, self._set_desktop_parent)

        if self.windowFlags() != flags:
            self.setWindowFlags(flags)
            self.show()

        self.setAttribute(Qt.WA_TransparentForMouseEvents, ignore_mouse)

    def _recreate_window(self):
        # Логика пересоздания окна (fix stacking)
        geo = self.geometry()
        opacity = self.windowOpacity()
        was_visible = self.isVisible()
        
        cfg_copy = self.cfg.copy()
        is_editing = self.is_editing
        is_preview = self.is_preview
        
        self.close()
        self.deleteLater()
        
        from core.registry import get_module
        module = get_module(cfg_copy.get("type"))
        if module and hasattr(module, "WidgetClass"):
            new_widget = module.WidgetClass(cfg_copy, is_preview=is_preview)
            new_widget.is_editing = is_editing
            new_widget.setGeometry(geo)
            new_widget.setWindowOpacity(opacity)
            if was_visible:
                new_widget.show()
            
            from core.qt_bridge import get_qt_bridge
            bridge = get_qt_bridge()
            if bridge and bridge.wm and cfg_copy.get("id") in bridge.wm.widgets:
                bridge.wm.widgets[cfg_copy.get("id")] = new_widget

    def _set_desktop_parent(self):
        if platform.system() != "Windows" or self.is_preview or self.is_editing:
            return
        try:
            import win32gui
            import win32con
            progman = win32gui.FindWindow("Progman", None)
            win32gui.SendMessageTimeout(progman, 0x052C, 0, 0, win32con.SMTO_NORMAL, 1000)
            def_view = win32gui.FindWindowEx(progman, 0, "SHELLDLL_DefView", None)
            if def_view:
                worker_w = win32gui.FindWindowEx(def_view, 0, "WorkerW", None)
                if worker_w:
                    win32gui.SetParent(int(self.winId()), worker_w)
        except Exception:
            pass

    def set_edit_mode(self, enabled: bool):
        self.is_editing = enabled
        if enabled:
            self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
            self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
            self.show()
        else:
            self.__apply_flags()
        self.__apply_opacity()
        self.update()
        self.raise_()
        self.activateWindow()

    def update_config(self, new_cfg):
        if self.is_editing:
            for key, value in new_cfg.items():
                if key not in ["x", "y", "width", "height"]:
                    self.cfg[key] = value
            self.update()
            return

        self.cfg = new_cfg.copy()
        self.__apply_flags()
        self.__apply_opacity()
        self.resize(
            max(self.cfg.get("width", 320), 10), max(self.cfg.get("height", 180), 10)
        )
        self.move(self.cfg.get("x", self.pos().x()), self.cfg.get("y", self.pos().y()))
        self.update()

    def paintEvent(self, event):
        """
        Отрисовывает виджет + рамку редактирования + Debug Borders.
        """
        painter = QPainter(self)
        try:
            r = self.rect()

            # 1. Очистка фона (для прозрачности)
            painter.setCompositionMode(QPainter.CompositionMode_Source)
            painter.fillRect(r, Qt.transparent)
            
            # 2. Подготовка к рисованию
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
            
            if self.is_editing:
                # Невидимый слой для захвата мыши при редактировании
                painter.fillRect(r, QColor(0, 0, 0, 1)) 
                self._draw_edit_border(painter)
                
            # Рисуем контент виджета
            self.draw_widget(painter)

            # === 3. DEBUG BORDERS (Wireframe) ===
            # Проверяем флаг в менеджере через мост
            try:
                # Ленивый импорт, чтобы избежать circular import
                from core.qt_bridge import get_qt_bridge 
                bridge = get_qt_bridge()
                
                # Если мост есть, и флаг debug_borders установлен в True
                if bridge and hasattr(bridge.wm, "debug_borders") and bridge.wm.debug_borders:
                    # Рисуем красную рамку
                    painter.setPen(QPen(QColor("red"), 2))
                    painter.setBrush(Qt.NoBrush)
                    painter.drawRect(r.adjusted(1, 1, -1, -1))
                    
                    # Рисуем ID виджета и геометрию
                    wid = str(self.cfg.get('id', '???'))[:4]
                    info = f"ID:{wid} {r.width()}x{r.height()}"
                    
                    painter.setPen(QColor("yellow"))
                    painter.setFont(QFont("Consolas", 10, QFont.Bold))
                    # Рисуем подложку под текст для читаемости
                    bg_rect = painter.fontMetrics().boundingRect(info)
                    bg_rect.moveTo(5, 5)
                    painter.fillRect(bg_rect, QColor(0, 0, 0, 150))
                    painter.drawText(bg_rect.adjusted(2,0,0,0), Qt.AlignCenter, info)
            except Exception:
                pass 

        except Exception as e:
            print(f"Paint Error in {self.__class__.__name__}: {e}")
        finally:
            painter.end()

    def _draw_edit_border(self, painter: QPainter):
        rect = self.rect()
        pen = QPen(QColor("#0099FF"))
        pen.setWidth(2)
        pen.setStyle(Qt.DashLine)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(rect.adjusted(1, 1, -1, -1))

        handle_size = 8
        painter.setBrush(QColor("#0099FF"))
        painter.setPen(Qt.NoPen)
        # Углы
        painter.drawRect(rect.width() - handle_size, rect.height() - handle_size, handle_size, handle_size)
        painter.drawRect(rect.width() - handle_size, 0, handle_size, handle_size)
        painter.drawRect(0, rect.height() - handle_size, handle_size, handle_size)
        painter.drawRect(0, 0, handle_size, handle_size)

    def draw_widget(self, painter: QPainter):
        pass

    def _get_resize_mode(self, pos):
        w, h = self.width(), self.height()
        m = self.resize_margin
        x, y = pos.x(), pos.y()
        mode = ""
        if y < m: mode += "top"
        elif y > h - m: mode += "bottom"
        if x < m: mode += "left"
        elif x > w - m: mode += "right"
        return mode

    def mousePressEvent(self, event):
        if (self.is_editing or self.is_preview) and event.button() == Qt.LeftButton:
            self.resize_mode = self._get_resize_mode(event.pos())
            self.drag_pos = event.globalPos()
            self.start_geometry = self.geometry()

    def mouseMoveEvent(self, event):
        if (self.is_editing or self.is_preview) and not self.drag_pos:
            mode = self._get_resize_mode(event.pos())
            cursor = Qt.ArrowCursor
            if mode in ["left", "right"]: cursor = Qt.SizeHorCursor
            elif mode in ["top", "bottom"]: cursor = Qt.SizeVerCursor
            elif mode in ["topleft", "bottomright"]: cursor = Qt.SizeFDiagCursor
            elif mode in ["topright", "bottomleft"]: cursor = Qt.SizeBDiagCursor
            elif mode == "": cursor = Qt.SizeAllCursor
            self.setCursor(cursor)
            return

        if self.drag_pos and event.buttons() == Qt.LeftButton:
            delta = event.globalPos() - self.drag_pos
            geo = self.start_geometry

            if self.resize_mode == "":
                self.move(geo.topLeft() + delta)
            else:
                x, y, w, h = geo.x(), geo.y(), geo.width(), geo.height()
                dx, dy = delta.x(), delta.y()
                min_w, min_h = 20, 20

                if "right" in self.resize_mode: w = max(min_w, w + dx)
                if "left" in self.resize_mode:
                    new_w = max(min_w, w - dx)
                    if new_w > min_w: x += dx; w = new_w
                if "bottom" in self.resize_mode: h = max(min_h, h + dy)
                if "top" in self.resize_mode:
                    new_h = max(min_h, h - dy)
                    if new_h > min_h: y += dy; h = new_h

                self.setGeometry(x, y, w, h)
            self.update()

    def mouseReleaseEvent(self, event):
        if self.drag_pos is not None:
            self.drag_pos = None
            self.resize_mode = None
            if self.is_editing:
                self.setCursor(Qt.ArrowCursor)

    @staticmethod
    def render_to_pixmap(cfg: dict) -> QPixmap:
        width = max(cfg.get("width", 320), 50)
        height = max(cfg.get("height", 180), 50)
        pixmap = QPixmap(width, height)
        pixmap.fill(Qt.transparent)

        temp_widget = BaseDesktopWidget._create_instance_for_render(cfg, is_preview=True)
        if not temp_widget:
            return pixmap

        temp_widget.resize(width, height)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Защищаем рендер превью тоже
        try:
            temp_widget.draw_widget(painter)
        except: pass
        finally:
            painter.end()
            
        temp_widget.deleteLater()
        return pixmap

    @staticmethod
    def _create_instance_for_render(cfg: dict, is_preview=False):
        from core.registry import get_module
        module = get_module(cfg.get("type"))
        if module and hasattr(module, "WidgetClass"):
             return module.WidgetClass(cfg, is_preview=is_preview)
        return BaseDesktopWidget(cfg, is_preview=is_preview)