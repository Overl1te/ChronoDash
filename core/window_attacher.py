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

import platform

if platform.system() != "Windows":

    def attach_loop(widget, cfg):
        return

else:
    import win32gui, time

    def find_hwnd_by_title(title):
        hwnds = []

        def enum(hwnd):
            txt = win32gui.GetWindowText(hwnd)
            if title.lower() in txt.lower():
                hwnds.append(hwnd)

        win32gui.EnumWindows(enum, None)
        return hwnds[0] if hwnds else None

    def attach_loop(widget, cfg):
        hwnd = None
        anchor = cfg.get("anchor", "top-left")
        offset_x = cfg.get("offset_x", 0)
        offset_y = cfg.get("offset_y", 0)
        while cfg.get("enabled"):
            if not hwnd:
                hwnd = find_hwnd_by_title(cfg.get("window_title", "") or "")
            if hwnd:
                try:
                    rect = win32gui.GetWindowRect(hwnd)
                    wx, wy = rect[0], rect[1], rect[2] - rect[0], rect[3] - rect[1]
                    x = wx + offset_x
                    y = wy + offset_y
                    try:
                        widget.move(int(x), int(y))
                    except Exception:
                        pass
                except Exception:
                    pass
            time.sleep(0.1)
