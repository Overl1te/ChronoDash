#!/bin/bash
# build_arch.sh - сборка ChronoDash для Arch Linux

set -e

echo "=== Начало сборки ChronoDash ==="

# Очищаем предыдущие сборки
echo "Очистка старых сборок..."
rm -rf build/ dist/ *.spec __pycache__/ *.pyc AppImage/ pkg/ *.AppImage venv/

echo "Создание виртуального окружения..."
python3 -m venv venv
source venv/bin/activate

# Устанавливаем зависимости
echo "Установка зависимостей..."
pip install --upgrade pip
pip install -r requirements.txt

echo "Сборка ChronoDash..."

# Собираем с правильными путями
pyinstaller \
    --onedir \
    --name ChronoDash \
    --icon assets/icons/chronodash.png \
    --add-data "assets:assets" \
    --add-data "core:core" \
    --add-data "widgets:widgets" \
    --hidden-import PySide6 \
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
echo ""
echo "Если приложение не работает - попробуйте его переустановить."
echo "Если переустановка не помогла установите предыдущую версию"
EOF

chmod +x check.sh

cat > install.sh << 'EOF'
#!/bin/bash
# Установка ChronoDash на Arch Linux

set -e

echo "=== Установка ChronoDash ==="

# Проверяем права
if [ "$EUID" -eq 0 ]; then
    echo "⚠️  Запуск напрямую от root не рекомендуется"
    echo "   Используйте: sudo ./install.sh"
    exit 1
fi

# Устанавливаем зависимости
echo "Установка зависимостей..."
sudo pacman -S --noconfirm --needed \
    python \
    tk \
    qt6-base \
    qt6-svg \
    qt6-wayland \
    gcc-libs \
    glibc \
    libx11 \
    libxcb \
    libxkbcommon \
    zlib \
    pango \
    gdk-pixbuf2 \
    cairo \
    fontconfig \
    freetype2 \
    harfbuzz \
    libjpeg-turbo \
    libpng \
    libtiff \
    libwebp

echo ""
echo "Проверяем собранное приложение..."


# Определяем структуру
BUILD_DIR="."
if [ -f "$BUILD_DIR/ChronoDash" ]; then
    echo "✅ Найден исполняемый файл в корне"
    EXECUTABLE="ChronoDash"
elif [ -f "$BUILD_DIR/_internal/ChronoDash" ]; then
    echo "✅ Найден исполняемый файл в _internal"
    EXECUTABLE="_internal/ChronoDash"
else
    # Ищем исполняемый файл
    EXECUTABLE=$(find "$BUILD_DIR" -type f -executable -name "ChronoDash" -printf "%P\n" | head -1)
    if [ -z "$EXECUTABLE" ]; then
        echo "❌ Ошибка: Исполняемый файл ChronoDash не найден!"
        echo "   Проверьте сборку: ./check.sh"
        exit 1
    fi
    echo "✅ Исполняемый файл найден: $EXECUTABLE"
fi

echo ""
echo "Создание директорий..."
sudo mkdir -p /opt/chronodash
sudo mkdir -p /usr/share/applications
mkdir -p ~/.config/chronodash

# Копируем приложение
echo "Копирование файлов..."
sudo cp -r ./* /opt/chronodash/

# Устанавливаем права
echo "Настройка прав доступа..."
sudo chown -R root:root /opt/chronodash
sudo find /opt/chronodash -type f -exec chmod 644 {} \;
sudo find /opt/chronodash -type d -exec chmod 755 {} \;
sudo chmod 755 "/opt/chronodash/$EXECUTABLE"

# Создаем запускающий скрипт
echo "Создание скрипта запуска..."
sudo tee /usr/bin/chronodash > /dev/null << 'SCRIPT'
#!/bin/bash
# Запускающий скрипт ChronoDash

APP_DIR="/opt/chronodash"
cd "$APP_DIR"

echo "=== ChronoDash Desktop Widgets ==="

# Настраиваем переменные окружения
export PATH="$APP_DIR:$PATH"

# Определяем структуру
if [ -f "./ChronoDash" ]; then
    EXEC="./ChronoDash"
elif [ -f "./_internal/ChronoDash" ]; then
    EXEC="./_internal/ChronoDash"
else
    # Пробуем найти любой исполняемый файл
    EXEC=$(find . -type f -executable -name "ChronoDash" -print -quit 2>/dev/null)
    if [ -z "$EXEC" ]; then
        echo "❌ Ошибка: Исполняемый файл не найден!"
        echo "Содержимое $APP_DIR:"
        ls -la
        exit 1
    fi
fi

# Настраиваем Qt
QT_PATHS=(
    "/usr/lib/qt6/plugins"
    "/usr/lib/qt/plugins"
    "./PySide6/Qt/plugins"
    "./_internal/PySide6/Qt/plugins"
)

for QT_PATH in "${QT_PATHS[@]}"; do
    if [ -d "$QT_PATH" ]; then
        export QT_QPA_PLATFORM_PLUGIN_PATH="$QT_PATH"
        export QT_PLUGIN_PATH="$QT_PATH"
        echo "Qt плагины: $QT_PATH"
        break
    fi
done

# Отключаем отладку Qt
export QT_DEBUG_PLUGINS=0

# Определяем тип сессии
if [ -z "$XDG_SESSION_TYPE" ]; then
    if [ -n "$WAYLAND_DISPLAY" ]; then
        export XDG_SESSION_TYPE=wayland
    else
        export XDG_SESSION_TYPE=x11
    fi
fi
echo "Сессия: $XDG_SESSION_TYPE"

# Запускаем приложение
echo "Запуск: $EXEC"
exec "$EXEC" "$@"
SCRIPT

sudo chmod 755 /usr/bin/chronodash

# Создаем скрипт отладки
# echo "Создание скрипта отладки..."
# sudo tee /usr/bin/chronodash-debug > /dev/null << 'DEBUG'
# #!/bin/bash
# # Скрипт отладки ChronoDash

# export QT_DEBUG_PLUGINS=1
# export QT_LOGGING_RULES="qt.*=true"
# export QT_FATAL_WARNINGS=1

# echo "=== РЕЖИМ ОТЛАДКИ ChronoDash ==="
# chronodash "$@"
# DEBUG

# sudo chmod 755 /usr/bin/chronodash-debug

# Ищем иконку для .desktop файла
echo "Поиск иконки..."
ICON_PATH=""
ICON_PATHS=(
    "/opt/chronodash/assets/icons/chronodash.png"
    "/opt/chronodash/_internal/assets/icons/chronodash.png"
    "/opt/chronodash/chronodash.png"
)

for icon in "${ICON_PATHS[@]}"; do
    if [ -f "$icon" ]; then
        ICON_PATH="$icon"
        echo "✅ Найдена иконка: $icon"
        break
    fi
done

if [ -z "$ICON_PATH" ]; then
    echo "⚠️  Иконка не найдена, создаем символическую ссылку"
    # Создаем простую иконку
    sudo convert -size 64x64 xc:#2C3E50 -pointsize 24 -fill white \
        -gravity center -draw "text 0,0 'CD'" \
        /opt/chronodash/chronodash.png 2>/dev/null || \
        sudo cp /usr/share/icons/hicolor/scalable/apps/system-run.svg /opt/chronodash/chronodash.png 2>/dev/null || true
    ICON_PATH="/opt/chronodash/chronodash.png"
fi

# Создаем MetaInfo
sudo tee /usr/share/metainfo/chronodash.metainfo.xml > /dev/null <<XML
<?xml version="2.2.6-beta" encoding="UTF-8"?>
<component type="desktop-application">
  <id>chronodash.desktop</id>

  <name>ChronoDash</name>
  <summary>Customizable desktop widgets for Linux</summary>

  <description>
    <p>
      ChronoDash is a modern desktop widgets manager for Linux.
      It allows you to place elegant, transparent widgets directly
      on your desktop.
    </p>
    <p>
      Features include clocks, weather information, and real-time
      system monitoring with an always-on-top, distraction-free design.
    </p>
  </description>

  <metadata_license>CC-BY-4.0</metadata_license>
  <project_license>GPL-3.0-or-later</project_license>

  <developer>
    <name>Overl1te</name>
  </developer>

  <url type="homepage">https://github.com/Overl1te/ChronoDash</url>
  <url type="bugtracker">https://github.com/Overl1te/ChronoDash/issues</url>
  <url type="source">https://github.com/Overl1te/ChronoDash</url>

  <categories>
    <category>Utility</category>
    <category>System</category>
  </categories>

  <launchable type="desktop-id">chronodash.desktop</launchable>
</component>
XML

# Создаем .desktop файл
echo "Создание файла меню..."
sudo tee /usr/share/applications/chronodash.desktop > /dev/null << 'DESKTOP'
[Desktop Entry]
Type=Application
Version=1.5

Name=ChronoDash
GenericName=Desktop Widgets
Comment=Modern, customizable desktop widgets for time, weather, and system monitoring

Exec=/usr/bin/chronodash
TryExec=/usr/bin/chronodash
Icon=chronodash

Terminal=false
StartupNotify=true

Categories=Utility;System;DesktopSettings;
Keywords=widget;desktop;clock;time;weather;system;monitor;
DESKTOP

# Создаем системную иконку
echo "Создание системной иконки..."
sudo mkdir -p /usr/share/icons/hicolor/256x256/apps/
sudo cp "$ICON_PATH" /usr/share/icons/hicolor/256x256/apps/chronodash.png 2>/dev/null || true

# Создаем конфигурационный файл по умолчанию
echo "Создание конфигурации..."
cat > ~/.config/chronodash/config.json << 'CONFIG'
{
    "version": "1.0",
    "widgets": {
        "clock": {
            "enabled": true,
            "position": "top-right",
            "format": "HH:mm:ss"
        },
        "weather": {
            "enabled": true,
            "position": "top-left",
            "units": "metric"
        }
    },
    "theme": "dark",
    "transparency": 0.8
}
CONFIG

echo ""
echo "✅ Установка завершена!"
echo ""
echo "=== КОМАНДЫ ==="
echo "  chronodash              # Запустить приложение"
echo "  chronodash-debug        # Запустить с отладкой"
echo ""
echo "=== ФАЙЛЫ ==="
echo "  Приложение:     /opt/chronodash/"
echo "  Скрипт запуска: /usr/bin/chronodash"
echo "  Меню:           /usr/share/applications/chronodash.desktop"
echo "  Конфигурация:   ~/.config/chronodash/"
echo "  Иконка:         /usr/share/icons/hicolor/64x64/apps/chronodash.png"
EOF

chmod +x install.sh

# Создаем README
cat > README.md << 'EOF'
# ChronoDash - Desktop Widgets

## Запуск приложения

1. **Быстрый запуск:**
   ```bash
   ./launch.sh
   ```
3. **Установить приложение системно (РЕКОМЕНДУЕТСЯ!):**
   ```bash
   sudo ./install.sh
   ```
2. **Проверка сборки:**
   ```bash
   ./check.sh
   ```
EOF

echo "✅Успешно"
# read -p "Установить сразу? [Y/N]: " ans
# case "$ans" in
#     [yY]) 
#         bash ./install.sh 
#         ;;
#     [nN]) 
#         exit 0
#         ;;
#     *)
#         bash ./install.sh 
#         ;;
# esac