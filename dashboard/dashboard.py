import customtkinter as ctk
import threading
import tkinter as tk
from tkinter import messagebox
import json


def run_dashboard_window(widget_manager):
    t = threading.Thread(target=_open, args=(widget_manager,), daemon=True)
    t.start()


def _open(widget_manager):
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    app = ctk.CTk()
    app.title("Dashboard — ChronoDash")
    app.geometry("600x420")

    def add_clock():
        template = {
            "id": None,
            "name": "Большие часы",
            "type": "clock",
            "x": 100,
            "y": 100,
            "width": 320,
            "height": 180,
            "opacity": 255,
            "click_through": True,
            "always_on_top": True,
            "attach_to_window": {"enabled": False},
            "content": {
                "format": "HH:mm:ss",
                "font_family": "Consolas",
                "font_size": 48,
                "color": "#00FF88",
            },
        }
        w = widget_manager.create_widget_from_template(template)
        messagebox.showinfo(
            "Добавлено",
            f"Виджет {w['name']} добавлен и сохранён в конфиге (id: {w['id']}).\nЗапустите приложение под Windows чтобы отобразить виджет.",
        )

    btn = ctk.CTkButton(app, text="Добавить шаблон часов", command=add_clock)
    btn.pack(pady=20)

    def list_widgets():
        lst = widget_manager.list_templates()
        top = ctk.CTkToplevel(app)
        top.title("Мои виджеты")
        text = tk.Text(top, width=80, height=20)
        text.insert("1.0", json.dumps(lst, indent=2, ensure_ascii=False))
        text.pack()

    ctk.CTkButton(app, text="Мои виджеты", command=list_widgets).pack(pady=10)
    app.mainloop()
