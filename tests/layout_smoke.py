"""Preferências visuais e agrupamento em janela Qt isolada."""
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
with tempfile.TemporaryDirectory() as data:
    os.environ['CENTRAL_WHATSAPP_DATA'] = data
    os.environ['XDG_CONFIG_HOME'] = data
    from central import QApplication, Window, QWebEngineView
    from desktop_ui import PreferencesDialog
    from PySide6.QtCore import QCoreApplication, QEvent, QEventLoop, QTimer, Qt
    app = QApplication([])
    with patch.object(QWebEngineView, 'load'):
        window = Window(); window.confirm_close = False
        for name, service in [('Pessoal','whatsapp'), ('Equipe','telegram'), ('Atendimento','chatwoot'), ('Trabalho','whatsapp')]:
            with patch('central.edit_profile_dialog', return_value=(name,'user',service,{'custom_url':'https://support.example.test/'} if service=='chatwoot' else {})):
                window.add()
        window.show(); app.processEvents()
        selected = window.selected_account()['id']
        views = dict(window.views)
        assert window.add_button.isHidden()
        assert window.menu_button.y() > window.list.y()
        groups = {a['id']: ('Pessoal' if a['name']=='Pessoal' else 'Trabalho') for a in window.accounts}
        for position in ('left','top','bottom'):
            for theme in ('light','dark','system'):
                assert window.apply_preferences(dict(bar_position=position, theme=theme, group_mode='custom', profile_groups=groups))
                app.processEvents()
                assert window.selected_account()['id'] == selected
                assert window.views == views
                assert window.preferences_store.load()['bar_position'] == position
                if position == 'left': assert window.sidebar.width() == 240
                else: assert window.sidebar.height() == (40 if position == 'top' else 48)
                if position == 'bottom': assert window.sidebar.y() > window.stack.y()
                if position == 'top': assert window.title_bar.isAncestorOf(window.sidebar)
                assert [window.profile_group(a) for a in window.accounts] == sorted(window.profile_group(a) for a in window.accounts)
                if os.environ.get('CENTRAL_LAYOUT_OUTPUT') and theme in ('light','dark'):
                    target = Path(os.environ['CENTRAL_LAYOUT_OUTPUT']); target.mkdir(parents=True,exist_ok=True)
                    # Only synthetic, unloaded accounts; no real conversations.
                    window.stack.setCurrentIndex(0)
                    window.grab().save(str(target / f'central-{position}-{theme}.png'))
        assert window.apply_preferences({'group_mode':'service'})
        assert [window.profile_group(a) for a in window.accounts] == sorted(window.profile_group(a) for a in window.accounts)
        dialog = PreferencesDialog(window, window.settings, window.accounts, True)
        assert dialog.values()['bar_position'] == 'bottom'
        assert not dialog.group_fields  # Grupos agora são definidos pelo botão direito.
        if os.environ.get('CENTRAL_LAYOUT_OUTPUT'):
            dialog.show(); app.processEvents()
            dialog.grab().save(str(Path(os.environ['CENTRAL_LAYOUT_OUTPUT'])/'configuracoes.png'))
        dialog.close()
        window.close()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        for profile in window.profiles.values():profile.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        app.processEvents()
        from shiboken6 import delete
        delete(dialog)
        delete(window)
    flush = QEventLoop()
    QTimer.singleShot(500, flush.quit)
    flush.exec()
    print('PASS: temas, posições, configurações, grupos e preservação de contas abertas')

delete(app)
