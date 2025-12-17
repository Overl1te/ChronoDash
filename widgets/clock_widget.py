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
Виджет цифровых часов.

Отображает текущее время в заданном формате.
Поддерживает настройку шрифта, размера, цвета и формата времени.
Обновляется автоматически каждую секунду (или чаще, если нужны миллисекунды).
"""

from widgets.base_widget import BaseDesktopWidget
from PySide6.QtGui import QPainter, QFont, QColor
from PySide6.QtCore import QDateTime, QTimer, Qt


class ClockWidget(BaseDesktopWidget):
    """
    Виджет, отображающий цифровые часы на рабочем столе.
    Наследуется от BaseDesktopWidget и реализует отрисовку времени.
    """
    def __init__(self, cfg=None, is_preview=False):
        super().__init__(cfg, is_preview=is_preview)

        # Применяем настройки контента из конфига
        self._apply_content_settings()

        # Запускаем таймер обновления только для реального виджета (не для превью)
        if not self.is_preview:
            self._start_clock()

    def _start_clock(self):
        """
        Запускает рекурсивный таймер для обновления времени.

        Интервал зависит от формата: 100 мс если есть миллисекунды, иначе 1000 мс.
        """
        self.update()  # Немедленное обновление

        interval = 100 if ".z" in self.format else 1000
        QTimer.singleShot(interval, self._start_clock)

    def _apply_content_settings(self):
        """Извлекает и применяет настройки контента из конфига."""
        content = self.cfg.get("content", {})

        self.format = content.get("format", "HH:mm:ss")
        self.font_family = content.get("font_family", "Consolas")
        self.font_size = int(content.get("font_size", 48))

        col_str = content.get("color", "#00FF88")
        self.color = QColor(col_str)
        if not self.color.isValid():
            self.color = QColor("#00FF88")

    def update_config(self, new_cfg):
        """
        Переопределяет обновление конфига — перечитывает настройки контента и обновляет отрисовку.
        """
        super().update_config(new_cfg)
        self._apply_content_settings()
        self.update()

    def draw_widget(self, painter: QPainter):
        """
        Отрисовывает текущее время по центру виджета.

        Использует заданный шрифт, размер и цвет.
        """
        try:
            current_time = QDateTime.currentDateTime().toString(self.format)

            font = QFont(self.font_family, self.font_size)
            font.setStyleStrategy(QFont.PreferAntialias)

            painter.setFont(font)
            painter.setPen(self.color)

            painter.drawText(self.rect(), Qt.AlignCenter, current_time)
        except Exception as e:
            print(f"Ошибка отрисовки часов: {e}")


# ==============================================================================
# Дефолтная конфигурация виджета
# ==============================================================================
def get_default_config():
    """
    Возвращает дефолтную конфигурацию для нового экземпляра часов.

    Используется при создании виджета через дашборд.
    """
    return {
        "type": "clock",
        "name": "Часы",
        "width": 350,
        "height": 150,
        "opacity": 1.0,
        "click_through": True,
        "always_on_top": True,
        "content": {
            "format": "HH:mm:ss",
            "color": "#00FF88",
            "font_family": "Segoe UI",
            "font_size": 64
        },
        "attach_to_window": {"enabled": False}
    }


# ==============================================================================
# UI настроек в дашборде (CustomTkinter)
# ==============================================================================
def render_settings_ui(parent, cfg, on_update):
    """
    Отрисовывает специфичные настройки часов во фрейме дашборда.

    Args:
        parent: Родительский фрейм (CTkFrame из дашборда)
        cfg: Текущий конфиг виджета
        on_update: Callback для обновления вложенных параметров (path, value)
    """
    import customtkinter as ctk
    import tkinter as tk

    content = cfg.get("content", {})

    # Формат времени
    ctk.CTkLabel(parent, text="Формат времени (Python strftime):", text_color="gray").pack(anchor="w", pady=(10, 0))
    fmt_entry = ctk.CTkEntry(parent, placeholder_text="Например: HH:mm:ss")
    fmt_entry.pack(fill="x", pady=5)
    fmt_entry.insert(0, content.get("format", "HH:mm:ss"))
    fmt_entry.bind("<KeyRelease>", lambda event: on_update("content.format", fmt_entry.get()))

    # Цвет текста
    ctk.CTkLabel(parent, text="Цвет текста (HEX):", text_color="gray").pack(anchor="w", pady=(10, 0))
    col_entry = ctk.CTkEntry(parent, placeholder_text="#RRGGBB")
    col_entry.pack(fill="x", pady=5)
    col_entry.insert(0, content.get("color", "#00FF88"))
    col_entry.bind("<KeyRelease>", lambda event: on_update("content.color", col_entry.get()))

    # Размер шрифта
    ctk.CTkLabel(parent, text="Размер шрифта:", text_color="gray").pack(anchor="w", pady=(10, 0))
    size_frame = ctk.CTkFrame(parent, fg_color="transparent")
    size_frame.pack(fill="x", pady=5)

    size_lbl = ctk.CTkLabel(size_frame, text=str(content.get("font_size", 48)), width=30)
    size_lbl.pack(side="right")

    slider = ctk.CTkSlider(size_frame, from_=10, to=200, number_of_steps=190)
    slider.pack(side="left", fill="x", expand=True, padx=(0, 10))
    slider.set(content.get("font_size", 48))

    def _on_size_drag(val):
        val_int = int(val)
        size_lbl.configure(text=str(val_int))
        on_update("content.font_size", val_int)

    slider.configure(command=_on_size_drag)

    # Семейство шрифта
    ctk.CTkLabel(parent, text="Шрифт (Family):", text_color="gray").pack(anchor="w", pady=(10, 0))
    font_entry = ctk.CTkEntry(parent)
    font_entry.pack(fill="x", pady=5)
    font_entry.insert(0, content.get("font_family", "Segoe UI"))
    font_entry.bind("<KeyRelease>", lambda event: on_update("content.font_family", font_entry.get()))

    # Глобальные флаги (поверх всех, клик насквозь)
    always_top_var = tk.BooleanVar(value=cfg.get("always_on_top", False))
    ctk.CTkCheckBox(parent, text="Поверх всех окон", variable=always_top_var,
                    command=lambda: on_update("always_on_top", always_top_var.get())).pack(anchor="w", padx=20, pady=5)

    click_through_var = tk.BooleanVar(value=cfg.get("click_through", False))
    ctk.CTkCheckBox(parent, text="Клик насквозь", variable=click_through_var,
                    command=lambda: on_update("click_through", click_through_var.get())).pack(anchor="w", padx=20, pady=5)


# ==============================================================================
# Экспорт класса для реестра
# ==============================================================================
WidgetClass = ClockWidget