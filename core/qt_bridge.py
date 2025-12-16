# core/qt_bridge.py
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication

class QtBridge(QObject):
    # Сигнал, который будет вызываться из потока Tkinter/CustomTkinter
    update_widget_signal = Signal(dict)

    def __init__(self, wm):
        super().__init__()
        # При подключении сигнала, мы будем передавать wm 
        # (или использовать wm из замыкания, если подключение происходит в _init_qt_app)
        self.wm = wm # Оставим, чтобы его можно было получить в get_qt_bridge
        self.update_widget_signal.connect(self._handle)

    def _handle(self, cfg):
        # Менеджер виджетов доступен через self.wm
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

# НОВАЯ ФУНКЦИЯ
def clear_qt_bridge():
    global _qt_bridge
    if _qt_bridge:
        _qt_bridge.disconnect()
    _qt_bridge = None