#!/bin/bash
set -e

# === НАСТРОЙКИ ===
APP_NAME="chronodash"
VERSION="2.2.8" # Поднял версию
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
    echo "  ./build_deb.sh release          -> Собрать 'толстый' .deb (PyInstaller)."
    echo "  ./build_deb.sh ppa [KEY_ID]     -> Отправить ГИБРИДНЫЙ PPA (venv + pip)."
}

function clean_all {
    echo -e "${BLUE}[Clean] Очистка мусора...${NC}"
    rm -rf dist build pkg *.deb *.spec venv *.egg-info
    # Удаляем файлы сборки уровнем выше
    rm -rf ../${APP_NAME}_*
}

# === ВАРИАНТ 1: RELEASE (PyInstaller) ===
function build_release {
    echo -e "${GREEN}=== СБОРКА RELEASE (PYINSTALLER / STANDALONE) ===${NC}"
    clean_all

    echo -e "${BLUE}[1/5] Подготовка venv...${NC}"
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt pyinstaller
    
    # Проверка tk
    if ! dpkg -s python3-tk >/dev/null 2>&1; then
        echo "Предупреждение: python3-tk не найден, ставим..."
        sudo apt install -y python3-tk
    fi

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

    # Лаунчер для Release версии
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
}

# === ВАРИАНТ 2: PPA (ГИБРИДНЫЙ) ===
function build_ppa {
    local KEY_ID="$1"
    
    echo -e "${GREEN}=== СБОРКА ГИБРИДНОГО PPA (venv + pip) ===${NC}"
    
    # Создаем папку debian если нет
    mkdir -p debian

    clean_all

    echo -e "${BLUE}[1/2] Генерация конфигурации PPA...${NC}"

    # 1. CONTROL (БЫЛО ПРОПУЩЕНО)
    cat > debian/control <<EOF
Source: $APP_NAME
Section: utils
Priority: optional
Maintainer: Overl1te <$EMAIL>
Build-Depends: debhelper-compat (= 13), python3-all, dh-python
Standards-Version: 4.6.2
Homepage: https://github.com/Overl1te/ChronoDash

Package: $APP_NAME
Architecture: all
Depends: \${python3:Depends}, \${misc:Depends}, python3-pip, python3-venv, python3-tk, libgl1
Description: ChronoDash Desktop Widgets
 Application for tracking time.
 NOTE: This package will download dependencies via pip into /usr/share/$APP_NAME/venv during installation.
EOF

    # 2. POSTINST
    cat > debian/postinst <<EOF
#!/bin/sh
set -e

case "\$1" in
    configure)
        echo "--> Creating virtual environment for ChronoDash..."
        # Убедимся, что родительская папка существует
        mkdir -p /usr/share/$APP_NAME
        
        if [ ! -d "/usr/share/$APP_NAME/venv" ]; then
            python3 -m venv /usr/share/$APP_NAME/venv
        fi
        
        echo "--> Installing dependencies via pip..."
        /usr/share/$APP_NAME/venv/bin/pip install --upgrade pip --quiet
        
        # Если есть requirements.txt, ставим из него
        if [ -f "/usr/share/$APP_NAME/requirements.txt" ]; then
            echo "Installing from requirements.txt..."
            # --break-system-packages нужен для pip в последних версиях, даже в venv бывает полезен
            /usr/share/$APP_NAME/venv/bin/pip install -r /usr/share/$APP_NAME/requirements.txt --quiet --break-system-packages || /usr/share/$APP_NAME/venv/bin/pip install -r /usr/share/$APP_NAME/requirements.txt --quiet
        else
            echo "WARNING: requirements.txt not found! Installing base set..."
            /usr/share/$APP_NAME/venv/bin/pip install PySide6 customtkinter Pillow requests --quiet
        fi
        
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

    # 3. PRERM
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

    # 4. INSTALL (БЫЛО ПРОПУЩЕНО - КРИТИЧНО!)
    # Без этого файла папка /usr/share/chronodash/ пуста!
    cat > debian/install <<EOF
requirements.txt usr/share/$APP_NAME/
main.py usr/share/$APP_NAME/
core/ usr/share/$APP_NAME/
widgets/ usr/share/$APP_NAME/
dashboard/ usr/share/$APP_NAME/
assets/ usr/share/$APP_NAME/
debian/$APP_NAME.desktop usr/share/applications/
assets/icons/chronodash.png usr/share/icons/hicolor/64x64/apps/
EOF

    # 5. RULES
    cat > debian/rules <<MAKE
#!/usr/bin/make -f

%:
	dh \$@ --with python3

override_dh_auto_build:
	true

override_dh_auto_install:
	true

override_dh_install:
	dh_install
	mkdir -p debian/$APP_NAME/usr/bin
	# ВАЖНО: Мы прописываем путь к python внутри venv!
	echo '#!/bin/sh' > debian/$APP_NAME/usr/bin/$APP_NAME
	echo 'exec /usr/share/$APP_NAME/venv/bin/python3 /usr/share/$APP_NAME/main.py "\$\$@"' >> debian/$APP_NAME/usr/bin/$APP_NAME
	chmod +x debian/$APP_NAME/usr/bin/$APP_NAME
MAKE
    chmod +x debian/rules

    echo -e "${BLUE}[2/2] Сборка и отправка...${NC}"
    
    ARGS="-S -sa -d"
    
    if [ -n "$KEY_ID" ]; then
        echo -e "🔑 Используем ключ: ${GREEN}$KEY_ID${NC}"
        ARGS="$ARGS -k$KEY_ID"
    else
        echo -e "⚠️ Ключ не передан."
    fi

    debuild $ARGS

    cd ..
    CHANGES_FILE=$(ls ${APP_NAME}_*source.changes | tail -n 1)
    
    if [ -z "$CHANGES_FILE" ]; then
        echo -e "${RED}ОШИБКА: Файл .changes не найден!${NC}"
        exit 1
    fi

    echo -e "${BLUE}Отправка...${NC}"
    dput $PPA_TARGET $CHANGES_FILE
    
    echo -e "${GREEN}✅ УСПЕШНО ОТПРАВЛЕНО В PPA!${NC}"
    cd "$APP_NAME" || cd ChronoDash || true
}

case "$1" in
    release) build_release ;;
    ppa) build_ppa "$2" ;;
    clean) clean_all ;;
    *) show_help; exit 1 ;;
esac