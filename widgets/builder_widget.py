# ChronoDash - Base Widget
# Copyright (C) 2025 Overl1te

import json
import zipfile
import shutil
import math
from pathlib import Path
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QFileDialog, QLabel, 
    QFormLayout, QGroupBox, QHBoxLayout, QFrame
)
from PySide6.QtGui import (
    QPainter, QPainterPath, QColor, QBrush, QPen, 
    QLinearGradient, QFont, QPixmap
)
from PySide6.QtCore import Qt, QTimer, QRectF, QStandardPaths

from widgets.base_widget import BaseDesktopWidget

# --- ХЕЛПЕР ДЛЯ ЧТЕНИЯ МЕТАДАННЫХ ДО СОЗДАНИЯ ---
def read_widget_metadata(file_path):
    """
    Читает 'root' секцию из .wgt или .json файла.
    Возвращает словарь с настройками или None, если файл битый.
    """
    path = Path(file_path)
    if not path.exists(): return None
    
    data = None
    try:
        if path.suffix.lower() == ".wgt":
            with zipfile.ZipFile(path, 'r') as zf:
                if "widget.json" in zf.namelist():
                    with zf.open("widget.json") as f:
                        data = json.load(f)
        elif path.suffix.lower() == ".json":
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
        if data and "root" in data:
            return data["root"]
    except Exception as e:
        print(f"Metadata read error: {e}")
    return None


class BuilderWidget(BaseDesktopWidget):
    def __init__(self, cfg=None, is_preview=False):
        super().__init__(cfg, is_preview=is_preview)
        
        self.render_tree = []  
        self.widgets_map = {}  
        self.children_map = {} 
        self.assets_dir = None
        self.root_data = {}
        self.image_cache = {} 
        
        self._load_source()
        
        if self._has_dynamic_elements() and not self.is_preview:
            self.timer = QTimer(self)
            self.timer.timeout.connect(self.update)
            self.timer.start(1000)

    def update_config(self, new_cfg):
        super().update_config(new_cfg)
        self._load_source()
        self.update()

    def _load_source(self):
        content = self.cfg.get("content", {})
        source_path = content.get("file_path", "")
        
        if not source_path or not Path(source_path).exists():
            return

        path_obj = Path(source_path)
        data = None
        
        try:
            if path_obj.suffix.lower() == ".wgt":
                # Кэшируем в папку с ID виджета
                cache_dir = Path(QStandardPaths.writableLocation(QStandardPaths.AppConfigLocation)) / "cache" / self.cfg["id"]
                if cache_dir.exists(): shutil.rmtree(cache_dir)
                cache_dir.mkdir(parents=True, exist_ok=True)
                
                with zipfile.ZipFile(path_obj, 'r') as zf:
                    zf.extractall(cache_dir)
                
                self.assets_dir = cache_dir
                json_file = cache_dir / "widget.json"
                if json_file.exists():
                    with open(json_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
            
            elif path_obj.suffix.lower() == ".json":
                self.assets_dir = path_obj.parent
                with open(path_obj, "r", encoding="utf-8") as f:
                    data = json.load(f)

            if data:
                self._parse_data(data)
                
        except Exception as e:
            print(f"[BuilderWidget] Error loading: {e}")

    def _parse_data(self, data):
        self.widgets_map = {}
        self.children_map = {}
        
        # Данные рута (фон, стили)
        self.root_data = data.get("root", {})
        
        # ВАЖНО: Мы НЕ меняем размеры окна здесь (self.resize), 
        # потому что теперь мы задаем их ПРИ СОЗДАНИИ в settings_window.
        # Но если юзер подменил файл на другой размер, можно обновить cfg.
        # if not self.is_preview:
            # self.cfg['width'] = self.root_data.get('width') ...
        
        widgets = data.get("widgets", [])
        widgets.sort(key=lambda x: x.get("z_index", 0))

        for w in widgets:
            wid = w.get("id")
            self.widgets_map[wid] = w
            pid = w.get("parent_id", "root")
            if pid not in self.children_map: self.children_map[pid] = []
            self.children_map[pid].append(w)

        self.render_tree = self.children_map.get("root", [])

    def _has_dynamic_elements(self):
        for w in self.widgets_map.values():
            if w.get("type") in ["clock", "date", "progress"]: return True
        return False

    def draw_widget(self, painter: QPainter):
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        
        # Рисуем фон Root Frame
        if self.root_data:
            root_draw_data = {"type": "rect", "style": self.root_data.get("style", {})}
            self._paint_shape(painter, QRectF(self.rect()), root_draw_data)
        
        for w_data in self.render_tree:
            self._draw_element_recursive(painter, w_data)

    def _draw_element_recursive(self, painter, data):
        painter.save()
        x = int(data.get("x", 0))
        y = int(data.get("y", 0))
        painter.translate(x, y)
        
        w = int(data.get("width", 100))
        h = int(data.get("height", 100))
        rect = QRectF(0, 0, w, h)
        
        self._paint_shape(painter, rect, data)
        self._paint_content(painter, rect, data)
        
        wid = data.get("id")
        if wid in self.children_map:
            for child in self.children_map[wid]:
                self._draw_element_recursive(painter, child)
        painter.restore()

    def _paint_shape(self, painter, rect, data):
        # ... (Код отрисовки шейпов без изменений) ...
        w_type = data.get("type", "rect")
        style = data.get("style", {})
        path = QPainterPath()
        
        if w_type == "circle": path.addEllipse(rect)
        else: path.addRoundedRect(rect, int(style.get("radius", 0)), int(style.get("radius", 0)))
            
        painter.save()
        painter.setClipPath(path)
        painter.setOpacity(float(style.get("opacity", 1.0)))
        
        bg_col = style.get("bg_color", "transparent")
        if bg_col != "transparent": painter.fillPath(path, QColor(bg_col))
            
        bg_img = style.get("bg_image", "")
        if bg_img:
            img_path = Path(bg_img)
            if not img_path.exists() and self.assets_dir: img_path = self.assets_dir / img_path.name
            
            key = str(img_path)
            if img_path.exists():
                if key not in self.image_cache: self.image_cache[key] = QPixmap(key)
                pix = self.image_cache[key]
                if not pix.isNull():
                    bg_x, bg_y = int(style.get("bg_x", 0)), int(style.get("bg_y", 0))
                    bg_w, bg_h = int(style.get("bg_w", 0)), int(style.get("bg_h", 0))
                    if bg_w <= 0: painter.drawPixmap(0, 0, pix.scaled(rect.size().toSize(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))
                    else: painter.drawPixmap(bg_x, bg_y, pix.scaled(bg_w, bg_h, Qt.IgnoreAspectRatio, Qt.SmoothTransformation))

        if style.get("use_gradient", False):
            start_c = QColor(style.get("grad_start", "#ffffff"))
            end_c = QColor(style.get("grad_end", "#000000"))
            angle = int(style.get("grad_angle", 90))
            cx, cy = rect.width()/2, rect.height()/2
            r = math.sqrt(rect.width()**2 + rect.height()**2)/2
            rad = math.radians(angle)
            grad = QLinearGradient(cx - r*math.cos(rad), cy - r*math.sin(rad), cx + r*math.cos(rad), cy + r*math.sin(rad))
            grad.setColorAt(0, start_c); grad.setColorAt(1, end_c)
            painter.fillPath(path, QBrush(grad))
        painter.restore()

        b_width = int(style.get("border_width", 0))
        if b_width > 0:
            pen = QPen(QColor(style.get("border_color", "#000000")), b_width)
            pen.setJoinStyle(Qt.MiterJoin)
            painter.setPen(pen); painter.setBrush(Qt.NoBrush); painter.drawPath(path)

    def _paint_content(self, painter, rect, data):
        # ... (Код отрисовки контента без изменений) ...
        w_type = data.get("type")
        content = data.get("content", {})
        text_to_draw = ""
        
        if w_type == "text": text_to_draw = content.get("text", "")
        elif w_type == "clock":
            try: text_to_draw = datetime.now().strftime(content.get("format", "HH:mm"))
            except: pass
        elif w_type == "date":
            try: text_to_draw = datetime.now().strftime(content.get("format", "%d.%m.%Y"))
            except: pass
            
        if text_to_draw:
            font = QFont(content.get("font_family", "Arial"), int(content.get("font_size", 12)))
            painter.setFont(font)
            pen = QPen(QColor(content.get("color", "#000000")))
            if content.get("use_text_gradient", False): pen.setColor(QColor(content.get("text_grad_start", "#000000")))
            painter.setPen(pen)
            painter.drawText(rect, Qt.AlignCenter, text_to_draw)

        if w_type == "progress":
            val, max_v = float(content.get("value", 0)), float(content.get("max_value", 100))
            if max_v <= 0: max_v = 1
            ratio = min(max(val/max_v, 0.0), 1.0)
            fill_rect = QRectF(0, 0, rect.width()*ratio, rect.height())
            
            path = QPainterPath()
            rad = int(data.get("style", {}).get("radius", 0))
            path.addRoundedRect(rect, rad, rad)
            
            painter.save()
            painter.setClipPath(path)
            painter.fillRect(fill_rect, QColor(content.get("bar_color", "#00ff88")))
            painter.restore()

# === UI НАСТРОЕК (Только отображение пути) ===
def render_qt_settings(layout, cfg, on_update):
    content = cfg.get("content", {})
    
    gb = QGroupBox("Источник")
    l = QVBoxLayout(gb)
    
    path_lbl = QLabel(content.get("file_path", "Нет файла"))
    path_lbl.setWordWrap(True)
    path_lbl.setStyleSheet("color: #44AAFF; font-weight: bold;")
    l.addWidget(path_lbl)
    
    # Кнопку "Сменить файл" можно оставить, но лучше пусть удаляют и создают заново
    btn = QPushButton("Сменить файл...")
    def change():
        path, _ = QFileDialog.getOpenFileName(None, "Выбрать виджет", "", "Chrono Widget (*.wgt *.json)")
        if path:
            on_update("content.file_path", path)
            # Тут можно было бы тоже подтянуть размеры, но это сложнее из UI callback
            path_lbl.setText(Path(path).name)
    btn.clicked.connect(change)
    l.addWidget(btn)
    
    layout.addWidget(gb)

# Дефолтный конфиг (используется как болванка)
def get_default_config():
    return {
        "type": "custom_builder",
        "name": "Imported Widget",
        "width": 300,
        "height": 200,
        "opacity": 1.0,
        "content": {"file_path": ""}
    }

WidgetClass = BuilderWidget