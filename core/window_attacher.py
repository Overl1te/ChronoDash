import platform
if platform.system() != 'Windows':
    def attach_loop(widget, cfg):
        return
else:
    import win32gui, win32con, win32api, ctypes, time
    def find_hwnd_by_title(title):
        hwnds = []
        def enum(hwnd, param):
            txt = win32gui.GetWindowText(hwnd)
            if title.lower() in txt.lower():
                hwnds.append(hwnd)
        win32gui.EnumWindows(enum, None)
        return hwnds[0] if hwnds else None

    def attach_loop(widget, cfg):
        hwnd = None
        anchor = cfg.get('anchor', 'top-left')
        offset_x = cfg.get('offset_x', 0)
        offset_y = cfg.get('offset_y', 0)
        while cfg.get('enabled'):
            if not hwnd:
                hwnd = find_hwnd_by_title(cfg.get('window_title','') or '')
            if hwnd:
                try:
                    rect = win32gui.GetWindowRect(hwnd)
                    wx, wy, ww, wh = rect[0], rect[1], rect[2]-rect[0], rect[3]-rect[1]
                    x = wx + offset_x
                    y = wy + offset_y
                    # widget expected to be a Qt QWidget or similar
                    try:
                        widget.move(int(x), int(y))
                    except Exception:
                        pass
                except Exception:
                    pass
            time.sleep(0.1)
