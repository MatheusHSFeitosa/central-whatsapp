#!/bin/sh
set -eu
base=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
sh "$base/scripts/check-app-closed.sh"
python3 "$base/scripts/prepare-cef.py"
dest="$HOME/.local/share/central-whatsapp"
mkdir -p "$dest" "$HOME/.local/bin" "$HOME/.local/share/applications" "$HOME/.local/share/icons/hicolor/scalable/apps"
runtime_python=$(python3 -c 'import os, sys; print(os.path.realpath(sys.executable))')
"$runtime_python" -m venv "$dest/runtime"
"$dest/runtime/bin/python" -m pip install -r "$base/requirements.txt"
mkdir -p "$dest/support/downloads"
if command -v apt-get >/dev/null && command -v dpkg-deb >/dev/null; then
    (cd "$dest/support/downloads" && apt-get download libxcb-cursor0 libnotify-bin)
    for package in "$dest/support/downloads/"*.deb; do dpkg-deb -x "$package" "$dest/support"; done
fi
mkdir -p "$dest/ui-icons"
install -m644 "$base/ui-icons/"* "$dest/ui-icons/"
mkdir -p "$dest/service-icons"
install -m644 "$base/service-icons/"* "$dest/service-icons/"
mkdir -p "$dest/cef-runtime"
cp -a "$base/build/cef-runtime/." "$dest/cef-runtime"/
install -m644 "$base/split_workspace.py" "$base/window_chrome.py" "$base/cef_engine.py" "$base/cef_storage.py" "$base/ui_widgets.py" "$base/desktop_notifications.py" "$base/central.py" "$base/profile_store.py" "$base/settings_store.py" "$base/desktop_ui.py" "$base/avatar_manager.py" "$base/services.py" "$base/grouping.py" "$base/VERSION" "$base/whatsapp-web.svg" "$base/check-symbolic.svg" "$dest/"
cat > "$HOME/.local/bin/central-whatsapp" <<'LAUNCH'
#!/bin/sh
export LD_LIBRARY_PATH="$HOME/.local/share/central-whatsapp/support/usr/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-xcb}"
export PATH="$HOME/.local/share/central-whatsapp/support/usr/bin:$PATH"
exec "$HOME/.local/share/central-whatsapp/runtime/bin/python" "$HOME/.local/share/central-whatsapp/central.py" "$@"
LAUNCH
chmod 755 "$HOME/.local/bin/central-whatsapp"
sed "s|Exec=central-whatsapp|Exec=\"$HOME/.local/bin/central-whatsapp\"|" "$base/packaging/central-whatsapp.desktop" > "$HOME/.local/share/applications/central-whatsapp.desktop"
install -m644 "$base/whatsapp-web.svg" "$HOME/.local/share/icons/hicolor/scalable/apps/central-whatsapp.svg"
if command -v update-desktop-database >/dev/null; then update-desktop-database "$HOME/.local/share/applications"; fi
echo 'Central Chats instalada. Abra pelo menu.'
