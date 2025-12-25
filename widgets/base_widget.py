# ChronoDash - Desktop Widgets
# Copyright (C) 2025 Overl1te
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
Базовый класс для всех десктопных виджетов.

Обеспечивает:
- Прозрачный фон и отсутствие рамки
- Поддержку click-through (прозрачность для мыши)
- Режим редактирования (изменение размера и перемещение)
- Автоматическое поднятие виджета при появлении
- Скрытие из таскбара и Alt+Tab на Windows (дочернее окно рабочего стола)
- Рендеринг превью в off-screen pixmap
"""

from pathlib import Path
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QPixmap, QColor, QPen, QIcon
from PySide6.QtCore import Qt, QTimer
import platform


class BaseDesktopWidget(QWidget):
    """
    Базовый класс, от которого наследуются все конкретные виджеты (ClockWidget, WeatherWidget и т.д.).
    """
    def __init__(self, cfg=None, is_preview=False):
        super().__init__()

        self.cfg = cfg or {}                # Конфигурация виджета
        self.is_preview = is_preview        # True — если это превью в дашборде
        self.is_editing = False             # True — в режиме редактирования
        self.resize_margin = 10             # Ширина зоны для изменения размера
        self.resize_mode = None             # Текущий режим изменения размера (top, bottom, left и т.д.)
        self.start_geometry = None          # Геометрия на момент начала изменения
        self.drag_pos = None                # Позиция мыши при драге

        # Прозрачный фон
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setAutoFillBackground(False)
        self.setStyleSheet("background: transparent;")

        # Применяем флаги окна и прозрачность
        self.__apply_flags()
        self.__apply_opacity()

        # Устанавливаем размер и позицию из конфига
        self.resize(
            max(self.cfg.get("width", 320), 10),
            max(self.cfg.get("height", 180), 10)
        )
        self.move(self.cfg.get("x", 100), self.cfg.get("y", 100))

        # Иконка приложения
        if platform.system() == "Windows":
            icon_path = Path(__file__).parent.parent / "assets" / "icons" / "logo.ico"
        else:
            icon_path = Path(__file__).parent.parent / "assets" / "icons" / "logo.png"

        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

    def closeEvent(self, event):
        """Обработчик закрытия окна — просто принимаем событие."""
        event.accept()

    def __apply_opacity(self):
        """Применяет прозрачность из конфига (в режиме редактирования — всегда полностью непрозрачный)."""
        opacity = self.cfg.get("opacity", 1.0)
        if self.is_editing:
            self.setWindowOpacity(1.0)
        else:
            self.setWindowOpacity(max(0.01, min(1.0, opacity)))

    def showEvent(self, event):
        """
        Вызывается при первом показе виджета.
        Поднимает виджет наверх и активирует окно (важно для десктопных виджетов).
        """
        super().showEvent(event)

        widget_id = self.cfg.get('id', 'unknown')
        print(f"[WIDGET {widget_id}] showEvent: виджет реально появился на экране")

        if not self.is_editing and not self.is_preview:
            self.raise_()
            self.activateWindow()
            QTimer.singleShot(100, self.raise_)

    def __apply_flags(self):
        """
        Устанавливает флаги окна:
        - FramelessWindowHint — без рамки
        - WindowStaysOnTopHint — поверх всех (если нужно)
        - Tool — скрывает из таскбара
        - WindowTransparentForInput — клик насквозь (если включено)
        На Windows дополнительно делает виджет дочерним окном рабочего стола.
        """
        flags = Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool

        ignore_mouse = False

        if not self.is_preview and not self.is_editing:
            if self.cfg.get("click_through", True):
                flags |= Qt.WindowTransparentForInput
                ignore_mouse = True

            # На Windows скрываем из таскбара и Alt+Tab
            if platform.system() == "Windows":
                import win32gui
                import win32con

                QTimer.singleShot(0, self._set_desktop_parent)

        if self.windowFlags() != flags:
            self.setWindowFlags(flags)
            self.show()  # Пересоздаём окно для применения флагов

        self.setAttribute(Qt.WA_TransparentForMouseEvents, ignore_mouse)
        # self.setAttribute(Qt.WA_TranslucentBackground, True)
        # self.setAttribute(Qt.WA_NoSystemBackground, True)
        # self.setAutoFillBackground(False)

    def _recreate_window(self):
        """Пересоздаёт окно заново — фикс для глюков raise() на Windows"""
        geo = self.geometry()
        opacity = self.windowOpacity()
        was_visible = self.isVisible()
        
        cfg_copy = self.cfg.copy()
        is_editing = self.is_editing
        is_preview = self.is_preview
        
        # Закрываем старое
        self.close()
        self.deleteLater()
        
        # Создаём новое (через реестр, как в менеджере)
        from core.registry import get_module
        module = get_module(cfg_copy.get("type"))
        if module and hasattr(module, "WidgetClass"):
            new_widget = module.WidgetClass(cfg_copy, is_preview=is_preview)
            new_widget.is_editing = is_editing  # Восстанавливаем режим
            new_widget.setGeometry(geo)
            new_widget.setWindowOpacity(opacity)
            if was_visible:
                new_widget.show()
            
            # Заменяем в менеджере
            from core.widget_manager import WidgetManager
            wm = None
            try:
                from core.qt_bridge import get_qt_bridge
                bridge = get_qt_bridge()
                if bridge and bridge.wm:
                    wm = bridge.wm
            except:
                pass
            
            if wm and cfg_copy.get("id") in wm.widgets:
                wm.widgets[cfg_copy.get("id")] = new_widget
            
            print(f"[WIDGET {cfg_copy.get('id')}] Окно пересоздано для фикса stacking")

    def _set_desktop_parent(self):
        """Делает виджет дочерним окном рабочего стола (только Windows)"""
        if platform.system() != "Windows" or self.is_preview or self.is_editing:
            return

        try:
            import win32gui
            import win32con

            # Находим hwnd рабочего стола (Progman -> SHELLDLL_DefView -> WorkerW)
            progman = win32gui.FindWindow("Progman", None)
            win32gui.SendMessageTimeout(progman, 0x052C, 0, 0, win32con.SMTO_NORMAL, 1000)

            def_view = win32gui.FindWindowEx(progman, 0, "SHELLDLL_DefView", None)
            if def_view:
                worker_w = win32gui.FindWindowEx(def_view, 0, "WorkerW", None)
                if worker_w:
                    # Устанавливаем WorkerW как родителя
                    win32gui.SetParent(int(self.winId()), worker_w)
                    print(f"[WIDGET {self.cfg.get('id')}] Прикреплён к рабочему столу (WorkerW)")
        except Exception as e:
            print(f"[WIDGET] Ошибка привязки к десктопу: {e}")

    def set_edit_mode(self, enabled: bool):
        """
        Включает/выключает режим редактирования.
        При включении — виджет начинает ловить мышь для перемещения/ресайза.
        """
        self.is_editing = enabled

        # Ключевые строки: в режиме редактирования мышь должна ловиться виджетом
        if enabled:
            # Снимаем прозрачность для мыши
            self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
            # Пересоздаём окно без WindowTransparentForInput
            flags = Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
            self.setWindowFlags(flags)
            self.show()  # Важно: show() применяет новые флаги
        else:
            # Возвращаем обычные флаги (включая click_through, если был)
            self.__apply_flags()

        self.__apply_opacity()
        self.update()

        self.__apply_opacity()

        # Дополнительно поднимаем (особенно важно при входе в edit_mode)
        self.raise_()
        self.activateWindow()

    def update_config(self, new_cfg):
        if self.is_editing:
            # During editing, only update non-geometry config to avoid conflicts
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
        """Отрисовывает рамку редактирования (если включён режим) и вызывает draw_widget."""
        painter = QPainter(self)
        r = self.rect()

        # 1. Честная очистка
        painter.setCompositionMode(QPainter.CompositionMode_Source)
        painter.fillRect(r, Qt.transparent)
        
        # 2. Если правим - создаем невидимый слой для захвата мышью
        if self.is_editing:
            painter.fillRect(r, QColor(0, 0, 0, 1)) # Почти прозрачный (1/255)
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
            self._draw_edit_border(painter)
        else:
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
            
        self.draw_widget(painter)

    def _draw_edit_border(self, painter: QPainter):
        """Рисует синюю рамку и ручки изменения размера в режиме редактирования."""
        rect = self.rect()
        pen = QPen(QColor("#0099FF"))
        pen.setWidth(2)
        pen.setStyle(Qt.DashLine)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(rect.adjusted(1, 1, -1, -1))

        # Ручки в углах
        handle_size = 8
        painter.setBrush(QColor("#0099FF"))
        painter.setPen(Qt.NoPen)

        painter.drawRect(
            rect.width() - handle_size,
            rect.height() - handle_size,
            handle_size,
            handle_size,
        )
        painter.drawRect(rect.width() - handle_size, 0, handle_size, handle_size)
        painter.drawRect(0, rect.height() - handle_size, handle_size, handle_size)
        painter.drawRect(0, 0, handle_size, handle_size)

    def draw_widget(self, painter: QPainter):
        """
        Переопределяемый метод для отрисовки содержимого виджета.
        Реализуется в наследниках (ClockWidget, WeatherWidget и т.д.).
        """
        pass

    def _get_resize_mode(self, pos):
        """Определяет, в какой зоне находится курсор (для изменения размера)."""
        w, h = self.width(), self.height()
        m = self.resize_margin
        x, y = pos.x(), pos.y()

        mode = ""

        if y < m:
            mode += "top"
        elif y > h - m:
            mode += "bottom"

        if x < m:
            mode += "left"
        elif x > w - m:
            mode += "right"

        return mode

    def mousePressEvent(self, event):
        """Начало драга или изменения размера в режиме редактирования/превью."""
        if (self.is_editing or self.is_preview) and event.button() == Qt.LeftButton:
            self.resize_mode = self._get_resize_mode(event.pos())
            self.drag_pos = event.globalPos()
            self.start_geometry = self.geometry()

    def mouseMoveEvent(self, event):
        """Изменение курсора или драг/ресайз."""
        if (self.is_editing or self.is_preview) and not self.drag_pos:
            mode = self._get_resize_mode(event.pos())
            cursor = Qt.ArrowCursor
            if mode in ["left", "right"]:
                cursor = Qt.SizeHorCursor
            elif mode in ["top", "bottom"]:
                cursor = Qt.SizeVerCursor
            elif mode in ["topleft", "bottomright"]:
                cursor = Qt.SizeFDiagCursor
            elif mode in ["topright", "bottomleft"]:
                cursor = Qt.SizeBDiagCursor
            elif mode == "":
                cursor = Qt.SizeAllCursor
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

                if "right" in self.resize_mode:
                    w = max(min_w, w + dx)
                if "left" in self.resize_mode:
                    new_w = max(min_w, w - dx)
                    if new_w > min_w:
                        x += dx
                        w = new_w
                if "bottom" in self.resize_mode:
                    h = max(min_h, h + dy)
                if "top" in self.resize_mode:
                    new_h = max(min_h, h - dy)
                    if new_h > min_h:
                        y += dy
                        h = new_h

                self.setGeometry(x, y, w, h)

            self.update()

    def mouseReleaseEvent(self, event):
        """Завершение драга/ресайза."""
        if self.drag_pos is not None:
            self.drag_pos = None
            self.resize_mode = None
            if self.is_editing:
                self.setCursor(Qt.ArrowCursor)

    @staticmethod
    def render_to_pixmap(cfg: dict) -> QPixmap:
        """
        Статический метод для рендеринга виджета в off-screen pixmap.
        Используется для превью в дашборде.
        """
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
        temp_widget.draw_widget(painter)
        painter.end()
        temp_widget.deleteLater()
        return pixmap

    @staticmethod
    def _create_instance_for_render(cfg: dict, is_preview=False):
        """
        Создаёт временный экземпляр виджета для рендеринга превью.
        Поддерживает только clock на данный момент (расширяется по мере добавления виджетов).
        """
        from widgets.clock_widget import ClockWidget
        if cfg.get("type") == "clock":
            return ClockWidget(cfg, is_preview=is_preview)
        return BaseDesktopWidget(cfg, is_preview=is_preview)