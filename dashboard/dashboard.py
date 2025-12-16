# dashboard.py
import customtkinter as ctk
import threading
import tkinter as tk
from tkinter import messagebox
import json
from PIL import Image, ImageTk
from PySide6.QtWidgets import QApplication
from core.widget_manager import WidgetManager
import os
from core.qt_bridge import get_qt_bridge

from widgets.base_widget import BaseDesktopWidget

# Отключаем лишний шум в консоли от Qt
os.environ["QT_LOGGING_RULES"] = "qt5ct.debug=false"
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="PySide6")


class WidgetPreview(ctk.CTkCanvas):
    def __init__(self, master):
        super().__init__(master, width=400, height=225, bg="#1e1e1e", highlightthickness=0)
        self.photo = None

    def update_preview(self, cfg: dict):
        if not cfg:
            self.delete("all")
            return

        app = QApplication.instance()
        if not app:
            return

        # Рендерим виджет в картинку через Qt
        pixmap = BaseDesktopWidget.render_to_pixmap(cfg)
        
        if pixmap.isNull():
            return

        # Конвертируем QPixmap -> PIL Image -> ImageTk
        qimage = pixmap.toImage()
        from PIL import Image
        pil_img = Image.fromqimage(qimage)
        # Масштабируем под размер превью
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

        # Получаем мост для общения с Qt
        self.qt_bridge = get_qt_bridge()

        self._build_ui()
        self.refresh_list()

    def _build_ui(self):
        # --- ЛЕВАЯ ПАНЕЛЬ (СПИСОК) ---
        left_frame = ctk.CTkFrame(self.root, width=300)
        left_frame.pack(side="left", fill="y", padx=10, pady=10)
        left_frame.pack_propagate(False)

        ctk.CTkLabel(left_frame, text="Мои виджеты", font=("Segoe UI", 16, "bold")).pack(pady=(10,5))
        
        add_btn = ctk.CTkButton(left_frame, text="+ Добавить часы", command=self.add_new_clock)
        add_btn.pack(pady=5, fill="x", padx=20)

        self.listbox = tk.Listbox(left_frame, bg="#2b2b2b", fg="white", selectbackground="#0078d7", bd=0, highlightthickness=0)
        self.listbox.pack(fill="both", expand=True, padx=20, pady=10)
        self.listbox.bind("<<ListboxSelect>>", self.on_select_widget)

        # --- ПРАВАЯ ПАНЕЛЬ (РЕДАКТОР) ---
        right_frame = ctk.CTkFrame(self.root)
        right_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        # 1. Область Превью
        preview_frame = ctk.CTkFrame(right_frame, height=250)
        preview_frame.pack(fill="x", pady=(0,10))
        preview_frame.pack_propagate(False)
        ctk.CTkLabel(preview_frame, text="Превью", font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=10, pady=5)
        self.preview = WidgetPreview(preview_frame)
        self.preview.pack(padx=10, pady=5)

        # 2. Вкладки настроек
        tabview = ctk.CTkTabview(right_frame)
        tabview.pack(fill="both", expand=True)

        tab_general = tabview.add("Основные")
        tab_position = tabview.add("Позиция и размер")
        tab_attach = tabview.add("Привязка к окну")
        tab_appearance = tabview.add("Внешний вид")

        # === Вкладка: Основные ===
        self.name_entry = ctk.CTkEntry(tab_general, placeholder_text="Название виджета")
        self.name_entry.pack(fill="x", padx=20, pady=5)
        self.name_entry.bind("<KeyRelease>", lambda e: self.update_cfg("name", self.name_entry.get()))

        # === Вкладка: Позиция и размер (ОБНОВЛЕНО) ===
        
        # Хедер с чекбоксом "Детальные настройки"
        pos_header = ctk.CTkFrame(tab_position, fg_color="transparent")
        pos_header.pack(fill="x", padx=20, pady=10)
        
        self.show_coords_var = ctk.BooleanVar(value=False)
        chk_details = ctk.CTkCheckBox(pos_header, text="Детальные настройки (координаты вручную)", 
                                      variable=self.show_coords_var, command=self.toggle_coords_inputs)
        chk_details.pack(side="left")

        # Кнопка визуального редактирования
        btn_visual = ctk.CTkButton(tab_position, text="📐 Изменить позицию/размер", 
                                   command=self.start_visual_edit, 
                                   fg_color="#e67e22", hover_color="#d35400",
                                   height=40, font=("Segoe UI", 13, "bold"))
        btn_visual.pack(fill="x", padx=20, pady=(0, 10))
        
        ctk.CTkLabel(tab_position, text="В режиме редактирования используйте мышь.\nНажмите ESC для сохранения и выхода.", 
                     text_color="gray", font=("Segoe UI", 11)).pack(pady=(0, 10))

        # Контейнер для полей ввода (чтобы скрывать/показывать их разом)
        self.coords_frame = ctk.CTkFrame(tab_position, fg_color="transparent")
        # Он не пакуется сразу, так как галочка выключена по умолчанию
        
        # Создаем поля ввода, но пока они скрыты внутри coords_frame
        for key, label in [
            ("x", "X"), ("y", "Y"), ("width", "Ширина"), ("height", "Высота")
        ]:
            frame = ctk.CTkFrame(self.coords_frame)
            frame.pack(fill="x", padx=20, pady=3)
            ctk.CTkLabel(frame, text=label, width=80).pack(side="left")
            entry = ctk.CTkEntry(frame, width=100)
            entry.pack(side="right")
            entry.bind("<KeyRelease>", lambda e, k=key, w=entry: self.update_cfg(k, int(w.get() or 0)))
            setattr(self, f"{key}_entry", entry) # Сохраняем ссылку self.x_entry и т.д.

        # Вызываем логику скрытия/показа при старте
        self.toggle_coords_inputs()

        # === Вкладка: Привязка к окну ===
        self.attach_var = ctk.BooleanVar()
        ctk.CTkCheckBox(tab_attach, text="Привязать к окну", variable=self.attach_var,
                        command=self.on_attach_toggle).pack(anchor="w", padx=20, pady=5)

        attach_inner = ctk.CTkFrame(tab_attach)
        attach_inner.pack(fill="x", padx=40, pady=5)

        ctk.CTkLabel(attach_inner, text="Название окна (часть):").pack(anchor="w")
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

        # === Вкладка: Внешний вид ===
        self.opacity_slider = ctk.CTkSlider(tab_appearance, from_=50, to=255, command=lambda v: self.update_cfg("opacity", int(v)))
        self.opacity_slider.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(tab_appearance, text="Прозрачность").pack()

        ctk.CTkLabel(tab_appearance, text="Формат времени:").pack(anchor="w", padx=20)
        self.time_format_entry = ctk.CTkEntry(tab_appearance)
        self.time_format_entry.pack(fill="x", padx=20, pady=2)
        self.time_format_entry.insert(0, "HH:mm:ss")
        self.time_format_entry.bind("<KeyRelease>", lambda e: self.update_cfg_path("content", "format", self.time_format_entry.get()))

        ctk.CTkLabel(tab_appearance, text="Цвет (HEX):").pack(anchor="w", padx=20)
        self.color_entry = ctk.CTkEntry(tab_appearance)
        self.color_entry.pack(fill="x", padx=20, pady=2)
        self.color_entry.insert(0, "#00FF88")
        self.color_entry.bind("<KeyRelease>", lambda e: self.update_cfg_path("content", "color", self.color_entry.get()))

        self.click_through_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(tab_appearance, text="Клик насквозь (не мешает работе)", variable=self.click_through_var,
                        command=lambda: self.update_cfg("click_through", self.click_through_var.get())).pack(anchor="w", padx=20, pady=5)

        self.always_top_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(tab_appearance, text="Поверх всех окон", variable=self.always_top_var,
                        command=lambda: self.update_cfg("always_on_top", self.always_top_var.get())).pack(anchor="w", padx=20, pady=5)

        # Кнопки управления (Низ)
        btn_frame = ctk.CTkFrame(right_frame)
        btn_frame.pack(fill="x", pady=10)
        ctk.CTkButton(btn_frame, text="Дублировать", command=self.duplicate_widget, fg_color="gray").pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Удалить", command=self.delete_current, fg_color="#d63031").pack(side="right", padx=10)

    # --- НОВЫЕ МЕТОДЫ ДЛЯ ВИЗУАЛЬНОГО РЕДАКТОРА ---

    def toggle_coords_inputs(self):
        """Скрывает или показывает поля ввода координат"""
        if self.show_coords_var.get():
            # Показываем фрейм с координатами
            self.coords_frame.pack(fill="x", after=self.coords_frame.master.winfo_children()[2])
        else:
            # Скрываем
            self.coords_frame.pack_forget()

    def start_visual_edit(self):
        """Запускает режим редактирования через Qt"""
        if not self.current_cfg:
            messagebox.showwarning("Внимание", "Сначала выберите виджет из списка!")
            return
        
        widget_id = self.current_cfg["id"]
        
        if self.qt_bridge:
            # Отправляем сигнал в поток Qt
            # Это вызовет wm.enter_edit_mode(widget_id)
            try:
                self.qt_bridge.start_edit_mode_signal.emit(widget_id)
            except AttributeError:
                 messagebox.showerror("Ошибка", "Сигнал start_edit_mode_signal не найден в QtBridge.\nОбновите qt_bridge.py!")
        else:
            messagebox.showerror("Ошибка", "Связь с графическим ядром (Qt) потеряна.")

    # -----------------------------------------------

    def add_new_clock(self):
        # Создаем шаблон новых часов
        new_clock = {
            "name": "Новые часы",
            "type": "clock",
            "x": 100, "y": 100,
            "width": 300, "height": 150,
            "opacity": 1.0,
            "click_through": True,
            "always_on_top": True,
            "content": {
                "format": "HH:mm:ss",
                "color": "#00FF88",
                "font_family": "Consolas",
                "font_size": 48
            }
        }
        self.wm.create_widget_from_template(new_clock)
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
        # Важно делать копию, чтобы не ломать конфиг в памяти напрямую до сохранения
        import copy
        self.current_cfg = copy.deepcopy(self.wm.config[idx])
        self.load_cfg_to_ui(self.current_cfg)

    def load_cfg_to_ui(self, cfg):
        self.current_cfg = cfg

        # === Основные ===
        self.name_entry.delete(0, tk.END)
        self.name_entry.insert(0, cfg.get("name", "Без имени"))

        # === Позиция и размер ===
        # Заполняем поля, даже если они скрыты
        for key in ["x", "y", "width", "height"]:
            entry = getattr(self, f"{key}_entry")
            entry.delete(0, tk.END)
            entry.insert(0, str(cfg.get(key, 0)))

        # === Прозрачность ===
        self.opacity_slider.set(int(cfg.get("opacity", 1.0) * 255))

        content = cfg.get("content", {})
        self.time_format_entry.delete(0, tk.END)
        self.time_format_entry.insert(0, content.get("format", "HH:mm:ss"))
        self.color_entry.delete(0, tk.END)
        self.color_entry.insert(0, content.get("color", "#00FF88"))

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

        # Если это прозрачность, нормализуем 0-255 -> 0.0-1.0
        if key == "opacity":
             value = value / 255.0

        self.current_cfg[key] = value
        self._push_update()

    def update_cfg_path(self, *path, value):
        if not self.current_cfg:
            return
        
        d = self.current_cfg
        for p in path[:-1]:
            if p not in d:
                d[p] = {}
            d = d[p]
        d[path[-1]] = value
        
        self._push_update()

    def _push_update(self):
        """Отправляет изменения в менеджер и Qt"""
        widget_id = self.current_cfg["id"]
        
        # 1. Сохраняем на диск (через менеджер, но хак с обновлением памяти)
        # Лучше обновить конфиг в менеджере полностью
        self.wm.update_widget_config(widget_id, self.current_cfg.copy())
        
        # 2. ОБНОВЛЯЕМ ЧЕРЕЗ МОСТ (сигнал Qt) для живого обновления
        if self.qt_bridge:
            config_copy = self.current_cfg.copy()
            self.qt_bridge.update_widget_signal.emit(config_copy)

        # 3. Обновляем превью
        self.preview.update_preview(self.current_cfg)

    def on_attach_toggle(self):
        enabled = self.attach_var.get()
        self.update_cfg_path("attach_to_window", "enabled", enabled)
        
        # Если включили — запускаем поток привязки
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
        # Очищаем форму (можно просто перезагрузить первый элемент или очистить)
        self.preview.delete("all")


def run_widgets_editor(widget_manager):
    def thread_target():
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        root = ctk.CTk()
        root.title("ChronoDash — Настройки")
        root.geometry("1100x700")
        root.minsize(1000, 600)

        # Передаем root, чтобы редактор встроился в это окно
        editor = WidgetsEditor(widget_manager, preexisting_root=root)
        
        root.mainloop()
        
    # Запускаем в отдельном потоке, чтобы не блокировать трей
    threading.Thread(target=thread_target, daemon=True).start()