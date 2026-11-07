"""Barra e contexto com Qt real, perfis temporários e navegação sem rede."""
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

with tempfile.TemporaryDirectory(prefix='central-refined-ui-') as data:
    os.environ['CENTRAL_WHATSAPP_DATA'] = data
    os.environ['XDG_CONFIG_HOME'] = str(Path(data) / 'config')
    from central import QApplication, Window, QWebEngineView, QInputDialog
    from desktop_ui import GROUP_ROLE
    from PySide6.QtCore import Qt, QPoint, QCoreApplication, QEvent, QEventLoop, QTimer
    from PySide6.QtTest import QTest
    from shiboken6 import delete

    app = QApplication([])
    with patch.object(QWebEngineView, 'load', lambda *args: None):
        window = Window()
        window.confirm_close = False
        with patch.object(Window, 'select', lambda *args: None):
            for i in range(12):
                name = f'{i:02} Atendimento comercial unidade regional com nome longo'
                with patch('central.edit_profile_dialog', return_value=(name, 'headset', 'telegram')):
                    window.add()
            window.list.setCurrentRow(0)
        groups = {a['id']: ('Equipe A' if i < 6 else 'Equipe B')
                  for i, a in enumerate(window.accounts)}
        window.apply_preferences(dict(group_mode='custom', profile_groups=groups,
                                      bar_position='left'))
        window.resize(800, 600)
        window.show()
        window.list.setCurrentRow(0)
        app.processEvents()
        selected = window.selected_account()['id']
        opened = dict(window.views)
        assert len(opened) == 1

        # A group heading is paint-only: clicking it must not activate its account.
        second_group_row = next(i for i in range(1, window.list.count())
                                if window.list.item(i).data(GROUP_ROLE))
        item = window.list.item(second_group_row)
        window.list.scrollToItem(item)
        app.processEvents()
        rect = window.list.visualItemRect(item)
        heading = QPoint(rect.center().x(), rect.top() + 6)
        assert window.list.profile_at(heading) is None
        QTest.mouseClick(window.list.viewport(), Qt.MouseButton.LeftButton, pos=heading)
        QTest.mouseDClick(window.list.viewport(), Qt.MouseButton.LeftButton, pos=heading)
        assert window.selected_account()['id'] == selected
        assert window.views == opened

        # Context actions on a never-opened account must not create a web session.
        target = window.accounts[1]['id']
        def context(callback):
            row = next(i for i, a in enumerate(window.accounts) if a['id'] == target)
            target_item = window.list.item(row)
            window.list.scrollToItem(target_item)
            app.processEvents()
            target_rect = window.list.visualItemRect(target_item)
            body = window.list.itemDelegate().body_rect(
                target_rect, window.list.indexFromItem(target_item))
            with patch.object(window.profile_menu, 'exec', side_effect=lambda *args: callback()):
                window.show_profile_menu(body.center())
            assert window.selected_account()['id'] == selected
            assert window.views == opened
            assert target not in window.profiles

        context(lambda: window.toggle_profile_notifications(True))
        assert target in window.settings['muted_profiles']
        with patch.object(QInputDialog, 'getText', return_value=('Equipe especial', True)):
            context(window.set_profile_group)
        assert window.settings['profile_groups'][target] == 'Equipe especial'

        for position in ('top', 'bottom', 'left', 'top'):
            window.apply_preferences(dict(bar_position=position))
            app.processEvents()
            app.processEvents()
            assert window.selected_account()['id'] == selected
            assert window.views == opened
            if position != 'left':
                assert window.sidebar.height() == (40 if position == 'top' else 48)
                assert window.sidebar_toggle.isHidden()
                assert all('\n' not in window.list.item(i).text()
                           for i in range(window.list.count()))
                bar = window.list.horizontalScrollBar()
                assert bar.maximum() > 0
                assert window.previous_profiles.isVisible() and window.next_profiles.isVisible()
                bar.setValue(0)
                window.scroll_profiles(1)
                assert 0 < bar.value() < bar.maximum(), 'A seta deve avançar parte da lista, não pular ao fim'

        window.list.setCurrentRow(0)
        window.list.setFocus()
        with patch.object(window.profile_menu, 'exec', return_value=None) as menu:
            QTest.keyClick(window.list, Qt.Key.Key_Menu)
            QTest.keyClick(window.list, Qt.Key.Key_F10, Qt.KeyboardModifier.ShiftModifier)
            assert menu.call_count == 2
        assert window.views == opened
        QTest.keyClick(window.list, Qt.Key.Key_Right)
        assert window.list.currentRow() == 1
        assert len(window.views) >= 2
        window.close()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        for profile in window.profiles.values():
            profile.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        opened.clear()
        app.processEvents()
        delete(window)
    flush = QEventLoop()
    QTimer.singleShot(500, flush.quit)
    flush.exec()
    delete(app)

print('PASS: grupos não acionáveis, contexto sem abrir contas, abas integradas à barra de título, overflow, teclado e sessões preservadas')
