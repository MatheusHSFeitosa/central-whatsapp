"""Widgets de apresentação; persistência e sessões pertencem à janela principal."""
import os
from pathlib import Path
from services import SERVICES, normalize_custom_url
from split_workspace import ProfileArea, LegacyTestArea
from grouping import SERVICE_COLORS, group_name
from PySide6.QtCore import Qt, QSize, QRectF, QRect, QByteArray, QTimer, Signal
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtGui import QAction, QActionGroup, QIcon, QPixmap, QPainter, QPen, QPalette, QColor, QPainterPath
from PySide6.QtWidgets import (QWidget, QSizeGrip, QHBoxLayout, QVBoxLayout, QBoxLayout, QLabel, QPushButton,
    QToolButton, QListWidget, QStackedWidget, QDialogButtonBox,
    QApplication, QStyle, QFormLayout, QLineEdit, QComboBox, QCheckBox, QGroupBox, QScrollArea, QStyledItemDelegate, QAbstractItemView, QTabWidget, QSizePolicy)

from ui_widgets import icon, SYMBOLS, Dialog as QDialog, Menu as QMenu, FileDialog as QFileDialog, MessageBox as QMessageBox

ICON_PRESETS = {
    'user': ('Pessoa', 'avatar-default'),
    'briefcase': ('Trabalho', 'briefcase'),
    'store': ('Loja', 'shop'),
    'building': ('Empresa', 'office-building'),
    'headset': ('Atendimento', 'audio-headphones'),
    'home': ('Casa', 'user-home'),
}



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


def service_icon(service):
    if service not in SERVICES:return icon('user')
    if service == 'custom':
        image = QPixmap(64, 64)
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(SERVICE_COLORS['custom']))
        painter.drawEllipse(QRectF(0, 0, 64, 64))
        raw = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#ffffff" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">' + SYMBOLS['globe'] + '</svg>'
        QSvgRenderer(QByteArray(raw.encode())).render(painter, QRectF(11, 11, 42, 42))
        painter.end()
        return QIcon(image)
    image=QPixmap(64,64);image.fill(Qt.GlobalColor.transparent)
    painter=QPainter(image);painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    solid=service in ('telegram','chatwoot')
    painter.setPen(Qt.PenStyle.NoPen);painter.setBrush(QColor('#ffffff' if solid else SERVICE_COLORS[service]))
    painter.drawEllipse(QRectF(0,0,64,64))
    path=Path(__file__).with_name('service-icons')/(service+'.svg')
    try:
        fill=SERVICE_COLORS[service] if solid else '#ffffff'
        raw=path.read_bytes().replace(b'<svg ',('<svg fill="'+fill+'" ').encode(),1)
        QSvgRenderer(QByteArray(raw)).render(painter,QRectF(0,0,64,64) if solid else QRectF(8,8,48,48))
    except OSError:
        painter.setPen(QColor('#ffffff'));painter.drawText(QRect(0,0,64,64),Qt.AlignmentFlag.AlignCenter,SERVICES[service]['name'][0])
    painter.end();return QIcon(image)


def aligned_form():
    form = QFormLayout()
    form.setHorizontalSpacing(16)
    form.setVerticalSpacing(10)
    form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
    form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
    return form


def edit_profile_dialog(parent, title, name='', icon='user', service='whatsapp', editing=False,
                        *, group_options=(), group='', avatar_mode='service', photo_path='', group_forced=False, automatic_grouping=False, custom_url=''):
    dialog=QDialog(parent);dialog.setWindowTitle(title);dialog.resize(470,440)
    layout=QVBoxLayout(dialog);layout.setSpacing(12)
    preview=QLabel();preview.setFixedSize(64,64)
    preview.setAccessibleName('Imagem do perfil')
    layout.addWidget(preview,0,Qt.AlignmentFlag.AlignHCenter)
    form=aligned_form()
    provider=QComboBox();provider.setObjectName('profileService')
    for key,config in SERVICES.items():provider.addItem(service_icon(key),config['name'],key)
    provider.setCurrentIndex(max(0,provider.findData(service)));provider.setEnabled(not editing)
    form.addRow('Serviço:',provider)
    address = QLineEdit(custom_url)
    address.setObjectName('profileCustomUrl')
    address.setPlaceholderText('https://chat.suaempresa.com')
    address.setMaxLength(2048)
    address.setReadOnly(editing and bool(custom_url))
    form.addRow('Endereço:', address)
    field=QLineEdit(name);field.setObjectName('profileName');field.setMaxLength(60)
    form.addRow('Nome:',field)
    groups=QComboBox();groups.setObjectName('profileGroup');groups.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon);groups.setMinimumContentsLength(12);groups.addItem('Sem grupo','')
    for value in group_options:groups.addItem(value,value)
    groups.addItem('Novo grupo…',None)
    groups.setCurrentIndex(max(0,groups.findData(group or '')))
    form.addRow('Grupo:',groups)
    new_group=QLineEdit();new_group.setObjectName('newGroupName');new_group.setMaxLength(40)
    new_group.setPlaceholderText('Nome do novo grupo');form.addRow('Novo grupo:',new_group)
    modes=QComboBox();modes.setObjectName('profileImageMode')
    for label,value in [('Logo do serviço','service'),('Foto do computador','file'),('Ícone predefinido','icon'),('Foto automática do WhatsApp','auto')]:modes.addItem(label,value)
    modes.setCurrentIndex(max(0,modes.findData(avatar_mode)))
    form.addRow('Imagem:',modes)
    choices=QComboBox();choices.setObjectName('profilePresetIcon')
    for key,(label,_) in ICON_PRESETS.items():choices.addItem(globals()['icon'](key),label,key)
    choices.setCurrentIndex(max(0,choices.findData(icon)));form.addRow('Ícone:',choices)
    choose_photo=QPushButton('Escolher foto…');choose_photo.setObjectName('chooseProfileImage')
    form.addRow('Foto:',choose_photo)
    layout.addLayout(form)
    error=QLabel();error.setWordWrap(True);error.hide();layout.addWidget(error)
    address.textChanged.connect(error.hide)
    touched=[bool(group_forced)]
    def update(*args):
        if automatic_grouping and not touched[0] and not editing:
            groups.blockSignals(True);groups.setCurrentIndex(max(0,groups.findData(SERVICES[provider.currentData()]['name'])));groups.blockSignals(False)
        form.setRowVisible(address, provider.currentData() in ('custom','chatwoot'))
        creating=groups.currentData() is None
        form.setRowVisible(new_group,creating)
        mode=modes.currentData()
        auto=modes.findData('auto');modes.model().item(auto).setEnabled(provider.currentData()=='whatsapp')
        if mode=='auto' and provider.currentData()!='whatsapp':
            modes.setCurrentIndex(modes.findData('service'));return
        form.setRowVisible(choices,mode=='icon');form.setRowVisible(choose_photo,mode=='file')
        image_icon=service_icon(provider.currentData()) if mode!='icon' else globals()['icon'](choices.currentData())
        if photo_path and mode in ('file','auto'):
            try:
                image=parent.avatar_manager._read(Path(photo_path))
                image=image.scaled(64,64,Qt.AspectRatioMode.KeepAspectRatioByExpanding,Qt.TransformationMode.SmoothTransformation)
                pixmap=QPixmap(64,64);pixmap.fill(Qt.GlobalColor.transparent)
                painter=QPainter(pixmap);painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                clip=QPainterPath();clip.addEllipse(QRectF(0,0,64,64));painter.setClipPath(clip)
                painter.drawImage(QRectF((64-image.width())/2,(64-image.height())/2,image.width(),image.height()),image)
                painter.end();image_icon=QIcon(pixmap)
            except (ValueError,OSError):pass
        preview.setPixmap(image_icon.pixmap(64,64))
    def pick_photo():
        nonlocal photo_path
        path,_=QFileDialog.getOpenFileName(dialog,'Escolher foto do perfil',str(Path.home()),'Imagens (*.png *.jpg *.jpeg *.webp)')
        if not path:return
        try:parent.avatar_manager._read(Path(path))
        except (ValueError,OSError) as failure:
            error.setText(str(failure));error.show();return
        photo_path=path;error.hide();update()
    groups.currentIndexChanged.connect(lambda *_:touched.__setitem__(0,True))
    groups.currentIndexChanged.connect(update)
    provider.currentIndexChanged.connect(update);modes.currentIndexChanged.connect(update);choices.currentIndexChanged.connect(update)
    choose_photo.clicked.connect(pick_photo)
    buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
    buttons.button(QDialogButtonBox.StandardButton.Ok).setText('Salvar');buttons.button(QDialogButtonBox.StandardButton.Cancel).setText('Cancelar')
    def accept():
        message=''
        if not field.text().strip():message='Informe um nome para o perfil.'
        elif groups.currentData() is None:
            try:value=group_name(new_group.text())
            except ValueError as failure:message=str(failure)
            else:
                if any(value.casefold()==existing.casefold() for existing in group_options):message='Este grupo já existe. Selecione-o na lista.'
        if not message and modes.currentData()=='file' and not photo_path:message='Escolha a foto do perfil ou use a logo do serviço.'
        if not message and provider.currentData() in ('custom','chatwoot'):
            try:
                address.setText(normalize_custom_url(address.text()))
            except ValueError as failure:
                message = str(failure)
        if message:error.setText(message);error.show();return
        dialog.accept()
    buttons.accepted.connect(accept);buttons.rejected.connect(dialog.reject);layout.addWidget(buttons)
    update();field.selectAll();field.setFocus()
    if dialog.exec()==QDialog.DialogCode.Accepted:
        creating=groups.currentData() is None
        return field.text().strip(),choices.currentData(),provider.currentData(),dict(
            group=new_group.text().strip() if creating else groups.currentData(),
            new_group=creating,group_touched=touched[0],avatar_mode=modes.currentData(),photo_path=photo_path if modes.currentData()=='file' else '',
            custom_url=address.text() if provider.currentData() in ('custom','chatwoot') else '')
    return None


GROUP_ROLE = Qt.ItemDataRole.UserRole + 1
COLLAPSED_ROLE = Qt.ItemDataRole.UserRole + 2
GROUP_COUNT_ROLE = Qt.ItemDataRole.UserRole + 3
GROUP_KEY_ROLE = Qt.ItemDataRole.UserRole + 4
GROUP_PENDING_ROLE = Qt.ItemDataRole.UserRole + 5
EMPTY_GROUP_ROLE = Qt.ItemDataRole.UserRole + 6
GROUP_COLOR_ROLE = Qt.ItemDataRole.UserRole + 7
GROUP_LAST_ROLE = Qt.ItemDataRole.UserRole + 8
GROUP_LABEL_ROLE = Qt.ItemDataRole.UserRole + 9
PROFILE_PENDING_ROLE = Qt.ItemDataRole.UserRole + 10


class LogoButton(QToolButton):
    """The same control shows the brand at rest and its action on hover."""
    def configure(self, logo, action_icon, label):
        self.logo_icon = logo;self.action_icon = action_icon
        self.setToolTip(label);self.setAccessibleName(label)
        self.setIcon(action_icon if self.underMouse() else logo)
        self.setIconSize(QSize(24,24))

    def enterEvent(self, event):
        if hasattr(self,'action_icon'):self.setIcon(self.action_icon)
        super().enterEvent(event)

    def leaveEvent(self, event):
        if hasattr(self,'logo_icon'):self.setIcon(self.logo_icon)
        super().leaveEvent(event)

    def focusInEvent(self, event):
        super().focusInEvent(event)

    def focusOutEvent(self, event):
        if hasattr(self,'logo_icon') and not self.underMouse():self.setIcon(self.logo_icon)
        super().focusOutEvent(event)


class ProfileDelegate(QStyledItemDelegate):
    """Paint profile tabs and independent group headers."""
    def __init__(self,view):
        super().__init__(view);self.view=view

    def prefix(self,index):
        group=index.data(GROUP_ROLE) or ''
        if not group:return 0
        if self.view.horizontal:
            count=index.data(GROUP_COUNT_ROLE) or 0
            label=group+(f' ({count})' if index.data(COLLAPSED_ROLE) else '')
            return min(190,self.view.fontMetrics().horizontalAdvance(label)+24)
        return 32 if index.data(COLLAPSED_ROLE) else (16 if self.view.compact else 30)

    def gap(self,index):
        return 6 if index.data(GROUP_LAST_ROLE) else 0

    def frame_rect(self,rect,index):
        return rect.adjusted(0,0,-self.gap(index) if self.view.horizontal else 0,0 if self.view.horizontal else -self.gap(index))

    def body_rect(self,rect,index):
        if index.data(COLLAPSED_ROLE) or index.data(EMPTY_GROUP_ROLE):return QRect()
        body=self.frame_rect(QRect(rect),index)
        if self.view.horizontal:body.setLeft(body.left()+self.prefix(index))
        else:body.setTop(body.top()+self.prefix(index))
        return body

    def sizeHint(self,option,index):
        gap=self.gap(index)
        if index.data(COLLAPSED_ROLE) or index.data(EMPTY_GROUP_ROLE):
            return QSize(self.prefix(index)+gap,36) if self.view.horizontal else QSize(max(44,self.view.viewport().width()),self.prefix(index)+gap)
        if self.view.horizontal:
            width=max(132,min(208,self.view.fontMetrics().horizontalAdvance(index.data() or '')+54))
            return QSize(width+self.prefix(index)+4+gap,36)
        return QSize(max(44,self.view.viewport().width()),44+self.prefix(index)+gap)

    def paint(self,painter,option,index):
        colors=self.view.colors;body=self.body_rect(option.rect,index).adjusted(2,1,-4 if self.view.horizontal else -2,-1)
        group=index.data(GROUP_ROLE) or ''
        painter.save();painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if group:
            collapsed=bool(index.data(COLLAPSED_ROLE));count=index.data(GROUP_COUNT_ROLE) or 0
            header=self.frame_rect(QRect(option.rect),index)
            if self.view.horizontal:header.setWidth(self.prefix(index))
            else:header.setHeight(self.prefix(index))
            if option.state & QStyle.StateFlag.State_MouseOver:
                painter.setPen(Qt.PenStyle.NoPen);painter.setBrush(QColor(colors['hover']));painter.drawRoundedRect(QRectF(header.adjusted(2,2,-2,-2)),6,6)
            color = index.data(GROUP_COLOR_ROLE)
            if color:
                painter.setPen(Qt.PenStyle.NoPen);painter.setBrush(QColor(color))
                painter.drawRoundedRect(QRectF(header.left()+4,header.center().y()-5,3,10),1.5,1.5)
            font=painter.font();font.setBold(True);font.setPointSizeF(max(8,font.pointSizeF()-1));painter.setFont(font)
            painter.setPen(QColor(colors['text'] if collapsed else colors['muted']))
            area=header.adjusted(11,0,-10 if index.data(GROUP_PENDING_ROLE) and collapsed else -8,0)
            if self.view.compact:
                if collapsed:painter.drawText(area,Qt.AlignmentFlag.AlignCenter,str(count))
            elif collapsed:
                counter=f' ({count})';width=painter.fontMetrics().horizontalAdvance(counter)
                name_area=area.adjusted(0,0,-width,0)
                painter.drawText(name_area,Qt.AlignmentFlag.AlignVCenter,painter.fontMetrics().elidedText(group,Qt.TextElideMode.ElideRight,max(0,name_area.width())))
                painter.drawText(QRect(area.right()-width+1,area.top(),width,area.height()),Qt.AlignmentFlag.AlignVCenter,counter)
            else:painter.drawText(area,Qt.AlignmentFlag.AlignVCenter,painter.fontMetrics().elidedText(group,Qt.TextElideMode.ElideRight,area.width()))
            if collapsed and index.data(GROUP_PENDING_ROLE):
                painter.setPen(Qt.PenStyle.NoPen);painter.setBrush(QColor('#e66100'));painter.drawEllipse(QRectF(header.right()-8,header.center().y()-3,6,6))
            if collapsed and option.state & QStyle.StateFlag.State_HasFocus:
                painter.setPen(QPen(QColor('#3584e4'),1));painter.setBrush(Qt.BrushStyle.NoBrush);painter.drawRoundedRect(QRectF(header.adjusted(3,3,-3,-3)),5,5)
        if not index.data(COLLAPSED_ROLE) and not index.data(EMPTY_GROUP_ROLE):
            painter.setFont(option.font)
            selected=bool(option.state & QStyle.StateFlag.State_Selected)
            if selected or option.state & QStyle.StateFlag.State_MouseOver:
                painter.setPen(Qt.PenStyle.NoPen);painter.setBrush(QColor(colors['selected'] if selected else colors['hover']));painter.drawRoundedRect(QRectF(body),7,7)
            image=index.data(Qt.ItemDataRole.DecorationRole)
            if selected:
                marker = QRectF(body.left()+8, body.bottom()-2, body.width()-16, 3) if self.view.horizontal else QRectF(body.left(), body.top()+8, 3, body.height()-16)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(colors['accent']))
                painter.drawRoundedRect(marker, 1.5, 1.5)
            avatar_x = body.center().x()-11 if self.view.compact else body.left()+9
            if image:
                image.paint(painter, QRect(avatar_x, body.center().y()-11, 24, 24))
            pending = bool(index.data(PROFILE_PENDING_ROLE))
            if pending:
                dot_x = avatar_x+21 if self.view.compact else body.right()-10
                dot_y = body.top()+5 if self.view.compact else body.center().y()-3
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(colors['notice']))
                painter.drawEllipse(QRectF(dot_x, dot_y, 7, 7))
            if not self.view.compact:
                text_area=body.adjusted(42,0,-22 if pending else -8,0);painter.setPen(QColor(colors['text']))
                painter.drawText(text_area,Qt.AlignmentFlag.AlignVCenter,painter.fontMetrics().elidedText(index.data() or '',Qt.TextElideMode.ElideRight,max(0,text_area.width())))
            if option.state & QStyle.StateFlag.State_HasFocus:
                painter.setPen(QPen(QColor('#3584e4'),1));painter.setBrush(Qt.BrushStyle.NoBrush);painter.drawRoundedRect(QRectF(body.adjusted(1,1,-1,-1)),6,6)
        painter.restore()


class ProfileList(QListWidget):
    groupToggleRequested = Signal(str)

    def __init__(self):
        super().__init__()
        self.horizontal = False
        self.compact = False
        self.colors = dict(text='#303236',muted='#72767a',border='#d8d8d8',selected='#e3efff',hover='#edf2f9',accent='#1768c6',notice='#b95512')
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

    def group_at(self, point):
        item = self.itemAt(point)
        return item if item and item.data(GROUP_ROLE) and not self.profile_at(point) else None

    def mouseMoveEvent(self,event):
        self.setCursor(Qt.CursorShape.PointingHandCursor if self.group_at(event.position().toPoint()) else Qt.CursorShape.ArrowCursor)
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        group = self.group_at(event.position().toPoint())
        if group and event.button() == Qt.MouseButton.LeftButton:
            self.groupToggleRequested.emit(group.data(GROUP_KEY_ROLE))
            event.accept();return
        if self.itemAt(event.position().toPoint()) and not self.profile_at(event.position().toPoint()):
            event.accept();return
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if self.itemAt(event.position().toPoint()) and not self.profile_at(event.position().toPoint()):
            event.accept();return
        super().mouseDoubleClickEvent(event)

    def keyPressEvent(self, event):
        item = self.currentItem()
        if item and item.data(COLLAPSED_ROLE) and event.key() in (Qt.Key.Key_Return,Qt.Key.Key_Enter,Qt.Key.Key_Space):
            self.groupToggleRequested.emit(item.data(GROUP_KEY_ROLE));event.accept();return
        if event.key() == Qt.Key.Key_Menu or (event.key() == Qt.Key.Key_F10 and event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
            item = self.currentItem()
            if item:
                self.scrollToItem(item)
                body = self.itemDelegate().body_rect(self.visualItemRect(item), self.indexFromItem(item))
                self.customContextMenuRequested.emit((body if not body.isEmpty() else self.visualItemRect(item)).center())
            event.accept();return
        super().keyPressEvent(event)

    def wheelEvent(self, event):
        if self.horizontal:
            bar = self.horizontalScrollBar()
            delta = event.pixelDelta().x() or event.pixelDelta().y() or event.angleDelta().x() or event.angleDelta().y()
            bar.setValue(bar.value()-delta);event.accept();return
        super().wheelEvent(event)


class TitleBar(QWidget):
    def __init__(self, window):
        super().__init__(window)
        self.setObjectName('centralTitleBar')
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        self.window_owner = window
        self.setFixedHeight(48)
        layout = QHBoxLayout(self)
        self.title_layout = layout
        layout.setContentsMargins(12, 4, 8, 4)
        layout.setSpacing(6)
        brand = QLabel()
        brand.setPixmap(window.windowIcon().pixmap(24, 24))
        brand.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(brand)
        self.divider = QLabel('|')
        self.divider.setFixedWidth(10)
        self.divider.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.divider)
        self.tabs_host = QWidget()
        self.tabs_layout = QHBoxLayout(self.tabs_host)
        self.tabs_layout.setContentsMargins(0, 0, 0, 0)
        self.tabs_host.setMinimumWidth(0)
        layout.addWidget(self.tabs_host, 1)
        title = QLabel('Central Chats')
        self.title_label = title
        title.setObjectName('centralTitle')
        title.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        title.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout.addWidget(title)
        self.drag_space = QWidget()
        self.drag_space.setFixedWidth(28)
        self.drag_space.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(self.drag_space)
        self.window_controls = {}
        for preset, label, callback in (
            ('window-minimize', 'Minimizar', window.showMinimized),
            ('window-maximize', 'Maximizar ou restaurar', self.toggle_maximized),
            ('window-close', 'Fechar', window.close),
        ):
            button = QToolButton()
            button.setIcon(icon(preset))
            button.setIconSize(QSize(18, 18))
            button.setObjectName(preset)
            button.setToolTip(label)
            button.setAccessibleName(label)
            button.setFixedSize(34, 34)
            button.clicked.connect(callback)
            self.window_controls[preset] = button
            layout.addWidget(button)

    def refresh_icons(self):
        for preset, button in self.window_controls.items():
            actual = 'window-restore' if preset == 'window-maximize' and self.window_owner.isMaximized() else preset
            button.setIcon(icon(actual))

    def toggle_maximized(self):
        if self.window_owner.isMaximized():
            self.window_owner.showNormal()
        else:
            self.window_owner.showMaximized()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            handle = self.window_owner.windowHandle()
            if handle and handle.startSystemMove():
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.toggle_maximized()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)


class DesktopUIMixin:
    def build_ui(self):
        root = QWidget()
        root.setObjectName('centralRoot')
        root.setProperty('squareCorners', False)
        self.setCentralWidget(root)
        shell = QVBoxLayout(root)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)
        self.title_bar = TitleBar(self)
        shell.addWidget(self.title_bar)
        outer = QBoxLayout(QBoxLayout.Direction.LeftToRight)
        shell.addLayout(outer, 1)
        self.resize_grip = QSizeGrip(root)
        self.resize_grip.setFixedSize(12, 8)
        shell.addWidget(self.resize_grip, 0, Qt.AlignmentFlag.AlignRight)
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
        self.list.groupToggleRequested.connect(self.toggle_group)
        self.previous_profiles = QToolButton()
        self.next_profiles = QToolButton()
        for button, preset, label, step in [(self.previous_profiles,'previous','Perfis anteriores',-1),(self.next_profiles,'next','Próximos perfis',1)]:
            button.setProperty('iconPreset',preset)
            button.setIcon(icon(preset));button.setToolTip(label);button.setAccessibleName(label)
            button.setFixedSize(28,36)
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
        self.sidebar_toggle = LogoButton()
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
        self.menu_button.setFixedSize(36,36)
        self.menu_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        menu = QMenu(self.menu_button)
        menu.addAction(icon('list-add'), 'Adicionar perfil…', self.add)
        self.groups_menu=menu.addMenu(icon('group'),'Grupos')
        self.groups_menu.aboutToShow.connect(self.populate_groups_menu)
        self.groups_menu.menuAction().setProperty('iconPreset', 'group')
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
        self.photo_service_action=photo_menu.addAction('Usar logo do serviço',self.use_service_icon)
        self.photo_file_action = photo_menu.addAction('Usar foto do computador…', self.choose_profile_photo)
        self.photo_auto_action = photo_menu.addAction('Usar foto automática do WhatsApp', self.use_automatic_photo)
        self.photo_auto_action.setToolTip('Usa somente sua própria foto quando ela estiver disponível; caso contrário, mantém o ícone.')
        self.photo_icon_action = photo_menu.addAction('Usar somente ícone', self.use_profile_icon)
        self.profile_menu.addSeparator()
        self.profile_groups_menu=QMenu('Grupos',self.profile_menu)
        self.profile_groups_menu.aboutToShow.connect(self.populate_profile_groups)
        self.group_action=self.profile_groups_menu.menuAction()
        self.mute_action = self.profile_menu.addAction('Silenciar avisos do sistema')
        self.mute_action.setCheckable(True)
        self.mute_action.triggered.connect(self.toggle_profile_notifications)
        self.seen_action = self.profile_menu.addAction('Limpar indicador de notificação', self.clear_selected_notification)
        self.call_permissions_action = QAction('Revisar câmera e microfone…', self)
        self.call_permissions_action.triggered.connect(self.reset_call_permissions)
        menu.addSeparator()
        self.split_action=menu.addAction(icon('group'),'Dividir tela…',self.show_split_dialog)
        self.split_action.setShortcut('Ctrl+\\')
        self.split_exit_action=menu.addAction('Voltar a um perfil',lambda:self.stack.leave_split())
        self.split_exit_action.setEnabled(False)
        menu.addSeparator()
        self.preferences_action = menu.addAction(icon('preferences-system'), 'Preferências…', self.show_preferences)
        menu.addSeparator()
        self.quit_action = menu.addAction(icon('application-exit'), 'Sair da central', self.quit_app)
        self.telegram_menu = QMenu('Cliente do Telegram',self.profile_menu)
        self.telegram_actions = {}
        self.telegram_action_group = QActionGroup(self)
        self.telegram_action_group.setExclusive(True)
        for client,label in [('a','Web A (padrão)'),('k','Web K (alternativo)')]:
            action=self.telegram_menu.addAction(label);action.setCheckable(True)
            action.triggered.connect(lambda checked=False,value=client:self.set_telegram_client(value))
            self.telegram_actions[client]=action;self.telegram_action_group.addAction(action)
        self.profile_header = QAction(self)
        self.profile_header.setEnabled(False)
        for action in list(self.profile_menu.actions()):self.profile_menu.removeAction(action)
        self.profile_menu.addAction(self.profile_header)
        self.profile_menu.addSeparator()
        self.profile_menu.addAction(self.rename_button)
        self.profile_menu.addMenu(photo_menu)
        self.profile_menu.addMenu(self.profile_groups_menu)
        self.profile_menu.addMenu(self.telegram_menu)
        self.profile_menu.addSeparator()
        self.profile_menu.addAction(self.reload_button)
        self.profile_menu.addAction(self.call_permissions_action)
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
                (self.group_action,'group'), (self.call_permissions_action,'microphone'), (self.mute_action,'mute'), (self.seen_action,'seen')]:
            action.setProperty('iconPreset', preset)
        self.sidebar_toolbar.addWidget(self.sidebar_toggle)
        self.app_name = QLabel('Central Chats')
        self.app_name.setTextFormat(Qt.TextFormat.PlainText)
        app_font = self.app_name.font();app_font.setBold(True);self.app_name.setFont(app_font)
        self.sidebar_toolbar.addWidget(self.app_name,1)
        side.addWidget(self.menu_button, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.stack = LegacyTestArea() if getattr(self,'use_legacy_test_engine',False) else ProfileArea()
        welcome = QLabel('Adicione um perfil de WhatsApp, Telegram, Chatwoot ou chat personalizado.\nEntre na conta pela tela do serviço.\n\nCada perfil mantém uma sessão independente.')
        welcome.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome.setWordWrap(True)
        welcome.setContentsMargins(24, 24, 24, 24)
        self.stack.addWidget(welcome)
        content.addWidget(self.stack, 1)
        self.stack.splitChanged.connect(self.split_exit_action.setEnabled)
        self.stack.activeChanged.connect(self.split_focus_changed)
        self.list.currentRowChanged.connect(self.select)
        self.apply_sidebar(False)
        self.apply_gnome_style()

    def apply_gnome_style(self):
        theme = self.settings.get('theme', 'system')
        scheme = QApplication.styleHints().colorScheme()
        dark = theme == 'dark' or (theme == 'system' and (scheme == Qt.ColorScheme.Dark or (scheme == Qt.ColorScheme.Unknown and self._system_palette.window().color().lightness() < 128)))
        main, side, text, border, hover, selected, muted, accent, notice = (
            ('#1b2431', '#202c3b', '#eff4fb', '#344052', '#29384a', '#253d59', '#aabbd0', '#65b2ff', '#ffab63')
            if dark else
            ('#f4f6fa', '#ffffff', '#172638', '#d6dfeb', '#edf2f9', '#e3efff', '#4f627b', '#1768c6', '#b95512')
        )
        palette = QPalette(self._system_palette)
        for role, color in (
            (QPalette.ColorRole.Window, main), (QPalette.ColorRole.WindowText, text),
            (QPalette.ColorRole.Base, side), (QPalette.ColorRole.AlternateBase, hover),
            (QPalette.ColorRole.Text, text), (QPalette.ColorRole.Button, side),
            (QPalette.ColorRole.ButtonText, text), (QPalette.ColorRole.Highlight, selected),
            (QPalette.ColorRole.HighlightedText, text), (QPalette.ColorRole.PlaceholderText, muted),
            (QPalette.ColorRole.Mid, border), (QPalette.ColorRole.ToolTipBase, side),
            (QPalette.ColorRole.ToolTipText, text), (QPalette.ColorRole.Link, accent),
        ):
            palette.setColor(role, QColor(color))
        for role in (QPalette.ColorRole.WindowText, QPalette.ColorRole.Text, QPalette.ColorRole.ButtonText):
            palette.setColor(QPalette.ColorGroup.Disabled, role, QColor(muted))
        QApplication.instance().setPalette(palette)
        self.setPalette(palette)
        self.list.colors = dict(text=text, muted=muted, border=border, selected=selected,
                                hover=hover, accent=accent, notice=notice)
        self.previous_profiles.setIcon(icon('previous'));self.next_profiles.setIcon(icon('next'))
        self.list.viewport().update()
        self.menu_button.setIcon(notification_icon(icon('preferences-system'), bool(self.pending_notifications)))
        for menu in self.findChildren(QMenu):
            for action in menu.actions():
                preset = action.property('iconPreset')
                if preset: action.setIcon(icon(preset))
        self.title_bar.refresh_icons()
        self.stack.refresh_icons()
        compact = self.settings.get('sidebar_collapsed',False)
        self.sidebar_toggle.configure(self.windowIcon(),icon('sidebar-show' if compact else 'sidebar-hide'),'Expandir barra lateral' if compact else 'Recolher barra lateral')
        for i, account in enumerate(self.accounts):
            if i < self.list.count():self.list.item(i).setIcon(self.account_icon(account))
        check_asset = Path(__file__).with_name('check-symbolic.svg').as_posix()
        chevron_asset = (Path(__file__).with_name('ui-icons') / ('chevron-down-dark.svg' if dark else 'chevron-down-light.svg')).as_posix()
        edge = {'left': 'right', 'top': 'bottom', 'bottom': 'top'}[self.settings.get('bar_position', 'left')]
        self.setStyleSheet(f"""
            QMainWindow {{ background: transparent; }}
            QWidget#centralRoot {{ background: {main}; border-radius: 12px; }}
            QWidget#centralRoot[squareCorners="true"] {{ border-radius: 0; }}
            QWidget#splitHeader {{ background: {side}; border-bottom: 1px solid {border}; }}
            QWidget#splitDivider {{ background: {border}; }}
            QListWidget#splitProfilePicker::indicator {{ width: 16px; height: 16px; border: 1px solid {muted}; border-radius: 4px; background: {side}; }}
            QListWidget#splitProfilePicker::indicator:checked {{ background: {accent}; border-color: {accent}; image: url('{check_asset}'); }}
            QWidget#serviceLoadingPanel {{ background: {main}; }}
            QWidget#centralTitleBar {{ border-top-left-radius: 12px; border-top-right-radius: 12px; background: {side}; border-bottom: 1px solid {border}; }}
            QWidget#centralRoot[squareCorners="true"] QWidget#centralTitleBar {{ border-radius: 0; }}
            QLabel#centralTitle, QLabel#dialogHeading {{ font-weight: 600; }}
            QWidget#dialogHeader {{ background: transparent; }}
            QToolButton#dialogClose, QWidget#centralTitleBar QToolButton {{ border-radius: 8px; }}
            QToolButton#window-close:hover, QToolButton#dialogClose:hover {{ background: {'#562e3b' if dark else '#fae6e6'}; }}
            QDialog#themedDialog {{ background: transparent; }}
            QWidget#centralTitleBar QToolButton {{ font-size: 19px; }}
            QWidget#titleSidebar {{ background: {side}; }}
            QWidget#sidebar {{ background: {side}; border-{edge}: 1px solid {border}; }}
            QLabel {{ color: {text}; }}
            QListWidget {{ border: 0; background: transparent; color: {text}; }}
            QListWidget::item {{ padding: 0; }}
            QToolButton:focus, QPushButton:focus, QComboBox:focus, QLineEdit:focus {{ border: 1px solid {accent}; }}
            QToolButton {{ border: 0;
                border-radius: 6px; background: transparent; color: {text}; }}
            QToolButton::menu-indicator {{ image: none; width: 0; }}
            QToolButton:hover {{ background: {hover}; }}
            QToolButton:pressed {{ background: {selected}; }}
            QPushButton {{ min-height: 20px; padding: 6px 10px; border-radius: 7px; border: 1px solid {border};
                background: {side}; color: {text}; }}
            QPushButton:hover {{ background: {hover}; }}
            QPushButton:pressed {{ background: {selected}; }}
            QPushButton:disabled, QToolButton:disabled {{ color: {muted}; }}
            QLineEdit, QComboBox {{ min-height: 20px; padding: 6px; border: 1px solid {border};
                border-radius: 6px; background: {main}; color: {text}; }}
            QLineEdit:focus, QComboBox:focus {{ border: 1px solid {accent}; }}
            QComboBox {{ padding-right: 26px; }}
            QComboBox::drop-down {{ border: 0; width: 24px; }}
            QComboBox::down-arrow {{ image: url('{chevron_asset}'); width: 12px; height: 12px; }}
            QPushButton:default {{ border-color: {accent}; background: {selected}; }}
            QDialogButtonBox {{ margin-top: 6px; }}
            QDialog {{ color: {text}; }}
            QMenu, QComboBox QAbstractItemView {{ background: {side}; color: {text}; }}
            QComboBox QAbstractItemView {{ selection-background-color: {selected}; selection-color: {text}; border: 1px solid {border}; padding: 4px; }}
            QMenu {{ border: 1px solid {border}; border-radius: 9px; padding: 6px; }}
            QMenu::item {{ padding: 7px 16px; border-radius: 6px; }}
            QMenu::item:selected {{ background: {selected}; }}
            QMenu::item:disabled {{ color: {muted}; }}
            QMenu::separator {{ height: 1px; background: {border}; margin: 5px 8px; }}
            QToolBar {{ border: 0; background: transparent; spacing: 4px; }}
            QTreeView, QTableView, QTextEdit, QPlainTextEdit {{ background: {side}; color: {text}; border: 1px solid {border}; border-radius: 6px; selection-background-color: {selected}; selection-color: {text}; }}
            QHeaderView::section {{ background: {main}; color: {muted}; border: 0; padding: 6px; }}
            QSplitter::handle {{ background: {border}; }}
            QProgressBar {{ border: 0; border-radius: 4px; background: {hover}; text-align: center; color: {text}; min-height: 8px; }}
            QProgressBar::chunk {{ background: {accent}; border-radius: 4px; }}
            QRadioButton {{ color: {text}; spacing: 8px; }}
            QRadioButton::indicator {{ width: 15px; height: 15px; border-radius: 8px; border: 1px solid {muted}; background: {side}; }}
            QRadioButton::indicator:checked {{ background: {accent}; border-color: {accent}; }}
            QSpinBox, QDoubleSpinBox {{ background: {side}; color: {text}; border: 1px solid {border}; border-radius: 6px; padding: 4px; }}
            QTabWidget::pane {{ border: 0; }}
            QTabBar::tab {{ padding: 10px 14px; background: transparent; color: {muted}; border-bottom: 2px solid transparent; }}
            QTabBar::tab:selected {{ color: {text}; border-bottom-color: {accent}; }}
            QTabBar::tab:focus {{ border: 1px solid {accent}; }}
            QScrollArea {{ border: 0; background: transparent; }}
            QCheckBox {{ min-height: 22px; spacing: 8px; color: {text}; }}
            QCheckBox:disabled {{ color: {muted}; }}
            QCheckBox::indicator {{ width: 16px; height: 16px; border: 1px solid {muted}; border-radius: 4px; background: {main}; }}
            QCheckBox::indicator:checked {{ background: {accent}; border: 1px solid {accent}; image: url('{check_asset}'); }}
            QScrollBar:vertical {{ background: {side}; width: 10px; border: 0; }}
            QScrollBar::handle:vertical {{ background: {muted}; min-height: 24px; border-radius: 5px; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
            QScrollBar:horizontal {{ background: {side}; height: 10px; border: 0; }}
            QScrollBar::handle:horizontal {{ background: {muted}; min-width: 24px; border-radius: 5px; }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: transparent; }}
            QGroupBox {{ border: 0; margin-top: 20px; padding-top: 6px; color: {text}; }}
            QGroupBox::title {{ subcontrol-origin: margin; subcontrol-position: top left; font-weight: bold; }}
            QToolTip {{ background: {main}; color: {text}; border: 1px solid {border}; padding: 4px; }}
        """)
        self.sidebar_toggle.setFixedSize(44,44)
        self.menu_button.setFixedSize(36,36)
        self.previous_profiles.setFixedSize(28,36)
        self.next_profiles.setFixedSize(28,36)

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
        self.title_bar.tabs_layout.removeWidget(self.sidebar)
        integrated = position == 'top'
        self.title_bar.title_label.setVisible(not integrated)
        self.title_bar.tabs_host.setVisible(integrated)
        if integrated:
            self.title_bar.tabs_layout.addWidget(self.sidebar)
            self.sidebar.setObjectName("titleSidebar")
        else:
            self.sidebar.setObjectName('sidebar')
            self.outer_layout.insertWidget(1 if position == 'bottom' else 0, self.sidebar)
        self.sidebar.setMinimumSize(0,0);self.sidebar.setMaximumSize(16777215,16777215)
        if horizontal:self.sidebar.setFixedHeight(40 if integrated else 48)
        else:self.sidebar.setFixedWidth(64 if compact else 240)
        self.side_layout.setContentsMargins(4 if horizontal else 10,0 if horizontal else 10,4 if horizontal else 10,0 if horizontal else 10)
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
        self.sidebar_toolbar.setDirection(QBoxLayout.Direction.LeftToRight)
        self.app_name.setVisible(not horizontal and not compact)
        self.add_button.setText('')
        self.sidebar_toggle.setToolTip('Expandir contas' if compact else 'Recolher contas')
        self.sidebar_toggle.configure(self.windowIcon(),icon('sidebar-show' if compact else 'sidebar-hide'),'Expandir barra lateral' if compact else 'Recolher barra lateral')
        counts = {}
        catalog=self.group_catalog()
        pending_groups = set()
        for account in self.accounts:
            group = self.profile_group(account)
            counts[group] = counts.get(group,0)+1
            if account['id'] in self.pending_notifications:pending_groups.add(group)
        current_row = self.list.currentRow()
        self.list.blockSignals(True)
        for index, account in enumerate(self.accounts):
            item = self.list.item(index)
            if item is None:continue
            name = account['name'];pending = account['id'] in self.pending_notifications
            group = self.profile_group(account)
            previous = self.profile_group(self.accounts[index-1]) if index else None
            first = bool(group and group != previous)
            key = self.settings.get('group_mode','none')+':'+group
            collapsed = bool(group and key in self.settings.get('collapsed_groups',[]))
            item.setData(GROUP_ROLE,group if first else '')
            item.setData(GROUP_KEY_ROLE,key)
            item.setData(GROUP_COUNT_ROLE,counts.get(group,0))
            item.setData(COLLAPSED_ROLE,collapsed and first)
            item.setData(GROUP_PENDING_ROLE,group in pending_groups)
            item.setData(PROFILE_PENDING_ROLE,pending)
            item.setData(GROUP_COLOR_ROLE,catalog.get(group,{}).get('color','#72767a') if group else '')
            item.setData(GROUP_LABEL_ROLE,group)
            following=self.profile_group(self.accounts[index+1]) if index+1<len(self.accounts) else None
            item.setData(GROUP_LAST_ROLE,bool(group and (following!=group or (collapsed and first))))
            item.setHidden(collapsed and not first)
            tooltip = name+' · '+SERVICES[account.get('service','whatsapp')]['name']
            if group:tooltip += ' · '+group
            if collapsed and first:tooltip = group+f' — {counts[group]} perfis — Clique para expandir'
            if pending:tooltip += ' · Notificação recebida'
            item.setToolTip(tooltip);item.setIcon(self.account_icon(account))
            item.setData(Qt.ItemDataRole.AccessibleDescriptionRole,tooltip)
            item.setText('' if compact else name)
            item.setData(Qt.ItemDataRole.AccessibleTextRole,(group+f', recolhido, {counts[group]} perfis' if collapsed and first else name)+(' — Notificação recebida' if pending else ''))
        for index in range(len(self.accounts),self.list.count()):
            item=self.list.item(index);name=item.data(GROUP_ROLE)
            item.setData(COLLAPSED_ROLE,True);item.setData(GROUP_COUNT_ROLE,0);item.setData(GROUP_LAST_ROLE,True)
            item.setData(GROUP_LABEL_ROLE,name);item.setData(GROUP_COLOR_ROLE,catalog.get(name,{}).get('color','#72767a'))
            item.setToolTip(name+' — 0 perfis — Botão direito para adicionar abas')
            item.setData(Qt.ItemDataRole.AccessibleTextRole,name+', 0 perfis')
        if current_row>=0:self.list.setCurrentRow(current_row)
        self.list.blockSignals(False)
        self.menu_button.setIcon(notification_icon(icon('preferences-system'),bool(self.pending_notifications)))
        self.menu_button.setToolTip('Configurações'+(' · Há perfis com notificações' if self.pending_notifications else ''))
        self.list.doItemsLayout()
        self.update_profile_overflow()
        self.list.viewport().update()


class PreferencesDialog(QDialog):
    def __init__(self, parent, settings, accounts, can_background):
        super().__init__(parent)
        self.setWindowTitle('Preferências')
        self.resize(570,560)
        self.original = dict(settings)
        self.group_fields = {}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16,16,16,16)
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        layout.addWidget(self.tabs,1)
        def section(title):
            scroll = QScrollArea();scroll.setWidgetResizable(True)
            body = QWidget();form = QVBoxLayout(body)
            form.setContentsMargins(12,16,12,12);form.setSpacing(12)
            scroll.setWidget(body);self.tabs.addTab(scroll,title)
            return form
        appearance = section('Aparência')
        form = aligned_form()
        self.theme = QComboBox()
        for label,value in [('Automático (GNOME)','system'),('Claro','light'),('Escuro','dark')]:self.theme.addItem(label,value)
        self.bar_position = QComboBox()
        for label,value in [('Esquerda','left'),('Parte de cima','top'),('Parte de baixo','bottom')]:self.bar_position.addItem(label,value)
        self.group_mode = QComboBox()
        for label,value in [('Sem grupos','none'),('Por tipo de chat','service'),('Grupos personalizados','custom')]:self.group_mode.addItem(label,value)
        for key,label,default in [('theme','Tema da central:','system'),('bar_position','Posição da barra:','left'),('group_mode','Agrupar perfis:','none')]:
            combo = getattr(self,key);combo.setCurrentIndex(max(0,combo.findData(settings.get(key,default))))
            form.addRow(label,combo)
        appearance.addLayout(form)
        note = QLabel('O tema das conversas é escolhido dentro de cada serviço. Clique no título de um grupo para recolher ou expandir. O número indica quantos perfis ele contém.')
        note.setWordWrap(True);appearance.addWidget(note)
        note = QLabel('Nomes, fotos e grupos personalizados ficam no botão direito de cada perfil.')
        note.setWordWrap(True);appearance.addWidget(note);appearance.addStretch()
        startup = section('Inicialização')
        self.startup_enabled = QCheckBox('Iniciar a central ao entrar no sistema')
        self.startup_enabled.setChecked(settings.get('startup_enabled',False))
        if os.environ.get('FLATPAK_ID'):
            self.startup_enabled.setChecked(False);self.startup_enabled.setEnabled(False)
            self.startup_enabled.setToolTip('Inicialização automática via Flatpak ainda não disponível.')
        startup.addWidget(self.startup_enabled)
        self.startup_mode = QComboBox()
        for label,value in [('Somente os perfis selecionados','selected'),('Todos os perfis','all'),('Nenhum perfil','none')]:self.startup_mode.addItem(label,value)
        self.startup_mode.setCurrentIndex(max(0,self.startup_mode.findData(settings.get('startup_mode','selected'))))
        start_form = aligned_form();start_form.addRow('Carregar ao iniciar:',self.startup_mode);startup.addLayout(start_form)
        self.profiles_box = QGroupBox('Perfis para carregar ao iniciar')
        profile_layout = QVBoxLayout(self.profiles_box);self.startup_checks = {}
        for account in accounts:
            key=account['id'];name=account['name']
            checkbox=QCheckBox();checkbox.setAccessibleName(name);checkbox.setToolTip(name)
            checkbox.setText(checkbox.fontMetrics().elidedText(name,Qt.TextElideMode.ElideRight,380))
            checkbox.setChecked(key in settings.get('startup_profiles',[]))
            self.startup_checks[key]=checkbox;profile_layout.addWidget(checkbox)
        if not accounts:profile_layout.addWidget(QLabel('Nenhum perfil disponível.'))
        startup.addWidget(self.profiles_box);startup.addStretch()
        self.startup_mode.currentIndexChanged.connect(self.update_startup_controls)
        self.update_startup_controls()
        background = section('Segundo plano')
        self.start_hidden = QCheckBox('Iniciar com a janela oculta')
        self.start_hidden.setChecked(settings.get('start_hidden',False) and can_background)
        self.start_hidden.setEnabled(can_background)
        background.addWidget(self.start_hidden)
        self.close_action = QComboBox()
        self.close_action.addItem('Continuar em segundo plano','background');self.close_action.addItem('Sair da central','exit')
        self.close_action.setCurrentIndex(0 if settings.get('close_action','background')=='background' and can_background else 1)
        if not can_background:self.close_action.model().item(0).setEnabled(False)
        close_form=aligned_form();close_form.addRow('Ao fechar a janela:',self.close_action);background.addLayout(close_form)
        note=QLabel('As contas carregadas continuam ativas enquanto a central funciona. Para reabrir, use o atalho no menu de aplicativos ou a bandeja. Silencie os avisos no botão direito de cada perfil; sons são controlados pelo próprio serviço.')
        note.setWordWrap(True);background.addWidget(note)
        if not can_background:
            note=QLabel('Nesta execução não há um caminho confirmado para reabrir uma janela oculta. Fechar encerra a central.')
            note.setWordWrap(True);background.addWidget(note)
        background.addStretch()
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText('Salvar');buttons.button(QDialogButtonBox.StandardButton.Cancel).setText('Cancelar')
        buttons.accepted.connect(self.accept);buttons.rejected.connect(self.reject);layout.addWidget(buttons)

    def update_startup_controls(self):
        self.profiles_box.setEnabled(self.startup_mode.currentData()=='selected')

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
