#!/bin/bash
# build_arch.sh - сборка ChronoDash для Arch Linux

set -e

echo "=== Начало сборки ChronoDash ==="

# Активируем виртуальное окружение
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    echo "Виртуальное окружение активировано"
else
    echo "❌ Виртуальное окружение не найдено"
    echo "Создайте его командой: python -m venv venv"
    exit 1
fi

# Очищаем предыдущие сборки
echo "Очистка старых сборок..."
rm -rf build/ dist/ *.spec __pycache__/ *.pyc AppImage/ pkg/

# Устанавливаем зависимости
echo "Установка зависимостей..."
pip install --upgrade pip
pip install PySide6 customtkinter Pillow requests openmeteo-requests requests-cache retry-requests numpy pandas psutil pystray Xlib

echo "Сборка ChronoDash..."

# Собираем с правильными путями
pyinstaller \
    --onedir \
    --name ChronoDash \
    --icon assets/icons/chronodash.png \
    --add-data "assets:assets" \
    --add-data "core:core" \
    --add-data "widgets:widgets" \
    --hidden-import tkinter \
    --hidden-import tkinter.ttk \
    --hidden-import tkinter.font \
    --hidden-import tkinter.messagebox \
    --hidden-import tkinter.filedialog \
    --hidden-import _tkinter \
    --hidden-import customtkinter \
    --hidden-import PySide6.QtCore \
    --hidden-import PySide6.QtGui \
    --hidden-import PySide6.QtWidgets \
    --hidden-import PySide6.QtSvg \
    --hidden-import PySide6.QtNetwork \
    --hidden-import pystray \
    --hidden-import pystray._xorg \
    --hidden-import Xlib \
    --hidden-import Xlib.display \
    --hidden-import openmeteo_requests \
    --hidden-import requests_cache \
    --hidden-import retry_requests \
    --hidden-import numpy \
    --hidden-import pandas \
    --hidden-import psutil \
    --hidden-import PIL \
    --hidden-import PIL._imaging \
    --exclude-module matplotlib \
    --exclude-module scipy \
    --clean \
    --noconfirm \
    --console \
    main.py

echo "✅ Сборка завершена!"

# Проверяем результат
if [ -f "dist/ChronoDash/ChronoDash" ]; then
    echo "✅ Исполняемый файл создан: dist/ChronoDash/ChronoDash"
    file dist/ChronoDash/ChronoDash
    ls -lh dist/ChronoDash/ChronoDash
else
    echo "❌ Файл не найден. Содержимое dist/ChronoDash/:"
    ls -la dist/ChronoDash/
    echo "Ищем исполняемые файлы..."
    find dist -type f -executable -o -name "ChronoDash" -o -name "chronodash"
    exit 1
fi

echo "=== ОПТИМИЗАЦИЯ ДЛЯ СИСТЕМЫ С _internal ==="

# Переходим в папку сборки
cd dist/ChronoDash

# Проверяем структуру
echo "Структура директории:"
find . -maxdepth 3 -type d | sort

# Определяем путь к _internal
if [ -d "_internal" ]; then
    INTERNAL_PATH="./_internal"
elif [ -d "./ChronoDash/_internal" ]; then
    INTERNAL_PATH="./ChronoDash/_internal"
else
    # Ищем _internal
    INTERNAL_PATH=$(find . -type d -name "_internal" -print -quit 2>/dev/null || echo "")
    if [ -z "$INTERNAL_PATH" ]; then
        echo "⚠️  Папка _internal не найдена, возможно другая структура"
        INTERNAL_PATH="."
    fi
fi

echo "Путь к ресурсам: $INTERNAL_PATH"

echo "Создаем скрипты в dist/ChronoDash/..."

# Создаем универсальный скрипт запуска
cat > launch.sh << 'EOF'
#!/bin/bash
# Скрипт запуска ChronoDash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================"
echo "ChronoDash - Desktop Widgets"
echo "========================================"
echo "Директория: $SCRIPT_DIR"

# Автоматически определяем структуру
if [ -f "./ChronoDash" ]; then
    EXECUTABLE="./ChronoDash"
    INTERNAL="./_internal"
elif [ -f "./_internal/ChronoDash" ]; then
    EXECUTABLE="./_internal/ChronoDash"
    INTERNAL="./_internal"
else
    # Ищем исполняемый файл
    EXECUTABLE=$(find . -type f -name "ChronoDash" -executable -print -quit 2>/dev/null || echo "")
    if [ -z "$EXECUTABLE" ]; then
        echo "❌ ОШИБКА: Файл ChronoDash не найден!"
        echo "Содержимое директории:"
        ls -la
        exit 1
    fi
    INTERNAL="$(dirname "$EXECUTABLE")"
fi

echo "Исполняемый файл: $EXECUTABLE"
echo "Внутренняя директория: $INTERNAL"

# Проверяем права
if [ ! -x "$EXECUTABLE" ]; then
    echo "Даем права на выполнение..."
    chmod +x "$EXECUTABLE"
fi

# Настраиваем пути Qt
QT_PLUGINS_PATHS=(
    "$INTERNAL/PySide6/Qt/plugins"
    "$INTERNAL/PySide6/plugins"
    "./PySide6/Qt/plugins"
    "/usr/lib/qt6/plugins"
    "/usr/lib/qt/plugins"
)

for QT_PATH in "${QT_PLUGINS_PATHS[@]}"; do
    if [ -d "$QT_PATH" ]; then
        export QT_QPA_PLATFORM_PLUGIN_PATH="$QT_PATH"
        export QT_PLUGIN_PATH="$QT_PATH"
        echo "Qt плагины: $QT_PATH"
        break
    fi
done

# Отключаем отладку Qt
export QT_DEBUG_PLUGINS=0

# Определяем тип сессии (Wayland/X11)
if [ -z "$XDG_SESSION_TYPE" ]; then
    if [ -n "$WAYLAND_DISPLAY" ]; then
        export XDG_SESSION_TYPE=wayland
    else
        export XDG_SESSION_TYPE=x11
    fi
fi
echo "Тип сессии: $XDG_SESSION_TYPE"

echo "Запуск ChronoDash..."
echo "========================================"

# Запускаем приложение
exec "$EXECUTABLE" "$@"
EOF

chmod +x launch.sh

# Создаем скрипт для отладки
cat > debug.sh << 'EOF'
#!/bin/bash
# Скрипт отладки ChronoDash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================"
echo "ChronoDash - Режим отладки"
echo "========================================"
echo "Директория: $SCRIPT_DIR"

# Автоматически определяем структуру
if [ -f "./ChronoDash" ]; then
    EXECUTABLE="./ChronoDash"
    INTERNAL="./_internal"
elif [ -f "./_internal/ChronoDash" ]; then
    EXECUTABLE="./_internal/ChronoDash"
    INTERNAL="./_internal"
else
    # Ищем исполняемый файл
    EXECUTABLE=$(find . -type f -name "ChronoDash" -executable -print -quit 2>/dev/null || echo "")
    if [ -z "$EXECUTABLE" ]; then
        echo "❌ Файл ChronoDash не найден!"
        ls -la
        exit 1
    fi
    INTERNAL="$(dirname "$EXECUTABLE")"
fi

echo "Исполняемый файл: $EXECUTABLE"
echo "Внутренняя директория: $INTERNAL"

# Включаем полную отладку Qt
export QT_DEBUG_PLUGINS=1
export QT_LOGGING_RULES="qt.*=true"
export QT_FATAL_WARNINGS=1

echo "Отладка Qt включена"
echo "Запуск приложения..."
echo "========================================"

# Запускаем
exec "$EXECUTABLE" "$@"
EOF

chmod +x debug.sh

# Создаем скрипт проверки
cat > check.sh << 'EOF'
#!/bin/bash
# Проверка сборки

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== ПРОВЕРКА СБОРКИ CHRONODASH ==="
echo "Время: $(date)"
echo "Директория: $SCRIPT_DIR"
echo ""
echo "1. СТРУКТУРА ДИРЕКТОРИИ:"
echo "------------------------"
find . -maxdepth 3 -type d | sort
echo ""
echo "2. ИСПОЛНЯЕМЫЕ ФАЙЛЫ:"
echo "---------------------"
find . -type f -executable -o -name "ChronoDash" | while read file; do
    echo "✅ Найден: $file"
    file "$file"
    echo "Размер: $(du -h "$file" | cut -f1)"
    echo "Права: $(stat -c "%A %U:%G" "$file")"
    echo ""
done
echo ""
echo "3. ПАПКА _internal:"
echo "------------------"
if [ -d "./_internal" ]; then
    echo "✅ Папка _internal найдена"
    echo "Содержимое:"
    ls -la ./_internal/
    echo ""
    echo "Ресурсы в _internal:"
    if [ -d "./_internal/assets" ]; then
        echo "✅ Ресурсы в _internal/assets"
        ls -la ./_internal/assets/
    else
        echo "❌ Ресурсы не найдены в _internal"
    fi
else
    echo "❌ Папка _internal не найдена"
fi
echo ""
echo "4. QT ПЛАГИНЫ:"
echo "-------------"
QT_PATHS=(
    "./_internal/PySide6/Qt/plugins"
    "./PySide6/Qt/plugins"
    "/usr/lib/qt6/plugins"
)

for QT_PATH in "${QT_PATHS[@]}"; do
    if [ -d "$QT_PATH" ]; then
        echo "✅ Qt плагины найдены в: $QT_PATH"
        find "$QT_PATH" -type f | head -10
        echo ""
    fi
done
echo ""
echo "=== ПРОВЕРКА ЗАВЕРШЕНА ==="
EOF

chmod +x check.sh

# Создаем README
cat > README.md << 'EOF'
# ChronoDash - Desktop Widgets

## Структура сборки

Версия PyInstaller может создавать разные структуры:
- `./ChronoDash` + `./_internal/` (современные версии)
- Все файлы в корне (старые версии)

## Запуск приложения

1. **Рекомендованный запуск:**
   ```bash
   ./launch.sh
EOF