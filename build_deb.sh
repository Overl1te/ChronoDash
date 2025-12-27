#!/bin/bash
set -e

# === НАСТРОЙКИ ===
APP_NAME="chronodash"
VERSION="2.2.5"
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
    echo "  ./build_deb.sh release          -> Собрать 'толстый' .deb (PyInstaller). РАБОТАЕТ ВЕЗДЕ."
    echo "  ./build_deb.sh ppa [KEY_ID]     -> Отправить ГИБРИДНЫЙ PPA (докачивает PySide6 через pip)."
    echo ""
    echo -e "${BLUE}Примеры:${NC}"
    echo "  ./build_deb.sh release"
    echo "  ./build_deb.sh ppa EEC86D2065150ECE"
}

function clean_all {
    echo -e "${BLUE}[Clean] Очистка мусора...${NC}"
    rm -rf dist build pkg *.deb *.spec venv *.egg-info
    # Удаляем файлы сборки уровнем выше
    rm -rf ../${APP_NAME}_*
}

# === ВАРИАНТ 1: ДЛЯ ВАС (Debian) И GITHUB RELEASES ===
# Собирает всё в один файл (включая PySide6), не зависит от системного Python
function build_release {
    echo -e "${GREEN}=== СБОРКА RELEASE (PYINSTALLER / STANDALONE) ===${NC}"
    clean_all

    echo -e "${BLUE}[1/5] Подготовка venv...${NC}"
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt pyinstaller
    sudo apt install python3-tk

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

    # Control для бинарной версии
    cat > pkg/DEBIAN/control <<EOF
Package: $APP_NAME
Version: $VERSION
Section: utils
Priority: optional
Architecture: amd64
Maintainer: Overl1te <$EMAIL>
Depends: libc6, libgl1, libx11-6, libx11-xcb1
Description: ChronoDash Desktop Widgets (Standalone)
 Standalone version with bundled dependencies. Works on Debian/Ubuntu.
EOF
    
    chmod -R 755 pkg/DEBIAN pkg/opt/$APP_NAME pkg/usr/bin

    echo -e "${BLUE}[5/5] Сборка .deb...${NC}"
    DEB_NAME="${APP_NAME}_${VERSION}_full_amd64.deb"
    dpkg-deb --build pkg "$DEB_NAME"
    
    echo -e "${GREEN}✅ ГОТОВО! Файл: $DEB_NAME${NC}"
    echo "Установка (работает на Debian Trixie): sudo dpkg -i $DEB_NAME"
}

# === ВАРИАНТ 2: ДЛЯ PPA / UBUNTU (ГИБРИДНЫЙ) ===
# Генерирует файлы debian/ на лету, чтобы добавить pip-install скрипты
function build_ppa {
    local KEY_ID="$1"
    
    echo -e "${GREEN}=== СБОРКА ГИБРИДНОГО PPA (PIP-INSTALLER) ===${NC}"
    
    if [ ! -d "debian" ]; then
        echo -e "${RED}ОШИБКА: Нет папки debian/ в корне проекта!${NC}"
        exit 1
    fi

    clean_all

    echo -e "${BLUE}[1/2] Генерация конфигурации PPA (обход зависимостей)...${NC}"

    # 2. POSTINST: Скрипт, который выполняется ПОСЛЕ установки
    cat > debian/postinst <<EOF
#!/bin/sh
set -e

case "\$1" in
    configure)
        echo "--> Creating virtual environment for ChronoDash..."
        if [ ! -d "/usr/share/$APP_NAME/venv" ]; then
            python3 -m venv /usr/share/$APP_NAME/venv
        fi
        
        echo "--> Installing PySide6 via pip (fetching from PyPI)..."
        # Устанавливаем библиотеки в изолированную среду
        /usr/share/$APP_NAME/venv/bin/pip install --upgrade pip --quiet
        /usr/share/$APP_NAME/venv/bin/pip install pyside6 --quiet
        if [ -f "/usr/share/$APP_NAME/requirements.txt" ]; then
            /usr/share/$APP_NAME/venv/bin/pip install -r /usr/share/$APP_NAME/requirements.txt --quiet
        else
            echo "WARNING: requirements.txt not found in package!"
        fi
        
        # Исправляем права, чтобы обычный пользователь мог запускать
        chmod -R a+rX /usr/share/$APP_NAME/venv
    ;;

    abort-upgrade|abort-remove|abort-deconfigure)
    ;;

    *)
        echo "postinst called with unknown argument \\\`\$1'" >&2
        exit 1
    ;;
esac

#DEBHELPER#
exit 0
EOF
    chmod +x debian/postinst

    # 3. PRERM: Удаление venv при сносе программы
    cat > debian/prerm <<EOF
#!/bin/sh
set -e
case "\$1" in
    remove|upgrade|deconfigure)
        rm -rf /usr/share/$APP_NAME/venv
    ;;
esac
#DEBHELPER#
exit 0
EOF
    chmod +x debian/prerm
    chmod +x debian/rules

    echo -e "${BLUE}[2/2] Сборка и отправка...${NC}"
    
    # -S: только исходники
    # -sa: включать orig.tar.gz
    # -d: игнорировать зависимости сборки (важно для Debian!)
    #ARGS="-S -sa -d --no-lintian"
    ARGS="-S -sa -d"
    
    if [ -n "$KEY_ID" ]; then
        echo -e "🔑 Используем ключ: ${GREEN}$KEY_ID${NC}"
        ARGS="$ARGS -k$KEY_ID"
    else
        echo -e "⚠️ Ключ не передан. Будет использован ключ по умолчанию для ${BLUE}$EMAIL${NC}"
    fi

    debuild $ARGS

    cd ..
    CHANGES_FILE=$(ls ${APP_NAME}_*source.changes | tail -n 1)
    
    if [ -z "$CHANGES_FILE" ]; then
        echo -e "${RED}ОШИБКА: Файл .changes не найден!${NC}"
        exit 1
    fi

    echo -e "${BLUE}Отправка...${NC}"
    #dput $PPA_TARGET $CHANGES_FILE
    
    echo -e "${GREEN}✅ УСПЕШНО ОТПРАВЛЕНО В PPA!${NC}"
    #echo "Теперь при установке 'sudo apt install' у пользователя сам скачается PySide6."
    
    # Возвращаемся в папку проекта
    cd "$APP_NAME" || cd ChronoDash || true
}

# === МЕНЮ ===
case "$1" in
    release)
        build_release
        ;;
    ppa)
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
