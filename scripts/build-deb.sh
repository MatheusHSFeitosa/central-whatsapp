#!/bin/sh
set -eu
base=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
stage="$base/build/deb"
mkdir -p "$stage/DEBIAN" "$stage/opt/central-whatsapp/lib" "$stage/usr/bin" "$stage/usr/share/applications" "$stage/usr/share/icons/hicolor/scalable/apps" "$base/dist"
if [ -n "${CENTRAL_PYTHON_LIB:-}" ]; then
    cp -a "$CENTRAL_PYTHON_LIB/PySide6" "$CENTRAL_PYTHON_LIB/shiboken6" "$stage/opt/central-whatsapp/lib/"
else
    python3 -m venv "$base/build/build-env"
    "$base/build/build-env/bin/python" -m pip install --target "$stage/opt/central-whatsapp/lib" -r "$base/requirements.txt"
fi
install -m644 "$base/central.py" "$base/whatsapp-web.svg" "$stage/opt/central-whatsapp/"
install -m644 "$base/packaging/central-whatsapp.desktop" "$stage/usr/share/applications/"
install -m644 "$base/whatsapp-web.svg" "$stage/usr/share/icons/hicolor/scalable/apps/central-whatsapp.svg"
cat > "$stage/usr/bin/central-whatsapp" <<'LAUNCH'
#!/bin/sh
export PYTHONPATH="/opt/central-whatsapp/lib${PYTHONPATH:+:$PYTHONPATH}"
exec /usr/bin/python3 /opt/central-whatsapp/central.py "$@"
LAUNCH
chmod 755 "$stage/usr/bin/central-whatsapp"
cat > "$stage/DEBIAN/control" <<'CONTROL'
Package: central-whatsapp
Version: 0.1.0
Section: net
Priority: optional
Architecture: amd64
Maintainer: Central WhatsApp contributors
Depends: python3 (>= 3.10), python3 (<< 3.11), libxcb-cursor0, libxcb-icccm4, libxcb-image0, libxcb-keysyms1, libxcb-render-util0, libxcb-xinerama0, libxcb-xkb1, libxkbcommon-x11-0, libnss3, libnspr4, libasound2, libdbus-1-3, libegl1, libgl1, libxcomposite1, libxdamage1, libxrandr2, libxtst6, libfontconfig1, libnotify-bin, libglib2.0-0
Description: Central com perfis independentes do WhatsApp Web
 Aplicativo comunitario sem afiliacao com WhatsApp ou Meta.
 Qt WebEngine integrado e armazenamento separado por perfil.
CONTROL
mkdir -p "$stage/usr/share/doc/central-whatsapp"
install -m644 "$base/LICENSE" "$base/README.md" "$stage/usr/share/doc/central-whatsapp/"
size=$(du -sk "$stage/opt" | cut -f1)
printf 'Installed-Size: %s\n' "$size" >> "$stage/DEBIAN/control"
dpkg-deb --root-owner-group -Zzstd -z3 --build "$stage" "$base/dist/central-whatsapp_0.1.0_amd64.deb"
