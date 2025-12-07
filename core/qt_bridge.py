# core/qt_bridge.py
from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtWidgets import QApplication
import json

class QtBridge(QObject):
    """Мост между Tkinter и Qt для безопасного обновления виджетов"""
    
    update_widget_signal = Signal(dict)  # Сигнал для обновления виджета
    
    def __init__(self, widget_manager):
        super().__init__()
        self.wm = widget_manager
        self.update_widget_signal.connect(self._on_update_widget)
    
    @Slot(dict)
    def _on_update_widget(self, config_data):
        """Слот для безопасного обновления виджета в главном Qt потоке"""
        widget_id = config_data.get("id")
        print(f"🔧 Сигнал: обновление виджета {widget_id}")
        
        # Обновляем конфиг
        for i, cfg in enumerate(self.wm.config):
            if cfg.get("id") == widget_id:
                self.wm.config[i] = config_data
                break
        
        # Сохраняем на диск
        self.wm.save_config()
        
        # Обновляем виджет если он существует
        if widget_id in self.wm.widgets:
            widget = self.wm.widgets[widget_id]
            try:
                widget.update_config(config_data)
                print(f"✅ Виджет {widget_id} обновлен через сигнал")
            except Exception as e:
                print(f"❌ Ошибка при обновлении виджета: {e}")

# Глобальная переменная для моста
_qt_bridge = None

def get_qt_bridge(widget_manager=None):
    """Получить или создать мост Qt"""
    global _qt_bridge
    if _qt_bridge is None and widget_manager:
        _qt_bridge = QtBridge(widget_manager)
    return _qt_bridge