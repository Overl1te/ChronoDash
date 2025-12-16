# core/qt_bridge.py
from PySide6.QtCore import QObject, Signal

class QtBridge(QObject):
    update_widget_signal = Signal(dict)

    def __init__(self, wm):
        super().__init__()
        self.wm = wm
        self.update_widget_signal.connect(self._handle)

    def _handle(self, cfg):
        widget_id = cfg.get("id")
        if not widget_id:
            return
        self.wm.update_widget_config(widget_id, cfg.copy())

_qt_bridge = None
def get_qt_bridge(wm=None):
    global _qt_bridge
    if _qt_bridge is None and wm:
        _qt_bridge = QtBridge(wm)
    return _qt_bridge