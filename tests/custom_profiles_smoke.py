"""Create custom profiles through the actual dialog without visiting external sites."""
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
with tempfile.TemporaryDirectory(prefix='central-custom-') as directory:
    os.environ['CENTRAL_WHATSAPP_DATA'] = directory
    os.environ['XDG_CONFIG_HOME'] = directory
    from central import Window, Page, QWebEngineView, QWebEnginePage
    from desktop_ui import edit_profile_dialog
    from services import allows_url
    from PySide6.QtCore import QTimer, QUrl, Qt, QEvent, QCoreApplication, QEventLoop
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication, QComboBox, QDialogButtonBox, QLineEdit, QLabel
    from shiboken6 import delete

    app = QApplication([])
    app.setStyle('Fusion')
    errors = []
    with patch.object(QWebEngineView, 'load') as load:
        window = Window()
        window.confirm_close = False
        window.show()
        def create_in_dialog():
            dialog = app.activeModalWidget()
            try:
                service = dialog.findChild(QComboBox, 'profileService')
                address = dialog.findChild(QLineEdit, 'profileCustomUrl')
                assert not address.isVisible()
                service.setCurrentIndex(service.findData('custom'))
                assert address.isVisible() and not address.isReadOnly()
                dialog.findChild(QLineEdit, 'profileName').setText('Minha equipe')
                address.setText('http://chat.example.test/')
                buttons = dialog.findChild(QDialogButtonBox)
                buttons.button(QDialogButtonBox.StandardButton.Ok).click()
                assert dialog.isVisible(), 'invalid URL must leave the form open'
                address.setText('chat.example.test:8443/inbox?lang=pt#chat')
                if os.environ.get('CENTRAL_CUSTOM_OUTPUT'):
                    destination = Path(os.environ['CENTRAL_CUSTOM_OUTPUT'])
                    destination.mkdir(parents=True, exist_ok=True)
                    for theme in ('light', 'dark'):
                        window.settings['theme'] = theme
                        window.apply_gnome_style()
                        app.processEvents()
                        dialog.grab().save(str(destination / f'custom-profile-{theme}.png'))
                buttons.button(QDialogButtonBox.StandardButton.Ok).click()
            except BaseException as error:
                errors.append(error)
                dialog.reject()
        QTimer.singleShot(60, create_in_dialog)
        window.add()
        assert not errors, errors
        account = window.accounts[0]
        key = account['id']
        assert account['service'] == 'custom'
        assert account['custom_url'] == 'https://chat.example.test:8443/inbox?lang=pt#chat'
        assert load.call_args.args[0].toString() == account['custom_url']
        assert window.store.load()[0]['custom_url'] == account['custom_url']
        page = window.views[key][0].page()
        assert page.custom_url == account['custom_url']
        assert page.acceptNavigationRequest(QUrl('https://chat.example.test:8443/other'), page.NavigationType.NavigationTypeOther, True)
        for url in ('https://chat.example.test/', 'https://other.test:8443/', 'file:///tmp/test'):
            assert not page.acceptNavigationRequest(QUrl(url), page.NavigationType.NavigationTypeOther, True)

        def edit_dialog():
            dialog = app.activeModalWidget()
            try:
                field = dialog.findChild(QLineEdit, 'profileCustomUrl')
                assert field.text() == account['custom_url']
                assert field.isReadOnly()
                dialog.findChild(QLineEdit, 'profileName').setText('Minha equipe atualizada')
                dialog.findChild(QDialogButtonBox).button(QDialogButtonBox.StandardButton.Ok).click()
            except BaseException as error:
                errors.append(error); dialog.reject()
        QTimer.singleShot(60, edit_dialog)
        old_view = window.views[key][0]
        window.rename()
        assert not errors, errors
        assert window.accounts[0]['name'] == 'Minha equipe atualizada'
        assert window.accounts[0]['custom_url'] == account['custom_url']
        assert window.views[key][0] is old_view
        assert window.profile_icon(account).isNull() is False
        for url in ('https://éxample.com/chat', 'https://[::1]:8443/chat'):
            assert allows_url('custom', QUrl(url), url)
        window.close()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        for profile in window.profiles.values():
            profile.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        app.processEvents()
        delete(window)
    flush = QEventLoop();QTimer.singleShot(300, flush.quit);flush.exec()
print('PASS: custom URL form, validation, same-origin navigation, editing and session preservation')
