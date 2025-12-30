# ChronoDash - Base Widget
# Copyright (C) 2025 Overl1te

from pathlib import Path
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QColor, QPen, QIcon, QRegion, QCursor, QPixmap
from PySide6.QtCore import Qt, QTimer, QPoint, QRect, Signal
import platform

# --- КОНСТАНТЫ ---
ACTION_NONE = 0
ACTION_MOVE = 1
ACTION_RESIZE = 2

# Зоны клика
AREA_CENTER = 0
AREA_TOP = 1
AREA_BOTTOM = 2
AREA_LEFT = 3
AREA_RIGHT = 4
AREA_TOP_LEFT = 5
AREA_TOP_RIGHT = 6
AREA_BOTTOM_LEFT = 7
AREA_BOTTOM_RIGHT = 8

class BaseDesktopWidget(QWidget):
    config_changed = Signal(str, dict)

    def __init__(self, cfg=None, is_preview=False):
        super().__init__()

        self.cfg = cfg or {}
        self.is_preview = is_preview
        self.is_editing = False
        self.wid_log_id = self.cfg.get("id", "unknown")[:4]
        
        self.resize_margin = 15       
        self.min_size = 50            

        self._action = ACTION_NONE
        self._resize_area = AREA_CENTER
        self._drag_start_pos = QPoint()
        self._win_start_geo = QRect()

        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WA_Hover, True) 
        self.setAutoFillBackground(False)
        self.setStyleSheet("background: transparent;")

        self.__apply_flags()
        self.__apply_opacity()

        w = max(int(self.cfg.get("width", 320)), self.min_size)
        h = max(int(self.cfg.get("height", 180)), self.min_size)
        self.resize(w, h)
        self.move(int(self.cfg.get("x", 100)), int(self.cfg.get("y", 100)))
        
        self._load_icon()

    def _log(self, msg):
        if self.is_editing:
            print(f"[{self.wid_log_id}] {msg}")

    def _load_icon(self):
        try:
            name = "chronodash.ico" if platform.system() == "Windows" else "chronodash.png"
            icon_path = Path(__file__).parent.parent / "assets" / "icons" / name
            if icon_path.exists():
                self.setWindowIcon(QIcon(str(icon_path)))
        except: pass

    # === ЖИЗНЕННЫЙ ЦИКЛ ===

    def showEvent(self, event):
        super().showEvent(event)
        if not self.is_editing and not self.is_preview:
            self.raise_()
            QTimer.singleShot(100, self.activateWindow)
        
        if self.is_editing:
            self.setMask(self.rect())

    def resizeEvent(self, event):
        # Страховка: если размер изменился НЕ мышкой (а кодом), 
        # маска все равно должна обновиться.
        if self.is_editing:
            self.clearMask()
            self.setMask(self.rect())
        else:
            self.clearMask()
        super().resizeEvent(event)

    def update_config(self, new_cfg):
        if self._action != ACTION_NONE: return

        if self.is_editing:
            for key, value in new_cfg.items():
                if key not in ["x", "y", "width", "height"]:
                    self.cfg[key] = value
            self.update()
            return

        self.cfg = new_cfg.copy()
        self.__apply_flags()
        self.__apply_opacity()
        
        target_w = max(int(self.cfg.get("width", 320)), self.min_size)
        target_h = max(int(self.cfg.get("height", 180)), self.min_size)
        
        self.setGeometry(
            int(self.cfg.get("x", self.x())), 
            int(self.cfg.get("y", self.y())),
            target_w, target_h
        )
        self.update()

    def set_edit_mode(self, enabled: bool):
        geo = self.geometry()
        self.is_editing = enabled
        
        if enabled:
            self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
            self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
            self.show()
            self.setMouseTracking(True)
            
            # Полный сброс и установка маски при входе
            self.clearMask()
            self.setMask(self.rect())
            self._log(f"Edit ENABLED. Mask Reset.")
        else:
            self.setMouseTracking(False)
            self.__apply_flags()
            self.clearMask()
            self._log(f"Edit DISABLED.")
            
        self.__apply_opacity()
        self.setGeometry(geo)
        
        if enabled:
            self.raise_()
            self.activateWindow()
        self.update()

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
            geo = self.geometry()
            self.setWindowFlags(flags)
            self.setGeometry(geo)
            self.show()

        self.setAttribute(Qt.WA_TransparentForMouseEvents, ignore_mouse)

    def __apply_opacity(self):
        val = 1.0 if self.is_editing else self.cfg.get("opacity", 1.0)
        self.setWindowOpacity(max(0.01, min(1.0, val)))

    def _set_desktop_parent(self):
        if platform.system() != "Windows" or self.is_preview or self.is_editing: return
        try:
            import win32gui, win32con
            progman = win32gui.FindWindow("Progman", None)
            win32gui.SendMessageTimeout(progman, 0x052C, 0, 0, win32con.SMTO_NORMAL, 1000)
            def_view = win32gui.FindWindowEx(progman, 0, "SHELLDLL_DefView", None)
            if def_view:
                worker_w = win32gui.FindWindowEx(def_view, 0, "WorkerW", None)
                if worker_w: win32gui.SetParent(int(self.winId()), worker_w)
        except: pass

    # ==========================================================================
    #  МАТЕМАТИКА И DRAG&DROP
    # ==========================================================================

    def _hit_test(self, global_pos):
        if not self.is_editing: return AREA_CENTER
        
        local_pos = self.mapFromGlobal(global_pos)
        x, y = local_pos.x(), local_pos.y()
        w, h = self.width(), self.height()
        m = self.resize_margin

        if x < m and y < m: return AREA_TOP_LEFT
        if x > w-m and y < m: return AREA_TOP_RIGHT
        if x < m and y > h-m: return AREA_BOTTOM_LEFT
        if x > w-m and y > h-m: return AREA_BOTTOM_RIGHT

        if x < m: return AREA_LEFT
        if x > w-m: return AREA_RIGHT
        if y < m: return AREA_TOP
        if y > h-m: return AREA_BOTTOM

        return AREA_CENTER

    def mousePressEvent(self, event):
        if not (self.is_editing or self.is_preview): return
        if event.button() != Qt.LeftButton: return

        self.grabMouse() 

        self._drag_start_pos = event.globalPos()
        self._win_start_geo = self.geometry()
        
        area = self._hit_test(event.globalPos())
        self._resize_area = area
        
        if area == AREA_CENTER:
            self._action = ACTION_MOVE
        else:
            self._action = ACTION_RESIZE

        event.accept()

    def mouseMoveEvent(self, event):
        if not (self.is_editing or self.is_preview): return

        global_pos = event.globalPos()

        if self._action == ACTION_NONE:
            area = self._hit_test(global_pos)
            self._update_cursor(area)
            return

        delta = global_pos - self._drag_start_pos
        dx, dy = delta.x(), delta.y()

        start = self._win_start_geo
        new_geo = QRect(start)

        if self._action == ACTION_MOVE:
            new_geo.translate(dx, dy)
            self.move(new_geo.topLeft())

        elif self._action == ACTION_RESIZE:
            area = self._resize_area
            min_s = self.min_size
            
            # --- Расчет геометрии ---
            if area in [AREA_LEFT, AREA_TOP_LEFT, AREA_BOTTOM_LEFT]:
                w = start.width() - dx
                if w < min_s: new_geo.setLeft(start.right() - min_s + 1)
                else: new_geo.setLeft(start.left() + dx)
            elif area in [AREA_RIGHT, AREA_TOP_RIGHT, AREA_BOTTOM_RIGHT]:
                w = start.width() + dx
                new_geo.setWidth(max(min_s, w))

            if area in [AREA_TOP, AREA_TOP_LEFT, AREA_TOP_RIGHT]:
                h = start.height() - dy
                if h < min_s: new_geo.setTop(start.bottom() - min_s + 1)
                else: new_geo.setTop(start.top() + dy)
            elif area in [AREA_BOTTOM, AREA_BOTTOM_LEFT, AREA_BOTTOM_RIGHT]:
                h = start.height() + dy
                new_geo.setHeight(max(min_s, h))

            # --- ПРИМЕНЕНИЕ (Hard Reset) ---
            # 1. Применяем размеры
            self.setGeometry(new_geo)
            
            # 2. ЖЕСТКАЯ ПЕРЕРИСОВКА МАСКИ
            # Как ты и просил: "удаляем и рисуем заново".
            # Мы не ждем resizeEvent, мы делаем это прямо здесь и сейчас.
            if self.is_editing:
                self.clearMask()
                # Важно: создаем регион по НОВЫМ размерам (w, h),
                # так как self.rect() может еще не успеть обновиться в недрах Qt.
                mask_region = QRegion(0, 0, new_geo.width(), new_geo.height())
                self.setMask(mask_region)

        self._notify_update()
        event.accept()

    def mouseReleaseEvent(self, event):
        if self._action != ACTION_NONE:
            self._action = ACTION_NONE
            self._resize_area = AREA_CENTER
            
            self.releaseMouse()
            
            self._update_cursor(self._hit_test(event.globalPos()))
            self._notify_update()
            event.accept()

    def _notify_update(self):
        if self.is_preview: return
        geo = self.geometry()
        self.cfg["x"] = geo.x()
        self.cfg["y"] = geo.y()
        self.cfg["width"] = geo.width()
        self.cfg["height"] = geo.height()
        self.config_changed.emit(self.cfg.get("id"), self.cfg)

    def leaveEvent(self, event):
        if self.is_editing and self._action == ACTION_NONE:
            self.setCursor(Qt.ArrowCursor)
        super().leaveEvent(event)

    def _update_cursor(self, area):
        cursors = {
            AREA_CENTER: Qt.SizeAllCursor,
            AREA_LEFT: Qt.SizeHorCursor,
            AREA_RIGHT: Qt.SizeHorCursor,
            AREA_TOP: Qt.SizeVerCursor,
            AREA_BOTTOM: Qt.SizeVerCursor,
            AREA_TOP_LEFT: Qt.SizeFDiagCursor,
            AREA_BOTTOM_RIGHT: Qt.SizeFDiagCursor,
            AREA_TOP_RIGHT: Qt.SizeBDiagCursor,
            AREA_BOTTOM_LEFT: Qt.SizeBDiagCursor
        }
        self.setCursor(cursors.get(area, Qt.ArrowCursor))

    def paintEvent(self, event):
        painter = QPainter(self)
        try:
            r = self.rect()
            
            painter.setCompositionMode(QPainter.CompositionMode_Source)
            painter.fillRect(r, Qt.transparent)
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
            
            if self.is_editing:
                # Рисуем подложку (почти прозрачную, но существующую)
                painter.fillRect(r, QColor(0, 0, 0, 1)) 
                self._draw_edit_handles(painter)
                
            self.draw_widget(painter)
        except Exception as e:
            print(f"Paint Error: {e}")
        finally:
            painter.end()

    def _draw_edit_handles(self, painter: QPainter):
        rect = self.rect()
        painter.fillRect(rect, QColor(0, 0, 0, 20))
        
        pen = QPen(QColor("#007fd4"))
        pen.setWidth(2)
        pen.setStyle(Qt.DashLine)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(rect.adjusted(1, 1, -1, -1))

        hs = 8 
        painter.setBrush(QColor("#007fd4"))
        painter.setPen(Qt.NoPen)
        w, h = rect.width(), rect.height()
        pts = [
            (0, 0), (w-hs, 0),                          
            (0, h-hs), (w-hs, h-hs),                    
            (w//2 - hs//2, 0), (w//2 - hs//2, h-hs),    
            (0, h//2 - hs//2), (w-hs, h//2 - hs//2)     
        ]
        for px, py in pts:
            painter.drawRect(px, py, hs, hs)

    def draw_widget(self, painter: QPainter):
        pass

    @staticmethod
    def render_to_pixmap(cfg: dict) -> QPixmap:
        width = max(int(cfg.get("width", 320)), 50)
        height = max(int(cfg.get("height", 180)), 50)
        pixmap = QPixmap(width, height)
        pixmap.fill(Qt.transparent)
        temp_widget = BaseDesktopWidget._create_instance_for_render(cfg, is_preview=True)
        if not temp_widget: return pixmap
        temp_widget.resize(width, height)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        try: temp_widget.draw_widget(painter)
        except: pass
        finally: painter.end()
        temp_widget.deleteLater()
        return pixmap

    @staticmethod
    def _create_instance_for_render(cfg: dict, is_preview=False):
        from core.registry import get_module
        module = get_module(cfg.get("type"))
        if module and hasattr(module, "WidgetClass"):
             return module.WidgetClass(cfg, is_preview=is_preview)
        return BaseDesktopWidget(cfg, is_preview=is_preview)