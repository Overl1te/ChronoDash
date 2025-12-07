# DesktopWidgetsPro (prototype)

This repository contains a Windows-targeted prototype implementing the DesktopWidgetsPro specification.

Key notes:
- The tray icon and dashboard (CustomTkinter) are implemented and functional cross-platform.
- OS-level window flags (WS_EX_TRANSPARENT, WS_EX_LAYERED) rely on pywin32 and thus only fully work on Windows.
- The project provides a minimal Clock widget implementation using PySide6.
- The Dashboard writes widget templates into `config/widgets.json`. Actual spawning of layered click-through Qt windows should be run on a Windows machine.

Quickstart (Windows):
1. Create a virtual env and install requirements: `pip install -r requirements.txt`
2. Run `python main.py`
3. Use tray -> Конструктор to add a clock template to config. Then you can extend `WidgetManager` to spawn Qt windows at startup.

Deliverables:
- A minimal working skeleton that follows the project structure from the provided TЗ.
