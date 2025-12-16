# core/widget_manager.py
import json
import uuid
from pathlib import Path
from widgets.clock_widget import ClockWidget
from PySide6.QtCore import Qt as QtCore
from PySide6.QtCore import QTimer
from core.edit_overlay import EditOverlay

class WidgetManager:
    def __init__(self, config_path):
        self.config_path = Path(config_path)
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.widgets = {}
        self.config = []
        self.overlay = None # Ссылка на оверлей
        self.editing_widget_id = None
        self._load()

    # ... (методы _load, _save, update_widget_config без изменений) ...
    def _load(self):
        if not self.config_path.exists():
            self.config = []
            self._save()
            return
        try:
            with open(self.config_path, encoding="utf-8") as f:
                self.config = json.load(f)
        except:
            self.config = []

    def _save(self):
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print("Ошибка сохранения конфига:", e)

    def update_widget_config(self, widget_id: str, cfg: dict):
        # Если мы в режиме редактора для этого виджета, игнорируем обновление позиции извне,
        # чтобы не было конфликта с drag-n-drop
        if self.editing_widget_id == widget_id:
            return 
            
        current_cfg = None
        i = -1
        for idx, c in enumerate(self.config):
            if c.get("id") == widget_id:
                current_cfg = c
                i = idx
                break
        
        if current_cfg is None: return

        critical_settings = ["opacity", "click_through", "type"] # убрал width/height из критичных для мягкости
        recreate_needed = False
        for setting in critical_settings:
            if current_cfg.get(setting) != cfg.get(setting):
                recreate_needed = True
                break

        self.config[i] = cfg
        self._save()

        if widget_id in self.widgets:
            if recreate_needed:
                QTimer.singleShot(0, lambda: self.recreate_widget(widget_id))
            else:
                self.widgets[widget_id].update_config(cfg)

    # --- ЛОГИКА РЕДАКТОРА ---
    def enter_edit_mode(self, widget_id):
        if widget_id not in self.widgets:
            return
        
        print(f"Вход в режим редактора: {widget_id}")
        
        if self.editing_widget_id and self.editing_widget_id != widget_id:
            self.exit_edit_mode()

        self.editing_widget_id = widget_id
        
        # 1. Сначала создаем и показываем оверлей
        if self.overlay:
            self.overlay.close()
            
        from core.edit_overlay import EditOverlay # Импорт тут, чтобы избежать циклической зависимости
        self.overlay = EditOverlay()
        self.overlay.stop_edit_signal.connect(self.exit_edit_mode)
        
        # 2. Теперь переводим виджет в режим редактора
        widget = self.widgets[widget_id]
        widget.set_edit_mode(True)
        
        # 3. Виджет должен быть над оверлеем
        # Поскольку у обоих WindowStaysOnTopHint, последний show() или raise_() выигрывает.
        # Мы подняли оверлей в его __init__ (raise_), чтобы он был над всем.
        # Теперь поднимаем виджет над оверлеем.
        widget.raise_()
        widget.activateWindow() # Дадим ему фокус, чтобы он мог ловить мышь
        
        # 4. Передадим фокус обратно оверлею для ESC (но это может быть нестабильно)
        # self.overlay.activateWindow() 
        # Вместо этого мы используем grabKeyboard() в EditOverlay

    def exit_edit_mode(self):
        if not self.editing_widget_id:
            # Если оверлей закрылся по клику, но мы уже не в режиме, просто чистим оверлей
            if self.overlay:
                self.overlay.close()
                self.overlay = None
            return
            
        print("Выход из режима редактора...")
        widget_id = self.editing_widget_id
        
        if widget_id in self.widgets:
            widget = self.widgets[widget_id]
            widget.set_edit_mode(False) # Выходим из режима, возвращаем старые флаги
            
            # Сохраняем новые координаты
            new_geo = widget.geometry()
            
            for c in self.config:
                if c["id"] == widget_id:
                    c["x"] = new_geo.x()
                    c["y"] = new_geo.y()
                    c["width"] = new_geo.width()
                    c["height"] = new_geo.height()
                    break
            
            self._save()
            print("Координаты сохранены.")

        # Закрываем оверлей только ПОСЛЕ сохранения и возврата виджета
        if self.overlay:
            try:
                self.overlay.releaseKeyboard() # Освобождаем клавиатуру
            except:
                pass # Может быть ошибка, если он уже закрыт
                
            self.overlay.close()
            self.overlay = None
            
        self.editing_widget_id = None

    def stop_all_widgets(self):
        print("Закрытие всех виджетов...")
        if self.overlay: self.overlay.close() # Закрываем оверлей если есть
        for widget in list(self.widgets.values()):
            widget.close()
            widget.deleteLater()
        self.widgets = {}
        from core.qt_bridge import clear_qt_bridge
        clear_qt_bridge()

    def recreate_widget(self, widget_id: str):
        if widget_id in self.widgets:
            old = self.widgets.pop(widget_id)
            old.close()
            old.deleteLater()
        cfg = next((c for c in self.config if c.get("id") == widget_id), None)
        if cfg: self._create_widget_instance(cfg.copy())

    def _create_widget_instance(self, cfg: dict):
        widget_id = cfg["id"]
        if widget_id in self.widgets: return
        if cfg.get("type") == "clock":
            widget = ClockWidget(cfg, is_preview=False)
        else: return
        widget.show()
        self.widgets[widget_id] = widget

    def load_and_create_all_widgets(self):
        for cfg in self.config:
            if cfg.get("id") not in self.widgets:
                self._create_widget_instance(cfg.copy())

    def create_widget_from_template(self, template: dict):
        template["id"] = str(uuid.uuid4())
        self.config.append(template)
        self._save()
        self._create_widget_instance(template.copy())
        return template

    def delete_widget(self, widget_id):
        if widget_id in self.widgets:
            self.widgets[widget_id].close()
            del self.widgets[widget_id]
        self.config = [c for c in self.config if c.get("id") != widget_id]
        self._save()