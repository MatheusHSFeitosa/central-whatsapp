#!/bin/sh
set -eu
base=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
sh "$base/scripts/check-app-closed.sh"
# Só remove autostart identificado como pertencente à aplicação.
autostart="${XDG_CONFIG_HOME:-$HOME/.config}/autostart/central-whatsapp.desktop"
if [ -f "$autostart" ] && grep -q -x 'X-CentralWhatsApp-Managed=true' "$autostart" 2>/dev/null; then
    rm -f -- "$autostart"
fi
# Dados e sessões são preservados em central-whatsapp-data.
rm -f "$HOME/.local/bin/central-whatsapp" "$HOME/.local/share/applications/central-whatsapp.desktop" "$HOME/.local/share/icons/hicolor/scalable/apps/central-whatsapp.svg"
rm -rf -- "$HOME/.local/share/central-whatsapp"
if command -v update-desktop-database >/dev/null; then update-desktop-database "$HOME/.local/share/applications"; fi
echo 'Aplicativo removido. Sessões preservadas em ~/.local/share/central-whatsapp-data.'
