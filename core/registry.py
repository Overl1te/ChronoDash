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

import widgets.clock_widget as clock_module
import widgets.weather_widget as weather_module 

# Словарь модулей
MODULES = {
    "clock": clock_module,
    "weather": weather_module 
}

def get_module(type_id: str):
    """Возвращает модуль виджета по его типу"""
    return MODULES.get(type_id)

def get_default_config(type_id: str):
    """Возвращает дефолтный конфиг виджета"""
    module = get_module(type_id)
    if module and hasattr(module, "get_default_config"):
        return module.get_default_config()
    
    # Базовый фолбэк для неизвестного типа
    return {"type": type_id, "x": 100, "y": 100, "width": 200, "height": 100}