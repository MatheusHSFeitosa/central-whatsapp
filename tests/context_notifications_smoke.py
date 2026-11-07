"""Contexto por perfil, indicador e avisos com dados temporários e sem rede."""
import os, sys, tempfile, uuid
from pathlib import Path
from unittest.mock import patch, Mock
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
with tempfile.TemporaryDirectory() as data:
    os.environ['CENTRAL_WHATSAPP_DATA']=data
    os.environ['XDG_CONFIG_HOME']=data
    from central import QApplication, Window
    from desktop_ui import PreferencesDialog
    from PySide6.QtWidgets import QLabel
    from shiboken6 import delete
    app=QApplication([])
    with patch.object(Window,'select',lambda *args, **kwargs:None):
        window=Window();window.confirm_close=False
        first,second=str(uuid.uuid4()),str(uuid.uuid4())
        window.accounts=[dict(id=first,name='Pessoal',service='whatsapp',icon='user'),dict(id=second,name='--Equipe',service='telegram',icon='briefcase')]
        window.refresh(0);window.show();app.processEvents()
        # Plain widgets replace only the web views; signals exercise the real presenter.
        first_view,second_view=QLabel('Página um'),QLabel('Página dois')
        window.stack.addWidget(first_view);window.stack.addWidget(second_view)
        window.views={first:(first_view,None),second:(second_view,None)}
        window.stack.setCurrentWidget(first_view)
        for position in ('top','bottom'):
            for collapsed in (False,True):
                window.apply_preferences({'bar_position':position,'sidebar_collapsed':collapsed,'group_mode':'service'})
                app.processEvents()
                assert window.sidebar_toggle.isHidden()
                assert all(window.list.item(i).text() and '\n' not in window.list.item(i).text() for i in range(2))
        window.apply_preferences({'bar_position':'left','sidebar_collapsed':True,'muted_profiles':[second]})
        n=Mock()
        with patch.object(window,'viewing_profile',return_value=False):window.notify(second,n)
        second_row=next(i for i,a in enumerate(window.accounts) if a['id']==second)
        assert second in window.pending_notifications
        n.close.assert_called_once();n.show.assert_not_called()
        assert 'Notificação recebida' in window.list.item(second_row).toolTip()
        assert 'perfis com notificações' in window.menu_button.toolTip()
        # Opening context does not switch the visible web page or clear its badge.
        def execute_context(*args):
            assert window.selected_account()['id']==second
            assert window.stack.currentWidget() is first_view
            assert window.mute_action.isChecked()
            assert window.seen_action.isEnabled()
        with patch.object(window.profile_menu,'exec',side_effect=execute_context):
            window.show_profile_menu(window.list.visualItemRect(window.list.item(second_row)).center())
        assert window.selected_account()['id']==first
        assert second in window.pending_notifications
        general=window.menu_button.menu().actions()
        assert window.rename_button not in general and window.archive_button not in general
        assert window.reload_button in window.profile_menu.actions()
        window.list.setCurrentRow(second_row)
        with patch('central.QInputDialog.getText',return_value=('Trabalho',True)):
            window.set_profile_group()
        assert window.settings['profile_groups'][second]=='Trabalho'
        window.toggle_profile_notifications(False)
        assert second not in window.settings['muted_profiles']
        n=Mock();n.title.return_value='Mensagem';n.message.return_value='Texto'
        with patch.object(window, 'viewing_profile', return_value=False), patch.object(window.desktop_notifications, 'send') as send:
            window.notify(second, n)
        token, _, summary, _, image, _ = send.call_args.args
        assert summary == '--Equipe · Mensagem' and Path(image).is_file()
        from desktop_ui import GROUP_KEY_ROLE
        group_key = window.list.item(second_row).data(GROUP_KEY_ROLE)
        window.toggle_group(group_key)
        window.list.setCurrentRow(0)
        window.hide()
        with patch.object(window, 'select', wraps=window.select) as select:
            window.desktop_notifications.clicked.emit(token)
            select.assert_called_with(second_row, force=True)
        assert window.isVisible() and window.selected_account()['id'] == second
        assert group_key not in window.settings['collapsed_groups']
        n.click.assert_called_once()
        window.desktop_notifications.dismissed.emit(token)
        assert not Path(image).exists()
        window.clear_selected_notification()
        assert second not in window.pending_notifications
        # Foreground account does not accumulate a marker.
        with patch.object(window,'viewing_profile',return_value=True), patch.object(window.desktop_notifications, 'send'):
            window.notify(second,n)
        assert second not in window.pending_notifications
        archived=str(uuid.uuid4())
        settings=dict(window.settings,profile_groups={archived:'Trabalho'},muted_profiles=[archived],startup_profiles=[archived])
        dialog=PreferencesDialog(window,settings,window.accounts,True)
        values=dialog.values()
        assert values['profile_groups'][archived]=='Trabalho' and archived in values['muted_profiles'] and archived in values['startup_profiles']
        delete(dialog)
        window.views.clear();window.close();delete(window);delete(app)
print('PASS: barra horizontal, contexto por perfil sem trocar conversa, badges, silêncio e preferências arquivadas')
