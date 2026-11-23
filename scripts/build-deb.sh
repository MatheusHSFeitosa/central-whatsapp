#!/bin/sh
set -eu
base=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
version=$(cat "$base/VERSION")
case "$version" in ""|*[!0-9.]*) echo "VERSION inválida" >&2; exit 1;; esac
stage="$base/build/deb"
rm -rf -- "$stage"
mkdir -p "$stage/DEBIAN" "$stage/opt/central-whatsapp/lib" "$stage/usr/bin" "$stage/usr/share/applications" "$stage/usr/share/icons/hicolor/scalable/apps" "$base/dist"
if [ -n "${CENTRAL_PYTHON_LIB:-}" ]; then
    cp -a "$CENTRAL_PYTHON_LIB/PySide6" "$CENTRAL_PYTHON_LIB/shiboken6" "$CENTRAL_PYTHON_LIB/dbus_next" "$stage/opt/central-whatsapp/lib/"
else
    python3 -m venv "$base/build/build-env"
    "$base/build/build-env/bin/python" -m pip install --target "$stage/opt/central-whatsapp/lib" -r "$base/requirements.txt"
fi
mkdir -p "$stage/opt/central-whatsapp/ui-icons"
install -m644 "$base/ui-icons/"* "$stage/opt/central-whatsapp/ui-icons/"
mkdir -p "$stage/opt/central-whatsapp/service-icons"
install -m644 "$base/service-icons/"* "$stage/opt/central-whatsapp/service-icons/"
python3 "$base/scripts/prepare-cef.py"
mkdir -p "$stage/opt/central-whatsapp/cef-runtime"
cp -a "$base/build/cef-runtime/." "$stage/opt/central-whatsapp/cef-runtime"/
install -m644 "$base/split_workspace.py" "$base/window_chrome.py" "$base/cef_engine.py" "$base/cef_storage.py" "$base/ui_widgets.py" "$base/desktop_notifications.py" "$base/central.py" "$base/profile_store.py" "$base/settings_store.py" "$base/desktop_ui.py" "$base/avatar_manager.py" "$base/services.py" "$base/grouping.py" "$base/VERSION" "$base/whatsapp-web.svg" "$base/check-symbolic.svg" "$stage/opt/central-whatsapp/"
install -m644 "$base/packaging/central-whatsapp.desktop" "$stage/usr/share/applications/"
install -m644 "$base/whatsapp-web.svg" "$stage/usr/share/icons/hicolor/scalable/apps/central-whatsapp.svg"
cat > "$stage/usr/bin/central-whatsapp" <<'LAUNCH'
#!/bin/sh
export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-xcb}"
export PYTHONPATH="/opt/central-whatsapp/lib${PYTHONPATH:+:$PYTHONPATH}"
exec /usr/bin/python3 /opt/central-whatsapp/central.py "$@"
LAUNCH
chmod 755 "$stage/usr/bin/central-whatsapp"
cat > "$stage/DEBIAN/control" <<CONTROL
Package: central-whatsapp
Version: $version
Section: net
Priority: optional
Architecture: amd64
Maintainer: Central Chats contributors
Depends: python3 (>= 3.10), python3 (<< 3.13), libx11-xcb1, libxcb-shape0, libxcb-cursor0, libxcb-icccm4, libxcb-image0, libxcb-keysyms1, libxcb-render-util0, libxcb-xinerama0, libxcb-xkb1, libxkbcommon-x11-0, libnss3, libnspr4, libasound2 | libasound2t64, libdbus-1-3, libegl1, libgl1, libgbm1, libxcomposite1, libxdamage1, libxrandr2, libxtst6, libfontconfig1, libnotify-bin, libglib2.0-0 | libglib2.0-0t64
Description: Central de perfis independentes de conversas
 WhatsApp Web, Telegram e Chatwoot na mesma janela.
 Aplicativo comunitario sem afiliacao com os servicos integrados.
 CEF Chromium integrado e armazenamento separado por perfil.
CONTROL
# The shipped application uses CEF. Keep Qt GUI modules and omit the unused
# Qt browser from full development installations passed via CENTRAL_PYTHON_LIB.
rm -f "$stage/opt/central-whatsapp/lib/PySide6/QtWebEngineCore.abi3.so" "$stage/opt/central-whatsapp/lib/PySide6/QtWebEngineWidgets.abi3.so" "$stage/opt/central-whatsapp/lib/PySide6/QtWebEngineQuick.abi3.so"
rm -f "$stage/opt/central-whatsapp/lib/PySide6/Qt/lib/"libQt6WebEngine*.so.6 "$stage/opt/central-whatsapp/lib/PySide6/Qt/libexec/QtWebEngineProcess"
rm -f "$stage/opt/central-whatsapp/lib/PySide6/Qt/resources/"qtwebengine* "$stage/opt/central-whatsapp/lib/PySide6/Qt/resources/"v8_context_snapshot.bin
rm -rf "$stage/opt/central-whatsapp/lib/PySide6/Qt/translations/qtwebengine_locales"
mkdir -p "$stage/usr/share/doc/central-whatsapp"
install -m644 "$base/LICENSE" "$base/README.md" "$base/CREDITS.md" "$stage/usr/share/doc/central-whatsapp/"
size=$(du -sk "$stage/opt" | cut -f1)
printf 'Installed-Size: %s\n' "$size" >> "$stage/DEBIAN/control"
dpkg-deb --root-owner-group -Zzstd -z3 --build "$stage" "$base/dist/central-whatsapp_${version}_amd64.deb"
