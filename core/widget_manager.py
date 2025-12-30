import json
from pathlib import Path
import uuid
from PySide6.QtCore import QTimer, QObject, Signal
from core.edit_overlay import EditOverlay
from core.registry import get_module

class WidgetManager(QObject):
    # Сигнал: (widget_id, new_config)
    widget_config_updated = Signal(str, dict)

    def __init__(self, config_path: Path):
        super().__init__()
        self.config_path = config_path
        self.widgets = {}
        self.config = []
        self.overlay = None
        self.editing_widget_id = None
        self.app_settings = {
            "autostart": False,
            "force_x11": True,
            "gpu_acceleration": True,
            "use_builder": False, # Дефолт
            "dev_mode": False
        }
        self._load()

    def get_all_configs(self):
        return self.config

    def _load(self):
        if not self.config_path.exists():
            self.config = []
            return
        try:
            with open(self.config_path, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                self.config = data
            elif isinstance(data, dict):
                self.config = data.get("widgets", [])
                if "global" in data:
                    self.app_settings.update(data["global"])
        except:
            self.config = []

    def _save(self):
        try:
            export_data = {
                "global": self.app_settings,
                "widgets": self.config
            }
            # Создаем папку, если ее нет (на всякий случай)
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            print("[WidgetManager] Config saved successfully.")
        except Exception as e:
            print(f"[WidgetManager] Save error: {e}")

    def create_widget_from_template(self, template):
        new_cfg = template.copy()
        new_cfg["id"] = str(uuid.uuid4())
        self.config.append(new_cfg)
        self._save()
        self._create_widget_instance(new_cfg)
        
    def delete_widget(self, wid):
        if wid in self.widgets:
            self.widgets[wid].close()
            del self.widgets[wid]
        self.config = [c for c in self.config if c["id"] != wid]
        self._save()

    def _create_widget_instance(self, cfg):
        module = get_module(cfg.get("type"))
        if not module: return
        
        if hasattr(module, "WidgetClass"):
            w = module.WidgetClass(cfg)
        else:
            return 
            
        w.config_changed.connect(self.update_widget_config)
        self.widgets[cfg["id"]] = w
        w.show()
        
        # Windows attachment (если нужно)
        try:
            from core.window_attacher import attach_loop
            import threading
            if cfg.get("attach_to_window", {}).get("enabled", False):
                threading.Thread(target=attach_loop, args=(w, cfg), daemon=True).start()
        except: pass

    def load_and_create_all_widgets(self):
        print(f"[WidgetManager] Loading {len(self.config)} widgets...")
        for cfg in self.config:
            self._create_widget_instance(cfg)
            
    def stop_all_widgets(self):
        """
        Закрывает все виджеты с предварительным сохранением их состояния.
        """
        print("[WidgetManager] Saving state before exit...")
        
        # 1. СИНХРОНИЗАЦИЯ: Принудительно забираем актуальные координаты у живых окон
        for wid, w in self.widgets.items():
            if not w.isVisible(): continue
            
            # Получаем геометрию прямо из окна
            geo = w.geometry()
            
            # Находим соответствующий конфиг в списке и обновляем его
            for c in self.config:
                if c["id"] == wid:
                    c["x"] = geo.x()
                    c["y"] = geo.y()
                    c["width"] = geo.width()
                    c["height"] = geo.height()
                    break
        
        # 2. СОХРАНЕНИЕ: Пишем обновленный конфиг на диск
        self._save()

        # 3. ОЧИСТКА: Закрываем окна
        for w in self.widgets.values():
            w.close()
            w.deleteLater()
        self.widgets.clear()

    def update_widget_config(self, wid, new_data):
        # 1. Обновляем в памяти
        found = False
        for i, c in enumerate(self.config):
            if c["id"] == wid:
                self.config[i] = new_data
                found = True
                break
        if not found: return

        # 2. Обновляем инстанс (если пришло из настроек)
        if wid in self.widgets:
            self.widgets[wid].update_config(new_data)
        
        # 3. Сохраняем на диск
        self._save()
        self.widget_config_updated.emit(wid, new_data)

    # === EDIT MODE ===
    def enter_edit_mode(self, wid):
        if wid not in self.widgets: return
        if self.editing_widget_id and self.editing_widget_id != wid:
            self.exit_edit_mode()

        self.editing_widget_id = wid
        target_w = self.widgets[wid]
        
        if not self.overlay:
            self.overlay = EditOverlay(target_w)
            self.overlay.stop_edit_signal.connect(self.exit_edit_mode)
            self.overlay.show()
            self.overlay.grabKeyboard()
            
        target_w.set_edit_mode(True)

    def exit_edit_mode(self):
        if not self.editing_widget_id: return
        wid = self.editing_widget_id
        
        # При выходе из режима редактирования тоже сохраняем актуальные координаты
        if wid in self.widgets:
            w = self.widgets[wid]
            w.set_edit_mode(False)
            
            geo = w.geometry()
            for c in self.config:
                if c["id"] == wid:
                    c["x"] = geo.x()
                    c["y"] = geo.y()
                    c["width"] = geo.width()
                    c["height"] = geo.height()
                    self.update_widget_config(wid, c)
                    break

        if self.overlay:
            self.overlay.close()
            self.overlay = None
        self.editing_widget_id = None
    
    def get_global_setting(self, key, default=None):
        return self.app_settings.get(key, default)

    def set_global_setting(self, key, value):
        self.app_settings[key] = value
        self._save()