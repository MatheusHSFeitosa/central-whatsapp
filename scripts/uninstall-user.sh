#!/bin/sh
set -eu
# Dados e sessões são preservados em central-whatsapp-data.
rm -f "$HOME/.local/bin/central-whatsapp" "$HOME/.local/share/applications/central-whatsapp.desktop" "$HOME/.local/share/icons/hicolor/scalable/apps/central-whatsapp.svg"
rm -rf -- "$HOME/.local/share/central-whatsapp"
if command -v update-desktop-database >/dev/null; then update-desktop-database "$HOME/.local/share/applications"; fi
echo 'Aplicativo removido. Sessões preservadas em ~/.local/share/central-whatsapp-data.'
