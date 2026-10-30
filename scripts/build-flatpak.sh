#!/bin/sh
set -eu
base=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
version=$(cat "$base/VERSION")
cd "$base"
flatpak-builder --user --install-deps-from=flathub --force-clean --repo=build/flatpak-repo build/flatpak packaging/io.github.MatheusHSFeitosa.CentralWhatsApp.json
mkdir -p dist
flatpak build-bundle build/flatpak-repo dist/central-whatsapp_${version}_x86_64.flatpak io.github.MatheusHSFeitosa.CentralWhatsApp
