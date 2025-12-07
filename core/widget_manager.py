import json, os, uuid, threading, time

class WidgetManager:
    def __init__(self, config_path):
        self.config_path = config_path
        self.widgets = {}  # id -> instance
        self._load_config()

    def _load_config(self):
        if not os.path.exists(self.config_path):
            self.config = []
            return
        with open(self.config_path, 'r', encoding='utf-8') as f:
            try:
                self.config = json.load(f)
            except Exception:
                self.config = []

    def save_config(self):
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)

    def create_widget_from_template(self, template: dict):
        widget_id = template.get('id') or str(uuid.uuid4())
        template['id'] = widget_id
        self.config.append(template)
        self.save_config()
        return template

    def list_templates(self):
        return self.config

    def get_widget(self, widget_id):
        for w in self.config:
            if w.get('id') == widget_id:
                return w
        return None

    def update_widget(self, widget_id, newdata):
        for i,w in enumerate(self.config):
            if w.get('id') == widget_id:
                self.config[i] = newdata
                self.save_config()
                return True
        return False

    def delete_widget(self, widget_id):
        self.config = [w for w in self.config if w.get('id') != widget_id]
        self.save_config()
        return True
