import sys
import os
from core.tray import TrayApp
from core.widget_manager import WidgetManager

def main():
    wm = WidgetManager(os.path.join(os.path.dirname(__file__), "config", "widgets.json"))
    tray = TrayApp(widget_manager=wm)
    tray.run()  # blocks

if __name__ == '__main__':
    main()
