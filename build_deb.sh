#!/bin/bash
set -e

# === НАСТРОЙКИ ===
APP_NAME="chronodash"
VERSION="2.2.1"
EMAIL="Overl1teGithub@yandex.ru"
PPA_TARGET="chronodash-ppa"
# =================

# Цвета для вывода
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

function show_help {
    echo -e "${BLUE}Использование:${NC}"
    echo "  ./build_deb.sh release          -> Собрать бинарный .deb (PyInstaller)"
    echo "  ./build_deb.sh ppa [KEY_ID]     -> Отправить в PPA (можно указать ID ключа)"
    echo ""
    echo -e "${BLUE}Примеры:${NC}"
    echo "  ./build_deb.sh ppa              -> Авто-поиск ключа по email"
    echo "  ./build_deb.sh ppa 3AA5C343...  -> Использовать конкретный ключ"
}

function clean_all {
    echo -e "${BLUE}[Clean] Очистка...${NC}"
    rm -rf dist build pkg *.deb *.spec venv *.egg-info
    # Удаляем файлы сборки уровнем выше, но оставляем debian/ внутри
    rm -rf ../${APP_NAME}_* }
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

    cp -r dist/$APP_NAME/* pkg/opt/$APP_NAME/
    cp assets/icons/chronodash.png pkg/usr/share/icons/hicolor/64x64/apps/$APP_NAME.png

    echo -e "${BLUE}[4/5] Метаданные...${NC}"
    
    cat > pkg/usr/bin/$APP_NAME <<EOF
#!/bin/sh
exec /opt/$APP_NAME/$APP_NAME "\$@"
EOF
    chmod +x pkg/usr/bin/$APP_NAME

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

    # Control для бинарной версии (БЕЗ зависимости от python3-pyside6)
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
}

function build_ppa {
    local KEY_ID="$1" # Получаем аргумент ключа
    
    echo -e "${GREEN}=== ОТПРАВКА В PPA (SOURCE PACKAGE) ===${NC}"
    
    if [ ! -d "debian" ]; then
        echo -e "${RED}ОШИБКА: Нет папки debian/!${NC}"
        exit 1
    fi

    clean_all

    echo -e "${BLUE}[1/3] Сборка Source Package...${NC}"
    
    # -S: только исходники
    # -sa: включать orig.tar.gz
    # -d: игнорировать отсутствие зависимостей (важно для Debian)
    ARGS="-S -sa -d --no-lintian"
    
    if [ -n "$KEY_ID" ]; then
        echo -e "🔑 Используем ключ: ${GREEN}$KEY_ID${NC}"
        ARGS="$ARGS -k$KEY_ID"
    else
        echo -e "⚠️ Ключ не передан. Будет использован ключ по умолчанию для ${BLUE}$EMAIL${NC}"
    fi

    # Запуск debuild
    debuild $ARGS

    echo -e "${BLUE}[2/3] Поиск файла .changes...${NC}"
    cd ..
    CHANGES_FILE=$(ls ${APP_NAME}_*source.changes | tail -n 1)
    
    if [ -z "$CHANGES_FILE" ]; then
        echo -e "${RED}ОШИБКА: Файл .changes не найден!${NC}"
        exit 1
    fi

    echo -e "${BLUE}[3/3] Отправка...${NC}"
    dput $PPA_TARGET $CHANGES_FILE
    
    echo -e "${GREEN}✅ УСПЕШНО ОТПРАВЛЕНО!${NC}"
    cd $APP_NAME
}

# === МЕНЮ ===
case "$1" in
    release)
        build_release
        ;;
    ppa)
        # Передаем второй аргумент (ключ) в функцию
        build_ppa "$2"
        ;;
    clean)
        clean_all
        ;;
    *)
        show_help
        exit 1
        ;;
esac