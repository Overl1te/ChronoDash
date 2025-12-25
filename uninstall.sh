#!/bin/bash
# Удаление ChronoDash с Arch Linux

set -e

echo "=== Удаление ChronoDash ==="

# Подтверждение
read -p "Вы уверены, что хотите удалить ChronoDash? [y/N]: " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Удаление отменено"
    exit 0
fi

echo "Удаление файлов..."

# Удаляем системные файлы
sudo rm -rf /opt/ChronoDash
sudo rm -f /usr/bin/chronodash
sudo rm -f /usr/bin/chronodash-debug
sudo rm -f /usr/share/applications/chronodash.desktop
sudo rm -f /usr/share/icons/hicolor/64x64/apps/chronodash.png

echo "Очистка кэша иконок..."
sudo gtk-update-icon-cache /usr/share/icons/hicolor/ 2>/dev/null || true

echo ""
echo "✅ ChronoDash удален"
echo ""
echo "=== ОСТАВШИЕСЯ ФАЙЛЫ (ручное удаление) ==="
echo "  Конфигурация:   ~/.config/chronodash/"
echo "  Кэш:            ~/.cache/chronodash/"
echo "  Логи:           ~/.local/share/chronodash/"
echo ""
echo "Для полного удаления:"
echo "  rm -rf ~/.config/chronodash ~/.cache/chronodash ~/.local/share/chronodash"