"""Interface Qt real com armazenamento temporário; navegação e diálogos simulados."""
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock

with tempfile.TemporaryDirectory(prefix='central-whatsapp-smoke-') as data:
    os.environ['CENTRAL_WHATSAPP_DATA'] = data
    os.environ['XDG_CONFIG_HOME'] = str(Path(data)/'xdg-config')
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from central import QApplication, QWebEngineView, Window, QInputDialog, QMessageBox, CONFIG
    from PySide6.QtCore import QCoreApplication, QEvent, Qt, QEventLoop, QTimer
    from PySide6.QtGui import QCloseEvent
    from desktop_ui import PreferencesDialog

    app = QApplication([])
    with patch.object(QWebEngineView, 'load', lambda *args: None):
        window = Window()
        window.confirm_close = False
        assert not window.rename_button.isEnabled()
        assert not window.archive_button.isEnabled()
        assert not window.restore_button.isEnabled()
        assert not window.reload_button.isEnabled()
        for name in ['Pessoal', 'Trabalho']:
            with patch('central.edit_profile_dialog', return_value=(name, 'user')):
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
        with patch('central.edit_profile_dialog', return_value=('Empresa', 'briefcase')):
            window.rename()
        assert window.accounts[1]['name'] == 'Empresa'

        assert window.accounts[1]['icon'] == 'briefcase'
        from PySide6.QtGui import QImage
        local_photo = Path(data)/'local-photo.png'
        photo = QImage(320,240,QImage.Format.Format_RGB32);photo.fill(0xff2978bd);photo.save(str(local_photo))
        with patch('central.QFileDialog.getOpenFileName',return_value=(str(local_photo),'PNG')):
            window.choose_profile_photo()
        assert window.accounts[1]['avatar_mode'] == 'file'
        assert window.avatar_manager.load(second).width() == 256
        assert window.photo_file_action.isEnabled()
        window.use_profile_icon()
        assert window.accounts[1]['avatar_mode'] == 'icon'
        window.use_automatic_photo()
        assert window.accounts[1]['avatar_mode'] == 'auto'
        assert not window.avatar_manager.path(second).exists()

        assert not window.list.item(1).icon().isNull()
        for button in [window.sidebar_toggle, window.add_button, window.reload_button, window.menu_button]:
            assert not button.icon().isNull()
        assert window.preferences_action.text() and window.quit_action.text()
        window.toggle_sidebar()
        assert window.settings['sidebar_collapsed']
        assert window.sidebar.width() == 64
        assert window.list.item(0).text() == ''
        assert window.list.item(0).toolTip() == 'Pessoal · WhatsApp'
        assert window.list.item(0).data(Qt.ItemDataRole.AccessibleTextRole) == 'Pessoal'
        window.toggle_sidebar()
        assert window.sidebar.width() == 240
        assert window.list.item(0).text() == 'Pessoal'
        candidate = dict(window.settings, startup_enabled=False, start_hidden=False,
                         startup_mode='selected', startup_profiles=[second], muted_profiles=[first])
        assert window.apply_preferences(candidate)
        assert window.preferences_store.load() == candidate
        previous_settings = dict(window.settings)
        window.autostart_manager.launch_command = ['/tmp/central-whatsapp-test']
        with patch.object(window.preferences_store, 'save', side_effect=OSError('escrita de preferências simulada')), \
             patch.object(QMessageBox, 'critical'):
            assert not window.apply_preferences(dict(candidate, startup_enabled=True))
        assert window.settings == previous_settings
        assert window.autostart_manager.capture() is None
        notification = Mock()
        with patch.object(window.desktop_notifications, 'send') as launch:
            window.notify(first, notification)
            notification.close.assert_called_once()
            notification.show.assert_not_called()
            launch.assert_not_called()
        dialog = PreferencesDialog(window, candidate, window.accounts, False)
        assert not dialog.start_hidden.isEnabled()
        assert dialog.values()['close_action'] == 'exit'
        dialog.deleteLater()

        before = CONFIG.read_bytes()
        accounts = [dict(a) for a in window.accounts]
        with patch.object(window.store, 'save', side_effect=OSError('falha de escrita simulada')), \
             patch.object(QMessageBox, 'critical') as alert:
            with patch('central.edit_profile_dialog', return_value=('Novo', 'user')):
                window.add()
            with patch('central.edit_profile_dialog', return_value=('Outro', 'user')):
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
        assert restored.settings == window.settings
        restored.load_startup_profiles()
        assert set(restored.views) == {second}
        restored.settings['startup_mode'] = 'all'
        restored.load_startup_profiles()
        assert set(restored.views) == {first, second}
        unloaded = Window()
        unloaded.confirm_close = False
        unloaded.settings['startup_mode'] = 'none'
        unloaded.load_startup_profiles()
        assert not unloaded.views
        unloaded.close()
        restored.show()
        restored.confirm_close = True
        restored.settings['close_action'] = 'background'
        with patch.object(restored, 'can_background', return_value=True):
            event = QCloseEvent()
            restored.closeEvent(event)
            assert not event.isAccepted() and not restored.isVisible()
        restored.show()
        with patch.object(restored, 'can_background', return_value=False), \
             patch.object(QMessageBox, 'information'), patch.object(QMessageBox, 'warning'):
            event = QCloseEvent()
            restored.closeEvent(event)
            assert not event.isAccepted() and restored.isVisible()
        restored.confirm_close = False
        assert len(json.loads(CONFIG.read_text())) == 2
        window.close()
        restored.close()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        app.processEvents()
        # Destroy profile owners before removing temporary Chromium storage.
        from shiboken6 import delete
        for candidate_window in (window, restored, unloaded):delete(candidate_window)
        flush = QEventLoop();QTimer.singleShot(500, flush.quit);flush.exec()
    print('PASS: CRUD, escrita, arquivo/restauro, ícones/sidebar/menu, preferências, fechamento seguro e isolamento')
