"""Teste local sem login: CRUD, configuração e armazenamento isolado."""
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

os.environ['CENTRAL_WHATSAPP_DATA'] = tempfile.mkdtemp(prefix='central-whatsapp-smoke-')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from central import *
app=QApplication([])
with patch.object(QWebEngineView,'load',lambda *args:None):
    window=Window();window.confirm_close=False
    for name in ['Pessoal','Trabalho']:
        with patch.object(QInputDialog,'getText',return_value=(name,True)):window.add()
    assert len(window.accounts)==2
    assert len(window.views)==2
    profiles=[p for v,p in window.views.values()]
    assert len({p.persistentStoragePath() for p in profiles})==2
    assert all(not p.isOffTheRecord() for p in profiles)
    with patch.object(QInputDialog,'getText',return_value=('Empresa',True)):window.rename()
    assert window.accounts[1]['name']=='Empresa'
    restored=Window();restored.confirm_close=False
    assert restored.accounts==window.accounts
    folder=Path(profiles[1].persistentStoragePath()).parent
    (folder/'preservar.txt').write_text('teste')
    with patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.Yes):window.remove()
    assert len(window.accounts)==1
    assert (folder/'preservar.txt').exists()
    assert len(json.loads(CONFIG.read_text()))==1
    print('PASS: adicionar, renomear, remover da lista, reabrir configuração, isolamento e preservação de dados')
    window.close();restored.close()
    app.processEvents()
