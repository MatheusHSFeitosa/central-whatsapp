#!/bin/sh
set -eu
data=${CENTRAL_WHATSAPP_DATA:-${XDG_DATA_HOME:-$HOME/.local/share}/central-whatsapp-data}
[ -e "$data/app.lock" ] || exit 0
runtime="$HOME/.local/share/central-whatsapp/runtime/bin/python"
if [ ! -x "$runtime" ]; then
    runtime=python3
    if [ -d /opt/central-whatsapp/lib ]; then
        export PYTHONPATH="/opt/central-whatsapp/lib${PYTHONPATH:+:$PYTHONPATH}"
    fi
fi
"$runtime" - "$data/app.lock" <<'PY'
import sys
try:
    from PySide6.QtCore import QCoreApplication, QLockFile
except ImportError:
    sys.exit('Não foi possível verificar a central aberta. Feche a aplicação antes de instalar ou remover.')
app = QCoreApplication([])
lock = QLockFile(sys.argv[1])
if not lock.tryLock(100):
    sys.exit('A Central WhatsApp está aberta ou o armazenamento está ocupado. Feche a aplicação e tente novamente.')
lock.unlock()
PY
