# widget_manager.py
import json, os, uuid
from widgets.clock_widget import ClockWidget
from pathlib import Path


class WidgetManager:
    def __init__(self, config_path=None):
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
        config_dir = os.path.dirname(self.config_path)
        if config_dir:
            os.makedirs(config_dir, exist_ok=True)

        if not os.path.exists(self.config_path):
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump([], f)
            self.config = []
            return
        
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                self.config = json.load(f)
        except:
            self.config = []
        print(f"📂 Загружено {len(self.config)} виджетов из конфига")

    def update_widget_config(self, widget_id: str, new_config: dict):
        """Обновляет конфиг виджета и сразу применяет изменения"""
        if not widget_id:
            return False
            
        print(f"🔄 Обновление виджета {widget_id}")
        
        # Обновляем конфиг в памяти
        for i, cfg in enumerate(self.config):
            if cfg.get("id") == widget_id:
                self.config[i] = new_config
                break
        
        # Сохраняем на диск
        self.save_config()
        
        # Обновляем существующий виджет если он есть
        if widget_id in self.widgets:
            widget = self.widgets[widget_id]
            try:
                # Важно: вызываем update_config напрямую
                widget.update_config(new_config)
                print(f"✅ Виджет {widget_id} обновлен напрямую")
            except Exception as e:
                print(f"❌ Ошибка при обновлении виджета: {e}")
        
        return True

    def recreate_widget(self, widget_id: str):
        """Удаляет и заново создает виджет"""
        print(f"🔄 Пересоздание виджета {widget_id}")
        
        # Перечитываем свежий конфиг с диска
        self._load_config()
        
        # Ищем обновленный конфиг
        cfg = next((c for c in self.config if c.get("id") == widget_id), None)
        if not cfg:
            print(f"❌ Виджет {widget_id} не найден после перезагрузки конфига")
            return
        
        print(f"📋 Новый конфиг для {widget_id}: {cfg.get('content', {}).get('color', 'default')}")
        
        # Удаляем старый виджет если он существует
        if widget_id in self.widgets:
            old_widget = self.widgets.pop(widget_id)
            try:
                old_widget.close()
                old_widget.deleteLater()
                print(f"🗑️ Старый виджет {widget_id} удален")
            except:
                pass
        
        # Создаем новый виджет с обновленным конфигом
        new_widget = self._create_widget_instance(cfg.copy())
        if new_widget:
            print(f"✅ Виджет {widget_id} пересоздан")
        else:
            print(f"❌ Не удалось пересоздать виджет {widget_id}")

    def save_config(self):
        """Сохраняет конфиг на диск"""
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            print(f"💾 Конфиг сохранен ({len(self.config)} виджетов)")
        except Exception as e:
            print(f"❌ Ошибка сохранения конфига: {e}")

    def create_widget_from_template(self, template: dict):
        widget_id = template.get("id") or str(uuid.uuid4())
        template["id"] = widget_id
        self.config.append(template)
        self.save_config()

        self._create_widget_instance(template)
        return template

    # В методе _create_widget_instance добавь проверку:
    def _create_widget_instance(self, cfg: dict):
        # Проверяем, не существует ли уже такой виджет
        widget_id = cfg.get("id")
        if widget_id and widget_id in self.widgets:
            print(f"⚠️ Виджет {widget_id} уже существует, обновляем")
            widget = self.widgets[widget_id]
            widget.update_config(cfg.copy())
            return widget
        
        widget_type = cfg.get("type", "clock")
        if widget_type == "clock":
            widget = ClockWidget(cfg)
        else:
            print(f"❌ Неизвестный тип виджета: {widget_type}")
            return None

        widget.show()
        self.widgets[cfg["id"]] = widget
        print(f"➕ Создан виджет {cfg['id']} ({cfg.get('name', 'без имени')})")
        return widget

    def load_and_create_all_widgets(self):
        print(f"🔄 Загружается {len(self.config)} виджет(ов) из конфига...")
        for cfg in self.config:
            if cfg.get("id") in self.widgets:
                continue
            self._create_widget_instance(cfg)

    def delete_widget(self, widget_id):
        if widget_id in self.widgets:
            self.widgets[widget_id].close()
            del self.widgets[widget_id]
            print(f"🗑️ Виджет {widget_id} закрыт")
        
        self.config = [w for w in self.config if w.get("id") != widget_id]
        self.save_config()
        print(f"🗑️ Виджет {widget_id} удален из конфига")