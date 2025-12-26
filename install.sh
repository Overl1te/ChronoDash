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

# Проверяем наличие собранного приложения
if [ ! -d "./dist/ChronoDash" ]; then
    echo "❌ Ошибка: Собранное приложение не найдено в ./dist/ChronoDash/"
    echo "   Сначала выполните: ./build_arch.sh"
    exit 1
fi

echo "✅ Сборка найдена в ./dist/ChronoDash/"
echo "Структура:"
find ./dist/ChronoDash -maxdepth 2 -type f -o -type d | sort

# Определяем структуру
BUILD_DIR="./dist/ChronoDash"
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
        echo "   Проверьте сборку: ./dist/ChronoDash/check.sh"
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
sudo cp -r ./dist/ChronoDash/* /opt/chronodash/

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
echo "Создание скрипта отладки..."
sudo tee /usr/bin/chronodash-debug > /dev/null << 'DEBUG'
#!/bin/bash
# Скрипт отладки ChronoDash

export QT_DEBUG_PLUGINS=1
export QT_LOGGING_RULES="qt.*=true"
export QT_FATAL_WARNINGS=1

echo "=== РЕЖИМ ОТЛАДКИ ChronoDash ==="
chronodash "$@"
DEBUG

sudo chmod 755 /usr/bin/chronodash-debug

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
cat > pkg/usr/share/metainfo/chronodash.metainfo.xml <<XML
<?xml version="2.2.1" encoding="UTF-8"?>
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
Version=2.2.1

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
sudo mkdir -p /usr/share/icons/hicolor/64x64/apps/
sudo cp "$ICON_PATH" /usr/share/icons/hicolor/64x64/apps/chronodash.png 2>/dev/null || true

# Создаем конфигурационный файл по умолчанию
echo "Создание конфигурации..."
cat > ~/.config/chronodash/config.json << 'CONFIG'
{
    "version": "2.2.1",
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
# echo ""
# echo "=== ПРОВЕРКА ==="
# echo "1. Проверьте структуру: ls -la /opt/chronodash/"
# echo "2. Проверьте исполняемый файл: file /opt/chronodash/ChronoDash"
# echo "3. Проверьте зависимости: ldd /opt/chronodash/ChronoDash 2>/dev/null || echo 'Используйте chronodash-debug'"
# echo ""
# echo "Приложение появится в меню приложений"
# echo "Для удаления используйте: sudo rm -rf /opt/chronodash /usr/bin/chronodash /usr/share/applications/chronodash.desktop"

# # Тестовый запуск (опционально)
# read -p "Запустить тестовую проверку? [y/N]: " -n 1 -r
# echo
# if [[ $REPLY =~ ^[Yy]$ ]]; then
#     echo "=== ТЕСТОВАЯ ПРОВЕРКА ==="
#     if /opt/chronodash/$EXECUTABLE --version 2>/dev/null || /opt/chronodash/$EXECUTABLE -h 2>/dev/null; then
#         echo "✅ Приложение запускается"
#     else
#         echo "⚠️  Не удалось проверить версию, но установка завершена"
#         echo "   Попробуйте: chronodash-debug"
#     fi
# fi