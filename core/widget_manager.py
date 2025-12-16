# core/widget_manager.py
import json
import uuid
from pathlib import Path
from widgets.clock_widget import ClockWidget
from PySide6.QtCore import Qt as QtCore

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
        for i, c in enumerate(self.config):
            if c.get("id") == widget_id:
                self.config[i] = cfg
                break
        self._save()

        if widget_id not in self.widgets:
            return

        widget = self.widgets[widget_id]
        old_cfg = widget.cfg  # старый конфиг у виджета

        # Проверяем, нужно ли пересоздать
        need_recreate = (
            cfg.get("click_through", True) != old_cfg.get("click_through", True) or
            cfg.get("always_on_top", True) != old_cfg.get("always_on_top", True)
        )

        # Применяем обновление
        widget.update_config(cfg)

        # Если сменились флаги окна — пересоздаём
        if need_recreate:
            from PySide6.QtCore import QTimer
            QTimer.singleShot(0, lambda: self.recreate_widget(widget_id))

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
            widget = ClockWidget(cfg)
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