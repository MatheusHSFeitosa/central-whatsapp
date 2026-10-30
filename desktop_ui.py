"""Widgets de apresentação; persistência e sessões pertencem à janela principal."""
import os
from pathlib import Path
from services import SERVICES
from PySide6.QtCore import Qt, QSize, QRectF, QRect, QByteArray, QTimer
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtGui import QAction, QIcon, QPixmap, QPainter, QPen, QPalette, QColor
from PySide6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QBoxLayout, QLabel, QPushButton,
    QToolButton, QListWidget, QStackedWidget, QMenu, QDialog, QDialogButtonBox,
    QApplication, QStyle, QFormLayout, QLineEdit, QComboBox, QCheckBox, QGroupBox, QScrollArea, QStyledItemDelegate, QAbstractItemView)

ICON_PRESETS = {
    'user': ('Pessoa', 'avatar-default'),
    'briefcase': ('Trabalho', 'briefcase'),
    'store': ('Loja', 'shop'),
    'building': ('Empresa', 'office-building'),
    'headset': ('Atendimento', 'audio-headphones'),
    'home': ('Casa', 'user-home'),
}


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


def notification_icon(base, pending):
    if not pending:
        return base
    image = base.pixmap(32, 32)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(QColor('#ffffff'), 2))
    painter.setBrush(QColor('#e66100'))
    painter.drawEllipse(QRectF(21, 21, 10, 10))
    painter.end()
    return QIcon(image)


def edit_profile_dialog(parent, title, name='', icon='user', service='whatsapp', editing=False):
    dialog = QDialog(parent)
    dialog.setWindowTitle(title)
    layout = QVBoxLayout(dialog)
    form = QFormLayout()
    provider = QComboBox()
    for key, config in SERVICES.items():
        provider.addItem(config['name'], key)
    provider.setCurrentIndex(max(0, provider.findData(service)))
    provider.setEnabled(not editing)
    provider.setToolTip('Para trocar de serviço, adicione outro perfil; cada perfil preserva sua sessão.')
    form.addRow('Serviço:', provider)
    field = QLineEdit(name)
    field.setMaxLength(60)
    form.addRow('Nome (até 60 caracteres):', field)
    choices = QComboBox()
    for key, (label, _) in ICON_PRESETS.items():
        choices.addItem(globals()['icon'](key), label, key)
    choices.setCurrentIndex(max(0, choices.findData(icon)))
    form.addRow('Ícone:', choices)
    layout.addLayout(form)
    error = QLabel('Informe um nome para o perfil.')
    error.setVisible(False)
    layout.addWidget(error)
    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    buttons.button(QDialogButtonBox.StandardButton.Ok).setText('Salvar')
    buttons.button(QDialogButtonBox.StandardButton.Cancel).setText('Cancelar')
    def accept():
        if not field.text().strip():
            error.show(); field.setFocus(); return
        dialog.accept()
    buttons.accepted.connect(accept)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)
    field.selectAll(); field.setFocus()
    if dialog.exec() == QDialog.DialogCode.Accepted:
        return field.text().strip(), choices.currentData(), provider.currentData()
    return None


GROUP_ROLE = Qt.ItemDataRole.UserRole + 1


class ProfileDelegate(QStyledItemDelegate):
    """Paint group labels outside the selectable profile body, preserving row IDs."""
    def __init__(self, view):
        super().__init__(view)
        self.view = view

    def prefix(self, index):
        group = index.data(GROUP_ROLE) or ''
        if not group:return 0
        if self.view.horizontal:
            return min(120, self.view.fontMetrics().horizontalAdvance(group) + 24)
        return 12 if self.view.compact else 28

    def body_rect(self, rect, index):
        body = QRect(rect)
        if self.view.horizontal:body.setLeft(body.left() + self.prefix(index))
        else:body.setTop(body.top() + self.prefix(index))
        return body

    def sizeHint(self, option, index):
        if self.view.horizontal:
            width = max(132, min(208, self.view.fontMetrics().horizontalAdvance(index.data() or '') + 54))
            return QSize(width + self.prefix(index) + 4, 44)
        return QSize(max(44, self.view.viewport().width()), 44 + self.prefix(index))

    def paint(self, painter, option, index):
        colors = self.view.colors
        body = self.body_rect(option.rect, index).adjusted(0, 0, -4 if self.view.horizontal else 0, 0)
        group = index.data(GROUP_ROLE) or ''
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if group:
            painter.setPen(QColor(colors['muted']))
            font = painter.font();font.setBold(True);font.setPointSizeF(max(8, font.pointSizeF()-1))
            painter.setFont(font)
            if self.view.horizontal:
                area = QRect(option.rect.left()+6, option.rect.top(), self.prefix(index)-12, 44)
                painter.drawText(area, Qt.AlignmentFlag.AlignVCenter, option.fontMetrics.elidedText(group, Qt.TextElideMode.ElideRight, area.width()))
            elif self.view.compact:
                y = option.rect.top()+6
                painter.setPen(QColor(colors['border']));painter.drawLine(option.rect.left()+4,y,option.rect.right()-4,y)
            else:
                area = QRect(option.rect.left()+12, option.rect.top()+4, option.rect.width()-20, 24)
                painter.drawText(area, Qt.AlignmentFlag.AlignVCenter, option.fontMetrics.elidedText(group, Qt.TextElideMode.ElideRight, area.width()))
        painter.setFont(option.font)
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        if selected or option.state & QStyle.StateFlag.State_MouseOver:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(colors['selected'] if selected else colors['hover']))
            painter.drawRoundedRect(QRectF(body), 8, 8)
        profile_icon = index.data(Qt.ItemDataRole.DecorationRole)
        if profile_icon:
            profile_icon.paint(painter,QRect(body.left()+10, body.top()+10,24,24))
        if not self.view.compact:
            area = body.adjusted(44,0,-10,0)
            painter.setPen(QColor(colors['text']))
            text = option.fontMetrics.elidedText(index.data() or '', Qt.TextElideMode.ElideRight, area.width())
            painter.drawText(area, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, text)
        if option.state & QStyle.StateFlag.State_HasFocus:
            painter.setPen(QPen(QColor('#3584e4'),1));painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(QRectF(body.adjusted(1,1,-1,-1)),7,7)
        painter.restore()


class ProfileList(QListWidget):
    def __init__(self):
        super().__init__()
        self.horizontal = False
        self.compact = False
        self.colors = dict(text='#303236',muted='#72767a',border='#d8d8d8',selected='#dceafb',hover='#e5e5e5')
        self.setItemDelegate(ProfileDelegate(self))
        self.setMouseTracking(True)
        self.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)

    def profile_at(self, point):
        item = self.itemAt(point)
        if item is None:return None
        index = self.indexFromItem(item)
        body = self.itemDelegate().body_rect(self.visualItemRect(item), index)
        return item if body.contains(point) else None

    def mousePressEvent(self, event):
        if self.itemAt(event.position().toPoint()) and not self.profile_at(event.position().toPoint()):
            event.accept();return
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if self.itemAt(event.position().toPoint()) and not self.profile_at(event.position().toPoint()):
            event.accept();return
        super().mouseDoubleClickEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Menu or (event.key() == Qt.Key.Key_F10 and event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
            item = self.currentItem()
            if item:
                self.scrollToItem(item)
                body = self.itemDelegate().body_rect(self.visualItemRect(item), self.indexFromItem(item))
                self.customContextMenuRequested.emit(body.center())
            event.accept();return
        super().keyPressEvent(event)

    def wheelEvent(self, event):
        if self.horizontal:
            bar = self.horizontalScrollBar()
            delta = event.pixelDelta().x() or event.pixelDelta().y() or event.angleDelta().x() or event.angleDelta().y()
            bar.setValue(bar.value()-delta);event.accept();return
        super().wheelEvent(event)


class DesktopUIMixin:
    def build_ui(self):
        root = QWidget()
        root.setObjectName('centralRoot')
        self.setCentralWidget(root)
        outer = QBoxLayout(QBoxLayout.Direction.LeftToRight, root)
        self.outer_layout = outer
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        self.sidebar = QWidget()
        self.sidebar.setObjectName('sidebar')
        side = QBoxLayout(QBoxLayout.Direction.TopToBottom, self.sidebar)
        self.side_layout = side
        side.setContentsMargins(10, 12, 10, 12)
        self.sidebar_toolbar = QBoxLayout(QBoxLayout.Direction.LeftToRight)
        self.sidebar_toolbar.setSpacing(4)
        side.addLayout(self.sidebar_toolbar)
        self.sidebar_caption = QLabel('Contas')
        font = self.sidebar_caption.font(); font.setBold(True)
        self.sidebar_caption.setFont(font)
        side.addWidget(self.sidebar_caption)
        self.add_button = QToolButton()
        self.add_button.setIcon(icon('list-add'))
        self.add_button.setToolTip('Adicionar perfil')
        self.add_button.clicked.connect(self.add)
        self.add_button.hide()
        self.list = ProfileList()
        self.list.setAccessibleName('Perfis de conversa')
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list.setIconSize(QSize(24, 24))
        self.list.setSpacing(0)
        self.list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list.customContextMenuRequested.connect(self.show_profile_menu)
        self.previous_profiles = QToolButton()
        self.next_profiles = QToolButton()
        for button, preset, label, step in [(self.previous_profiles,'previous','Perfis anteriores',-1),(self.next_profiles,'next','Próximos perfis',1)]:
            button.setProperty('iconPreset',preset)
            button.setIcon(icon(preset));button.setToolTip(label);button.setAccessibleName(label)
            button.setFixedSize(32,44)
            button.clicked.connect(lambda checked=False,direction=step:self.scroll_profiles(direction))
            button.hide()
        side.addWidget(self.previous_profiles)
        side.addWidget(self.list, 1)
        side.addWidget(self.next_profiles)
        self.list.horizontalScrollBar().rangeChanged.connect(lambda *_:self.update_profile_overflow())
        self.list.horizontalScrollBar().valueChanged.connect(lambda *_:self.update_profile_overflow())
        outer.addWidget(self.sidebar)
        content = QVBoxLayout()
        self.content_layout = content
        content.setContentsMargins(0, 0, 0, 0)
        outer.addLayout(content, 1)
        self.sidebar_toggle = QToolButton()
        self.sidebar_toggle.setIcon(icon('sidebar-show'))
        self.sidebar_toggle.setAccessibleName('Alternar lista de contas')
        self.sidebar_toggle.clicked.connect(self.toggle_sidebar)
        self.sidebar_toggle.setFixedSize(44,44)
        self.status = QLabel('Selecione ou adicione um perfil')
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status.setTextFormat(Qt.TextFormat.PlainText)
        self.status.setWordWrap(True)
        side.addWidget(self.status)
        self.menu_button = QToolButton()
        self.menu_button.setIcon(icon('preferences-system'))
        self.menu_button.setAccessibleName('Configurações')
        self.menu_button.setToolTip('Configurações')
        self.menu_button.setFixedSize(44,44)
        self.menu_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        menu = QMenu(self.menu_button)
        menu.addAction(icon('list-add'), 'Adicionar perfil…', self.add)
        menu.addSeparator()
        self.profile_menu = QMenu(self.list)
        self.reload_button = self.profile_menu.addAction(icon('view-refresh'), 'Recarregar conta', self.reload)
        self.profile_menu.addSeparator()
        for attr, label, theme, callback in [
            ('rename_button', 'Editar perfil…', 'document-edit', self.rename),
            ('archive_button', 'Arquivar perfil…', 'folder-download', self.remove),
            ('restore_button', 'Restaurar perfil…', 'edit-undo', self.restore),
        ]:
            action = QAction(icon(theme), label, self)
            action.triggered.connect(callback)
            (menu if attr == 'restore_button' else self.profile_menu).addAction(action); setattr(self, attr, action)
        photo_menu = self.profile_menu.addMenu(icon('user'), 'Foto do perfil')
        photo_menu.setToolTipsVisible(True)
        photo_menu.menuAction().setToolTip('A foto automática depende da sua própria foto disponível no WhatsApp; quando indisponível, será usado o ícone.')
        self.photo_file_action = photo_menu.addAction('Usar foto do computador…', self.choose_profile_photo)
        self.photo_auto_action = photo_menu.addAction('Usar foto automática do WhatsApp', self.use_automatic_photo)
        self.photo_auto_action.setToolTip('Usa somente sua própria foto quando ela estiver disponível; caso contrário, mantém o ícone.')
        self.photo_icon_action = photo_menu.addAction('Usar somente ícone', self.use_profile_icon)
        self.profile_menu.addSeparator()
        self.group_action = self.profile_menu.addAction('Grupo personalizado…', self.set_profile_group)
        self.mute_action = self.profile_menu.addAction('Silenciar avisos do sistema')
        self.mute_action.setCheckable(True)
        self.mute_action.triggered.connect(self.toggle_profile_notifications)
        self.seen_action = self.profile_menu.addAction('Limpar indicador de notificação', self.clear_selected_notification)
        menu.addSeparator()
        self.preferences_action = menu.addAction(icon('preferences-system'), 'Preferências…', self.show_preferences)
        menu.addSeparator()
        self.quit_action = menu.addAction(icon('application-exit'), 'Sair da central', self.quit_app)
        self.profile_header = QAction(self)
        self.profile_header.setEnabled(False)
        for action in list(self.profile_menu.actions()):self.profile_menu.removeAction(action)
        self.profile_menu.addAction(self.profile_header)
        self.profile_menu.addSeparator()
        self.profile_menu.addAction(self.rename_button)
        self.profile_menu.addMenu(photo_menu)
        self.profile_menu.addAction(self.group_action)
        self.profile_menu.addSeparator()
        self.profile_menu.addAction(self.reload_button)
        self.profile_menu.addSeparator()
        self.profile_menu.addAction(self.mute_action)
        self.profile_menu.addAction(self.seen_action)
        self.profile_menu.addSeparator()
        self.profile_menu.addAction(self.archive_button)
        self.menu_button.setMenu(menu)
        for action, preset in [(menu.actions()[0], 'list-add'), (self.reload_button,'view-refresh'),
                (self.rename_button,'document-edit'), (self.archive_button,'folder-download'),
                (self.restore_button,'edit-undo'), (photo_menu.menuAction(),'user'),
                (self.preferences_action,'preferences-system'), (self.quit_action,'application-exit'),
                (self.group_action,'group'), (self.mute_action,'mute'), (self.seen_action,'seen')]:
            action.setProperty('iconPreset', preset)
        for button in (self.sidebar_toggle,):
            self.sidebar_toolbar.addWidget(button)
        side.addWidget(self.menu_button, 0, Qt.AlignmentFlag.AlignLeft)
        self.stack = QStackedWidget()
        welcome = QLabel('Adicione um perfil de WhatsApp, Telegram ou Chatwoot.\nEntre na conta pela tela do serviço.\n\nCada perfil mantém uma sessão independente.')
        welcome.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome.setWordWrap(True)
        welcome.setContentsMargins(24, 24, 24, 24)
        self.stack.addWidget(welcome)
        content.addWidget(self.stack, 1)
        self.list.currentRowChanged.connect(self.select)
        self.apply_sidebar(False)
        self.apply_gnome_style()

    def apply_gnome_style(self):
        theme = self.settings.get('theme', 'system')
        scheme = QApplication.styleHints().colorScheme()
        dark = theme == 'dark' or (theme == 'system' and (scheme == Qt.ColorScheme.Dark or (scheme == Qt.ColorScheme.Unknown and self._system_palette.window().color().lightness() < 128)))
        palette = QPalette(self._system_palette)
        if theme != 'system':
            for role, color in [(QPalette.ColorRole.Window, '#242424' if dark else '#fafafa'),
                                (QPalette.ColorRole.WindowText, '#eeeeec' if dark else '#242424'),
                                (QPalette.ColorRole.Base, '#242424' if dark else '#ffffff'),
                                (QPalette.ColorRole.Text, '#eeeeec' if dark else '#242424'),
                                (QPalette.ColorRole.ButtonText, '#eeeeec' if dark else '#242424')]:
                palette.setColor(role, QColor(color))
        QApplication.instance().setPalette(palette)
        self.setPalette(palette)
        main, side, text, border, hover, selected, muted = (
            ('#242424', '#303030', '#eeeeec', '#505050', '#424242', '#224b70', '#92928e')
            if dark else
            ('#ffffff', '#f2f2f2', '#303236', '#d8d8d8', '#e5e5e5', '#dceafb', '#72767a')
        )
        self.list.colors = dict(text=text,muted=muted,border=border,selected=selected,hover=hover)
        self.previous_profiles.setIcon(icon('previous'));self.next_profiles.setIcon(icon('next'))
        self.list.viewport().update()
        self.menu_button.setIcon(notification_icon(icon('preferences-system'), bool(self.pending_notifications)))
        for menu in (self.menu_button.menu(), self.profile_menu):
            for action in menu.actions():
                preset = action.property('iconPreset')
                if preset: action.setIcon(icon(preset))
        self.sidebar_toggle.setIcon(icon('sidebar-show' if self.settings.get('sidebar_collapsed') else 'sidebar-hide'))
        for i, account in enumerate(self.accounts):
            if i < self.list.count():self.list.item(i).setIcon(self.account_icon(account))
        check_asset = Path(__file__).with_name('check-symbolic.svg').as_posix()
        self.setStyleSheet(f"""
            QWidget#centralRoot {{ background: {main}; }}
            QWidget#sidebar {{ background: {side}; }}
            QLabel {{ color: {text}; }}
            QListWidget {{ border: 0; background: transparent; color: {text}; }}
            QListWidget::item {{ padding: 0; }}
            QToolButton:focus, QPushButton:focus, QComboBox:focus, QLineEdit:focus {{ border: 1px solid #3584e4; }}
            QToolButton {{ border: 0;
                border-radius: 6px; background: transparent; color: {text}; }}
            QToolButton::menu-indicator {{ image: none; width: 0; }}
            QToolButton:hover {{ background: {hover}; }}
            QToolButton:pressed {{ background: {selected}; }}
            QPushButton {{ padding: 6px 10px; border-radius: 7px; border: 1px solid {border};
                background: {side}; color: {text}; }}
            QPushButton:hover {{ background: {hover}; }}
            QPushButton:pressed {{ background: {selected}; }}
            QPushButton:disabled, QToolButton:disabled {{ color: {muted}; }}
            QLineEdit, QComboBox {{ padding: 6px; border: 1px solid {border};
                border-radius: 6px; background: {main}; color: {text}; }}
            QLineEdit:focus, QComboBox:focus {{ border: 1px solid #3584e4; }}
            QDialog, QMenu, QComboBox QAbstractItemView {{ background: {main}; color: {text}; }}
            QMenu {{ border: 1px solid {border}; padding: 6px; }}
            QMenu::item {{ padding: 7px 16px; border-radius: 6px; }}
            QMenu::item:selected {{ background: {selected}; }}
            QMenu::item:disabled {{ color: {muted}; }}
            QScrollArea {{ border: 0; background: transparent; }}
            QCheckBox {{ min-height: 22px; spacing: 8px; color: {text}; }}
            QCheckBox:disabled {{ color: {muted}; }}
            QCheckBox::indicator {{ width: 16px; height: 16px; border: 1px solid {muted}; border-radius: 4px; background: {main}; }}
            QCheckBox::indicator:checked {{ background: #3584e4; border: 1px solid #3584e4; image: url('{check_asset}'); }}
            QScrollBar:vertical {{ background: {side}; width: 10px; border: 0; }}
            QScrollBar::handle:vertical {{ background: {muted}; min-height: 24px; border-radius: 5px; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
            QGroupBox {{ border: 0; margin-top: 20px; padding-top: 6px; color: {text}; }}
            QGroupBox::title {{ subcontrol-origin: margin; subcontrol-position: top left; font-weight: bold; }}
            QToolTip {{ background: {main}; color: {text}; border: 1px solid {border}; padding: 4px; }}
        """)
        self.sidebar_toggle.setFixedSize(44,44)
        self.menu_button.setFixedSize(44,44)
        self.previous_profiles.setFixedSize(32,44)
        self.next_profiles.setFixedSize(32,44)

    def scroll_profiles(self, direction):
        bar = self.list.horizontalScrollBar()
        bar.setValue(bar.value()+direction*max(120,self.list.viewport().width()//2))

    def update_profile_overflow(self):
        horizontal = self.settings.get('bar_position','left') != 'left'
        bar = self.list.horizontalScrollBar()
        overflow = horizontal and bar.maximum()>0
        self.previous_profiles.setVisible(overflow)
        self.next_profiles.setVisible(overflow)
        self.previous_profiles.setEnabled(bar.value()>0)
        self.next_profiles.setEnabled(bar.value()<bar.maximum())

    def apply_sidebar(self, collapsed):
        position = self.settings.get('bar_position', 'left')
        horizontal = position != 'left'
        compact = collapsed and not horizontal
        self.list.horizontal = horizontal
        self.list.compact = compact
        self.outer_layout.setDirection(QBoxLayout.Direction.TopToBottom if horizontal else QBoxLayout.Direction.LeftToRight)
        self.outer_layout.removeWidget(self.sidebar)
        self.outer_layout.insertWidget(1 if position == 'bottom' else 0, self.sidebar)
        self.sidebar.setMinimumSize(0,0);self.sidebar.setMaximumSize(16777215,16777215)
        if horizontal:self.sidebar.setFixedHeight(52)
        else:self.sidebar.setFixedWidth(64 if compact else 240)
        self.side_layout.setContentsMargins(6 if horizontal else 10,4 if horizontal else 10,6 if horizontal else 10,4 if horizontal else 10)
        self.side_layout.setSpacing(4 if horizontal else 0)
        self.sidebar_toggle.setVisible(not horizontal)
        self.side_layout.setDirection(QBoxLayout.Direction.LeftToRight if horizontal else QBoxLayout.Direction.TopToBottom)
        self.list.setFlow(QListWidget.Flow.LeftToRight if horizontal else QListWidget.Flow.TopToBottom)
        self.list.setWrapping(False)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff if horizontal else Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.sidebar_caption.hide()
        account = self.selected_account()
        failed = bool(account and self.load_states.get(account['id'])=='error')
        self.status.setVisible(failed and not horizontal and not compact)
        self.sidebar_toolbar.setDirection(QBoxLayout.Direction.TopToBottom)
        self.add_button.setText('')
        self.sidebar_toggle.setToolTip('Expandir contas' if compact else 'Recolher contas')
        self.sidebar_toggle.setIcon(icon('sidebar-show' if compact else 'sidebar-hide'))
        for index, account in enumerate(self.accounts):
            item = self.list.item(index)
            if item is None:continue
            name = account['name'];pending = account['id'] in self.pending_notifications
            group = self.profile_group(account)
            previous = self.profile_group(self.accounts[index-1]) if index else None
            item.setData(GROUP_ROLE,group if group and group != previous else '')
            tooltip = name+' · '+SERVICES[account.get('service','whatsapp')]['name']
            if group:tooltip += ' · '+group
            if pending:tooltip += ' · Notificação recebida'
            item.setToolTip(tooltip);item.setIcon(self.account_icon(account))
            item.setData(Qt.ItemDataRole.AccessibleDescriptionRole,tooltip)
            item.setText('' if compact else name)
            item.setData(Qt.ItemDataRole.AccessibleTextRole,name+(' — Notificação recebida' if pending else ''))
        self.menu_button.setIcon(notification_icon(icon('preferences-system'),bool(self.pending_notifications)))
        self.menu_button.setToolTip('Configurações'+(' · Há perfis com notificações' if self.pending_notifications else ''))
        self.list.doItemsLayout()
        self.update_profile_overflow()
        self.list.viewport().update()


class PreferencesDialog(QDialog):
    def __init__(self, parent, settings, accounts, can_background):
        super().__init__(parent)
        self.setWindowTitle('Preferências')
        self.resize(560, 680)
        self.original = dict(settings)
        layout = QVBoxLayout(self)
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        body = QWidget(); form = QVBoxLayout(body)
        appearance_title = QLabel('Aparência')
        appearance_font = appearance_title.font();appearance_font.setBold(True);appearance_title.setFont(appearance_font)
        form.addWidget(appearance_title)
        appearance = QFormLayout()
        self.theme = QComboBox()
        for label, value in [('Automático (GNOME)', 'system'), ('Claro', 'light'), ('Escuro', 'dark')]:
            self.theme.addItem(label, value)
        self.bar_position = QComboBox()
        for label, value in [('Esquerda', 'left'), ('Parte de cima', 'top'), ('Parte de baixo', 'bottom')]:
            self.bar_position.addItem(label, value)
        self.group_mode = QComboBox()
        for label, value in [('Sem grupos', 'none'), ('Por tipo de chat', 'service'), ('Grupos personalizados', 'custom')]:
            self.group_mode.addItem(label, value)
        for key, label in [('theme', 'Tema da central:'), ('bar_position', 'Posição da barra:'), ('group_mode', 'Agrupar perfis:')]:
            combo = getattr(self, key)
            combo.setCurrentIndex(max(0, combo.findData(settings.get(key, {'theme':'system', 'bar_position':'left', 'group_mode':'none'}[key]))))
            appearance.addRow(label, combo)
        form.addLayout(appearance)
        form.addWidget(QLabel('O tema das conversas é definido dentro de cada serviço.'))
        self.group_fields = {}
        group_hint = QLabel('Para definir o grupo de uma conta, clique com o botão direito no perfil → Grupo personalizado.')
        group_hint.setWordWrap(True)
        form.addWidget(group_hint)
        behavior_title = QLabel('Inicialização e segundo plano')
        behavior_font = behavior_title.font();behavior_font.setBold(True);behavior_title.setFont(behavior_font)
        form.addSpacing(12);form.addWidget(behavior_title)
        self.startup_enabled = QCheckBox('Iniciar a central ao entrar no sistema')
        self.startup_enabled.setChecked(settings.get('startup_enabled', False))
        if os.environ.get('FLATPAK_ID'):
            self.startup_enabled.setChecked(False)
            self.startup_enabled.setEnabled(False)
            self.startup_enabled.setToolTip('Inicialização automática via Flatpak ainda não disponível nesta versão.')
        form.addWidget(self.startup_enabled)
        self.start_hidden = QCheckBox('Iniciar com a janela oculta')
        self.start_hidden.setChecked(settings.get('start_hidden', False) and can_background)
        self.start_hidden.setEnabled(can_background)
        form.addWidget(self.start_hidden)
        close_form = QFormLayout()
        self.close_action = QComboBox()
        self.close_action.addItem('Continuar em segundo plano', 'background')
        self.close_action.addItem('Sair da central', 'exit')
        self.close_action.setCurrentIndex(0 if settings.get('close_action', 'background') == 'background' and can_background else 1)
        if not can_background:
            self.close_action.model().item(0).setEnabled(False)
        close_form.addRow('Ao fechar a janela:', self.close_action)
        self.startup_mode = QComboBox()
        for text, value in [('Somente os perfis selecionados', 'selected'), ('Todos os perfis', 'all'), ('Nenhum perfil', 'none')]:
            self.startup_mode.addItem(text, value)
        self.startup_mode.setCurrentIndex(max(0, self.startup_mode.findData(settings.get('startup_mode', 'selected'))))
        close_form.addRow('Carregar ao iniciar:', self.startup_mode)
        form.addLayout(close_form)
        self.profiles_box = QGroupBox('Perfis para carregar ao iniciar')
        profiles_layout = QVBoxLayout(self.profiles_box)
        self.startup_checks = {}
        for account in accounts:
            key = account['id']; name = account['name']
            start = QCheckBox(name)
            start.setToolTip(name); start.setAccessibleName(name)
            start.setText(start.fontMetrics().elidedText(name, Qt.TextElideMode.ElideRight, 380))
            start.setChecked(key in settings.get('startup_profiles', []))
            profiles_layout.addWidget(start); self.startup_checks[key] = start
        if not accounts:
            profiles_layout.addWidget(QLabel('Nenhum perfil disponível.'))
        form.addWidget(self.profiles_box)
        self.startup_mode.currentIndexChanged.connect(self.update_startup_controls)
        self.update_startup_controls()
        hint = QLabel('Mais contas carregadas usam mais memória e processamento. Avisos dependem da conta carregada e das permissões do sistema. Sons das conversas são controlados pelo próprio serviço.\n\nPara reabrir a janela, use o ícone da central no menu de aplicativos ou na bandeja.')
        if not can_background:
            hint.setText(hint.text() + '\n\nNão há um meio confirmado de reabrir a central nesta sessão. Use Sair para encerrar.')
        hint.setWordWrap(True); form.addWidget(hint); form.addStretch()
        scroll.setWidget(body); layout.addWidget(scroll)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText('Salvar')
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText('Cancelar')
        buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def update_startup_controls(self):
        self.profiles_box.setEnabled(self.startup_mode.currentData() == 'selected')

    def values(self):
        result = dict(self.original)
        groups = dict(self.original.get('profile_groups', {}))
        for key, field in self.group_fields.items():
            value = field.text().strip()
            if value: groups[key] = value
            else: groups.pop(key, None)
        result.update(theme=self.theme.currentData(), bar_position=self.bar_position.currentData(),
            group_mode=self.group_mode.currentData(), profile_groups=groups,
            startup_enabled=self.startup_enabled.isChecked(), start_hidden=self.start_hidden.isChecked(),
            close_action=self.close_action.currentData(), startup_mode=self.startup_mode.currentData(),
            startup_profiles=[key for key in self.original.get('startup_profiles', []) if key not in self.startup_checks] + [key for key, box in self.startup_checks.items() if box.isChecked()])
        result.setdefault('sidebar_collapsed', False)
        return result
