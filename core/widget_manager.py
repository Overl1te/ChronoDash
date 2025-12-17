# ChronoDash - Desktop Widgets
# Copyright (C) 2025 Overl1te
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import json
import uuid
from pathlib import Path
from PySide6.QtCore import Qt as QtCore
from PySide6.QtCore import QTimer
from core.edit_overlay import EditOverlay
from core.registry import get_module


class WidgetManager:
    def __init__(self, config_path):
        self.config_path = Path(config_path)
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.widgets = {}
        self.config = []
        self.overlay = None
        self.editing_widget_id = None
        self._load()

    def get_all_configs(self) -> list:
        """
        Возвращает копию всего списка конфигураций виджетов.
        Используется Dashboard для отображения списка.
        """
        # self.config - это список, который хранит конфиги всех виджетов
        return self.config.copy()

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
        if self.editing_widget_id == widget_id:
            return

        # Просто обновляем конфиг
        for i, c in enumerate(self.config):
            if c.get("id") == widget_id:
                self.config[i] = cfg.copy()
                break
        self._save()

        if widget_id in self.widgets:
            print(f"[MANAGER] Обновляем виджет {widget_id} без пересоздания")
            self.widgets[widget_id].update_config(cfg.copy())

    def _raise_editing_widget(self, widget, widget_id):
        if widget.isVisible():
            print(f"[EDIT] Поднимаем виджет {widget_id} наверх: raise_() + activateWindow()")
            widget.raise_()
            widget.activateWindow()
        else:
            print(f"[EDIT] ПРЕДУПРЕЖДЕНИЕ: Виджет {widget_id} не visible при попытке поднять!")

    # --- ЛОГИКА РЕДАКТОРА ---
    def enter_edit_mode(self, widget_id):
        if widget_id not in self.widgets:
            return
        self.editing_widget_id = widget_id
        widget = self.widgets[widget_id]

        if not self.overlay:
            self.overlay = EditOverlay(widget)  # Передаём ссылку на виджет
            self.overlay.stop_edit_signal.connect(self.exit_edit_mode)
        
        self.overlay.show()
        
        # Включаем режим редактирования
        widget.set_edit_mode(True)

        # Оверлей захватывает клавиатуру для ESC
        self.overlay.grabKeyboard()
        
        QTimer.singleShot(50, lambda w=widget: (w.raise_(), w.activateWindow()))
        QTimer.singleShot(150, lambda w=widget: (w.raise_(), w.activateWindow()))
        QTimer.singleShot(300, lambda w=widget: w.raise_())

    def _final_raise(self, widget):
        widget.raise_()
        widget.activateWindow()

    def exit_edit_mode(self):
        if not self.editing_widget_id:
            print("[EDIT] Выход из edit mode: уже не в режиме")
            if self.overlay:
                print("[EDIT] Закрываем висящий оверлей")
                self.overlay.close()
                self.overlay = None
            return

        widget_id = self.editing_widget_id
        print(f"[EDIT] === ВЫХОД ИЗ РЕЖИМА РЕДАКТИРОВАНИЯ === Виджет ID: {widget_id}")

        if widget_id in self.widgets:
            widget = self.widgets[widget_id]
            widget.set_edit_mode(False)

            QTimer.singleShot(50, lambda w=widget: (w.raise_(), w.activateWindow()))

            # Сохраняем позицию и размер
            new_geo = widget.geometry()
            for c in self.config:
                if c["id"] == widget_id:
                    c["x"] = new_geo.x()
                    c["y"] = new_geo.y()
                    c["width"] = new_geo.width()
                    c["height"] = new_geo.height()
                    break
            self._save()
            print(f"[EDIT] Геометрия сохранена: {new_geo}")

        # Закрываем оверлей
        if self.overlay:
            print("[EDIT] Закрываем EditOverlay")
            try:
                self.overlay.releaseKeyboard()
            except:
                pass
            self.overlay.close()
            self.overlay = None

        self.editing_widget_id = None
        print("[EDIT] Режим редактирования завершён")

    def stop_all_widgets(self):
        print("Закрытие всех виджетов...")
        if self.overlay:
            self.overlay.close()  # Закрываем оверлей если есть
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
        if cfg:
            self._create_widget_instance(cfg.copy())
            # Поднимаем новый виджет сразу
            QTimer.singleShot(50, lambda: self._raise_widget_if_exists(widget_id))

    def _raise_widget_if_exists(self, widget_id):
        if widget_id in self.widgets:
            w = self.widgets[widget_id]
            if w.isVisible():
                w.raise_()
                w.activateWindow()

    def _create_widget_instance(self, cfg: dict):
        widget_id = cfg["id"]
        if widget_id in self.widgets:
            return

        w_type = cfg.get("type")
        module = get_module(w_type) # Берем модуль через универсальный реестр

        if module:
            # Пытаемся получить класс виджета, который мы экспортировали как WidgetClass
            widget_class = getattr(module, "WidgetClass", None)
            
            if widget_class:
                widget = widget_class(cfg, is_preview=False)
                widget.show()
                self.widgets[widget_id] = widget
            else:
                print(f"Ошибка: В модуле {w_type} не найден класс 'WidgetClass'")
        else:
            print(f"Неизвестный тип виджета: {w_type}")

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
            widget = self.widgets.pop(widget_id)  # Сначала убираем из dict
            widget.close()
            widget.deleteLater()
        self.config = [c for c in self.config if c.get("id") != widget_id]
        self._save()