#!/usr/bin/env python3
from services import SERVICES, allows_url, service_url, normalize_custom_url
import json
import re
from itertools import count
import os
import sys
import uuid
import hashlib
from copy import deepcopy
from grouping import known_groups, canonical_name, custom_settings, renamed_group, group_name, DEFAULT_GROUP_COLOR
from pathlib import Path
from avatar_manager import AvatarManager, OWN_AVATAR_SCRIPT
from profile_store import ProfileStore
from settings_store import PreferencesStore, AutostartManager
from desktop_notifications import DesktopNotifications
from split_workspace import SplitDialog
from window_chrome import WindowChrome
from desktop_ui import DesktopUIMixin, PreferencesDialog, edit_profile_dialog, icon, notification_icon, service_icon, COLLAPSED_ROLE, GROUP_ROLE, GROUP_KEY_ROLE, EMPTY_GROUP_ROLE
from PySide6.QtCore import QUrl, QLockFile, QTimer, Qt, QRect, QRectF, QEvent, Signal, QTemporaryDir, QSignalBlocker, QMimeDatabase, QTranslator, QLibraryInfo
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtGui import QDesktopServices, QIcon, QColor, QPainter, QPainterPath, QRegion
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
 QListWidget, QPushButton, QLabel, QStackedWidget, QSystemTrayIcon, QDialogButtonBox, QCheckBox)
from ui_widgets import (
    Dialog as QDialog, Menu as QMenu, InputDialog as QInputDialog,
    MessageBox as QMessageBox, FileDialog as QFileDialog, ColorDialog as QColorDialog,
)
USE_QT_TEST_ENGINE = os.environ.get('CENTRAL_BROWSER_ENGINE') == 'qt-test'
if USE_QT_TEST_ENGINE:
    from PySide6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage, QWebEnginePermission, QWebEngineSettings, QWebEngineLoadingInfo
    from PySide6.QtWebEngineWidgets import QWebEngineView
else:
    from cef_engine import Profile as CefProfile, ServiceView as CefServiceView, Permission as QWebEnginePermission

DATA = Path(os.environ.get('CENTRAL_WHATSAPP_DATA', str(Path(os.environ.get('XDG_DATA_HOME',str(Path.home()/'.local/share')))/'central-whatsapp-data')))
CONFIG = DATA/'profiles.json'

if USE_QT_TEST_ENGINE:
    class Page(QWebEnginePage):
        initialResourceFailed = Signal()

        def __init__(self, profile, parent=None, service="whatsapp", custom_url=""):
            super().__init__(profile, parent)
            self.service = service
            self.custom_url = custom_url
            self.newWindowRequested.connect(self.open_requested_window)

        def javaScriptConsoleMessage(self, level, message, line, source):
            if self.service == 'telegram' and 'Failed to fetch dynamically imported module' in message:
                self.initialResourceFailed.emit()
            super().javaScriptConsoleMessage(level,message,line,source)

        def acceptNavigationRequest(self, url, kind, main):
            if allows_url(self.service, url, self.custom_url):
                return True
            if main and kind == QWebEnginePage.NavigationType.NavigationTypeLinkClicked:
                self.open_external(url)
            return False

        @staticmethod
        def open_external(url):
            if not url.isValid() or url.userInfo():
                return
            if (url.scheme() in ('https', 'http') and url.host()) or url.scheme() == 'mailto':
                QDesktopServices.openUrl(url)

        def open_requested_window(self, request):
            if not request.isUserInitiated():
                return
            url = request.requestedUrl()
            if allows_url(self.service, url, self.custom_url):
                self.setUrl(url)
            else:
                self.open_external(url)


    class ServiceView(QWebEngineView):
        """A local recovery panel, without injecting privileged code into web content."""
        def __init__(self):
            super().__init__()
            self.loading_panel = QWidget(self)
            self.loading_panel.setObjectName('serviceLoadingPanel')
            layout = QVBoxLayout(self.loading_panel)
            layout.addStretch()
            self.loading_title = QLabel();self.loading_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.loading_title.setWordWrap(True);layout.addWidget(self.loading_title)
            self.retry_button = QPushButton('Tentar novamente')
            self.alternative_button = QPushButton('Usar outro cliente do Telegram')
            for button in (self.retry_button,self.alternative_button):
                button.setMaximumWidth(300);layout.addWidget(button,0,Qt.AlignmentFlag.AlignHCenter)
            layout.addStretch();self.loading_panel.hide()

        def contextMenuEvent(self, event):
            request = self.lastContextMenuRequest()
            menu = self.createStandardContextMenu()
            menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            if request and request.mediaType() == request.MediaType.MediaTypeVideo:
                download = self.pageAction(QWebEnginePage.WebAction.DownloadMediaToDisk)
                if download in menu.actions():
                    download.setText('Salvar vídeo para abrir no player…')
            menu.exec(event.globalPos())
            menu.deleteLater()

        def resizeEvent(self, event):
            super().resizeEvent(event)
            self.loading_panel.setGeometry(self.rect())

        def show_loading(self, message):
            self.loading_title.setText(message)
            self.loading_panel.setGeometry(self.rect());self.loading_panel.show();self.loading_panel.raise_()


class Window(DesktopUIMixin, QMainWindow):
    def __init__(self):
        super().__init__()
        self._system_palette = QApplication.palette()
        self.setWindowTitle('Central Chats')
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, USE_QT_TEST_ENGINE)
        self.resize(1250, 820)
        self.setWindowIcon(QIcon(str(Path(__file__).with_name('whatsapp-web.svg'))))
        self.views, self.profiles, self.load_states = {}, {}, {}
        self.notifications = {}
        self.notification_ids = count(1)
        self.notification_images = QTemporaryDir()
        self.tray_notification = None
        self.desktop_notifications = DesktopNotifications(self)
        self.desktop_notifications.delivered.connect(self.notification_delivered)
        self.desktop_notifications.clicked.connect(self.open_notification)
        self.desktop_notifications.dismissed.connect(self.dismiss_notification)
        self.pending_notifications = set()
        self.capture_permissions = {}
        self._startup_ready = set()
        self._retry_counts = {}
        self._retry_pending = {}
        self._load_generations = {}
        self._content_checks = {}
        self._fullscreen_state = None
        self._fullscreen_key = None
        self.avatar_manager = AvatarManager(DATA)
        self.avatar_pending = set()
        self.confirm_close = True
        self.activation_ready = False
        self._quitting = False
        self._cleaned = False
        try:
            self.store = ProfileStore(DATA)
            records = self.store.load()
            self.accounts = [a for a in records if not a.get('archived', False)]
            self.archived = [a for a in records if a.get('archived', False)]
            self.preferences_store = PreferencesStore(DATA)
            self.settings = self.preferences_store.load()
            self.autostart_manager = AutostartManager()
        except (ValueError, OSError) as error:
            QMessageBox.critical(self, 'Dados indisponíveis', f'Os dados foram preservados. Não foi possível ler a configuração: {error}')
            raise SystemExit(1)
        self.use_legacy_test_engine=USE_QT_TEST_ENGINE
        self.build_ui()
        if not USE_QT_TEST_ENGINE:self.chrome=WindowChrome(self)
        QApplication.styleHints().colorSchemeChanged.connect(lambda *_: self.apply_gnome_style())
        self.setup_tray()
        self.refresh()
        self.avatar_timer = QTimer(self)
        self.avatar_timer.timeout.connect(self.poll_avatars)
        self.avatar_timer.start(30000)

    def split_focus_changed(self,view):
        row=next((i for i,a in enumerate(self.accounts) if self.views.get(a['id'],(None,))[0] is view),-1)
        if row>=0:
            with QSignalBlocker(self.list):self.list.setCurrentRow(row)
            self.update_status(self.accounts[row]['id']);self.update_actions()
    def show_split_dialog(self):
        selected=[key for key,(view,_) in self.views.items() if self.stack.isDisplayed(view)]
        dialog=SplitDialog(self,self.accounts,lambda a:self.profile_group(a) or self.assigned_group(a) or SERVICES[a.get('service','whatsapp')]['name'],selected)
        if dialog.exec()==QDialog.DialogCode.Accepted:self.activate_split(dialog.selected_ids(),dialog.arrangement.currentData())
        dialog.deleteLater()
    def activate_split(self,identifiers,mode='columns'):
        if not 2<=len(identifiers)<=4 or len(set(identifiers))!=len(identifiers):raise ValueError('Selecione de 2 a 4 perfis diferentes')
        rows=[next((i for i,a in enumerate(self.accounts) if a['id']==key),-1) for key in identifiers]
        if any(row<0 for row in rows):raise ValueError('Perfil indisponível')
        for row in rows:self.select(row,force=True)
        if any(key not in self.views for key in identifiers):return False
        self.stack.set_names({self.views[a['id']][0]:a['name'] for a in self.accounts if a['id'] in self.views})
        self.stack.set_split([self.views[key][0] for key in identifiers],mode)
        with QSignalBlocker(self.list):self.list.setCurrentRow(rows[0])
        self.stack.setCurrentWidget(self.views[identifiers[0]][0]);self.update_actions()
        return True

    def setup_tray(self):
        self.tray = QSystemTrayIcon(self.windowIcon(), self)
        self.tray.setToolTip('Central Chats')
        menu = QMenu(self)
        menu.addAction('Abrir central', self.show_window)
        menu.addAction('Preferências…', self.show_preferences)
        menu.addSeparator()
        menu.addAction('Sair da central', self.quit_app)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self.tray_activated)
        self.tray.messageClicked.connect(self.open_tray_notification)
        # O Qt também registra o ícone se uma bandeja surgir depois.
        self.tray.show()

    def tray_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self.show_window()

    def update_window_corners(self):
        if not USE_QT_TEST_ENGINE:
            if self.isMaximized() or self.isFullScreen():self.clearMask()
            else:
                path=QPainterPath();path.addRoundedRect(QRectF(self.rect()),12,12)
                self.setMask(QRegion(path.toFillPolygon().toPolygon()))
        square = self.isMaximized() or self.isFullScreen()
        root = self.centralWidget()
        if root and root.property('squareCorners') != square:
            root.setProperty('squareCorners', square)
            for widget in (root, self.title_bar):
                widget.style().unpolish(widget)
                widget.style().polish(widget)
                widget.update()
        if hasattr(self, 'resize_grip'):
            self.resize_grip.setVisible(not square)
        if hasattr(self, 'title_bar'):
            self.title_bar.refresh_icons()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_window_corners()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange:
            self.update_window_corners()

    def show_window(self):
        if self.isMinimized():
            self.setWindowState(self.windowState() & ~Qt.WindowState.WindowMinimized)
        self.show()
        self.raise_()
        self.activateWindow()

    def can_background(self):
        launcher = bool(os.environ.get('FLATPAK_ID')) or any(
            path.is_file() and os.access(path, os.X_OK)
            for path in (Path.home()/'.local/bin/central-whatsapp', Path('/usr/bin/central-whatsapp')))
        return QSystemTrayIcon.isSystemTrayAvailable() or (self.activation_ready and launcher)

    def apply_preferences(self, candidate):
        candidate = deepcopy({**self.settings, **candidate})
        snapshot = None
        captured = False
        autostart_changed = candidate.get('startup_enabled') != self.settings['startup_enabled']
        try:
            if candidate.get('startup_enabled') and os.environ.get('FLATPAK_ID'):
                raise ValueError('Inicialização automática via Flatpak ainda não disponível nesta versão.')
            if candidate.get('start_hidden') and not self.can_background():
                raise ValueError('Não há um meio confirmado de reabrir a central nesta sessão.')
            if autostart_changed:
                snapshot = self.autostart_manager.capture()
                captured = True
                self.autostart_manager.sync(candidate['startup_enabled'])
            self.preferences_store.save(candidate)
        except (ValueError, OSError) as error:
            rollback_error = None
            if autostart_changed and captured:
                try:
                    self.autostart_manager.restore(snapshot)
                except (ValueError, OSError) as failure:
                    rollback_error = failure
            message = f'Não foi possível salvar as preferências. {error}'
            if rollback_error:
                message += f' Verifique a inicialização automática: {rollback_error}'
            QMessageBox.critical(self, 'Preferências não salvas', message)
            return False
        self.settings = candidate
        selected = self.selected_account()
        key = selected['id'] if selected else next((key for key,(view,_) in self.views.items() if view is self.stack.currentWidget()),None)
        self.sort_accounts()
        row = next((i for i,a in enumerate(self.accounts) if a['id']==key), -1)
        self.refresh(row)
        self.apply_gnome_style()
        return True

    def show_preferences(self):
        self.show_window()
        dialog = PreferencesDialog(self, self.settings, self.accounts, self.can_background())
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.apply_preferences(dialog.values())

    def toggle_sidebar(self):
        candidate = dict(self.settings)
        candidate['sidebar_collapsed'] = not candidate['sidebar_collapsed']
        self.apply_preferences(candidate)

    def load_startup_profiles(self):
        mode = self.settings['startup_mode']
        selected = set(self.settings['startup_profiles'])
        rows = [i for i, account in enumerate(self.accounts)
                if mode == 'all' or (mode == 'selected' and account['id'] in selected)]
        for row in rows:
            self.list.setCurrentRow(row)
            self.select(row,force=True)
        if rows:
            self.list.setCurrentRow(rows[0]);self.select(rows[0],force=True)

    def start(self, autostart=False):
        self.load_startup_profiles()
        if autostart and self.settings['start_hidden'] and self.can_background():
            self.hide()
        else:
            self.show_window()

    def save(self, accounts=None, archived=None):
        accounts = self.accounts if accounts is None else accounts
        archived = self.archived if archived is None else archived
        records = [dict(a, archived=False) for a in accounts] + [dict(a, archived=True) for a in archived]
        try:
            self.store.save(records)
        except (ValueError, OSError) as error:
            QMessageBox.critical(self, 'Não foi possível salvar', f'Nenhum perfil foi alterado. {error}')
            return False
        return True

    def update_actions(self):
        selected = 0 <= self.list.currentRow() < len(self.accounts) and not self.list.currentItem().data(COLLAPSED_ROLE)
        for action in (self.photo_file_action, self.photo_auto_action, self.photo_icon_action, self.photo_service_action):
            action.setEnabled(selected)
        self.photo_auto_action.setEnabled(selected and self.accounts[self.list.currentRow()].get('service', 'whatsapp') == 'whatsapp')
        self.rename_button.setEnabled(selected)
        self.archive_button.setEnabled(selected)
        self.reload_button.setEnabled(selected and self.accounts[self.list.currentRow()]['id'] in self.views)
        self.restore_button.setEnabled(bool(self.archived))
        account = self.accounts[self.list.currentRow()] if selected else None
        telegram = bool(account and account.get('service','whatsapp')=='telegram')
        self.telegram_menu.menuAction().setVisible(telegram)
        for client,action in self.telegram_actions.items():action.setChecked(bool(account and account.get('telegram_client','a')==client))
        self.profile_header.setText(account['name']+' · '+SERVICES[account.get('service','whatsapp')]['name'] if account else 'Perfil')
        self.group_action.setEnabled(selected)
        self.call_permissions_action.setEnabled(bool(account and account['id'] in self.views))
        self.mute_action.setEnabled(selected)
        self.mute_action.setChecked(selected and self.accounts[self.list.currentRow()]['id'] in self.settings['muted_profiles'])
        self.seen_action.setEnabled(selected and self.accounts[self.list.currentRow()]['id'] in self.pending_notifications)

    def show_profile_menu(self, position):
        header=self.list.group_at(position)
        if header:
            self.show_group_menu(header.data(GROUP_KEY_ROLE),position);return
        item = self.list.profile_at(position)
        if item is None:return
        previous = self.selected_account()
        previous_key = previous['id'] if previous else next((key for key,(view,_) in self.views.items() if view is self.stack.currentWidget()),None)
        self.list.blockSignals(True)
        self.list.setCurrentItem(item)
        self.list.blockSignals(False)
        self.update_actions()
        self._profile_context_active = True
        try:
            self.profile_menu.exec(self.list.viewport().mapToGlobal(position))
        finally:
            self._profile_context_active = False
            row = next((i for i,a in enumerate(self.accounts) if a['id']==previous_key), -1)
            self.list.setCurrentRow(row)
            if row >= 0:self.select(row)
            else:self.stack.setCurrentIndex(0)
            self.update_actions()

    def group_catalog(self):
        return known_groups(self.settings,self.accounts+self.archived)

    def assigned_group(self, account):
        if self.settings.get('group_mode')=='service':return SERVICES[account.get('service','whatsapp')]['name']
        value=self.settings.get('profile_groups',{}).get(account['id'],'').strip()
        return canonical_name(self.settings,value,self.accounts+self.archived) if value else ''

    def create_group(self, assign=False):
        value,ok=QInputDialog.getText(self,'Novo grupo','Nome do grupo (até 40 caracteres):')
        if not ok:return
        try:
            value=group_name(value)
            if any(name.casefold()==value.casefold() for name in self.group_catalog()):raise ValueError('Este grupo já existe.')
        except ValueError as error:
            QMessageBox.information(self,'Grupo não criado',str(error));return
        candidate=custom_settings(self.settings,self.accounts+self.archived)
        candidate['groups'][value]={'color':DEFAULT_GROUP_COLOR}
        account=self.selected_account() if assign else None
        if account:candidate['profile_groups'][account['id']]=value
        self.apply_preferences(candidate)

    def set_profile_group(self):
        self.create_group(assign=True)

    def assign_profile_group(self, name):
        account=self.selected_account()
        if account is None:return
        candidate=custom_settings(self.settings,self.accounts+self.archived)
        if name:
            name=canonical_name(self.settings,name,self.accounts+self.archived)
            candidate['groups'].setdefault(name,{'color':DEFAULT_GROUP_COLOR})
            candidate['profile_groups'][account['id']]=name
        else:candidate['profile_groups'].pop(account['id'],None)
        self.apply_preferences(candidate)

    def populate_profile_groups(self):
        menu=self.profile_groups_menu;menu.clear()
        account=self.selected_account()
        current=self.assigned_group(account) if account else ''
        action=menu.addAction('Sem grupo',lambda:self.assign_profile_group(''))
        action.setCheckable(True);action.setChecked(not current)
        for name in self.group_catalog():
            action=menu.addAction(name,lambda checked=False,value=name:self.assign_profile_group(value))
            action.setCheckable(True);action.setChecked(name.casefold()==current.casefold())
        menu.addSeparator();menu.addAction('Novo grupo…',self.set_profile_group)

    def populate_groups_menu(self):
        menu=self.groups_menu;menu.clear()
        names=self.group_catalog()
        for name in names:menu.addAction(name,lambda checked=False,value=name:self.reveal_group(value))
        if not names:
            action=menu.addAction('Nenhum grupo criado');action.setEnabled(False)
        menu.addSeparator();menu.addAction('Novo grupo…',lambda:self.create_group(False))

    def reveal_group(self, name):
        present={self.profile_group(a) for a in self.accounts}
        if self.settings.get('group_mode')=='none' or (name not in present and self.settings.get('group_mode')!='custom'):
            candidate=custom_settings(self.settings,self.accounts+self.archived)
            self.apply_preferences(candidate)
        for row in range(self.list.count()):
            item=self.list.item(row)
            if item.data(GROUP_ROLE)==name:
                key=item.data(GROUP_KEY_ROLE)
                if key in self.settings.get('collapsed_groups',[]):self.toggle_group(key)
                self.list.scrollToItem(item);return

    def show_group_menu(self, key, position):
        name=key.partition(':')[2]
        menu=QMenu(self)
        heading=menu.addAction(name);heading.setEnabled(False)
        menu.addSeparator()
        menu.addAction(icon('document-edit'),'Renomear grupo…',lambda:self.rename_group(name))
        menu.addAction(icon('palette'),'Cor do grupo…',lambda:self.choose_group_color(name))
        tabs=menu.addMenu(icon('list-add'),'Adicionar abas')
        tabs.addAction(icon('list-add'),'Novo perfil…',lambda:self.add(name))
        tabs.addAction(icon('group'),'Perfis existentes…',lambda:self.add_profiles_to_group(name))
        menu.exec(self.list.viewport().mapToGlobal(position))
        menu.deleteLater()

    def rename_group(self, name):
        value,ok=QInputDialog.getText(self,'Renomear grupo','Novo nome:',text=name)
        if not ok:return
        try:candidate=renamed_group(self.settings,self.accounts+self.archived,name,value)
        except ValueError as error:
            QMessageBox.information(self,'Grupo não alterado',str(error));return
        self.apply_preferences(candidate)

    def choose_group_color(self, name):
        catalog=self.group_catalog()
        old=catalog.get(name,{}).get('color',DEFAULT_GROUP_COLOR)
        color=QColorDialog.getColor(QColor(old),self,'Cor do grupo')
        if not color.isValid():return
        candidate=deepcopy(self.settings)
        candidate['groups']=catalog
        candidate['groups'][name]={'color':color.name()}
        self.apply_preferences(candidate)

    def add_profiles_to_group(self, name):
        candidates=[account for account in self.accounts if self.profile_group(account)!=name]
        dialog=QDialog(self);dialog.setWindowTitle('Adicionar abas ao grupo '+name);dialog.resize(420,360)
        layout=QVBoxLayout(dialog);scroll=QWidget();options=QVBoxLayout(scroll);checks={}
        for account in candidates:
            check=QCheckBox();check.setAccessibleName(account['name']);check.setText(check.fontMetrics().elidedText(account['name'],Qt.TextElideMode.ElideRight,340));check.setToolTip(account['name']+' · '+SERVICES[account.get('service','whatsapp')]['name'])
            options.addWidget(check);checks[account['id']]=check
        if not candidates:options.addWidget(QLabel('Todos os perfis já estão neste grupo.'))
        from PySide6.QtWidgets import QScrollArea
        area=QScrollArea();area.setWidgetResizable(True);area.setWidget(scroll);layout.addWidget(area)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText('Adicionar')
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText('Cancelar')
        buttons.accepted.connect(dialog.accept);buttons.rejected.connect(dialog.reject);layout.addWidget(buttons)
        if dialog.exec()!=QDialog.DialogCode.Accepted:return
        selected=[key for key,check in checks.items() if check.isChecked()]
        if not selected:return
        candidate=custom_settings(self.settings,self.accounts+self.archived)
        candidate['groups'].setdefault(name,{'color':DEFAULT_GROUP_COLOR})
        for key in selected:candidate['profile_groups'][key]=name
        self.apply_preferences(candidate)

    def toggle_profile_notifications(self, muted):
        account = self.selected_account()
        if account is None:return
        keys = set(self.settings['muted_profiles'])
        if muted: keys.add(account['id'])
        else: keys.discard(account['id'])
        self.apply_preferences({'muted_profiles':sorted(keys)})
        self.update_actions()

    def clear_selected_notification(self):
        account = self.selected_account()
        if account and account['id'] in self.pending_notifications:
            self.pending_notifications.discard(account['id'])
            self.apply_sidebar(self.settings['sidebar_collapsed'])
            self.update_actions()

    def viewing_profile(self, key):
        return bool(key in self.views and self.stack.isDisplayed(self.views[key][0])
                    and self.isVisible() and not self.isMinimized() and self.isActiveWindow())

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.Type.ActivationChange and self.isActiveWindow() and hasattr(self, 'list'):
            key=next((key for key,(view,_) in self.views.items() if view is self.stack.currentWidget()),None)
            if key in self.pending_notifications and self.viewing_profile(key):
                self.pending_notifications.discard(key)
                self.apply_sidebar(self.settings['sidebar_collapsed']);self.update_actions()

    def toggle_group(self, key):
        collapsed = set(self.settings.get('collapsed_groups',[]))
        if key in collapsed:collapsed.remove(key)
        else:collapsed.add(key)
        candidate = deepcopy(self.settings)
        candidate['collapsed_groups'] = sorted(collapsed)
        try:self.preferences_store.save(candidate)
        except (ValueError,OSError) as error:
            QMessageBox.critical(self,'Grupo não alterado',str(error));return
        self.settings = candidate
        self.apply_sidebar(self.settings['sidebar_collapsed'])
        self.update_actions()

    def profile_group(self, account):
        mode = self.settings.get('group_mode', 'none')
        if mode == 'service':
            return SERVICES[account.get('service','whatsapp')]['name']
        if mode == 'custom':
            return self.assigned_group(account) or 'Sem grupo'
        return ''

    def sort_accounts(self):
        if self.settings.get('group_mode', 'none') != 'none':
            self.accounts.sort(key=lambda a: (self.profile_group(a).casefold(), a['name'].casefold()))

    def refresh(self, row=-1):
        key = self.accounts[row]['id'] if 0 <= row < len(self.accounts) else None
        self.sort_accounts()
        row = next((i for i,a in enumerate(self.accounts) if a['id']==key), -1)
        self.list.blockSignals(True); self.list.clear()
        self.list.addItems([a['name'] for a in self.accounts])
        if self.settings.get('group_mode')=='custom':
            present={self.profile_group(a) for a in self.accounts}
            for name in self.group_catalog():
                if name not in present:
                    from PySide6.QtWidgets import QListWidgetItem
                    item=QListWidgetItem(name);item.setData(EMPTY_GROUP_ROLE,True)
                    item.setData(GROUP_ROLE,name);item.setData(GROUP_KEY_ROLE,'custom:'+name)
                    self.list.addItem(item)
        for i, account in enumerate(self.accounts):
            self.list.item(i).setToolTip(account['name']+' · '+SERVICES[account.get('service','whatsapp')]['name'])
            self.list.item(i).setIcon(self.account_icon(account))
        self.list.setCurrentRow(row)
        self.list.blockSignals(False)
        if row >= 0 and not getattr(self, '_profile_context_active', False):self.select(row)
        if row < 0:
            self.stack.setCurrentIndex(0)
            self.status.setText('Selecione ou adicione um perfil')
        self.apply_sidebar(self.settings['sidebar_collapsed'])
        self.update_actions()

    def ask_name(self, title, current='', exclude=None):
        name, ok = QInputDialog.getText(self, title, 'Nome do perfil (até 60 caracteres):', text=current)
        if not ok:
            return None
        name = name.strip()
        if not name or len(name) > 60:
            QMessageBox.information(self, 'Nome inválido', 'Informe um nome entre 1 e 60 caracteres.')
            return None
        if any(a['id'] != exclude and a['name'].casefold() == name.casefold() for a in self.accounts):
            QMessageBox.information(self, 'Nome já usado', 'Escolha outro nome para o perfil.')
            return None
        return name

    def ask_profile(self, title, current=None, default_group=None):
        editing=current is not None
        current=current or {'name':'','icon':'user','service':'whatsapp','avatar_mode':'service'}
        options=list(self.group_catalog())
        automatic=not editing and default_group is None and self.settings.get('group_mode')=='service'
        if automatic:
            options=sorted(set(options)|{service['name'] for service in SERVICES.values()},key=str.casefold)
        initial_group=default_group if default_group is not None else (self.assigned_group(current) if editing else (SERVICES[current.get('service','whatsapp')]['name'] if automatic else ''))
        photo=self.avatar_manager.path(current['id']) if current.get('id') else None
        result=edit_profile_dialog(self,title,current['name'],current.get('icon','user'),current.get('service','whatsapp'),editing,
            group_options=options,group=initial_group,group_forced=default_group is not None,
            avatar_mode=current.get('avatar_mode','auto'),photo_path=str(photo) if photo and photo.exists() else '',automatic_grouping=automatic,
            custom_url=current.get('custom_url',''))
        if result is None:return None
        name,preset=result[:2];service=result[2] if len(result)>2 else current.get('service','whatsapp')
        extra=result[3] if len(result)>3 else {}
        name=name.strip()
        if not name or len(name)>60:
            QMessageBox.information(self,'Nome inválido','Informe um nome entre 1 e 60 caracteres.');return None
        if any(a['id']!=current.get('id') and a['name'].casefold()==name.casefold() for a in self.accounts):
            QMessageBox.information(self,'Nome já usado','Escolha outro nome para o perfil.');return None
        draft=dict(name=name,icon=preset,service=service,avatar_mode=extra.get('avatar_mode',current.get('avatar_mode','service')),
            photo_path=extra.get('photo_path',''),group=extra.get('group',default_group or ''),
            new_group=extra.get('new_group',False),group_touched=extra.get('group_touched',default_group is not None),
            custom_url=extra.get('custom_url',current.get('custom_url','')))
        return draft

    def commit_profile(self, draft, row=None):
        old_records=[dict(a,archived=False) for a in self.accounts]+[dict(a,archived=True) for a in self.archived]
        key=self.accounts[row]['id'] if row is not None else str(uuid.uuid4())
        account=dict(self.accounts[row]) if row is not None else {'id':key}
        account.update({field:draft[field] for field in ('name','icon','service','avatar_mode')})
        if account['service'] in ('custom','chatwoot'):
            account['custom_url'] = draft.get('custom_url', '')
        else:
            account.pop('custom_url', None)
        accounts=[dict(a) for a in self.accounts]
        if row is None:accounts.append(account)
        else:accounts[row]=account
        candidate=deepcopy(self.settings)
        target=self.avatar_manager.path(key);previous_photo=None
        photo_written=False;profile_written=False
        try:
            if account['service'] in ('custom','chatwoot'):
                account['custom_url'] = normalize_custom_url(account['custom_url'])
                if row is not None and self.accounts[row].get('custom_url') and account['custom_url'] != self.accounts[row].get('custom_url'):
                    raise ValueError('Crie outro perfil para usar um endereço diferente.')
            if target.exists():previous_photo=target.read_bytes()
            if draft.get('group_touched'):
                candidate=custom_settings(self.settings,self.accounts+self.archived)
                value=draft.get('group','')
                if value:
                    value=group_name(value)
                    if draft.get('new_group') and any(existing.casefold()==value.casefold() for existing in self.group_catalog()):raise ValueError('Este grupo já existe.')
                    value=canonical_name(candidate,value,self.accounts+self.archived)
                    candidate['groups'].setdefault(value,{'color':DEFAULT_GROUP_COLOR})
                    candidate['profile_groups'][key]=value
                else:candidate['profile_groups'].pop(key,None)
            photo_path=draft.get('photo_path','')
            if account['avatar_mode']=='file' and photo_path and Path(photo_path).resolve()!=target.resolve():
                self.avatar_manager.import_file(key,photo_path);photo_written=True
            if account['avatar_mode']=='file' and not target.exists():raise ValueError('Escolha uma foto para o perfil.')
            self.store.save([dict(a,archived=False) for a in accounts]+[dict(a,archived=True) for a in self.archived]);profile_written=True
            if candidate!=self.settings:self.preferences_store.save(candidate)
        except (ValueError,OSError) as error:
            rollback=[]
            if profile_written:
                try:self.store.save(old_records)
                except (ValueError,OSError) as failure:rollback.append(str(failure))
            if photo_written and not rollback:
                try:
                    if previous_photo is None:self.avatar_manager.remove(key)
                    else:target.write_bytes(previous_photo);target.chmod(0o600)
                except OSError as failure:rollback.append(str(failure))
            message='Não foi possível salvar o perfil. '+str(error)
            if rollback:message+=' A reversão também encontrou um erro: '+'; '.join(rollback)
            QMessageBox.critical(self,'Perfil não salvo',message);return False
        self.accounts=accounts;self.settings=candidate
        self.refresh(len(accounts)-1 if row is None else row)
        return True

    def add(self, default_group=None):
        if not isinstance(default_group,str):default_group=None
        draft=self.ask_profile('Adicionar perfil',default_group=default_group)
        if draft is not None:self.commit_profile(draft)

    def rename(self):
        row=self.list.currentRow()
        if not 0<=row<len(self.accounts):return
        draft=self.ask_profile('Editar perfil',self.accounts[row])
        if draft is not None:self.commit_profile(draft,row)

    def remove(self):
        row = self.list.currentRow()
        if not 0<=row<len(self.accounts):return
        account = self.accounts[row]
        answer = QMessageBox.question(self, 'Arquivar perfil', f'Arquivar {account["name"]}?\nA conta deixará de funcionar nesta central até ser restaurada. A sessão local será preservada.\nPara encerrar o acesso definitivamente, saia da conta pelo próprio serviço.')
        if answer != QMessageBox.StandardButton.Yes:return
        accounts = self.accounts[:row] + self.accounts[row+1:]
        archived = self.archived + [dict(account, archived=True)]
        if not self.save(accounts, archived):return
        self.accounts, self.archived = accounts, archived
        for token, entry in list(self.notifications.items()):
            if entry[0] == account['id']:
                self.dismiss_notification(token)
        self.capture_permissions.pop(account['id'], None)
        item = self.views.pop(account['id'], None)
        if item:
            view, profile = item
            view.loadStarted.disconnect(); view.loadFinished.disconnect()
            self.stack.removeWidget(view); view.stop()
            view.page().deleteLater()
            if USE_QT_TEST_ENGINE:view.deleteLater()
            # Reutilizar o mesmo perfil ao restaurar evita abrir dois armazenamentos iguais.
        self.load_states.pop(account['id'], None)
        self._startup_ready.discard(account['id']);self._retry_counts.pop(account['id'],None);self._retry_pending.pop(account['id'],None);self._load_generations[account['id']]=self._load_generations.get(account['id'],0)+1
        self.pending_notifications.discard(account['id'])
        self.refresh()

    def restore(self):
        if not self.archived:return
        labels = [f'{i+1}. {a["name"]}' for i,a in enumerate(self.archived)]
        selected, ok = QInputDialog.getItem(self, 'Restaurar perfil', 'Perfil arquivado:', labels, 0, False)
        if not ok:return
        index = labels.index(selected)
        account = dict(self.archived[index], archived=False)
        if any(a['name'].casefold() == account['name'].casefold() for a in self.accounts):
            name = self.ask_name('Escolha outro nome para restaurar', account['name'])
            if name is None:return
            account['name'] = name
        accounts = self.accounts + [account]
        archived = self.archived[:index] + self.archived[index+1:]
        if not self.save(accounts, archived):return
        self.accounts, self.archived = accounts, archived
        self.refresh(len(accounts)-1)

    def update_status(self, key):
        if not 0<=self.list.currentRow()<len(self.accounts):return
        account = self.accounts[self.list.currentRow()]
        if account['id'] != key:return
        suffix = {'loading':' — Carregando…', 'error':' — Falha ao carregar. Verifique a conexão e recarregue.'}.get(self.load_states.get(key), '')
        self.status.setText(account['name'] + suffix)
        self.status.setToolTip(account['name'] + suffix)
        self.status.setVisible(self.load_states.get(key)=='error' and self.settings.get('bar_position','left')=='left' and not self.settings['sidebar_collapsed'])
        if self.load_states.get(key)=='error':
            self.list.item(self.list.currentRow()).setToolTip(account['name']+suffix)

    def loading(self, key):
        if key not in self.views:return
        self.load_states[key] = 'loading'
        account = next((a for a in self.accounts if a['id']==key),None)
        if account and account.get('service')=='telegram' and key not in self._startup_ready:
            self.views[key][0].show_loading('Carregando Telegram…')
        self.update_status(key)

    def select(self,row,force=False):
        if row<0 or row>=len(self.accounts) or (self.list.item(row).data(COLLAPSED_ROLE) and not force):
            self.update_actions(); return
        account=self.accounts[row]; key=account['id']
        if account.get('service')=='chatwoot' and not account.get('custom_url'):
            address,ok=QInputDialog.getText(self,'Endereço do Chatwoot','Informe o endereço HTTPS do seu Chatwoot:')
            if not ok:return
            try:address=normalize_custom_url(address)
            except ValueError as error:QMessageBox.information(self,'Endereço inválido',str(error));return
            candidate=[dict(a,custom_url=address) if a['id']==key else dict(a) for a in self.accounts]
            if not self.save(accounts=candidate):return
            self.accounts=candidate;account=self.accounts[row]
        if key not in self.views:
            try:
                folder = self.store.session_path(key)
            except (ValueError, OSError) as error:
                self.stack.setCurrentIndex(0)
                self.load_states[key] = 'error'
                self.update_status(key); self.update_actions()
                QMessageBox.critical(self, 'Não foi possível abrir o perfil', f'A sessão foi preservada. {error}')
                return
            if USE_QT_TEST_ENGINE:
                profile=self.profiles.get(key)
                if profile is None:
                    profile=QWebEngineProfile(key,self)
                    self.profiles[key]=profile
                    profile.downloadRequested.connect(self.download)
                # O WhatsApp rejeita o identificador QtWebEngine; mantém a versão real do Chromium.
                ua = re.sub(r'\sQtWebEngine/[^ ]+', '', profile.httpUserAgent())
                ua = re.sub(r'\scentral-whatsapp/[^ ]+', '', ua)
                profile.setHttpUserAgent(ua)
                profile.setPersistentStoragePath(str(folder/'storage')); profile.setCachePath(str(folder/'cache'))
                profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies)
                profile.setHttpCacheMaximumSize(100*1024*1024)
                profile.setHttpAcceptLanguage('pt-BR,pt;q=0.9,en;q=0.7')
                profile.setNotificationPresenter(lambda n,k=key:self.notify(k,n))
                view=ServiceView(); page=Page(profile,view,account.get('service','whatsapp'),account.get('custom_url',''));view.setPage(page)
                page.settings().setAttribute(QWebEngineSettings.WebAttribute.FullScreenSupportEnabled,True)
                page.settings().setAttribute(QWebEngineSettings.WebAttribute.PlaybackRequiresUserGesture,False)
                page.fullScreenRequested.connect(lambda request,k=key:self.media_fullscreen(k,request))
                page.initialResourceFailed.connect(lambda k=key:self.check_initial_content(k))
                page.loadingChanged.connect(lambda info,k=key:self.load_information(k,info))
            else:
                profile=CefProfile(self)
                self.profiles[key]=profile
                profile.downloadRequested.connect(self.download)
                profile.setNotificationPresenter(lambda n,k=key:self.notify(k,n))
                try:
                    view=CefServiceView(folder,account,profile)
                except (ValueError,OSError) as error:
                    self.profiles.pop(key,None);profile.deleteLater()
                    self.load_states[key]='error';self.update_status(key);self.update_actions()
                    QMessageBox.critical(self,'Não foi possível preparar o novo motor',f'A sessão antiga foi preservada. {error}')
                    return
                page=view
                page.fullScreenRequested.connect(lambda request,k=key:self.media_fullscreen(k,request))
            view.retry_button.clicked.connect(lambda checked=False,k=key:self.retry_service(k))
            view.alternative_button.clicked.connect(lambda checked=False,k=key:self.other_telegram_client(k))
            page.permissionRequested.connect(lambda permission,k=key:self.permission(k,permission))
            view.loadStarted.connect(lambda k=key:self.loading(k))
            view.loadFinished.connect(lambda ok,k=key:self.loaded(k,ok))
            self.views[key]=(view,profile);self.stack.addWidget(view)
            self.load_states[key] = 'loading'
            view.load(QUrl(service_url(account)))
        if self._fullscreen_key and self._fullscreen_key!=key and self._fullscreen_key in self.views:
            self.views[self._fullscreen_key][0].page().runJavaScript('document.exitFullscreen?.()')
        self.stack.setCurrentWidget(self.views[key][0])
        if self.viewing_profile(key):self.clear_selected_notification()
        self.update_status(key)
        self.update_actions()

    def loaded(self,key,ok):
        if key not in self.views:return
        self.load_states[key] = 'ready' if ok else 'error'
        self.update_status(key)
        account = next((a for a in self.accounts if a['id']==key),None)
        if account and account.get('service')=='telegram':
            if ok:QTimer.singleShot(2000,lambda k=key:self.check_initial_content(k))
            elif key not in self._retry_pending:self.views[key][0].show_loading('O Telegram não carregou. Tente novamente ou use o outro cliente web.')
        if ok:
            QTimer.singleShot(1500, lambda k=key:self.refresh_avatar(k))

    def load_information(self, key, info):
        account=next((a for a in self.accounts if a['id']==key),None)
        if account and account.get('service')=='telegram' and info.url().path()!=QUrl(service_url(account)).path():return
        if info.status()==QWebEngineLoadingInfo.LoadStatus.LoadFailedStatus and info.errorCode() in (-21,-101,-105,-106,-118):
            self.recover_initial_load(key)

    def check_initial_content(self, key):
        account = next((a for a in self.accounts if a['id']==key),None)
        if not account or account.get('service')!='telegram' or key not in self.views or key in self._startup_ready:return
        page = self.views[key][0].page()
        if not allows_url('telegram',page.url()):return
        generation=self._load_generations.get(key,0)
        count=self._content_checks.get(key,0)
        self._content_checks[key]=count+1
        def checked(ready):
            if key not in self.views or self._load_generations.get(key,0)!=generation:return
            if ready:
                self._startup_ready.add(key);self.views[key][0].loading_panel.hide()
                self.load_states[key]='ready';self.update_status(key)
            else:
                self.recover_initial_load(key)
                if count<10:QTimer.singleShot(3000,lambda:self.check_initial_content(key) if self._load_generations.get(key,0)==generation else None)
        # Only a boolean leaves the page; no conversation text is collected.
        page.runJavaScript('Boolean(location.protocol === \"https:\" && location.hostname === \"web.telegram.org\" && document.body && document.body.innerText.trim().length > 20)',checked)

    def recover_initial_load(self, key):
        account = next((a for a in self.accounts if a['id']==key),None)
        if not account or account.get('service')!='telegram' or key not in self.views or key in self._startup_ready or key in self._retry_pending:return
        count = self._retry_counts.get(key,0)
        if count>=2:
            self.load_states[key]='error';self.update_status(key)
            self.views[key][0].show_loading('O Telegram não carregou. Tente novamente ou use o outro cliente web.')
            return
        generation=self._load_generations.get(key,0)
        self._retry_counts[key]=count+1;self._retry_pending[key]=generation
        self.views[key][0].show_loading('Reconectando Telegram…')
        def retry():
            if self._load_generations.get(key,0)!=generation:return
            self._retry_pending.pop(key,None)
            current = next((a for a in self.accounts if a['id']==key),None)
            if current and key in self.views and key not in self._startup_ready:
                self.views[key][0].load(QUrl(service_url(current)))
        QTimer.singleShot(1200*(count+1),retry)

    def retry_service(self, key):
        account = next((a for a in self.accounts if a['id']==key),None)
        if account and key in self.views:
            self._retry_counts[key]=0;self._startup_ready.discard(key)
            self._retry_pending.pop(key,None);self._content_checks[key]=0
            self._load_generations[key]=self._load_generations.get(key,0)+1
            self.views[key][0].load(QUrl(service_url(account)))

    def other_telegram_client(self, key):
        account = next((a for a in self.accounts if a['id']==key),None)
        if account:self.set_telegram_client('k' if account.get('telegram_client','a')=='a' else 'a',key)

    def set_telegram_client(self, client, key=None):
        account = self.selected_account() if key is None else next((a for a in self.accounts if a['id']==key),None)
        if not account or account.get('service')!='telegram' or client not in ('a','k'):return
        key=account['id']
        accounts=[dict(a,telegram_client=client) if a['id']==key else dict(a) for a in self.accounts]
        if not self.save(accounts=accounts):return
        self.accounts=accounts;self._retry_counts[key]=0;self._startup_ready.discard(key)
        self._retry_pending.pop(key,None);self._content_checks[key]=0
        self._load_generations[key]=self._load_generations.get(key,0)+1
        if key in self.views:self.views[key][0].load(QUrl(service_url(next(a for a in accounts if a['id']==key))))
        self.update_actions()

    def keyPressEvent(self, event):
        if event.key()==Qt.Key.Key_Escape and self._fullscreen_state is not None:
            widget=self.views.get(self._fullscreen_key,(self.stack.currentWidget(),None))[0]
            if hasattr(widget,'page'):widget.page().runJavaScript('document.exitFullscreen?.()')
            event.accept();return
        super().keyPressEvent(event)

    def media_fullscreen(self, key, request):
        if request.toggleOn():
            if key not in self.views or not self.stack.isDisplayed(self.views[key][0]):request.reject();return
            self.stack.begin_fullscreen(self.views[key][0])
            self._fullscreen_state=self.windowState();self._fullscreen_key=key
            request.accept()
            self.showFullScreen()
            self.title_bar.hide();self.resize_grip.hide();self.sidebar.hide()
        else:
            if self._fullscreen_key!=key:request.reject();return
            request.accept()
            state=self._fullscreen_state if self._fullscreen_state is not None else Qt.WindowState.WindowNoState
            self.setWindowState(state);self._fullscreen_state=None;self._fullscreen_key=None
            self.stack.end_fullscreen()
            self.title_bar.show();self.sidebar.show();self.update_window_corners()

    def profile_icon(self, account):
        mode=account.get('avatar_mode','auto')
        fallback=service_icon(account.get('service','whatsapp'))
        if mode=='icon':base=icon(account.get('icon','user'))
        elif mode=='service':base=fallback
        else:base=self.avatar_manager.icon(account['id'],fallback)
        return base

    def account_icon(self, account):
        return self.profile_icon(account)

    def update_avatar_icon(self, key):
        for row, account in enumerate(self.accounts):
            if account['id'] == key:self.list.item(row).setIcon(self.account_icon(account))

    def selected_account(self):
        row=self.list.currentRow()
        return self.accounts[row] if 0 <= row < len(self.accounts) and not self.list.item(row).data(COLLAPSED_ROLE) else None

    def set_avatar_mode(self, key, mode):
        accounts=[dict(a, avatar_mode=mode) if a['id']==key else dict(a) for a in self.accounts]
        if not self.save(accounts=accounts):return False
        self.accounts=accounts
        self.update_avatar_icon(key)
        return True

    def choose_profile_photo(self):
        account=self.selected_account()
        if account is None:return
        path,_=QFileDialog.getOpenFileName(self,'Escolher foto do perfil',str(Path.home()),'Imagens (*.png *.jpg *.jpeg *.webp)')
        if not path:return
        key=account['id']
        # Mantém tanto o arquivo anterior quanto a configuração se a gravação falhar.
        target=self.avatar_manager.path(key)
        try:
            previous=target.read_bytes() if target.exists() else None
            self.avatar_manager.import_file(key,path)
            if not self.set_avatar_mode(key,'file'):
                if previous is None:self.avatar_manager.remove(key)
                else:target.write_bytes(previous);target.chmod(0o600)
        except (ValueError,OSError) as error:
            QMessageBox.warning(self,'Foto não alterada',str(error))

    def use_service_icon(self):
        account=self.selected_account()
        if account:self.set_avatar_mode(account['id'],'service')

    def use_profile_icon(self):
        account=self.selected_account()
        if account:self.set_avatar_mode(account['id'],'icon')

    def use_automatic_photo(self):
        account=self.selected_account()
        if account is None:return
        key=account['id']
        if self.set_avatar_mode(key,'auto'):
            if account.get('avatar_mode','auto')!='auto':
                try:self.avatar_manager.remove(key)
                except OSError:pass
                self.update_avatar_icon(key)
            self.refresh_avatar(key, explain=True)
            self.status.setText(account['name']+' — Buscando sua foto; o ícone será usado se ela não estiver disponível.')

    def poll_avatars(self):
        for account in self.accounts:
            if account.get('avatar_mode','auto')=='auto':self.refresh_avatar(account['id'])

    def refresh_avatar(self, key, explain=False):
        account=next((a for a in self.accounts if a['id']==key),None)
        if not account or account.get('service','whatsapp')!='whatsapp' or account.get('avatar_mode','auto')!='auto' or key not in self.views or key in self.avatar_pending:return
        page=self.views[key][0].page()
        if page.url().host()!='web.whatsapp.com' or page.url().scheme()!='https':return
        self.avatar_pending.add(key)
        def received(value):
            self.avatar_pending.discard(key)
            try:value=json.loads(value) if isinstance(value,str) else value
            except (ValueError,TypeError):value=None
            current=next((a for a in self.accounts if a['id']==key),None)
            if not current or current.get('avatar_mode','auto')!='auto' or key not in self.views:return
            success=False
            try:
                if isinstance(value,str) and value.startswith('data:image/png;base64,'):
                    self.avatar_manager.save_data_url(key,value)
                    success=True
                elif isinstance(value,dict) and value.get('status')=='capture':
                    view=self.views[key][0]
                    # Não captura janelas ocultas, outro perfil ou a área de conversas.
                    if view.isVisible() and self.stack.currentWidget() is view:
                        rect=value.get('rect',{})
                        factor=view.zoomFactor()
                        bounds=QRect(round(float(rect['x'])*factor),round(float(rect['y'])*factor),round(float(rect['width'])*factor),round(float(rect['height'])*factor))
                        if 16 <= bounds.width() <= 256 and 16 <= bounds.height() <= 256 and view.rect().contains(bounds):
                            image=view.grab(bounds).toImage()
                            if not image.isNull():
                                self.avatar_manager._save(key,image)
                                success=True
                if success:self.update_avatar_icon(key)
            except (ValueError,OSError,KeyError,TypeError,OverflowError,RuntimeError):pass
            if explain:
                if success:
                    self.status.setText(current['name']+' — Foto atualizada.')
                else:
                    self.status.setText(current['name']+' — Foto automática indisponível.')
                    QMessageBox.information(self,'Foto automática indisponível',
                        'Não foi possível identificar sua própria foto nesta tela. Confira se a conta está conectada e sua foto aparece na barra do WhatsApp. Você também pode usar Botão direito no perfil → Foto do perfil → Usar foto do computador.')
        page.runJavaScript('JSON.stringify('+OWN_AVATAR_SCRIPT+')',received)

    def reset_call_permissions(self):
        account = self.selected_account()
        if not account or account['id'] not in self.views:
            return
        if QMessageBox.question(self, 'Câmera e microfone',
                'Revisar as permissões e recarregar este perfil? Uma ligação em andamento será interrompida. Na próxima ligação, o chat pedirá autorização novamente.') != QMessageBox.StandardButton.Yes:
            return
        if not USE_QT_TEST_ENGINE:
            self.views[account['id']][0].reload()
            QMessageBox.information(self, 'Permissões revisadas', 'Inicie a ligação novamente. O novo motor solicita autorização para câmera e microfone a cada chamada.')
            return
        profile = self.views[account['id']][1]
        origin = QUrl(service_url(account))
        kinds = (
            QWebEnginePermission.PermissionType.MediaAudioCapture,
            QWebEnginePermission.PermissionType.MediaVideoCapture,
            QWebEnginePermission.PermissionType.MediaAudioVideoCapture,
        )
        previous = self.capture_permissions.pop(account['id'], {})
        for kind in kinds:
            permission = previous.get(kind)
            if permission is None or not permission.isValid():
                permission = profile.queryPermission(origin, kind)
            if permission.isValid():
                permission.reset()
        self.views[account['id']][0].reload()
        QMessageBox.information(self, 'Permissões revisadas',
            'Inicie a ligação novamente e permita o uso da câmera e do microfone quando o chat solicitar.')

    def permission(self,key,permission):
        account=next((a for a in self.accounts if a['id']==key),None)
        if key not in self.views or not account or not allows_url(account.get('service','whatsapp'), permission.origin(), account.get('custom_url','')):permission.deny();return
        kind=permission.permissionType()
        allowed={QWebEnginePermission.PermissionType.Notifications:'mostrar notificações',QWebEnginePermission.PermissionType.MediaAudioCapture:'usar o microfone',QWebEnginePermission.PermissionType.MediaVideoCapture:'usar a câmera',QWebEnginePermission.PermissionType.MediaAudioVideoCapture:'usar câmera e microfone'}
        if kind not in allowed:permission.deny();return
        if kind != QWebEnginePermission.PermissionType.Notifications:
            self.capture_permissions.setdefault(key, {})[kind] = permission
        name=next((a['name'] for a in self.accounts if a['id']==key),'Perfil')
        if QMessageBox.question(self,'Permissão do serviço',f'{name}\n{permission.origin().toDisplayString()}\n\nPermitir {allowed[kind]}?')==QMessageBox.StandardButton.Yes:permission.grant()
        else:permission.deny()

    def notify(self,key,notification):
        if key not in self.views:
            notification.close(); return
        if not self.viewing_profile(key):
            self.pending_notifications.add(key)
            self.apply_sidebar(self.settings['sidebar_collapsed'])
            self.update_actions()
        if key in self.settings['muted_profiles']:
            notification.close(); return
        account = next((a for a in self.accounts if a['id'] == key), None)
        if account is None:
            notification.close()
            return
        token = next(self.notification_ids)
        summary = account['name'] + ' · ' + notification.title()
        body = notification.message()
        avatar = self.profile_icon(account).pixmap(64, 64)
        composed = avatar.copy()
        painter = QPainter(composed)
        painter.drawPixmap(composed.width() - 26, composed.height() - 26, self.windowIcon().pixmap(26, 26))
        painter.end()
        image = str(Path(self.notification_images.path()) / f'{token}.png') if self.notification_images.isValid() else ''
        if image and not composed.save(image):
            image = ''
        self.notifications[token] = (key, notification, image, summary, body)
        notification.closed.connect(lambda: self.dismiss_notification(token, close_web=False))
        notification.show()
        desktop_entry = os.environ.get('FLATPAK_ID', 'central-whatsapp')
        self.desktop_notifications.send(token, desktop_entry, summary, body, image, desktop_entry)

    def notification_delivered(self, token, delivered):
        entry = self.notifications.get(token)
        if entry is None:
            self.desktop_notifications.close_notification(token)
        elif not delivered:
            self.dismiss_notification(self.tray_notification)
            self.tray_notification = token
            self.tray.showMessage(entry[3], entry[4], QIcon(entry[2]) if entry[2] else self.windowIcon())
            QTimer.singleShot(30000, lambda: self.dismiss_notification(token))

    def open_tray_notification(self):
        self.open_notification(self.tray_notification)

    def open_notification(self, token):
        entry = self.notifications.get(token)
        if entry is None:
            return
        key, notification, _, _, _ = entry
        row = next((i for i, account in enumerate(self.accounts) if account['id'] == key), -1)
        if row >= 0 and key in self.views:
            group_key = self.list.item(row).data(GROUP_KEY_ROLE)
            if group_key in self.settings['collapsed_groups']:
                self.toggle_group(group_key)
            self.show_window()
            with QSignalBlocker(self.list):
                self.list.setCurrentRow(row)
            self.select(row, force=True)
            self.list.scrollToItem(self.list.item(row))
            # The originating site's click handler knows the conversation.
            notification.click()

    def dismiss_notification(self, token, close_web=True):
        entry = self.notifications.pop(token, None)
        if entry is None:
            return
        if token == self.tray_notification:
            self.tray_notification = None
        self.desktop_notifications.close_notification(token)
        if entry[2]:
            Path(entry[2]).unlink(missing_ok=True)
        if close_web:
            try:
                entry[1].close()
            except RuntimeError:
                pass

    def download(self,item):
        path,_=QFileDialog.getSaveFileName(self,'Salvar arquivo',str(Path.home()/'Downloads'/Path(item.downloadFileName()).name))
        if not path:item.cancel();return
        item.stateChanged.connect(lambda state, request=item:self.download_state(request, state))
        target=Path(path);item.setDownloadDirectory(str(target.parent));item.setDownloadFileName(target.name);item.accept()

    def download_state(self, item, state):
        if state == item.DownloadState.DownloadInterrupted:
            QMessageBox.warning(self, 'Download interrompido', 'Não foi possível concluir o download. Tente novamente no serviço de origem.')
        elif state == item.DownloadState.DownloadCompleted:
            path = Path(item.downloadDirectory()) / item.downloadFileName()
            if QMimeDatabase().mimeTypeForFile(str(path), QMimeDatabase.MatchMode.MatchContent).name().startswith('video/'):
                answer = QMessageBox.question(self, 'Vídeo salvo', 'Abrir o vídeo no player do sistema?')
                if answer == QMessageBox.StandardButton.Yes and not QDesktopServices.openUrl(QUrl.fromLocalFile(str(path))):
                    QMessageBox.warning(self, 'Player indisponível', 'Abra o arquivo salvo em um player de vídeo do sistema.')


    def reload(self):
        account = self.selected_account()
        if account and account['id'] in self.views:
            if account.get('service')=='telegram':self.retry_service(account['id'])
            else:self.views[account['id']][0].reload()

    def cleanup(self):
        if self._cleaned:
            return
        self._cleaned = True
        self.avatar_timer.stop()
        if hasattr(self,'chrome'):self.chrome.close()
        self.capture_permissions.clear()
        self.tray.hide()
        for token in list(self.notifications):
            self.dismiss_notification(token)
        for view, profile in self.views.values():
            self.stack.removeWidget(view)
            view.stop()
            view.page().deleteLater()
            if USE_QT_TEST_ENGINE:view.deleteLater()
        self.views.clear()

    def quit_app(self):
        self._quitting = True
        self.close()
        QApplication.instance().quit()

    def closeEvent(self, event):
        if self._quitting or not self.confirm_close:
            self.cleanup()
            event.accept()
            return
        if self.settings['close_action'] == 'background':
            event.ignore()
            if self.can_background():
                self.hide()
            else:
                QMessageBox.information(self, 'Central continua aberta',
                    'Não há um meio confirmado de reabrir a central oculta. A janela continuará visível. Para encerrar, use Menu → Sair da central.')
            return
        self.cleanup()
        event.accept()
        QApplication.instance().quit()


def instance_name(data_dir=DATA):
    digest = hashlib.sha256(str(Path(data_dir).resolve()).encode()).hexdigest()[:24]
    return f'central-whatsapp-{os.getuid()}-{digest}'


def activate_existing(data_dir=DATA):
    socket = QLocalSocket()
    socket.connectToServer(instance_name(data_dir))
    if not socket.waitForConnected(1500):
        return False
    socket.write(b'SHOW\n')
    socket.flush()
    if not socket.bytesAvailable():
        socket.waitForReadyRead(1500)
    acknowledged = bytes(socket.readAll()) == b'OK\n'
    socket.disconnectFromServer()
    return acknowledged


class ActivationServer:
    def __init__(self, window, data_dir=DATA):
        self.window = window
        self.name = instance_name(data_dir)
        self.server = QLocalServer(window)
        self.server.setSocketOptions(QLocalServer.SocketOption.UserAccessOption)
        # Chamador principal já detém o QLockFile; pode limpar socket obsoleto.
        QLocalServer.removeServer(self.name)
        self.ready = self.server.listen(self.name)
        self.window.activation_ready = self.ready
        self.server.newConnection.connect(self.accept)
        self.clients = set()

    def accept(self):
        while self.server.hasPendingConnections():
            socket = self.server.nextPendingConnection()
            self.clients.add(socket)
            socket.setReadBufferSize(64)
            socket.readyRead.connect(lambda client=socket:self.read(client))
            socket.disconnected.connect(lambda client=socket:self.drop(client))
            timer = QTimer(socket)
            timer.setSingleShot(True)
            timer.timeout.connect(socket.disconnectFromServer)
            timer.start(3000)
            if socket.bytesAvailable():
                self.read(socket)

    def read(self, socket):
        if not socket.canReadLine():return
        if bytes(socket.readLine(64)) == b'SHOW\n':
            self.window.show_window()
            socket.write(b'OK\n')
            socket.flush()
        socket.disconnectFromServer()

    def drop(self, socket):
        self.clients.discard(socket)
        socket.deleteLater()

    def close(self):
        self.window.activation_ready = False
        for socket in list(self.clients):
            socket.abort()
        self.server.close()


def main():
    app = QApplication(sys.argv)
    if not USE_QT_TEST_ENGINE and app.platformName() != 'xcb':
        QMessageBox.critical(None, 'Sessão gráfica incompatível', 'O novo motor requer X11 ou XWayland. Abra a Central pelo atalho instalado, que seleciona essa compatibilidade.')
        return 1
    app.setStyle('Fusion')
    translator = QTranslator(app)
    if translator.load('qtbase_pt_BR', QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)):
        app.installTranslator(translator)
    app.setApplicationName('central-whatsapp')
    app.setDesktopFileName(os.environ.get('FLATPAK_ID', 'central-whatsapp'))
    app.setQuitOnLastWindowClosed(False)
    try:
        ProfileStore(DATA)
    except OSError as error:
        QMessageBox.critical(None, 'Dados indisponíveis', f'Não foi possível abrir a pasta da central. {error}')
        return 1
    lock = QLockFile(str(DATA/'app.lock'))
    if not lock.tryLock(100):
        if '--autostart' in sys.argv:
            return 0
        if activate_existing():
            return 0
        QMessageBox.information(None, 'Central já aberta',
            'A central está aberta, mas esta instância não respondeu ao pedido de mostrar a janela. Abra-a pela bandeja ou feche a versão anterior antes de iniciar a nova.')
        return 1
    window = Window()
    server = ActivationServer(window)
    app.aboutToQuit.connect(window.cleanup)
    app.aboutToQuit.connect(server.close)
    QTimer.singleShot(0, lambda:window.start(autostart='--autostart' in sys.argv))
    result = app.exec()
    lock.unlock()
    return result


if __name__ == '__main__':
    sys.exit(main())
