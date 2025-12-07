# dashboard.py (или widgets_editor.py)
import customtkinter as ctk
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import json
from PIL import Image, ImageQt, ImageTk
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QPixmap
from core.widget_manager import WidgetManager
import os

from widgets.base_widget import BaseDesktopWidget
os.environ["QT_LOGGING_RULES"] = "qt5ct.debug=false"  # или просто
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="PySide6")

# Глобальное приложение Qt нужно только для превью
_qt_app = None

def get_qt_app():
    global _qt_app
    if _qt_app is None:
        _qt_app = QApplication.instance() or QApplication([])
    return _qt_app

# ←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←
# Замени весь класс WidgetPreview в dashboard.py на этот:
# ←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←

class WidgetPreview(ctk.CTkCanvas):
    def __init__(self, master):
        super().__init__(master, width=400, height=225, bg="#1e1e1e", highlightthickness=0)
        self.photo = None

    def update_preview(self, cfg: dict):
        if not cfg:
            self.delete("all")
            return

        # ←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←
        # Самое важное — используем статический метод!
        pixmap = BaseDesktopWidget.render_to_pixmap(cfg)
        # ←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←

        # Конвертируем в PhotoImage
        qimage = pixmap.toImage()
        pil_img = Image.fromqimage(qimage)
        pil_img = pil_img.resize((400, 225), Image.LANCZOS)

        self.photo = ImageTk.PhotoImage(pil_img)
        self.delete("all")
        self.create_image(200, 112, image=self.photo, anchor="center")

class WidgetsEditor:
    def __init__(self, widget_manager: WidgetManager, preexisting_root=None):
        self.wm = widget_manager
        
        if preexisting_root:
            self.root = preexisting_root
        else:
            self.root = ctk.CTkToplevel()
            self.root.title("Мои виджеты — ChronoDash")
            self.root.geometry("1100x700")

        self.current_cfg = None
        self.preview = None

        self._build_ui()
        self.refresh_list()

    def _build_ui(self):
        # Левый фрейм — список виджетов
        left_frame = ctk.CTkFrame(self.root, width=300)
        left_frame.pack(side="left", fill="y", padx=10, pady=10)
        left_frame.pack_propagate(False)

        ctk.CTkLabel(left_frame, text="Мои виджеты", font=("Segoe UI", 16, "bold")).pack(pady=(10,5))
        
        add_btn = ctk.CTkButton(left_frame, text="+ Добавить часы", command=self.add_new_clock)
        add_btn.pack(pady=5, fill="x", padx=20)

        self.listbox = tk.Listbox(left_frame, bg="#2b2b2b", fg="white", selectbackground="#0078d7")
        self.listbox.pack(fill="both", expand=True, padx=20, pady=10)
        self.listbox.bind("<<ListboxSelect>>", self.on_select_widget)

        # Правый фрейм — редактор
        right_frame = ctk.CTkFrame(self.root)
        right_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        # Превью
        preview_frame = ctk.CTkFrame(right_frame, height=250)
        preview_frame.pack(fill="x", pady=(0,10))
        preview_frame.pack_propagate(False)
        ctk.CTkLabel(preview_frame, text="Превью", font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=10, pady=5)
        self.preview = WidgetPreview(preview_frame)
        self.preview.pack(padx=10, pady=5)

        # Вкладки настроек
        tabview = ctk.CTkTabview(right_frame)
        tabview.pack(fill="both", expand=True)

        tab_general = tabview.add("Основные")
        tab_position = tabview.add("Позиция и размер")
        tab_attach = tabview.add("Привязка к окну")
        tab_appearance = tabview.add("Внешний вид")

        # === Основные ===
        self.name_entry = ctk.CTkEntry(tab_general, placeholder_text="Название виджета")
        self.name_entry.pack(fill="x", padx=20, pady=5)
        self.name_entry.bind("<KeyRelease>", lambda e: self.update_cfg("name", self.name_entry.get()))

        # === Позиция и размер ===
        for key, label in [
            ("x", "X"), ("y", "Y"), ("width", "Ширина"), ("height", "Высота")
        ]:
            frame = ctk.CTkFrame(tab_position)
            frame.pack(fill="x", padx=20, pady=3)
            ctk.CTkLabel(frame, text=label, width=80).pack(side="left")
            entry = ctk.CTkEntry(frame, width=100)
            entry.pack(side="right")
            entry.bind("<KeyRelease>", lambda e, k=key, w=entry: self.update_cfg(k, int(w.get() or 0)))
            setattr(self, f"{key}_entry", entry)

        # === Привязка к окну ===
        self.attach_var = ctk.BooleanVar()
        ctk.CTkCheckBox(tab_attach, text="Привязать к окну", variable=self.attach_var,
                        command=self.on_attach_toggle).pack(anchor="w", padx=20, pady=5)

        attach_inner = ctk.CTkFrame(tab_attach)
        attach_inner.pack(fill="x", padx=40, pady=5)

        ctk.CTkLabel(attach_inner, text="Название окна:").pack(anchor="w")
        self.window_title_entry = ctk.CTkEntry(attach_inner)
        self.window_title_entry.pack(fill="x", pady=2)
        self.window_title_entry.bind("<KeyRelease>", lambda e: self.update_cfg_path("attach_to_window", "window_title", self.window_title_entry.get()))

        ctk.CTkLabel(attach_inner, text="Смещение X:").pack(anchor="w")
        self.offset_x_entry = ctk.CTkEntry(attach_inner)
        self.offset_x_entry.pack(fill="x", pady=2)
        self.offset_x_entry.bind("<KeyRelease>", lambda e: self.update_cfg_path("attach_to_window", "offset_x", int(self.offset_x_entry.get() or 0)))

        ctk.CTkLabel(attach_inner, text="Смещение Y:").pack(anchor="w")
        self.offset_y_entry = ctk.CTkEntry(attach_inner)
        self.offset_y_entry.pack(fill="x", pady=2)
        self.offset_y_entry.bind("<KeyRelease>", lambda e: self.update_cfg_path("attach_to_window", "offset_y", int(self.offset_y_entry.get() or 0)))

        # === Внешний вид ===
        self.opacity_slider = ctk.CTkSlider(tab_appearance, from_=50, to=255, command=lambda v: self.update_cfg("opacity", int(v)))
        self.opacity_slider.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(tab_appearance, text="Прозрачность").pack()

        self.click_through_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(tab_appearance, text="Клик насквозь", variable=self.click_through_var,
                        command=lambda: self.update_cfg("click_through", self.click_through_var.get())).pack(anchor="w", padx=20, pady=5)

        self.always_top_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(tab_appearance, text="Поверх всех окон", variable=self.always_top_var,
                        command=lambda: self.update_cfg("always_on_top", self.always_top_var.get())).pack(anchor="w", padx=20, pady=5)

        # Кнопки управления
        btn_frame = ctk.CTkFrame(right_frame)
        btn_frame.pack(fill="x", pady=10)
        ctk.CTkButton(btn_frame, text="Дублировать", command=self.duplicate_widget, fg_color="gray").pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Удалить", command=self.delete_current, fg_color="#d63031").pack(side="right", padx=10)

    def add_new_clock(self):
        from dashboard import add_clock  # импорт здесь, чтобы избежать цикла
        add_clock()  # используем уже готовую функцию из старого dashboard
        self.refresh_list()

    def refresh_list(self):
        self.listbox.delete(0, tk.END)
        for cfg in self.wm.config:
            name = cfg.get("name", "Без имени")
            wtype = cfg.get("type", "unknown")
            self.listbox.insert(tk.END, f"{name} [{wtype}]")

    def on_select_widget(self, event=None):
        sel = self.listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        self.current_cfg = self.wm.config[idx]
        self.load_cfg_to_ui(self.current_cfg)

    def load_cfg_to_ui(self, cfg):
        self.current_cfg = cfg

        # === Основные ===
        self.name_entry.delete(0, tk.END)
        self.name_entry.insert(0, cfg.get("name", "Без имени"))

        # === Позиция и размер ===
        for key in ["x", "y", "width", "height"]:
            entry = getattr(self, f"{key}_entry")
            entry.delete(0, tk.END)
            entry.insert(0, str(cfg.get(key, 0)))

        # === Прозрачность ===
        self.opacity_slider.set(cfg.get("opacity", 255))

        # === Флаги ===
        self.click_through_var.set(cfg.get("click_through", True))
        self.always_top_var.set(cfg.get("always_on_top", True))

        # === Привязка к окну ===
        attach = cfg.get("attach_to_window", {})
        self.attach_var.set(attach.get("enabled", False))
        self.window_title_entry.delete(0, tk.END)
        self.window_title_entry.insert(0, attach.get("window_title", ""))
        self.offset_x_entry.delete(0, tk.END)
        self.offset_x_entry.insert(0, str(attach.get("offset_x", 0)))
        self.offset_y_entry.delete(0, tk.END)
        self.offset_y_entry.insert(0, str(attach.get("offset_y", 0)))

        self.preview.update_preview(self.current_cfg)


    def update_cfg(self, key, value):
        if not self.current_cfg:
            return

        self.current_cfg[key] = value
        widget_id = self.current_cfg["id"]

        if widget_id in self.wm.widgets:
            widget = self.wm.widgets[widget_id]
            # Просто передаём обновлённый конфиг — виджет сам разберётся
            widget.update_config(self.current_cfg)

        self.wm.save_config()
        self.preview.update_preview(self.current_cfg)

    def update_cfg_path(self, *path, value):
        if not self.current_cfg:
            return
        d = self.current_cfg
        for p in path[:-1]:
            if p not in d:
                d[p] = {}
            d = d[p]
        d[path[-1]] = value
        self.update_cfg("attach_to_window", self.current_cfg.get("attach_to_window", {}))

    def on_attach_toggle(self):
        enabled = self.attach_var.get()
        self.update_cfg_path("attach_to_window", "enabled", enabled)
        # Если включили — сразу запускаем attach_loop (нужен доступ к виджету)
        if enabled and self.current_cfg:
            widget_id = self.current_cfg["id"]
            if widget_id in self.wm.widgets:
                from core.window_attacher import attach_loop
                import threading
                threading.Thread(target=attach_loop, args=(self.wm.widgets[widget_id], self.current_cfg), daemon=True).start()

    def duplicate_widget(self):
        if not self.current_cfg:
            return
        new_cfg = json.loads(json.dumps(self.current_cfg))  # глубокая копия
        new_cfg["id"] = None
        new_cfg["name"] += " (копия)"
        self.wm.create_widget_from_template(new_cfg)
        self.refresh_list()

    def delete_current(self):
        if not self.current_cfg or not messagebox.askyesno("Удалить?", "Удалить виджет навсегда?"):
            return
        self.wm.delete_widget(self.current_cfg["id"])
        self.refresh_list()
        self.current_cfg = None

def run_widgets_editor(widget_manager):
    def thread_target():
        # Создаём полностью независимый root в этом потоке
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # ВАЖНО: создаём НОВЫЙ Tk(), а не CTkToplevel
        root = ctk.CTk()  # ← это и есть Tk() под капотом
        root.title("Мои виджеты — ChronoDash")
        root.geometry("1100x700")
        root.minsize(1000, 600)
        root.protocol("WM_DELETE_WINDOW", root.quit)  # чтобы корректно закрывалось

        # Передаём управление нашему классу, но с уже готовым root
        editor = WidgetsEditor(widget_manager, preexisting_root=root)
        
        # Запускаем свой собственный mainloop
        root.mainloop()
        
        # После закрытия окна — чистим за собой
        try:
            root.destroy()
        except:
            pass

    # Запускаем в отдельном потоке — теперь всё легально
    threading.Thread(target=thread_target, daemon=True).start()