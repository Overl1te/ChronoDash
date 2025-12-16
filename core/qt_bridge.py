from PySide6.QtCore import QObject, Signal


class QtBridge(QObject):
    update_widget_signal = Signal(dict)
    start_edit_mode_signal = Signal(str)
    delete_widget_signal = Signal(str)
    create_widget_signal = Signal(dict)

    def __init__(self, wm):
        super().__init__()
        self.wm = wm

        # Подключения (слоты)
        self.update_widget_signal.connect(self._handle_update)
        self.start_edit_mode_signal.connect(self.wm.enter_edit_mode)
        self.delete_widget_signal.connect(self._handle_delete)
        self.create_widget_signal.connect(self._handle_create)

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
