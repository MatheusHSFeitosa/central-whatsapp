#!/bin/sh
set -eu
echo "A migração CEF 0.12 ainda não foi validada no isolamento do Flatpak. Use a instalação local ou DEB em X11/XWayland." >&2
exit 1
base=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
version=$(cat "$base/VERSION")
cd "$base"
flatpak-builder --user --install-deps-from=flathub --force-clean --repo=build/flatpak-repo build/flatpak packaging/io.github.MatheusHSFeitosa.CentralWhatsApp.json
mkdir -p dist
flatpak build-bundle build/flatpak-repo dist/central-whatsapp_${version}_x86_64.flatpak io.github.MatheusHSFeitosa.CentralWhatsApp
