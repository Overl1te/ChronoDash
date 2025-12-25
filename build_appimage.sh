#!/usr/bin/env bash
# set -euo pipefail

echo "=== Сборка ChronoDash v2.2.0-beta AppImage ==="

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
mkdir -p AppDir/usr/bin AppDir/usr/share/icons/hicolor/64x64/apps AppDir/usr/share/applications

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

# .desktop файл
cat > AppDir/chronodash.desktop << EOF
[Desktop Entry]
Name=ChronoDash
Comment=Transparent always-on-top desktop widgets manager
Exec=AppRun
Icon=/usr/share/icons/hicolor/64x64/apps/chronodash
Terminal=false
Type=Application
Categories=Utility;System;
StartupNotify=true
EOF

# 4. Собираем AppImage
appimagetool AppDir ChronoDash-2.2.0-beta-x86_64.AppImage

echo "Успешно"