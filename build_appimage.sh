#!/usr/bin/env bash
# set -euo pipefail

echo "=== Сборка ChronoDash v2.2.5-beta AppImage ==="

# 1. Создаём venv и ставим всё нужное
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install pyinstaller
pip install -r requirements.txt

# 2. PyInstaller — onefile + hidden imports для Qt/tkinter
pyinstaller \
  --name ChronoDash \
  --onefile \
  --windowed \
  --icon="assets/icons/chronodash.png" \
  --add-data "assets:assets" \
  --add-data "core:core" \
  --add-data "dashboard:dashboard" \
  --add-data "widgets:widgets" \
  --hidden-import PySide6.QtSvg \
  --hidden-import PySide6.QtWidgets \
  --hidden-import PySide6.QtGui \
  --hidden-import PySide6.QtCore \
  --hidden-import PySide6.QtNetwork \
  --hidden-import tkinter \
  main.py
deactivate

# 3. Готовим структуру AppDir
rm -rf AppDir
mkdir -p AppDir/usr/bin AppDir/usr/share/icons/hicolor/64x64/apps AppDir/usr/share/applications AppDir/usr/share/metainfo

# Копируем бинарник → AppRun (обязательно!)
cp dist/ChronoDash AppDir/usr/bin/AppRun
chmod +x AppDir/usr/bin/AppRun

# Иконка (ищем подходящую)
ICON_FOUND=false
for icon in assets/icons/{logo,chronodash,app,icon}.png; do
  if [[ -f "$icon" ]]; then
    cp "$icon" AppDir/usr/share/icons/hicolor/64x64/apps/chronodash.png
    ICON_FOUND=true
    break
  fi
done
if ! $ICON_FOUND; then
  echo "Предупреждение: иконка не найдена в assets/icons/"
fi

# Создаем MetaInfo
cat > pkg/usr/share/metainfo/chronodash.metainfo.xml <<XML
<?xml version="2.2.5" encoding="UTF-8"?>
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

# .desktop файл
cat > AppDir/chronodash.desktop << EOF
[Desktop Entry]
Type=Application
Version=2.2.5

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
EOF

# 4. Собираем AppImage
appimagetool AppDir ChronoDash-2.2.5-beta-x86_64.AppImage

echo "Успешно"