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

from pathlib import Path
import customtkinter as ctk
import threading
import tkinter as tk
from tkinter import messagebox
import json
from core.registry import MODULES, get_default_config, get_module
from core.widget_manager import WidgetManager
import os
from core.qt_bridge import get_qt_bridge
from core.registry import get_module

# Отключаем лишний шум в консоли от Qt
os.environ["QT_LOGGING_RULES"] = "qt5ct.debug=false"
import warnings

warnings.filterwarnings("ignore", category=UserWarning, module="PySide6")


class WidgetPreview(ctk.CTkCanvas):
    def __init__(self, master, qt_bridge):
        super().__init__(
            master, width=400, height=225, bg="#1e1e1e", highlightthickness=0
        )
        self.qt_bridge = qt_bridge          # Сохраняем мост
        self.photo = None

    def update_preview(self, cfg: dict):
        if not cfg:
            self.delete("all")
            return

        # Запрашиваем превью через Qt-мост (рендеринг происходит в главном Qt-потоке)
        data = self.qt_bridge.get_preview_bytes(cfg)
        if not data:
            self.delete("all")
            return

        # Конвертируем байты в изображение
        from PIL import Image, ImageTk
        import io

        try:
            pil_img = Image.open(io.BytesIO(data))
            pil_img = pil_img.resize((400, 225), Image.LANCZOS)

            self.photo = ImageTk.PhotoImage(pil_img)
            self.delete("all")
            self.create_image(200, 112, image=self.photo, anchor="center")
        except Exception as e:
            print(f"Ошибка при обновлении превью: {e}")
            self.delete("all")

class WidgetsEditor(ctk.CTkFrame):
    def __init__(self, widget_manager: WidgetManager, preexisting_root=None):
        super().__init__(master=preexisting_root)
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
        # ----------------------------------------------------------------------
        # Главный фрейм: Левая колонка (Настройки/Превью) и Правая (Список виджетов)
        # ----------------------------------------------------------------------
        self.grid_columnconfigure(0, weight=1)  # Левая колонка (Настройки/Превью) - большая
        self.grid_columnconfigure(1, weight=0)  # Правая колонка (Список) - фиксированная ширина
        self.grid_rowconfigure(0, weight=1)

        left_frame = ctk.CTkFrame(self)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
        right_frame = ctk.CTkFrame(self, width=280)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)

        # ----------------------------------------------------------------------
        # Правая колонка: Список виджетов
        # ----------------------------------------------------------------------
        right_frame.grid_columnconfigure(0, weight=1)
        right_frame.grid_rowconfigure(0, weight=0) # Фрейм добавления
        right_frame.grid_rowconfigure(1, weight=1) # Список
        right_frame.grid_rowconfigure(2, weight=0) # Кнопки

        # Фрейм добавления виджета (ComboBox + Кнопка)
        add_frame = ctk.CTkFrame(right_frame, fg_color="transparent")
        add_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        add_frame.columnconfigure(0, weight=1)

        # Выпадающий список типов: Динамически берем ключи из реестра
        self.type_combo = ctk.CTkComboBox(
            add_frame, 
            values=list(MODULES.keys()), # <-- Получаем clock, weather и т.д.
            width=180
        )
        self.type_combo.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        self.type_combo.set("clock") 
        
        # Кнопка "+"
        add_btn = ctk.CTkButton(
            add_frame, text="+", width=30, command=self.add_new_widget
        )
        add_btn.grid(row=0, column=1, sticky="e")

        # Список виджетов (ListBox)
        self.widget_list = tk.Listbox(
            right_frame,
            selectmode=tk.SINGLE,
            exportselection=False,
            height=8,
            bg="#2a2d2e",
            fg="white",
            selectbackground="#1f6aa5",
            selectforeground="white",
            borderwidth=0,
            highlightthickness=0,
        )
        self.widget_list.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        self.widget_list.bind("<<ListboxSelect>>", self.on_select_widget)

        # Кнопки управления списком
        btn_frame = ctk.CTkFrame(right_frame, fg_color="transparent")
        btn_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=(5, 10))
        btn_frame.columnconfigure(0, weight=1)
        btn_frame.columnconfigure(1, weight=1)

        ctk.CTkButton(btn_frame, text="Удалить", command=self.delete_selected_widget).grid(
            row=0, column=0, sticky="ew", padx=(0, 5)
        )
        ctk.CTkButton(btn_frame, text="Редактировать (Qt)", command=self.start_edit_mode).grid(
            row=0, column=1, sticky="ew", padx=(5, 0)
        )


        # ----------------------------------------------------------------------
        # Левая колонка: Превью и Настройки
        # ----------------------------------------------------------------------
        left_frame.columnconfigure(0, weight=1)
        left_frame.rowconfigure(1, weight=1)

        # === Превью ===
        self.preview_canvas = WidgetPreview(left_frame, self.qt_bridge)
        self.preview_canvas.pack(fill="x", padx=10, pady=10)

        # === Вкладки настроек ===
        self.tabview = ctk.CTkTabview(left_frame)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        tab_general = self.tabview.add("Общее")
        tab_appearance = self.tabview.add("Внешний вид")
        tab_content = self.tabview.add("Контент")
        tab_attacher = self.tabview.add("Привязка")
        
        # ----------------------------------------------------------------------
        # === Вкладка: Общее (Name, X, Y, W, H) ===
        # ----------------------------------------------------------------------
        general_container = ctk.CTkScrollableFrame(tab_general, fg_color="transparent")
        general_container.pack(fill="both", expand=True, padx=10, pady=5)

        # --- Имя ---
        ctk.CTkLabel(general_container, text="Имя виджета:").pack(anchor="w", padx=10, pady=(10, 0))
        self.name_entry = ctk.CTkEntry(general_container)
        self.name_entry.pack(fill="x", padx=10, pady=5)
        self.name_entry.bind("<KeyRelease>", lambda e: self._update_cfg_with_path("name", self.name_entry.get()))
        
        # --- Позиция ---
        ctk.CTkLabel(general_container, text="Позиция X:").pack(anchor="w", padx=10, pady=(10, 0))
        self.pos_x_entry = ctk.CTkEntry(general_container)
        self.pos_x_entry.pack(fill="x", padx=10, pady=5)
        self.pos_x_entry.bind("<KeyRelease>", lambda e: self._update_cfg_with_path("x", int(self.pos_x_entry.get())))

        ctk.CTkLabel(general_container, text="Позиция Y:").pack(anchor="w", padx=10, pady=(10, 0))
        self.pos_y_entry = ctk.CTkEntry(general_container)
        self.pos_y_entry.pack(fill="x", padx=10, pady=5)
        self.pos_y_entry.bind("<KeyRelease>", lambda e: self._update_cfg_with_path("y", int(self.pos_y_entry.get())))
        
        # --- Размер ---
        ctk.CTkLabel(general_container, text="Ширина:").pack(anchor="w", padx=10, pady=(10, 0))
        self.size_w_entry = ctk.CTkEntry(general_container)
        self.size_w_entry.pack(fill="x", padx=10, pady=5)
        self.size_w_entry.bind("<KeyRelease>", lambda e: self._update_cfg_with_path("width", int(self.size_w_entry.get())))

        ctk.CTkLabel(general_container, text="Высота:").pack(anchor="w", padx=10, pady=(10, 0))
        self.size_h_entry = ctk.CTkEntry(general_container)
        self.size_h_entry.pack(fill="x", padx=10, pady=5)
        self.size_h_entry.bind("<KeyRelease>", lambda e: self._update_cfg_with_path("height", int(self.size_h_entry.get())))


        # ----------------------------------------------------------------------
        # === Вкладка: Внешний вид (Opacity, Flags) ===
        # ----------------------------------------------------------------------

        # --- Прозрачность ---
        ctk.CTkLabel(tab_appearance, text="Прозрачность:").pack(anchor="w", padx=20, pady=(10, 0))
        self.opacity_slider = ctk.CTkSlider(
            tab_appearance,
            from_=50,
            to=255,
            # Важно: делим на 255 для значения 0.0-1.0
            command=lambda v: self._update_cfg_with_path("opacity", int(v) / 255), 
        )
        self.opacity_slider.pack(fill="x", padx=20, pady=5)
        
        # ----------------------------------------------------------------------
        # === Вкладка: Контент (Специфические настройки) ===
        # ----------------------------------------------------------------------
        
        self.specific_settings_frame = ctk.CTkScrollableFrame(tab_content, fg_color="transparent")
        self.specific_settings_frame.pack(fill="both", expand=True, padx=10, pady=5)


        # ----------------------------------------------------------------------
        # === Вкладка: Привязка ===
        # ----------------------------------------------------------------------

        attach_container = ctk.CTkScrollableFrame(tab_attacher, fg_color="transparent")
        attach_container.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.attach_enabled_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            attach_container,
            text="Привязать к окну",
            variable=self.attach_enabled_var,
            command=lambda: self._update_cfg_with_path("attach_to_window.enabled", self.attach_enabled_var.get()),
        ).pack(anchor="w", padx=10, pady=(10, 5))
        
        ctk.CTkLabel(attach_container, text="Заголовок окна (часть названия):").pack(anchor="w", padx=10, pady=(10, 0))
        self.attach_title_entry = ctk.CTkEntry(attach_container)
        self.attach_title_entry.pack(fill="x", padx=10, pady=5)
        self.attach_title_entry.bind(
            "<KeyRelease>", 
            lambda e: self._update_cfg_with_path("attach_to_window.window_title", self.attach_title_entry.get())
        )

        # --- Финальная загрузка ---
        self.refresh_list()

    def add_new_widget(self):
        # Получаем выбранный тип из выпадающего списка
        w_type = self.type_combo.get()
        if not w_type:
            return 
            
        # Используем реестр для получения дефолтного конфига
        new_cfg = get_default_config(w_type)
        
        if self.qt_bridge:
            # Отправляем в Qt-поток на создание
            self.qt_bridge.create_widget_signal.emit(new_cfg)
            
        # Пауза и обновление списка
        import time
        time.sleep(0.1)
        self.refresh_list()

    def _rebuild_content_tab(self, cfg):
        # 1. Очищаем старое
        for w in self.specific_settings_frame.winfo_children():
            w.destroy()

        w_type = cfg.get("type")
        module = get_module(w_type)

        if not module:
            ctk.CTkLabel(self.specific_settings_frame, text="Нет настроек для этого типа").pack()
            return

        # 2. Функция-посредник для обновления конфига
        def on_update(key_path, value):
            keys = key_path.split(".")
            target = cfg
            for k in keys[:-1]: # идем вглубь
                target = target.setdefault(k, {})
            target[keys[-1]] = value
            
            # Отправляем в Qt мост, как раньше
            if self.qt_bridge:
                self.qt_bridge.update_widget_signal.emit(cfg)
            
            # Обновляем превью
            self.preview_canvas.update_preview(cfg)

        # 3. ДЕЛЕГИРУЕМ ОТРИСОВКУ МОДУЛЮ
        if hasattr(module, "render_settings_ui"):
            module.render_settings_ui(self.specific_settings_frame, cfg, on_update)

    def delete_selected_widget(self):
        """Отправляет сигнал в Qt-поток для удаления текущего виджета."""
        if not self.current_cfg or not messagebox.askyesno(
            "Удалить?", "Удалить виджет навсегда?"
        ):
            return

        widget_id = self.current_cfg["id"]

        if self.qt_bridge:
            # Отправляем сигнал в Qt-поток (через qt_bridge.py)
            self.qt_bridge.delete_widget_signal.emit(widget_id)

        # Ждем, пока Qt-поток обработает удаление
        import time
        time.sleep(0.1)

        # Обновляем UI
        self.refresh_list()
        self.current_cfg = None
        self.preview_canvas.delete("all")

    def toggle_coords_inputs(self):
        """Скрывает или показывает поля ввода координат"""
        if self.show_coords_var.get():
            # Показываем фрейм с координатами
            self.coords_frame.pack(
                fill="x", after=self.coords_frame.master.winfo_children()[2]
            )
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
                messagebox.showerror(
                    "Ошибка",
                    "Сигнал start_edit_mode_signal не найден в QtBridge.\nОбновите qt_bridge.py!",
                )
        else:
            messagebox.showerror("Ошибка", "Связь с графическим ядром (Qt) потеряна.")

    # --- НОВЫЕ МЕТОДЫ ДЛЯ ВИЗУАЛЬНОГО РЕДАКТОРА ---

    def toggle_coords_inputs(self):
        """Скрывает или показывает поля ввода координат"""
        if self.show_coords_var.get():
            # Показываем фрейм с координатами
            self.coords_frame.pack(
                fill="x", after=self.coords_frame.master.winfo_children()[2]
            )
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
                messagebox.showerror(
                    "Ошибка",
                    "Сигнал start_edit_mode_signal не найден в QtBridge.\nОбновите qt_bridge.py!",
                )
        else:
            messagebox.showerror("Ошибка", "Связь с графическим ядром (Qt) потеряна.")

    def add_new_clock(self):
        new_cfg = {
            "id": None,
            "type": "clock",
            "name": "Часы",
            "x": 100,
            "y": 100,
            "width": 320,
            "height": 180,
            "opacity": 1.0,
            "click_through": True,
            "always_on_top": True,
            "content": {
                "format": "HH:mm:ss",
                "color": "#00FF88",
                "font_family": "Consolas",
                "font_size": 48,
            },
            "attach_to_window": {
                "enabled": False,
                "window_title": "",
                "offset_x": 0,
                "offset_y": 0,
            },
        }

        if self.qt_bridge:
            self.qt_bridge.create_widget_signal.emit(new_cfg)

        import time

        time.sleep(0.1)

        self.refresh_list()


    def refresh_list(self):
        """Обновляет список виджетов, беря данные из WidgetManager через QtBridge."""
        self.widget_list.delete(0, tk.END)
        if self.wm:
            # Получаем конфиги из менеджера, чтобы отобразить их
            configs = self.wm.get_all_configs()
            for cfg in configs:
                display_name = f"{cfg.get('name', 'Без имени')} [{cfg.get('type')}]"
                self.widget_list.insert(tk.END, display_name)

    def on_select_widget(self, event):
        """Обрабатывает выбор виджета в ListBox."""
        try:
            # Получаем индекс выбранного элемента
            selection = self.widget_list.curselection()
            if not selection:
                return

            list_index = selection[0]
            
            # Получаем конфиг по индексу из WidgetManager
            cfg = self.wm.get_all_configs()[list_index]
            
            # Загружаем конфиг в UI
            self.load_cfg_to_ui(cfg)

        except IndexError:
            # Может произойти, если список был обновлен, а выбор остался
            pass
        except Exception as e:
            print(f"Ошибка при выборе виджета: {e}")

    def start_edit_mode(self):
        """Отправляет сигнал в Qt-поток для активации режима редактирования."""
        print('editmode stared')
        if not self.current_cfg:
            messagebox.showerror("Ошибка", "Сначала выберите виджет для редактирования.")
            return

        widget_id = self.current_cfg["id"]
        
        if self.qt_bridge:
            # Отправляем сигнал в Qt-поток (обрабатывается в widget_manager.py)
            self.qt_bridge.start_edit_mode_signal.emit(widget_id)

    def _update_cfg_with_path(self, key_path: str, value):
        """Обновляет текущий конфиг по пути (например, 'content.color')"""
        if not self.current_cfg:
            return

        keys = key_path.split(".")
        target = self.current_cfg
        
        # Идем вглубь словаря
        for k in keys[:-1]:
            # Используем setdefault, чтобы создать вложенный словарь, если его нет
            target = target.setdefault(k, {}) 
        
        # Обновляем конечное значение
        target[keys[-1]] = value
        
        # 1. Обновляем имя в списке, если изменилось поле 'name'
        if key_path == "name":
            self.refresh_list()
            
        # 2. Отправляем обновленный конфиг через Qt-мост
        if self.qt_bridge:
            self.qt_bridge.update_widget_signal.emit(self.current_cfg)
        
        # 3. Обновляем превью
        self.preview_canvas.update_preview(self.current_cfg)

    def load_cfg_to_ui(self, cfg: dict):
        """Загружает конфигурацию виджета в поля редактора."""
        self.current_cfg = cfg.copy() # Работаем с копией, которая будет обновлена

        # ----------------------------------------------------------------------
        # 1. ОБЩИЕ НАСТРОЙКИ (Вкладка "Внешний вид")
        # ----------------------------------------------------------------------
        
        # Имя
        self.name_entry.delete(0, "end")
        self.name_entry.insert(0, cfg.get("name", "Виджет"))

        # Позиция
        self.pos_x_entry.delete(0, "end")
        self.pos_x_entry.insert(0, str(cfg.get("x", 100)))
        self.pos_y_entry.delete(0, "end")
        self.pos_y_entry.insert(0, str(cfg.get("y", 100)))

        # Размер
        self.size_w_entry.delete(0, "end")
        self.size_w_entry.insert(0, str(cfg.get("width", 320)))
        self.size_h_entry.delete(0, "end")
        self.size_h_entry.insert(0, str(cfg.get("height", 180)))

        # Прозрачность (значения 50-255)
        # В конфиге она хранится как 0.0-1.0, но слайдер использует 50-255 (Qt scale)
        qt_opacity = int(cfg.get("opacity", 1.0) * 255)
        self.opacity_slider.set(qt_opacity)
        
        # Вкладка "Привязка" (если она у тебя есть)
        attach_cfg = cfg.get("attach_to_window", {})
        self.attach_enabled_var.set(attach_cfg.get("enabled", False))
        self.attach_title_entry.delete(0, "end")
        self.attach_title_entry.insert(0, attach_cfg.get("window_title", ""))

        # ----------------------------------------------------------------------
        # 2. Вкладка "Контент"
        # ----------------------------------------------------------------------
        
        # 1. Очищаем динамический фрейм (тут была твоя ошибка!)
        for w in self.specific_settings_frame.winfo_children():
            w.destroy()

        # 2. Получаем модуль виджета из реестра
        w_type = cfg.get("type")
        module = get_module(w_type)

        # 3. Делегируем отрисовку модулю
        if module and hasattr(module, "render_settings_ui"):
            # Вызываем функцию из модуля, передавая ей фрейм и callback-функцию
            module.render_settings_ui(self.specific_settings_frame, cfg, self._update_cfg_with_path)
        else:
            # Если модуль не найден или не имеет функции render_settings_ui
            ctk.CTkLabel(
                self.specific_settings_frame, 
                text=f"Нет специфичных настроек для типа: {w_type}",
                text_color="gray"
            ).pack(pady=20)
        
        # Обновляем превью
        self.preview_canvas.update_preview(cfg)

    def update_cfg(self, key, value):
        if not self.current_cfg:
            return

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

        self.wm.update_widget_config(widget_id, self.current_cfg.copy())

        if self.qt_bridge:
            config_copy = self.current_cfg.copy()
            self.qt_bridge.update_widget_signal.emit(config_copy)

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

                threading.Thread(
                    target=attach_loop,
                    args=(self.wm.widgets[widget_id], self.current_cfg),
                    daemon=True,
                ).start()

    def duplicate_widget(self):
        if not self.current_cfg:
            return
        new_cfg = json.loads(json.dumps(self.current_cfg))
        new_cfg["id"] = None
        new_cfg["name"] += " (копия)"

        if self.qt_bridge:
            self.qt_bridge.create_widget_signal.emit(new_cfg)

        import time

        time.sleep(0.1)

        self.refresh_list()

    def delete_current(self):
        if not self.current_cfg or not messagebox.askyesno(
            "Удалить?", "Удалить виджет навсегда?"
        ):
            return

        widget_id = self.current_cfg["id"]

        if self.qt_bridge:
            self.qt_bridge.delete_widget_signal.emit(widget_id)

        import time

        time.sleep(0.1)

        self.refresh_list()
        self.current_cfg = None
        self.preview.delete("all")
    

def run_widgets_editor(widget_manager):
    def thread_target():
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        root = ctk.CTk()
        root.title("ChronoDash — Настройки")
        root.geometry("1100x700")
        root.minsize(1000, 600)

        icon_path = Path(__file__).parent.parent / "assets" / "icons" / "logo.ico"


        if icon_path.exists():
            try:
                root.iconbitmap(str(icon_path))
            except Exception as e:
                print(f"Ошибка при установке иконки: {e}")

        # Передаём root в редактор
        editor = WidgetsEditor(widget_manager, preexisting_root=root)
        editor.pack(fill="both", expand=True)

        root.mainloop()

    # Запускаем в отдельном потоке
    threading.Thread(target=thread_target, daemon=True).start()
