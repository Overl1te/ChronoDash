#!/bin/bash
set -e

# === НАСТРОЙКИ ===
APP_NAME="chronodash"
VERSION="2.2.1"
EMAIL="Overl1teGithub@yandex.ru"
PPA_TARGET="chronodash-ppa" # Имя из ~/.dput.cf
# =================

# Цвета для вывода
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

function show_help {
    echo -e "${BLUE}Использование:${NC}"
    echo "  ./build_deb.sh release   -> Собрать бинарный .deb (PyInstaller) для GitHub/Debian"
    echo "  ./build_deb.sh ppa       -> Собрать source package и отправить на Launchpad PPA"
    echo "  ./build_deb.sh clean     -> Очистить временные файлы"
}

function clean_all {
    echo -e "${BLUE}[Clean] Удаление временных файлов...${NC}"
    rm -rf dist build pkg *.deb *.spec venv *.egg-info
    # Не удаляем папку debian/, она нужна для PPA!
    rm -rf ../${APP_NAME}_* # Удаляем старые файлы сборки уровнем выше
}

function build_release {
    echo -e "${GREEN}=== СБОРКА RELEASE (BINARY .DEB) ===${NC}"
    clean_all

    echo -e "${BLUE}[1/5] Подготовка venv...${NC}"
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt pyinstaller

    echo -e "${BLUE}[2/5] Компиляция PyInstaller...${NC}"
    pyinstaller --noconfirm --onedir --windowed --clean \
        --name "$APP_NAME" \
        --icon "assets/icons/chronodash.png" \
        --add-data "assets:assets" \
        --add-data "core:core" \
        --add-data "widgets:widgets" \
        --add-data "dashboard:dashboard" \
        --hidden-import "PIL._tkinter_finder" \
        main.py

    echo -e "${BLUE}[3/5] Структура пакета...${NC}"
    mkdir -p pkg/DEBIAN pkg/opt/$APP_NAME pkg/usr/bin
    mkdir -p pkg/usr/share/applications pkg/usr/share/icons/hicolor/64x64/apps

    # Копируем файлы
    cp -r dist/$APP_NAME/* pkg/opt/$APP_NAME/
    cp assets/icons/chronodash.png pkg/usr/share/icons/hicolor/64x64/apps/$APP_NAME.png

    echo -e "${BLUE}[4/5] Генерация метаданных...${NC}"
    
    # 1. Launcher
    cat > pkg/usr/bin/$APP_NAME <<EOF
#!/bin/sh
exec /opt/$APP_NAME/$APP_NAME "\$@"
EOF
    chmod +x pkg/usr/bin/$APP_NAME

    # 2. Desktop file
    cat > pkg/usr/share/applications/$APP_NAME.desktop <<EOF
[Desktop Entry]
Type=Application
Version=$VERSION
Name=ChronoDash
Comment=Desktop Widgets
Exec=/usr/bin/$APP_NAME
Icon=$APP_NAME
Terminal=false
Categories=Utility;
EOF

    # 3. Control file (БЕЗ зависимостей Python, так как все вшито!)
    cat > pkg/DEBIAN/control <<EOF
Package: $APP_NAME
Version: $VERSION
Section: utils
Priority: optional
Architecture: amd64
Maintainer: Overl1te <$EMAIL>
Depends: libc6, libgl1, libx11-6
Description: ChronoDash Desktop Widgets (Standalone)
 Standalone version with bundled dependencies.
EOF
    
    chmod -R 755 pkg/DEBIAN pkg/opt/$APP_NAME pkg/usr/bin

    echo -e "${BLUE}[5/5] Сборка .deb...${NC}"
    DEB_NAME="${APP_NAME}_${VERSION}_amd64.deb"
    dpkg-deb --build pkg "$DEB_NAME"
    
    echo -e "${GREEN}✅ ГОТОВО! Файл: $DEB_NAME${NC}"
    echo "Установка: sudo dpkg -i $DEB_NAME"
}

function build_ppa {
    echo -e "${GREEN}=== ОТПРАВКА В PPA (SOURCE PACKAGE) ===${NC}"
    
    # Проверка наличия папки debian/
    if [ ! -d "debian" ]; then
        echo -e "${RED}ОШИБКА: Нет папки debian/ в корне репозитория!${NC}"
        echo "Для PPA нужны файлы debian/control, debian/rules и т.д."
        exit 1
    fi

    # Очистка мусора от PyInstaller, чтобы он не попал в исходники
    clean_all

    echo -e "${BLUE}[1/3] Сборка Source Package (игнорируя зависимости системы)...${NC}"
    # -S: только исходники
    # -sa: включать orig.tar.gz
    # -d: не проверять зависимости сборки (критично для вашего Debian!)
    debuild -S -sa -d --no-lintian

    echo -e "${BLUE}[2/3] Поиск файла .changes...${NC}"
    cd ..
    CHANGES_FILE=$(ls ${APP_NAME}_*source.changes | tail -n 1)
    
    if [ -z "$CHANGES_FILE" ]; then
        echo -e "${RED}ОШИБКА: Файл .changes не найден! Сборка не удалась?${NC}"
        exit 1
    fi

    echo -e "${BLUE}[3/3] Отправка $CHANGES_FILE в $PPA_TARGET...${NC}"
    dput $PPA_TARGET $CHANGES_FILE
    
    echo -e "${GREEN}✅ УСПЕШНО ОТПРАВЛЕНО!${NC}"
    echo "Проверьте статус на Launchpad через 10-20 минут."
    cd $APP_NAME # Возвращаемся в папку
}

# === МЕНЮ ===
case "$1" in
    release)
        build_release
        ;;
    ppa)
        build_ppa
        ;;
    clean)
        clean_all
        ;;
    *)
        show_help
        exit 1
        ;;
esac