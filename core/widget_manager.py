import json, os, uuid
from widgets.clock_widget import ClockWidget
from pathlib import Path

class WidgetManager:
    def __init__(self, config_path=None):
        # Если путь не указан, используем Documents/ChronoDash/widgets.json
        if config_path is None:
            documents_path = Path.home() / "Documents" / "ChronoDash"
            documents_path.mkdir(exist_ok=True, parents=True)
            config_path = documents_path / "widgets.json"
            print(f"📁 Конфиг будет сохранен в: {config_path}")
        
        self.config_path = str(config_path)
        self.widgets = {}  # id → QWidget instance
        self.config = []
        self._load_config()

    def _load_config(self):
        # Создаем папку если ее нет
        config_dir = os.path.dirname(self.config_path)
        if config_dir:
            os.makedirs(config_dir, exist_ok=True)
        
        if not os.path.exists(self.config_path):
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump([], f)
            self.config = []
            return
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        except:
            self.config = []

    def save_config(self):
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)

    def create_widget_from_template(self, template: dict):
        widget_id = template.get('id') or str(uuid.uuid4())
        template['id'] = widget_id
        self.config.append(template)
        self.save_config()
        

        self._create_widget_instance(template)
        return template

    def _create_widget_instance(self, cfg: dict):
        widget_type = cfg.get("type", "clock")
        if widget_type == "clock":
            widget = ClockWidget(cfg)
        else:
            print(f"Неизвестный тип виджета: {widget_type}")
            return None
        
        widget.show()
        
        self.widgets[cfg["id"]] = widget
        return widget


    def load_and_create_all_widgets(self):
        print(f"Загружается {len(self.config)} виджет(ов) из конфига...")
        for cfg in self.config:
            if cfg.get("id") in self.widgets:
                continue
            self._create_widget_instance(cfg)


    def delete_widget(self, widget_id):
        if widget_id in self.widgets:
            self.widgets[widget_id].close()
            del self.widgets[widget_id]
        self.config = [w for w in self.config if w.get('id') != widget_id]
        self.save_config()