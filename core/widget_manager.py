# core/widget_manager.py
import json
import uuid
from pathlib import Path
from widgets.clock_widget import ClockWidget
from PySide6.QtCore import Qt as QtCore
from PySide6.QtCore import QTimer

class WidgetManager:
    def __init__(self, config_path):
        self.config_path = Path(config_path)
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.widgets = {}
        self.config = []
        self._load()

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
        # print(f"Загружено {len(self.config)} виджетов")

    def _save(self):
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print("Ошибка сохранения конфига:", e)

    def update_widget_config(self, widget_id: str, cfg: dict):
        current_cfg = None
        i = -1
        for idx, c in enumerate(self.config):
            if c.get("id") == widget_id:
                current_cfg = c
                i = idx
                break
        
        if current_cfg is None:
            return

        # 1. Определяем, нужно ли пересоздать виджет
        # (для критических изменений, требующих нового окна)
        critical_settings = ["opacity", "click_through", "width", "height", "type"]

        recreate_needed = False
        
        for setting in critical_settings:
            # Проверяем, изменилась ли критическая настройка
            if current_cfg.get(setting) != cfg.get(setting):
                recreate_needed = True
                break

        # 2. Обновляем конфиг в памяти и сохраняем
        self.config[i] = cfg
        self._save()

        # 3. Применяем изменения к живому виджету ИЛИ пересоздаем
        if widget_id in self.widgets:
            if recreate_needed:
                # Пересоздание: старый виджет закрывается, новый создается с новыми флагами
                QTimer.singleShot(0, lambda: self.recreate_widget(widget_id))
            else:
                # Обновление: некритические изменения (цвет, формат, позиция)
                self.widgets[widget_id].update_config(cfg)

    def stop_all_widgets(self):
        print("Закрытие всех виджетов...")
        # Закрываем все виджеты
        for widget in list(self.widgets.values()):
            widget.close()
            widget.deleteLater()
        self.widgets = {}
        
        # Очищаем QtBridge
        from core.qt_bridge import clear_qt_bridge
        clear_qt_bridge()

    def recreate_widget(self, widget_id: str):
        if widget_id in self.widgets:
            old = self.widgets.pop(widget_id)
            old.close()
            old.deleteLater()

        cfg = next((c for c in self.config if c.get("id") == widget_id), None)
        if cfg:
            self._create_widget_instance(cfg.copy())

    def _create_widget_instance(self, cfg: dict):
        widget_id = cfg["id"]
        if widget_id in self.widgets:
            return

        if cfg.get("type") == "clock":
            widget = ClockWidget(cfg, is_preview=False)
        else:
            return

        widget.show()
        self.widgets[widget_id] = widget
        # print(f"Создан виджет: {cfg.get('name', widget_id)}")

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