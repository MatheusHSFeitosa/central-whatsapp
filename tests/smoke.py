"""Interface Qt real com armazenamento temporário; navegação e diálogos simulados."""
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

with tempfile.TemporaryDirectory(prefix='central-whatsapp-smoke-') as data:
    os.environ['CENTRAL_WHATSAPP_DATA'] = data
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from central import QApplication, QWebEngineView, Window, QInputDialog, QMessageBox, CONFIG
    from PySide6.QtCore import QCoreApplication, QEvent

    app = QApplication([])
    with patch.object(QWebEngineView, 'load', lambda *args: None):
        window = Window()
        window.confirm_close = False
        assert not window.rename_button.isEnabled()
        assert not window.archive_button.isEnabled()
        assert not window.restore_button.isEnabled()
        assert not window.reload_button.isEnabled()
        for name in ['Pessoal', 'Trabalho']:
            with patch.object(QInputDialog, 'getText', return_value=(name, True)):
                window.add()
        assert len(window.accounts) == len(window.views) == 2
        profiles = [p for v, p in window.views.values()]
        assert len({p.persistentStoragePath() for p in profiles}) == 2
        assert all(not p.isOffTheRecord() for p in profiles)
        assert window.rename_button.isEnabled() and window.reload_button.isEnabled()

        first, second = [a['id'] for a in window.accounts]
        window.loaded(first, False)
        window.list.setCurrentRow(0)
        assert 'Falha ao carregar' in window.status.text()
        window.list.setCurrentRow(1)
        assert 'Falha ao carregar' not in window.status.text()
        window.list.setCurrentRow(0)
        assert 'Falha ao carregar' in window.status.text()
        window.loaded(first, True)
        assert 'Falha ao carregar' not in window.status.text()
        window.list.setCurrentRow(1)
        with patch.object(QInputDialog, 'getText', return_value=('Empresa', True)):
            window.rename()
        assert window.accounts[1]['name'] == 'Empresa'

        before = CONFIG.read_bytes()
        accounts = [dict(a) for a in window.accounts]
        with patch.object(window.store, 'save', side_effect=OSError('falha de escrita simulada')), \
             patch.object(QMessageBox, 'critical') as alert:
            with patch.object(QInputDialog, 'getText', return_value=('Novo', True)):
                window.add()
            with patch.object(QInputDialog, 'getText', return_value=('Outro', True)):
                window.rename()
            with patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.Yes):
                window.remove()
            assert alert.call_count == 3
        assert window.accounts == accounts
        assert CONFIG.read_bytes() == before
        assert window.list.count() == 2 and len(window.views) == 2

        folder = Path(profiles[1].persistentStoragePath()).parent
        (folder/'preservar.txt').write_text('teste')
        with patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.Yes):
            window.remove()
        assert len(window.accounts) == 1 and len(window.archived) == 1
        assert len(window.views) == 1 and window.restore_button.isEnabled()
        assert (folder/'preservar.txt').exists()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        label = '1. ' + window.archived[0]['name']
        with patch.object(QInputDialog, 'getItem', return_value=(label, True)):
            window.restore()
        assert len(window.accounts) == 2 and not window.archived
        assert window.accounts[-1]['id'] == second
        assert window.views[second][1] is profiles[1]
        assert (folder/'preservar.txt').exists()
        assert not window.restore_button.isEnabled()

        restored = Window()
        restored.confirm_close = False
        assert [(a["id"], a["name"]) for a in restored.accounts] == [(a["id"], a["name"]) for a in window.accounts]
        assert restored.archived == window.archived
        assert len(json.loads(CONFIG.read_text())) == 2
        window.close()
        restored.close()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        app.processEvents()
    print('PASS: CRUD, falha de escrita sem mutação, arquivar/restaurar UUID e sessão, controles, estado de erro e isolamento')
