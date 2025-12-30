#!/usr/bin/env bash
# set -euo pipefail

echo "=== Сборка ChronoDash v2.2.6-beta AppImage ==="

rm -rf dist/ venv/ build/ AppDir/ *.spec *.AppImage

# 1. Создаём venv и ставим всё нужное
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install pyinstaller
pip install -r requirements.txt

# 2. PyInstaller
pyinstaller \
  --name ChronoDash \
  --onefile \
  --windowed \
  --icon="assets/icons/chronodash.png" \
  --add-data "assets:assets" \
  --add-data "core:core" \
  --add-data "widgets:widgets" \
  --hidden-import PySide6.QtSvg \
  --hidden-import PySide6.QtWidgets \
  --hidden-import PySide6.QtGui \
  --hidden-import PySide6.QtCore \
  --hidden-import PySide6.QtNetwork \
  main.py
deactivate

# 3. Готовим структуру AppDir
rm -rf AppDir
mkdir -p AppDir/usr/bin AppDir/usr/share/icons/hicolor/256x256/apps AppDir/usr/share/applications AppDir/usr/share/metainfo

# --- ИСПРАВЛЕНИЕ 1: Копируем бинарник с правильным именем ---
cp dist/ChronoDash AppDir/usr/bin/chronodash
chmod +x AppDir/usr/bin/chronodash

# --- ИСПРАВЛЕНИЕ 2: Создаем AppRun как симлинк на бинарник ---
# Это стандартный способ для AppImage: файл AppRun в корне запускает приложение
ln -s usr/bin/chronodash AppDir/AppRun

# Иконка
ICON_FOUND=false
# Ищем иконку (лучше брать png большого разрешения)
for icon in assets/icons/{logo,chronodash,app,icon}.png; do
  if [[ -f "$icon" ]]; then
    # Копируем в стандартное место
    cp "$icon" AppDir/usr/share/icons/hicolor/256x256/apps/chronodash.png
    # --- ИСПРАВЛЕНИЕ 3: Копируем иконку в корень AppDir (для appimagetool) ---
    cp "$icon" AppDir/chronodash.png
    ICON_FOUND=true
    break
  fi
done

if ! $ICON_FOUND; then
  echo "Предупреждение: иконка не найдена!"
fi

# MetaInfo (без изменений, кроме версии)
cat > AppDir/usr/share/metainfo/chronodash.metainfo.xml <<XML
<?xml version="1.0" encoding="UTF-8"?>
<component type="desktop-application">
  <id>chronodash.desktop</id>
  <metadata_license>CC0-1.0</metadata_license>
  <project_license>GPL-3.0-or-later</project_license>
  <name>ChronoDash</name>
  <summary>Customizable desktop widgets for Linux</summary>
  <description>
    <p>ChronoDash is a modern desktop widgets manager for Linux.</p>
  </description>
  <launchable type="desktop-id">chronodash.desktop</launchable>

  <releases>
    <release version="2.2.6-beta" date="$(date +%Y-%m-%d)"/>
  </releases>
</component>
XML

# --- ИСПРАВЛЕНИЕ 4: Правильный .desktop файл ---
cat > AppDir/chronodash.desktop << EOF
[Desktop Entry]
Type=Application
Version=1.5
Name=ChronoDash
GenericName=Desktop Widgets
Comment=Modern, customizable desktop widgets

# Exec указывает просто на имя файла (так как AppRun добавляет usr/bin в PATH)
Exec=chronodash
TryExec=chronodash

# Icon указывает ТОЛЬКО имя (без пути и расширения)
Icon=chronodash

Terminal=false
StartupNotify=true
Categories=Utility;System;
EOF

# 4. Собираем AppImage
# Используем ARCH=x86_64 чтобы инструмент не спрашивал архитектуру
ARCH=x86_64 appimagetool AppDir ChronoDash-2.2.6-beta-x86_64.AppImage

echo "Успешно! Попробуйте запустить: ./ChronoDash-2.2.6-beta-x86_64.AppImage"