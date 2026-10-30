#!/bin/sh
set -eu
base=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
sh "$base/scripts/check-app-closed.sh"
dest="$HOME/.local/share/central-whatsapp"
mkdir -p "$dest" "$HOME/.local/bin" "$HOME/.local/share/applications" "$HOME/.local/share/icons/hicolor/scalable/apps"
python3 -m venv "$dest/runtime"
"$dest/runtime/bin/python" -m pip install -r "$base/requirements.txt"
mkdir -p "$dest/support/downloads"
if command -v apt-get >/dev/null && command -v dpkg-deb >/dev/null; then
    (cd "$dest/support/downloads" && apt-get download libxcb-cursor0 libnotify-bin)
    for package in "$dest/support/downloads/"*.deb; do dpkg-deb -x "$package" "$dest/support"; done
fi
install -m644 "$base/central.py" "$base/profile_store.py" "$base/settings_store.py" "$base/desktop_ui.py" "$base/avatar_manager.py" "$base/VERSION" "$base/whatsapp-web.svg" "$dest/"
cat > "$HOME/.local/bin/central-whatsapp" <<'LAUNCH'
#!/bin/sh
export LD_LIBRARY_PATH="$HOME/.local/share/central-whatsapp/support/usr/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export PATH="$HOME/.local/share/central-whatsapp/support/usr/bin:$PATH"
exec "$HOME/.local/share/central-whatsapp/runtime/bin/python" "$HOME/.local/share/central-whatsapp/central.py" "$@"
LAUNCH
chmod 755 "$HOME/.local/bin/central-whatsapp"
sed "s|Exec=central-whatsapp|Exec=\"$HOME/.local/bin/central-whatsapp\"|" "$base/packaging/central-whatsapp.desktop" > "$HOME/.local/share/applications/central-whatsapp.desktop"
install -m644 "$base/whatsapp-web.svg" "$HOME/.local/share/icons/hicolor/scalable/apps/central-whatsapp.svg"
if command -v update-desktop-database >/dev/null; then update-desktop-database "$HOME/.local/share/applications"; fi
echo 'Central WhatsApp instalada. Abra pelo menu.'
