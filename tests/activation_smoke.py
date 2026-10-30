"""IPC entre processos Qt novos, sem contas, rede ou dados reais."""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
SERVER = r'''
import os
from pathlib import Path
from PySide6.QtCore import QTimer
from unittest.mock import patch
from central import QApplication, Window, ActivationServer, QSystemTrayIcon
app=QApplication([])
app.setQuitOnLastWindowClosed(False)
w=Window()
w.confirm_close=True
w.settings["close_action"]="background"
no_tray=patch.object(QSystemTrayIcon,"isSystemTrayAvailable",return_value=False)
no_tray.start()
server=ActivationServer(w, data_dir=Path(os.environ['CENTRAL_WHATSAPP_DATA']))
assert server.ready
w.activation_ready=True
assert w.can_background(), 'Launcher temporário + IPC devem permitir segundo plano'
w.show()
views_before=dict(w.views)
w.close()
assert not w.isVisible() and w.views == views_before
assert not w._cleaned, 'Fechar em segundo plano não deve destruir páginas' 
root=Path(os.environ['CENTRAL_WHATSAPP_DATA'])
(root/'server-ready').write_text('ready')
def observe():
    if w.isVisible():
        (root/'activated').write_text('shown')
        server.close()
        w.quit_app()
timer=QTimer();timer.timeout.connect(observe);timer.start(50)
QTimer.singleShot(10000, app.quit)
app.exec()
server.close()
assert (root/'activated').exists(), 'Janela não reabriu via IPC'
'''
CLIENT = r'''
import os
from pathlib import Path
from PySide6.QtCore import QCoreApplication
from central import activate_existing
app=QCoreApplication([])
assert activate_existing(data_dir=Path(os.environ['CENTRAL_WHATSAPP_DATA']))
'''

with tempfile.TemporaryDirectory(prefix='central-ipc-smoke-') as directory:
    root = Path(directory)
    launcher = root/'.local/bin/central-whatsapp'
    launcher.parent.mkdir(parents=True)
    launcher.write_text('#!/bin/sh\nexit 0\n')
    launcher.chmod(0o755)
    env = dict(os.environ, HOME=directory, CENTRAL_WHATSAPP_DATA=directory,
               XDG_CONFIG_HOME=str(root/'config'), PYTHONPATH=str(PROJECT))
    server = subprocess.Popen([sys.executable, '-c', SERVER], cwd=PROJECT, env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        # Poll bounded by the server process, without touching the user's instance.
        import time
        deadline = time.monotonic()+10
        while not (root/'server-ready').exists() and server.poll() is None and time.monotonic()<deadline:
            time.sleep(0.05)
        if not (root/'server-ready').exists():
            output, errors = server.communicate(timeout=2)
            raise AssertionError('Servidor IPC não iniciou: '+output+errors)
        client = subprocess.run([sys.executable, '-c', CLIENT], cwd=PROJECT, env=env,
                                capture_output=True, text=True, timeout=5)
        assert client.returncode == 0, client.stdout+client.stderr
        output, errors = server.communicate(timeout=12)
        assert server.returncode == 0, output+errors
        assert (root/'activated').read_text() == 'shown'
    finally:
        if server.poll() is None:
            server.terminate()
            server.communicate(timeout=5)
print('PASS: segunda instância reabre janela oculta via IPC e Sair encerra processo isolado')
