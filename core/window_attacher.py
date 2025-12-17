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
Модуль для привязки виджета к окну другого приложения (только Windows).

Позволяет «приклеивать» виджет к краю указанного окна (например, к панели задач
или браузеру). Работает в отдельном потоке, постоянно отслеживая позицию целевого окна.
"""

import platform
import time
import threading

if platform.system() != "Windows":
    # На других ОС привязка не поддерживается — заглушка
    def attach_loop(widget, cfg):
        """Заглушка для не-Windows платформ."""
        return

else:
    import win32gui
    import win32con

    def _find_hwnd_by_title(title: str):
        """
        Ищет HWND окна по частичному совпадению заголовка.

        Возвращает первый найденный HWND или None.
        """
        hwnds = []

        def enum_callback(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                window_text = win32gui.GetWindowText(hwnd)
                if title.lower() in window_text.lower():
                    hwnds.append(hwnd)

        win32gui.EnumWindows(enum_callback, None)
        return hwnds[0] if hwnds else None

    def attach_loop(widget, cfg: dict):
        """
        Основной цикл привязки виджета к окну.

        Запускается в отдельном daemon-потоке. Работает, пока cfg["attach_to_window"]["enabled"] == True.
        """
        if not cfg.get("attach_to_window", {}).get("enabled", False):
            return

        window_title = cfg["attach_to_window"].get("window_title", "").strip()
        if not window_title:
            return

        anchor = cfg["attach_to_window"].get("anchor", "top-left")
        offset_x = cfg["attach_to_window"].get("offset_x", 0)
        offset_y = cfg["attach_to_window"].get("offset_y", 0)

        hwnd = None

        while cfg.get("attach_to_window", {}).get("enabled", False):
            if not hwnd:
                hwnd = _find_hwnd_by_title(window_title)

            if hwnd and win32gui.IsWindow(hwnd):
                try:
                    rect = win32gui.GetWindowRect(hwnd)
                    wx, wy, ww, wh = rect[0], rect[1], rect[2] - rect[0], rect[3] - rect[1]

                    # Поддержка только top-left пока (можно расширить)
                    if anchor == "top-left":
                        x = wx + offset_x
                        y = wy + offset_y
                    else:
                        # fallback
                        x = wx + offset_x
                        y = wy + offset_y

                    widget.move(int(x), int(y))
                except Exception:
                    hwnd = None  # окно исчезло — ищем заново
            else:
                hwnd = None

            time.sleep(0.1)  # 10 FPS — достаточно плавно и не грузит CPU