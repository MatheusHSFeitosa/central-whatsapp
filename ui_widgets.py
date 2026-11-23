"""Shared symbolic controls and application-owned dialog chrome."""
from PySide6.QtCore import QByteArray, QEvent, QPoint, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPalette, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QApplication, QColorDialog as NativeColorDialog, QDialog as NativeDialog,
    QFileDialog as NativeFileDialog, QHBoxLayout, QInputDialog as NativeInputDialog,
    QLabel, QLineEdit, QMenu as NativeMenu, QMessageBox as NativeMessageBox,
    QSizePolicy, QToolButton, QWidget,
)

# All controls share the same symbolic family, independent of the desktop theme.
SYMBOLS = {
    'user':'<circle cx="12" cy="7" r="3"/><path d="M5 21v-2a7 7 0 0 1 14 0v2"/>',
    'briefcase':'<rect x="4" y="8" width="16" height="12" rx="2"/><path d="M9 8V4h6v4M4 13h16"/>',
    'headset':'<path d="M5 13V11a7 7 0 0 1 14 0v2M19 19v2h-5"/><rect x="4" y="12" width="4" height="7" rx="1"/><rect x="16" y="12" width="4" height="7" rx="1"/>',
    'store':'<path d="M4 10l3-6h10l3 6M5 10h14v10H5zM10 20v-6h5v6M3 10h18"/>',
    'building':'<path d="M6 21V3h12v18M3 21h18M10 7h.01M14 7h.01M10 11h.01M14 11h.01M10 15h.01M14 15h.01"/>',
    'home':'<path d="M3 11l9-8 9 8M6 9v12h12V9M10 21v-7h4v7"/>',
    'list-add':'<path d="M12 4v16M4 12h16"/>',
    'view-refresh':'<path d="M20 10a8 8 0 1 0-1 8M20 4v6h-6"/>',
    'document-edit':'<path d="M5 16L17 4l3 3L8 19l-4 1zM14 7l3 3"/>',
    'folder-download':'<path d="M5 8h14v12H5zM4 4h16v4H4zM10 12h4"/>',
    'edit-undo':'<path d="M4 10h9a6 6 0 0 1 0 12M4 10l5-5M4 10l5 5"/>',
    'preferences-system':'<circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/><path d="M12 3v3M12 18v3M3 12h3M18 12h3M6 6l2 2M16 16l2 2M6 18l2-2M16 8l2-2"/>',
    'application-exit':'<path d="M12 3v9M6 5a9 9 0 1 0 12 0"/>',
    'group':'<rect x="3" y="6" width="8" height="12" rx="2"/><rect x="13" y="6" width="8" height="12" rx="2"/>',
    'mute':'<path d="M6 15V10a6 6 0 0 1 12 0v5l2 3H4l2-3M10 21h4M3 3l18 18"/>',
    'seen':'<path d="M4 12l5 5L20 6"/>',
    'previous':'<path d="M15 5l-7 7 7 7"/>',
    'next':'<path d="M9 5l7 7-7 7"/>',
    'chevron-down':'<path d="M5 9l7 7 7-7"/>',
    'sidebar-show':'<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M9 4v16M13 8l4 4-4 4"/>',
    'sidebar-hide':'<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M9 4v16M17 8l-4 4 4 4"/>',
    'open-menu-symbolic':'<path d="M4 6h16M4 12h16M4 18h16"/>',
}

def icon(preset):
    color = QApplication.palette().text().color().name()
    paths = SYMBOLS.get(preset, SYMBOLS['user'])
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">{paths}</svg>'
    image = QPixmap(32, 32)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    QSvgRenderer(QByteArray(svg.encode())).render(painter)
    painter.end()
    return QIcon(image)



SYMBOLS.update({
    'globe': '<circle cx="12" cy="12" r="9"/><ellipse cx="12" cy="12" rx="4" ry="9"/><path d="M3 12h18"/>',
    'microphone': '<rect x="9" y="3" width="6" height="12" rx="3"/><path d="M5 10v2a7 7 0 0 0 14 0v-2M12 19v3M8 22h8"/>',
    'window-minimize': '<path d="M6 12h12"/>',
    'window-maximize': '<rect x="5" y="5" width="14" height="14" rx="2"/>',
    'window-restore': '<rect x="4" y="8" width="12" height="12" rx="2"/><path d="M8 8V4h12v12h-4"/>',
    'window-close': '<path d="m6 6 12 12M18 6 6 18"/>',
    'image': '<rect x="3" y="4" width="18" height="16" rx="3"/><circle cx="8" cy="9" r="1.5"/><path d="m4 18 6-6 4 4 3-3 4 4"/>',
    'palette': '<path d="M12 3a9 9 0 1 0 0 18h1a2 2 0 0 0 0-4 2 2 0 0 1 0-4h4a4 4 0 0 0 4-4c0-3-4-6-9-6Z"/><path d="M7 10h.01M10 6h.01M16 7h.01M6 15h.01"/>',
})


class HeadingLabel(QLabel):
    def __init__(self, text):
        self._full_text = text
        super().__init__(text)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.setMinimumWidth(0)

    def setText(self, text):
        self._full_text = text
        self.setToolTip(text)
        self.setAccessibleName(text)
        self._update_text()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_text()

    def _update_text(self):
        super().setText(self.fontMetrics().elidedText(
            self._full_text, Qt.TextElideMode.ElideRight, max(0, self.width())
        ))


class DialogChrome:
    """Give all Qt dialogs the same rounded header without OS decorations."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setObjectName('themedDialog')
        self._chrome_prepared = False
        self._header = QWidget(self)
        self._header.setObjectName('dialogHeader')
        self._header.installEventFilter(self)
        row = QHBoxLayout(self._header)
        row.setContentsMargins(16, 4, 8, 4)
        row.setSpacing(8)
        self._heading = HeadingLabel(self.windowTitle())
        self._heading.setTextFormat(Qt.TextFormat.PlainText)
        self._heading.setObjectName('dialogHeading')
        self._heading.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        row.addWidget(self._heading, 1)
        self._close = QToolButton()
        self._close.setObjectName('dialogClose')
        self._close.setFixedSize(32, 32)
        self._close.setIcon(icon('window-close'))
        self._close.setToolTip('Fechar')
        self._close.setAccessibleName('Fechar')
        self._close.clicked.connect(self.reject)
        row.addWidget(self._close)
        self.windowTitleChanged.connect(self._heading.setText)

    def eventFilter(self, watched, event):
        if watched is self._header and event.type() == QEvent.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.LeftButton:
                handle = self.windowHandle()
                if handle and handle.startSystemMove():
                    return True
        return super().eventFilter(watched, event)

    def showEvent(self, event):
        if not self._chrome_prepared:
            layout = self.layout()
            if layout:
                margins = layout.contentsMargins()
                layout.setContentsMargins(
                    max(16, margins.left()), margins.top() + 48,
                    max(16, margins.right()), max(16, margins.bottom()),
                )
            self._chrome_prepared = True
        self._close.setIcon(icon('window-close'))
        super().showEvent(event)
        self._position_header()
        # Let Qt account for the header before choosing the final size.
        self.resize(self.size().expandedTo(self.minimumSizeHint()))

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.Type.PaletteChange and hasattr(self, '_close'):
            self._close.setIcon(icon('window-close'))
            self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._position_header()

    def _position_header(self):
        if hasattr(self, '_header'):
            self._header.setGeometry(1, 3, max(0, self.width()-2), 44)
            self._header.raise_()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        palette = QApplication.palette()
        painter.setPen(palette.color(QPalette.ColorRole.Mid))
        painter.setBrush(palette.color(QPalette.ColorRole.Base))
        painter.drawRoundedRect(QRectF(self.rect()).adjusted(.5, .5, -.5, -.5), 12, 12)
        painter.setPen(palette.color(QPalette.ColorRole.Mid))
        painter.drawLine(QPoint(16, 48), QPoint(max(16, self.width()-16), 48))
        painter.end()


class Dialog(DialogChrome, NativeDialog):
    pass


class InputDialog(DialogChrome, NativeInputDialog):
    @classmethod
    def getText(cls, parent, title, label, echo=QLineEdit.EchoMode.Normal, text='', flags=Qt.WindowType.Widget,
                inputMethodHints=Qt.InputMethodHint.ImhNone):
        dialog = cls(parent, flags)
        dialog.setWindowTitle(title)
        dialog.setLabelText(label)
        dialog.setTextEchoMode(echo)
        dialog.setTextValue(text)
        dialog.setInputMethodHints(inputMethodHints)
        dialog.setOkButtonText('Salvar')
        dialog.setCancelButtonText('Cancelar')
        accepted = dialog.exec() == NativeDialog.DialogCode.Accepted
        result = dialog.textValue(), accepted
        dialog.deleteLater()
        return result

    @classmethod
    def getItem(cls, parent, title, label, items, current=0, editable=True, flags=Qt.WindowType.Widget,
                inputMethodHints=Qt.InputMethodHint.ImhNone):
        dialog = cls(parent, flags)
        dialog.setWindowTitle(title)
        dialog.setLabelText(label)
        dialog.setComboBoxItems(items)
        dialog.setComboBoxEditable(editable)
        if items:
            dialog.setTextValue(items[max(0, min(current, len(items)-1))])
        dialog.setInputMethodHints(inputMethodHints)
        dialog.setOkButtonText('Selecionar')
        dialog.setCancelButtonText('Cancelar')
        accepted = dialog.exec() == NativeDialog.DialogCode.Accepted
        result = dialog.textValue(), accepted
        dialog.deleteLater()
        return result


class MessageBox(DialogChrome, NativeMessageBox):
    @classmethod
    def _message(cls, parent, title, text, kind, buttons, default):
        box = cls(parent)
        box.setWindowTitle(title)
        box.setIcon(kind)
        box.setTextFormat(Qt.TextFormat.PlainText)
        box.setText(text)
        box.setStandardButtons(buttons)
        if default != cls.StandardButton.NoButton:
            box.setDefaultButton(default)
        labels = {
            cls.StandardButton.Ok: 'OK', cls.StandardButton.Yes: 'Sim',
            cls.StandardButton.No: 'Não', cls.StandardButton.Cancel: 'Cancelar',
            cls.StandardButton.Close: 'Fechar', cls.StandardButton.Retry: 'Tentar novamente',
        }
        for role, label in labels.items():
            button = box.button(role)
            if button:
                button.setText(label)
        result = cls.StandardButton(box.exec())
        box.deleteLater()
        return result

    @classmethod
    def information(cls, parent, title, text, buttons=NativeMessageBox.StandardButton.Ok,
                    defaultButton=NativeMessageBox.StandardButton.NoButton):
        return cls._message(parent, title, text, cls.Icon.Information, buttons, defaultButton)

    @classmethod
    def warning(cls, parent, title, text, buttons=NativeMessageBox.StandardButton.Ok,
                defaultButton=NativeMessageBox.StandardButton.NoButton):
        return cls._message(parent, title, text, cls.Icon.Warning, buttons, defaultButton)

    @classmethod
    def critical(cls, parent, title, text, buttons=NativeMessageBox.StandardButton.Ok,
                 defaultButton=NativeMessageBox.StandardButton.NoButton):
        return cls._message(parent, title, text, cls.Icon.Critical, buttons, defaultButton)

    @classmethod
    def question(cls, parent, title, text,
                 buttons=NativeMessageBox.StandardButton.Yes | NativeMessageBox.StandardButton.No,
                 defaultButton=NativeMessageBox.StandardButton.NoButton):
        return cls._message(parent, title, text, cls.Icon.Question, buttons, defaultButton)


class FileDialog(DialogChrome, NativeFileDialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setLabelText(self.DialogLabel.LookIn, 'Pasta:')
        self.setLabelText(self.DialogLabel.FileType, 'Tipo de arquivo:')

    @classmethod
    def _file(cls, parent, caption, directory, name_filter, selected_filter, options, save):
        dialog = cls(parent, caption, directory, name_filter)
        dialog.setOptions(options | cls.Option.DontUseNativeDialog)
        dialog.setAcceptMode(cls.AcceptMode.AcceptSave if save else cls.AcceptMode.AcceptOpen)
        dialog.setFileMode(cls.FileMode.AnyFile if save else cls.FileMode.ExistingFile)
        if selected_filter:
            dialog.selectNameFilter(selected_filter)
        if dialog.exec() == NativeDialog.DialogCode.Accepted:
            result = dialog.selectedFiles()[0], dialog.selectedNameFilter()
        else:
            result = '', ''
        dialog.deleteLater()
        return result

    @classmethod
    def getOpenFileName(cls, parent=None, caption='', dir='', filter='', selectedFilter='',
                        options=NativeFileDialog.Option(0)):
        return cls._file(parent, caption, dir, filter, selectedFilter, options, False)

    @classmethod
    def getSaveFileName(cls, parent=None, caption='', dir='', filter='', selectedFilter='',
                        options=NativeFileDialog.Option(0)):
        return cls._file(parent, caption, dir, filter, selectedFilter, options, True)


class ColorDialog(DialogChrome, NativeColorDialog):
    @classmethod
    def getColor(cls, initial=Qt.GlobalColor.white, parent=None, title='Cor do grupo',
                 options=NativeColorDialog.ColorDialogOption(0)):
        dialog = cls(initial, parent)
        dialog.setWindowTitle(title)
        dialog.setOptions(options | cls.ColorDialogOption.DontUseNativeDialog)
        result = dialog.currentColor() if dialog.exec() == NativeDialog.DialogCode.Accepted else QColor()
        dialog.deleteLater()
        return result


class Menu(NativeMenu):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def addMenu(self, *args):
        if len(args) == 1 and isinstance(args[0], NativeMenu):
            return super().addMenu(args[0])
        if len(args) == 1 and isinstance(args[0], str):
            menu = Menu(args[0], self)
        elif len(args) == 2 and isinstance(args[0], QIcon) and isinstance(args[1], str):
            menu = Menu(args[1], self)
            menu.setIcon(args[0])
        else:
            return super().addMenu(*args)
        super().addMenu(menu)
        return menu
