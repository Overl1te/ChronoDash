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

"""
Реестр доступных типов виджетов.

Содержит словарь всех зарегистрированных модулей виджетов.
WidgetManager использует этот реестр для динамического получения модуля по типу виджета.
Каждый модуль должен экспортировать:
  - WidgetClass — класс виджета
  - get_default_config() — функцию с дефолтной конфигурацией (опционально)
  - render_settings_ui() — функцию для отрисовки специфичных настроек (опционально)
"""

import widgets.clock_widget as clock_module
import widgets.weather_widget as weather_module

# Словарь: строковый тип виджета → модуль (импортированный объект)
MODULES = {
    "clock": clock_module,
    "weather": weather_module,
    # Добавляйте новые виджеты сюда: "new_type": new_widget_module,
}

def get_module(type_id: str):
    """
    Возвращает модуль виджета по его типу.

    Используется WidgetManager'ом для получения WidgetClass и других атрибутов.
    """
    return MODULES.get(type_id)

def get_default_config(type_id: str) -> dict:
    """
    Возвращает дефолтную конфигурацию для нового виджета указанного типа.

    Если в модуле есть функция get_default_config — вызывает её.
    Иначе возвращает базовый шаблон.
    """
    module = get_module(type_id)
    if module and hasattr(module, "get_default_config"):
        return module.get_default_config()

    # Базовый fallback на случай неизвестного типа
    return {
        "type": type_id,
        "name": f"Виджет {type_id}",
        "x": 100,
        "y": 100,
        "width": 300,
        "height": 200,
        "opacity": 1.0,
        "click_through": True,
        "attach_to_window": {"enabled": False}
    }

def get_available_types() -> list[str]:
    """
    Возвращает список всех зарегистрированных типов виджетов.
    
    Полезно для дашборда при заполнении комбобокса добавления виджета.
    """
    return list(MODULES.keys())