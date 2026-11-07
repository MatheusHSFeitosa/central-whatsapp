"""Exercise real themed dialogs, returned values and window state using isolated data."""
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


with tempfile.TemporaryDirectory(prefix='central-theme-') as temporary:
    os.environ['CENTRAL_WHATSAPP_DATA'] = temporary
    os.environ['XDG_CONFIG_HOME'] = temporary
    from central import Window
    from desktop_ui import PreferencesDialog, edit_profile_dialog
    from ui_widgets import ColorDialog, FileDialog, InputDialog, MessageBox
    from PySide6.QtCore import QEvent, QCoreApplication, QPoint, QTimer, Qt
    from PySide6.QtTest import QTest
    from PySide6.QtGui import QColor
    from PySide6.QtWidgets import QApplication, QDialogButtonBox, QLineEdit, QToolButton

    app = QApplication([])
    app.setStyle('Fusion')
    errors = []

    def interact(callback):
        def run():
            try:
                dialog = app.activeModalWidget()
                assert dialog is not None
                callback(dialog)
            except BaseException as error:
                errors.append(error)
                if app.activeModalWidget():
                    app.activeModalWidget().reject()
        QTimer.singleShot(40, run)

    def accept_input(dialog):
        dialog.setTextValue('Equipe revisada')
        dialog.accept()

    with patch.object(Window, 'select', lambda *args, **kwargs: None):
        window = Window()
        window.confirm_close = False
        window.resize(900, 650)
        window.show()
        app.processEvents()
        output = os.environ.get('CENTRAL_THEME_OUTPUT')
        if output:
            Path(output).mkdir(parents=True, exist_ok=True)

        for theme in ('light', 'dark'):
            window.apply_preferences(dict(theme=theme, bar_position='top'))
            for position in ('top', 'left', 'bottom', 'top'):
                window.apply_preferences(dict(bar_position=position))
                app.processEvents()
                assert window.title_bar.isAncestorOf(window.sidebar) == (position == 'top')
                if position == 'top':
                    center = window.title_bar.mapTo(window, window.title_bar.rect().center()).y()
                    gear = window.menu_button.mapTo(window, window.menu_button.rect().center()).y()
                    assert abs(center - gear) <= 1, (center, gear)

            dialog = PreferencesDialog(window, window.settings, window.accounts, True)
            dialog.show()
            app.processEvents()
            for tab in range(dialog.tabs.count()):
                dialog.tabs.setCurrentIndex(tab)
                app.processEvents()
                assert dialog.windowFlags() & Qt.WindowType.FramelessWindowHint
                assert dialog.layout().contentsMargins().top() >= 48
                for widget in dialog.findChildren(QLineEdit):
                    if widget.isVisible():
                        point = widget.mapTo(dialog, QPoint(0, 0))
                        assert point.y() >= 48
                image = dialog.grab().toImage()
                # Interior must be opaque; only the rounded outer corners are transparent.
                assert image.pixelColor(image.width()//2, 25).alpha() == 255
                assert image.pixelColor(0, 0).alpha() < 255
                if output:
                    image.save(str(Path(output) / f'preferences-{theme}-{tab}.png'))
            dialog.close()
            dialog.deleteLater()

            def inspect_profile(dialog):
                assert dialog.windowFlags() & Qt.WindowType.FramelessWindowHint
                field = dialog.findChild(QLineEdit, 'profileName')
                field.setText('Novo perfil')
                if output:
                    dialog.grab().save(str(Path(output) / f'profile-{theme}.png'))
                dialog.findChild(QDialogButtonBox).button(QDialogButtonBox.StandardButton.Ok).click()

            interact(inspect_profile)
            result = edit_profile_dialog(window, 'Adicionar perfil', group_options=('Equipe',))
            assert result and result[0] == 'Novo perfil'
            interact(accept_input)
            assert InputDialog.getText(window, 'Renomear grupo', 'Nome:', text='Equipe') == ('Equipe revisada', True)
            interact(lambda dialog: dialog.reject())
            assert not InputDialog.getText(window, 'Novo grupo', 'Nome:')[1]
            interact(lambda dialog: dialog.accept())
            assert InputDialog.getItem(window, 'Restaurar perfil', 'Perfil:', ['Um', 'Dois'], 1, False) == ('Dois', True)

            def answer(dialog):
                assert dialog._heading.text() == 'Confirmação'
                if output:
                    dialog.grab().save(str(Path(output) / f'confirmation-{theme}.png'))
                dialog.button(MessageBox.StandardButton.No).click()

            interact(answer)
            assert MessageBox.question(window, 'Confirmação', 'Texto de teste com <tag> literal.') == MessageBox.StandardButton.No

            fixture = Path(temporary) / 'avatar.png'
            fixture.write_bytes(b'synthetic')
            def choose_file(dialog):
                assert dialog.testOption(FileDialog.Option.DontUseNativeDialog)
                dialog.findChild(QLineEdit, 'fileNameEdit').setText(str(fixture))
                if output:
                    dialog.grab().save(str(Path(output) / f'file-{theme}.png'))
                dialog.accept()
            interact(choose_file)
            selected, _ = FileDialog.getOpenFileName(window, 'Escolher foto', str(fixture.parent), 'Imagens (*.png)')
            assert selected == str(fixture)
            interact(lambda dialog: dialog.reject())
            assert FileDialog.getSaveFileName(window, 'Salvar arquivo', str(fixture))[0] == ''
            def choose_color(dialog):
                dialog.setCurrentColor(QColor('#65b2ff'))
                if output:
                    dialog.grab().save(str(Path(output) / f'color-{theme}.png'))
                dialog.accept()
            interact(choose_color)
            assert ColorDialog.getColor(QColor('#ffffff'), window).name() == '#65b2ff'
            interact(lambda dialog: dialog.reject())
            assert not ColorDialog.getColor(QColor('#ffffff'), window).isValid()
            if errors:
                raise errors[0]

        window.showMaximized()
        QTest.qWait(200)
        assert window.centralWidget().property('squareCorners') is True
        window.show_window()
        assert window.isMaximized(), 'Reopening must preserve maximization'
        window.showMinimized()
        QTest.qWait(200)
        window.show_window()
        QTest.qWait(200)
        assert window.isMaximized()
        window.title_bar.toggle_maximized()
        QTest.qWait(200)
        assert not window.isMaximized()
        assert window.centralWidget().property('squareCorners') is False
        window.close()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)

    assert not errors, errors
print('PASS: all themed dialogs, opacity, inputs, cancel/accept and maximize/reopen')
