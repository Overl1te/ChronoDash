from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QTabWidget, 
    QLabel, QLineEdit, QSpinBox, QSlider, QCheckBox, QPushButton, 
    QComboBox, QScrollArea, QMessageBox, QFrame, QSplitter
)
from PySide6.QtCore import Qt, QTimer
from core.registry import MODULES, get_default_config, get_module

class SettingsWindow(QWidget):
    def __init__(self, widget_manager):
        super().__init__()
        self.wm = widget_manager
        self.current_widget_id = None
        
        self.setWindowTitle("ChronoDash — Настройки")
        self.resize(1000, 650)
        
        self._init_ui()
        self.refresh_list()

    def _init_ui(self):
        main_layout = QHBoxLayout(self)
        
        # Сплиттер делит окно на список (слева) и настройки (справа)
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # === ЛЕВАЯ ПАНЕЛЬ (Список) ===
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # Блок добавления
        add_layout = QHBoxLayout()
        self.type_combo = QComboBox()
        self.type_combo.addItems(list(MODULES.keys()))
        btn_add = QPushButton("Создать")
        btn_add.clicked.connect(self._add_widget)
        add_layout.addWidget(self.type_combo, 1)
        add_layout.addWidget(btn_add, 0)
        left_layout.addLayout(add_layout)
        
        # Список виджетов
        self.list_widget = QListWidget()
        self.list_widget.currentRowChanged.connect(self._on_selection_changed)
        left_layout.addWidget(self.list_widget)
        
        # Кнопки действия
        btn_layout = QHBoxLayout()
        self.btn_edit_mode = QPushButton("Режим перемещения")
        self.btn_edit_mode.setCheckable(True)
        self.btn_edit_mode.toggled.connect(self._toggle_edit_mode)
        
        btn_del = QPushButton("Удалить")
        btn_del.setStyleSheet("background-color: #552222;")
        btn_del.clicked.connect(self._delete_widget)
        
        btn_layout.addWidget(self.btn_edit_mode)
        btn_layout.addWidget(btn_del)
        left_layout.addLayout(btn_layout)
        
        splitter.addWidget(left_panel)
        
        # === ПРАВАЯ ПАНЕЛЬ (Настройки) ===
        self.right_panel = QTabWidget()
        splitter.addWidget(self.right_panel)
        
        # Пропорции сплиттера (30% список, 70% настройки)
        splitter.setSizes([300, 700])

    def refresh_list(self):
        """Обновляет список виджетов из менеджера."""
        current_row = self.list_widget.currentRow()
        self.list_widget.clear()
        
        configs = self.wm.get_all_configs()
        for cfg in configs:
            name = cfg.get("name", "Widget")
            w_type = cfg.get("type", "?")
            self.list_widget.addItem(f"{name}  [{w_type}]")
            
        if current_row >= 0 and current_row < self.list_widget.count():
            self.list_widget.setCurrentRow(current_row)

    def _add_widget(self):
        w_type = self.type_combo.currentText()
        if not w_type: return
        
        template = get_default_config(w_type)
        self.wm.create_widget_from_template(template)
        self.refresh_list()
        # Выбираем созданный (последний)
        self.list_widget.setCurrentRow(self.list_widget.count() - 1)

    def _delete_widget(self):
        if not self.current_widget_id: return
        
        reply = QMessageBox.question(self, "Удаление", "Удалить виджет безвозвратно?", 
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.wm.delete_widget(self.current_widget_id)
            self.current_widget_id = None
            self.right_panel.clear()
            self.refresh_list()

    def _toggle_edit_mode(self, active):
        if not self.current_widget_id: 
            self.btn_edit_mode.setChecked(False)
            return
            
        if active:
            self.wm.enter_edit_mode(self.current_widget_id)
            # Если оверлей закроется по ESC, отжимаем кнопку
            if self.wm.overlay:
                self.wm.overlay.stop_edit_signal.connect(lambda: self.btn_edit_mode.setChecked(False))
        else:
            self.wm.exit_edit_mode()

    def _on_selection_changed(self, row):
        if row < 0: return
        
        configs = self.wm.get_all_configs()
        if row < len(configs):
            cfg = configs[row]
            self.current_widget_id = cfg["id"]
            self._load_settings_tabs(cfg)

    def _load_settings_tabs(self, cfg):
        self.right_panel.clear()
        
        # --- TAB 1: Общие ---
        tab_general = QWidget()
        layout_g = QVBoxLayout(tab_general)
        
        # Имя
        layout_g.addWidget(QLabel("Имя виджета:"))
        entry_name = QLineEdit(cfg.get("name", ""))
        entry_name.textChanged.connect(lambda v: self._update_val(cfg, "name", v, refresh_list=True))
        layout_g.addWidget(entry_name)
        
        # Прозрачность
        layout_g.addWidget(QLabel("Прозрачность (10% - 100%):"))
        slider_op = QSlider(Qt.Horizontal)
        slider_op.setRange(10, 100)
        slider_op.setValue(int(cfg.get("opacity", 1.0) * 100))
        slider_op.valueChanged.connect(lambda v: self._update_val(cfg, "opacity", v / 100.0))
        layout_g.addWidget(slider_op)
        
        # Координаты (только чтение или ручной ввод)
        coord_layout = QHBoxLayout()
        for key in ["x", "y", "width", "height"]:
            coord_layout.addWidget(QLabel(f"{key.upper()}:"))
            sb = QSpinBox()
            sb.setRange(-10000, 10000)
            sb.setValue(int(cfg.get(key, 0)))
            # При изменении спинбокса обновляем конфиг
            # (используем замыкание val=key чтобы зафиксировать значение ключа)
            sb.valueChanged.connect(lambda v, k=key: self._update_val(cfg, k, v, refresh_geometry=True))
            coord_layout.addWidget(sb)
        layout_g.addLayout(coord_layout)
        layout_g.addWidget(QLabel("(Или используйте 'Режим перемещения' слева)"))
        
        # Чекбоксы
        cb_top = QCheckBox("Поверх всех окон")
        cb_top.setChecked(cfg.get("always_on_top", False))
        cb_top.toggled.connect(lambda v: self._update_val(cfg, "always_on_top", v))
        layout_g.addWidget(cb_top)
        
        cb_click = QCheckBox("Клик насквозь (невидим для мыши)")
        cb_click.setChecked(cfg.get("click_through", True))
        cb_click.toggled.connect(lambda v: self._update_val(cfg, "click_through", v))
        layout_g.addWidget(cb_click)
        
        layout_g.addStretch()
        self.right_panel.addTab(tab_general, "Общее")
        
        # --- TAB 2: Контент (Специфично для типа) ---
        module = get_module(cfg.get("type"))
        if module and hasattr(module, "render_qt_settings"):
            tab_content = QWidget()
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.NoFrame)
            
            content_widget = QWidget()
            content_layout = QVBoxLayout(content_widget)
            
            # Передаем функцию обратного вызова для обновления вложенных ключей
            module.render_qt_settings(content_layout, cfg, 
                                      lambda path, val: self._update_nested_val(cfg, path, val))
            
            content_layout.addStretch()
            scroll.setWidget(content_widget)
            
            # Оборачиваем скролл в лейаут таба
            tab_layout = QVBoxLayout(tab_content)
            tab_layout.setContentsMargins(0,0,0,0)
            tab_layout.addWidget(scroll)
            
            self.right_panel.addTab(tab_content, "Контент")

    def _update_val(self, cfg, key, value, refresh_list=False, refresh_geometry=False):
        cfg[key] = value
        self.wm.update_widget_config(cfg["id"], cfg)
        if refresh_list:
            item = self.list_widget.currentItem()
            if item: item.setText(f"{value}  [{cfg.get('type')}]")
        if refresh_geometry:
            # Если меняем размеры вручную, нужно перерисовать/подвинуть окно
            self.wm.update_widget_config(cfg["id"], cfg)

    def _update_nested_val(self, cfg, path, value):
        """Обновляет ключи вида 'content.color'."""
        keys = path.split('.')
        target = cfg
        for k in keys[:-1]:
            target = target.setdefault(k, {})
        target[keys[-1]] = value
        self.wm.update_widget_config(cfg["id"], cfg)