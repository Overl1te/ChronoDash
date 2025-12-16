# core/qt_bridge.py
from PySide6.QtCore import QObject, Signal

class QtBridge(QObject):
    # Сигнал для обновления конфига виджета: (cfg_dict)
    update_widget_signal = Signal(dict)
    
    # НОВЫЙ СИГНАЛ: для запуска редактора: (widget_id)
    start_edit_mode_signal = Signal(str) 

    def __init__(self, wm):
        super().__init__()
        self.wm = wm
        
        # Подключения (слоты)
        self.update_widget_signal.connect(self._handle_update)
        self.start_edit_mode_signal.connect(self.wm.enter_edit_mode)

    def _handle_update(self, cfg):
        widget_id = cfg.get("id")
        if not widget_id:
            return
        # Убедимся, что апдейт не прилетает, если мы редактируем (WM должен его игнорировать)
        self.wm.update_widget_config(widget_id, cfg.copy())
        
    def disconnect(self):
        """Явно отсоединяем все наши сигналы от слотов."""
        # Отсоединяем update_widget_signal от _handle_update
        try:
            self.update_widget_signal.disconnect(self._handle_update)
        except RuntimeError:
            pass # Игнорируем, если уже отсоединен
            
        # Отсоединяем start_edit_mode_signal от wm.enter_edit_mode
        try:
            self.start_edit_mode_signal.disconnect(self.wm.enter_edit_mode)
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
        _qt_bridge.disconnect() # Теперь вызываем наш кастомный метод
    _qt_bridge = None