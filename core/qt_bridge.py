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

from queue import Queue
from PySide6.QtCore import QObject, Signal, QBuffer, QIODevice


class QtBridge(QObject):
    update_widget_signal = Signal(dict)
    start_edit_mode_signal = Signal(str)
    delete_widget_signal = Signal(str)
    create_widget_signal = Signal(dict)
    recreate_widget_signal = Signal(str)
    preview_signal = Signal(dict)

    def __init__(self, wm):
        super().__init__()
        self.wm = wm

        # Подключения (слоты)
        self.update_widget_signal.connect(self._handle_update)
        self.start_edit_mode_signal.connect(self.wm.enter_edit_mode)
        self.delete_widget_signal.connect(self._handle_delete)
        self.create_widget_signal.connect(self._handle_create)
        self.recreate_widget_signal.connect(self.wm.recreate_widget)
        self.preview_result_queue = Queue()
        self.preview_signal.connect(self._handle_preview_request)

    def _handle_preview_request(self, cfg):
        from widgets.base_widget import BaseDesktopWidget
        pixmap = BaseDesktopWidget.render_to_pixmap(cfg)
        if pixmap.isNull():
            self.preview_result_queue.put(None)
            return
        image = pixmap.toImage()
        buffer = QBuffer()
        buffer.open(QIODevice.WriteOnly)
        image.save(buffer, "PNG")
        data = bytes(buffer.data())
        self.preview_result_queue.put(data)

    def get_preview_bytes(self, cfg):
        self.preview_signal.emit(cfg)
        return self.preview_result_queue.get()

    def _handle_update(self, cfg):
        widget_id = cfg.get("id")
        if not widget_id:
            return
        self.wm.update_widget_config(widget_id, cfg.copy())

    def _handle_delete(self, widget_id: str):
        self.wm.delete_widget(widget_id)

    def _handle_create(self, cfg: dict):
        self.wm.create_widget_from_template(cfg.copy())  # Вызываем в Qt-потоке

    def disconnect(self):
        try:
            self.update_widget_signal.disconnect(self._handle_update)
        except RuntimeError:
            pass
        try:
            self.start_edit_mode_signal.disconnect(self.wm.enter_edit_mode)
        except RuntimeError:
            pass
        try:
            self.delete_widget_signal.disconnect(self._handle_delete)
        except RuntimeError:
            pass
        try:
            self.create_widget_signal.disconnect(self._handle_create)
        except RuntimeError:
            pass


_qt_bridge = None


def get_qt_bridge(wm=None):
    global _qt_bridge
    if _qt_bridge is None and wm:
        _qt_bridge = QtBridge(wm)
    return _qt_bridge


def clear_qt_bridge():
    global _qt_bridge
    if _qt_bridge:
        _qt_bridge.disconnect()
    _qt_bridge = None