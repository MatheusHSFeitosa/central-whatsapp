"""Widgets de apresentação; persistência e sessões pertencem à janela principal."""
import os
from PySide6.QtCore import Qt, QSize, QRectF
from PySide6.QtGui import QAction, QIcon, QPixmap, QPainter, QPen
from PySide6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QToolButton, QListWidget, QStackedWidget, QMenu, QDialog, QDialogButtonBox,
    QApplication, QStyle, QFormLayout, QLineEdit, QComboBox, QCheckBox, QGroupBox, QScrollArea)

ICON_PRESETS = {
    'user': ('Pessoa', 'avatar-default'),
    'briefcase': ('Trabalho', 'user-business'),
    'store': ('Loja', 'applications-internet'),
    'building': ('Empresa', 'folder'),
    'headset': ('Atendimento', 'audio-headphones'),
    'home': ('Casa', 'user-home'),
}


def icon(preset):
    theme = ICON_PRESETS.get(preset, ('', preset))[1]
    themed = QIcon.fromTheme(theme)
    if not themed.isNull():
        return themed
    if preset not in ICON_PRESETS:
        standards = {
            'list-add': QStyle.StandardPixmap.SP_FileDialogNewFolder,
            'view-refresh': QStyle.StandardPixmap.SP_BrowserReload,
            'sidebar-show': QStyle.StandardPixmap.SP_ArrowRight,
            'sidebar-hide': QStyle.StandardPixmap.SP_ArrowLeft,
            'open-menu-symbolic': QStyle.StandardPixmap.SP_TitleBarMenuButton,
            'document-edit': QStyle.StandardPixmap.SP_FileDialogDetailedView,
            'folder-download': QStyle.StandardPixmap.SP_DirClosedIcon,
            'edit-undo': QStyle.StandardPixmap.SP_ArrowBack,
            'preferences-system': QStyle.StandardPixmap.SP_FileDialogContentsView,
            'application-exit': QStyle.StandardPixmap.SP_DialogCloseButton,
        }
        return QApplication.style().standardIcon(standards.get(preset, QStyle.StandardPixmap.SP_FileIcon))
    # Six small line drawings stay distinct when the desktop has no icon theme.
    image = QPixmap(32, 32)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(QApplication.palette().text().color(), 2))
    if preset == 'user':
        painter.drawEllipse(QRectF(11, 5, 10, 10))
        painter.drawArc(QRectF(6, 17, 20, 17), 0, 180 * 16)
    elif preset == 'briefcase':
        painter.drawRoundedRect(QRectF(4, 11, 24, 17), 2, 2)
        painter.drawRoundedRect(QRectF(11, 5, 10, 6), 1, 1)
        painter.drawLine(4, 18, 28, 18); painter.drawLine(16, 16, 16, 21)
    elif preset == 'store':
        painter.drawRect(QRectF(6, 14, 20, 14))
        painter.drawLine(4, 14, 28, 14); painter.drawLine(4, 14, 8, 6)
        painter.drawLine(8, 6, 24, 6); painter.drawLine(24, 6, 28, 14)
        painter.drawRect(QRectF(13, 20, 7, 8))
    elif preset == 'building':
        painter.drawRect(QRectF(7, 4, 18, 24))
        for x in (12, 20):
            for y in (9, 15, 21):
                painter.drawPoint(x, y)
        painter.drawLine(3, 28, 29, 28)
    elif preset == 'headset':
        painter.drawArc(QRectF(5, 5, 22, 23), 0, 180 * 16)
        painter.drawRoundedRect(QRectF(4, 15, 5, 10), 2, 2)
        painter.drawRoundedRect(QRectF(23, 15, 5, 10), 2, 2)
        painter.drawLine(25, 25, 25, 28); painter.drawLine(25, 28, 17, 28)
    else:
        painter.drawLine(3, 15, 16, 4); painter.drawLine(16, 4, 29, 15)
        painter.drawLine(7, 12, 7, 28); painter.drawLine(7, 28, 25, 28)
        painter.drawLine(25, 28, 25, 12); painter.drawRect(QRectF(13, 19, 6, 9))
    painter.end()
    return QIcon(image)


def edit_profile_dialog(parent, title, name='', icon='user'):
    dialog = QDialog(parent)
    dialog.setWindowTitle(title)
    layout = QVBoxLayout(dialog)
    form = QFormLayout()
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
        return field.text().strip(), choices.currentData()
    return None


class DesktopUIMixin:
    def build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        outer = QHBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        self.sidebar = QWidget()
        self.sidebar.setObjectName('sidebar')
        side = QVBoxLayout(self.sidebar)
        side.setContentsMargins(10, 12, 10, 12)
        self.sidebar_caption = QLabel('Contas')
        font = self.sidebar_caption.font(); font.setBold(True)
        self.sidebar_caption.setFont(font)
        side.addWidget(self.sidebar_caption)
        self.add_button = QPushButton('Adicionar perfil')
        self.add_button.setIcon(icon('list-add'))
        self.add_button.setToolTip('Adicionar perfil')
        self.add_button.clicked.connect(self.add)
        side.addWidget(self.add_button)
        self.list = QListWidget()
        self.list.setAccessibleName('Perfis do WhatsApp')
        self.list.setIconSize(QSize(24, 24))
        self.list.setSpacing(3)
        side.addWidget(self.list, 1)
        self.sidebar_hint = QLabel('As contas abertas continuam ativas enquanto a central estiver funcionando.')
        self.sidebar_hint.setWordWrap(True)
        self.sidebar_hint.setMaximumWidth(200)
        side.addWidget(self.sidebar_hint)
        outer.addWidget(self.sidebar)
        content = QVBoxLayout()
        content.setContentsMargins(8, 8, 8, 8)
        outer.addLayout(content, 1)
        header = QHBoxLayout()
        self.sidebar_toggle = QToolButton()
        self.sidebar_toggle.setIcon(icon('sidebar-show'))
        self.sidebar_toggle.setAccessibleName('Alternar lista de contas')
        self.sidebar_toggle.clicked.connect(self.toggle_sidebar)
        header.addWidget(self.sidebar_toggle)
        self.status = QLabel('Selecione ou adicione um perfil')
        self.status.setTextFormat(Qt.TextFormat.PlainText)
        self.status.setWordWrap(True)
        header.addWidget(self.status, 1)
        self.reload_button = QToolButton()
        self.reload_button.setIcon(icon('view-refresh'))
        self.reload_button.setToolTip('Recarregar conta selecionada')
        self.reload_button.setAccessibleName('Recarregar conta selecionada')
        self.reload_button.clicked.connect(self.reload)
        header.addWidget(self.reload_button)
        self.menu_button = QToolButton()
        self.menu_button.setIcon(icon('open-menu-symbolic'))
        self.menu_button.setAccessibleName('Menu da central')
        self.menu_button.setToolTip('Menu da central')
        self.menu_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        menu = QMenu(self.menu_button)
        for attr, label, theme, callback in [
            ('rename_button', 'Editar perfil…', 'document-edit', self.rename),
            ('archive_button', 'Arquivar perfil…', 'folder-download', self.remove),
            ('restore_button', 'Restaurar perfil…', 'edit-undo', self.restore),
        ]:
            action = QAction(icon(theme), label, self)
            action.triggered.connect(callback)
            menu.addAction(action); setattr(self, attr, action)
        menu.addSeparator()
        self.preferences_action = menu.addAction(icon('preferences-system'), 'Preferências…', self.show_preferences)
        menu.addSeparator()
        self.quit_action = menu.addAction(icon('application-exit'), 'Sair da central', self.quit_app)
        self.menu_button.setMenu(menu)
        header.addWidget(self.menu_button)
        content.addLayout(header)
        self.stack = QStackedWidget()
        welcome = QLabel('Adicione um perfil e conecte seu WhatsApp pelo QR Code.\n\nCada perfil mantém uma sessão independente.')
        welcome.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome.setWordWrap(True)
        welcome.setContentsMargins(24, 24, 24, 24)
        self.stack.addWidget(welcome)
        content.addWidget(self.stack, 1)
        self.list.currentRowChanged.connect(self.select)
        self.apply_sidebar(False)

    def apply_sidebar(self, collapsed):
        self.sidebar.setFixedWidth(64 if collapsed else 220)
        self.sidebar_caption.setVisible(not collapsed)
        self.sidebar_hint.setVisible(not collapsed)
        self.add_button.setText('' if collapsed else 'Adicionar perfil')
        self.add_button.setAccessibleName('Adicionar perfil')
        self.sidebar_toggle.setToolTip('Expandir contas' if collapsed else 'Recolher contas')
        self.sidebar_toggle.setIcon(icon('sidebar-show' if collapsed else 'sidebar-hide'))
        for index in range(self.list.count()):
            item = self.list.item(index)
            name = item.toolTip() or item.text()
            item.setToolTip(name)
            item.setText('' if collapsed else name)
            item.setData(Qt.ItemDataRole.AccessibleTextRole, name)


class PreferencesDialog(QDialog):
    def __init__(self, parent, settings, accounts, can_background):
        super().__init__(parent)
        self.setWindowTitle('Preferências')
        self.resize(510, 570)
        self.original = dict(settings)
        layout = QVBoxLayout(self)
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        body = QWidget(); form = QVBoxLayout(body)
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
        self.muted_checks = {}
        notifications_box = QGroupBox('Avisos do sistema por perfil')
        notifications_layout = QVBoxLayout(notifications_box)
        for account in accounts:
            key = account['id']; name = account['name']
            start = QCheckBox(name); start.setChecked(key in settings.get('startup_profiles', []))
            profiles_layout.addWidget(start); self.startup_checks[key] = start
            notifications = QCheckBox(name); notifications.setChecked(key not in settings.get('muted_profiles', []))
            notifications_layout.addWidget(notifications); self.muted_checks[key] = notifications
        if not accounts:
            profiles_layout.addWidget(QLabel('Nenhum perfil disponível.'))
            notifications_layout.addWidget(QLabel('Adicione um perfil para configurar notificações.'))
        form.addWidget(self.profiles_box); form.addWidget(notifications_box)
        self.startup_mode.currentIndexChanged.connect(self.update_startup_controls)
        self.update_startup_controls()
        hint = QLabel('Mais contas carregadas usam mais memória e processamento. Avisos dependem da conta carregada e das permissões do sistema. Sons das conversas são controlados pelo próprio WhatsApp.\n\nPara reabrir a janela, use o ícone da central no menu de aplicativos ou na bandeja.')
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
        result.update(startup_enabled=self.startup_enabled.isChecked(), start_hidden=self.start_hidden.isChecked(),
            close_action=self.close_action.currentData(), startup_mode=self.startup_mode.currentData(),
            startup_profiles=[key for key, box in self.startup_checks.items() if box.isChecked()],
            muted_profiles=[key for key, box in self.muted_checks.items() if not box.isChecked()])
        result.setdefault('sidebar_collapsed', False)
        return result
