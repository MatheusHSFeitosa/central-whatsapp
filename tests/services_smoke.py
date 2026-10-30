"""Perfis multissserviço, isolamento e navegação sem rede nem contas reais."""
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import QUrl, QCoreApplication, QEvent, QEventLoop, QTimer
from services import SERVICES, allows_url
with tempfile.TemporaryDirectory() as data:
    os.environ['CENTRAL_WHATSAPP_DATA'] = data
    os.environ['XDG_CONFIG_HOME'] = data
    from central import QApplication, Window, QWebEngineView, QWebEnginePage
    app = QApplication([])
    with patch.object(QWebEngineView, 'load') as load:
        window = Window()
        window.confirm_close = False
        for service, config in SERVICES.items():
            with patch('central.edit_profile_dialog', return_value=(config['name'], 'user', service)):
                window.add()
            account = window.accounts[-1]
            assert account['service'] == service
            assert load.call_args.args[0].toString() == config['url']
            page = window.views[account['id']][0].page()
            assert page.service == service
            assert page.acceptNavigationRequest(QUrl(config['url']), QWebEnginePage.NavigationType.NavigationTypeOther, True)
            assert window.photo_auto_action.isEnabled() == (service == 'whatsapp')
            for bad in ('http://' + config['host'], config['url'].replace(config['host'], config['host']+'.evil.test'), config['url'].replace(config['host'], config['host']+':444')):
                assert not allows_url(service, QUrl(bad))
        assert len({p.persistentStoragePath() for p in window.profiles.values()}) == 3
        assert [a['service'] for a in window.store.load()] == list(SERVICES)
        window.close()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        app.processEvents()
        for profile in window.profiles.values():
            profile.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        app.processEvents()
    flush = QEventLoop()
    QTimer.singleShot(500, flush.quit)
    flush.exec()
    print('PASS: três serviços, URLs, origens, foto automática e sessões isoladas')
