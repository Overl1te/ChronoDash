import json
from pathlib import Path
import uuid
from PySide6.QtCore import QTimer
from core.edit_overlay import EditOverlay
from core.registry import get_module

class WidgetManager:
    def __init__(self, config_path: Path):
        self.config_path = config_path
        self.widgets = {}
        self.config = []
        self.overlay = None
        self.editing_widget_id = None
        self._load()
        self.app_settings = {
            "autostart": False,
            "force_x11": True,
            "gpu_acceleration": True
        }

    def get_all_configs(self):
        return self.config

    def _load(self):
        if not self.config_path.exists():
            self.config = []
            return

        try:
            with open(self.config_path, encoding="utf-8") as f:
                # Читаем файл один раз в переменную data
                data = json.load(f)

            # Теперь разбираем, что прочитали (уже вне блока with, но данные в памяти)
            if isinstance(data, list):
                # Старый формат (просто список виджетов)
                self.config = data
            elif isinstance(data, dict):
                # Новый формат: { "global": {...}, "widgets": [...] }
                self.config = data.get("widgets", [])
                if "global" in data:
                    self.app_settings.update(data["global"])
            else:
                self.config = []

        except Exception as e:
            print(f"Config load error: {e}")
            self.config = []

    def _save(self):
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2)
            export_data = {
                "global": self.app_settings,
                "widgets": self.config
            }
            json.dump(export_data, f, indent=2)
        except Exception as e:
            print(f"Save error: {e}")

    def get_global_setting(self, key, default=None):
        return self.app_settings.get(key, default)

    def set_global_setting(self, key, value):
        self.app_settings[key] = value
        self._save()

    def load_and_create_all_widgets(self):
        for cfg in self.config:
            self._create_widget_instance(cfg)

    def _create_widget_instance(self, cfg):
        wid = cfg.get("id")
        if not wid: return
        
        # Если уже есть - пропускаем
        if wid in self.widgets: return
        
        w_type = cfg.get("type")
        module = get_module(w_type)
        if module and hasattr(module, "WidgetClass"):
            # Создаем
            w = module.WidgetClass(cfg, is_preview=False)
            w.show()
            self.widgets[wid] = w
        else:
            print(f"Unknown widget type: {w_type}")

    def create_widget_from_template(self, template):
        new_cfg = template.copy()
        new_cfg["id"] = str(uuid.uuid4())
        self.config.append(new_cfg)
        self._save()
        self._create_widget_instance(new_cfg)

    def delete_widget(self, wid):
        if wid in self.widgets:
            w = self.widgets.pop(wid)
            w.close()
            w.deleteLater()
        
        self.config = [c for c in self.config if c["id"] != wid]
        self._save()

    def update_widget_config(self, wid, new_cfg):
        # 1. Обновляем в списке конфигов
        for i, c in enumerate(self.config):
            if c["id"] == wid:
                self.config[i] = new_cfg.copy()
                break
        self._save()
        
        # 2. Обновляем живой виджет
        if wid in self.widgets:
            self.widgets[wid].update_config(new_cfg)

    def stop_all_widgets(self):
        self.exit_edit_mode()
        for w in self.widgets.values():
            w.close()
            w.deleteLater()
        self.widgets.clear()

    # === EDIT MODE ===
    def enter_edit_mode(self, wid):
        if wid not in self.widgets: return
        
        # Если уже редактируем другой - завершаем
        if self.editing_widget_id and self.editing_widget_id != wid:
            self.exit_edit_mode()

        self.editing_widget_id = wid
        target_w = self.widgets[wid]
        
        if not self.overlay:
            self.overlay = EditOverlay(target_w)
            self.overlay.stop_edit_signal.connect(self.exit_edit_mode)
            self.overlay.show()
            # Оверлей хватает клавиатуру для ESC
            self.overlay.grabKeyboard()
            
        target_w.set_edit_mode(True)

    def exit_edit_mode(self):
        if not self.editing_widget_id: return
        
        wid = self.editing_widget_id
        if wid in self.widgets:
            w = self.widgets[wid]
            w.set_edit_mode(False)
            
            # Сохраняем новые координаты после драга
            geo = w.geometry()
            for c in self.config:
                if c["id"] == wid:
                    c["x"] = geo.x()
                    c["y"] = geo.y()
                    break
            self._save()

        if self.overlay:
            self.overlay.releaseKeyboard()
            self.overlay.close()
            self.overlay = None
            
        self.editing_widget_id = None