#!/bin/bash
echo "Starting compilation"
rm -rf *.deb *.spec  # Без sudo
rm -rf pkg build dist
echo "Installing dependencies"

python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt pyinstaller

# 5. Собираем директорией через PyInstaller (без --onefile)
echo "Compress as onedir"
pyinstaller \
  --name chronodash \
  --add-data "assets:assets" \
  --add-data "widgets:widgets" \
  --windowed \
  --icon=assets/icon.ico \
  main.py
echo "Compress done"

# 6. Теперь упаковываем в .deb с помощью fpm
echo "Making an archive"
echo "Preparing"
mkdir -p pkg/opt/chronodash pkg/usr/bin pkg/usr/share/applications pkg/usr/share/icons/hicolor/256x256/apps pkg/usr/share/metainfo

# Копируем директорию в /opt/ (стандартно для проприетарных/самосборных приложений)
cp -r dist/chronodash/* pkg/opt/chronodash/

# Создаём launcher в /usr/bin/ для удобного запуска
cat > pkg/usr/bin/chronodash <<EOF
#!/bin/sh
exec /opt/chronodash/chronodash "\$@"
EOF
chmod +x pkg/usr/bin/chronodash

# Иконка (замени путь, если chronodash.png нет в assets/icons/ — например, на assets/icon.png)
cp assets/icons/chronodash.png pkg/usr/share/icons/hicolor/256x256/apps/chronodash.png

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

# Создаём .desktop-файл
cat > pkg/usr/share/applications/chronodash.desktop <<EOF
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
EOF
echo "Prepare done"

# 7. Создаём .deb
echo "Making deb file"
fpm -s dir -t deb \
  -n chronodash \
  -v 2.2.1-beta \
  --iteration 1 \
  --license "GPL-3.0" \
  --description "Transparent always-on-top desktop widgets (clocks and more)" \
  --maintainer "Overl1te Overl1teGithub@yandex.ru" \
  -C pkg \
  opt/ usr/

echo "Successful!"