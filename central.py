#!/usr/bin/env python3
import json
import re
import shutil
import subprocess
import os
import sys
import uuid
import hashlib
from copy import deepcopy
from pathlib import Path
from avatar_manager import AvatarManager, OWN_AVATAR_SCRIPT
from profile_store import ProfileStore
from settings_store import PreferencesStore, AutostartManager
from desktop_ui import DesktopUIMixin, PreferencesDialog, edit_profile_dialog, icon
from PySide6.QtCore import QUrl, QLockFile, QTimer, Qt, QRect
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtGui import QDesktopServices, QIcon
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
 QListWidget, QPushButton, QLabel, QStackedWidget, QInputDialog, QMessageBox, QFileDialog, QSystemTrayIcon, QMenu, QDialog)
from PySide6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage, QWebEnginePermission
from PySide6.QtWebEngineWidgets import QWebEngineView

DATA = Path(os.environ.get('CENTRAL_WHATSAPP_DATA', str(Path(os.environ.get('XDG_DATA_HOME',str(Path.home()/'.local/share')))/'central-whatsapp-data')))
CONFIG = DATA/'profiles.json'

class Page(QWebEnginePage):
    def acceptNavigationRequest(self, url, kind, main):
        if url.scheme() == 'https' and url.host() == 'web.whatsapp.com':
            return True
        if kind == QWebEnginePage.NavigationType.NavigationTypeLinkClicked:
            if url.scheme() in ('https', 'http', 'mailto'):
                QDesktopServices.openUrl(url)
        return False

class Window(DesktopUIMixin, QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Central Chats')
        self.resize(1250, 820)
        self.setWindowIcon(QIcon(str(Path(__file__).with_name('whatsapp-web.svg'))))
        self.views, self.profiles, self.load_states = {}, {}, {}
        self.notifications = []
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
        self.build_ui()
        self.setup_tray()
        self.refresh()
        self.avatar_timer = QTimer(self)
        self.avatar_timer.timeout.connect(self.poll_avatars)
        self.avatar_timer.start(30000)

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
        # O Qt também registra o ícone se uma bandeja surgir depois.
        self.tray.show()

    def tray_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self.show_window()

    def show_window(self):
        self.showNormal()
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
        self.apply_sidebar(self.settings['sidebar_collapsed'])
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
        if rows:
            self.list.setCurrentRow(rows[0])

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
        selected = 0 <= self.list.currentRow() < len(self.accounts)
        for action in (self.photo_file_action, self.photo_auto_action, self.photo_icon_action):
            action.setEnabled(selected)
        self.rename_button.setEnabled(selected)
        self.archive_button.setEnabled(selected)
        self.reload_button.setEnabled(selected and isinstance(self.stack.currentWidget(), QWebEngineView))
        self.restore_button.setEnabled(bool(self.archived))

    def refresh(self, row=-1):
        self.list.blockSignals(True); self.list.clear()
        self.list.addItems([a['name'] for a in self.accounts])
        for i, account in enumerate(self.accounts):
            self.list.item(i).setToolTip(account['name'])
            self.list.item(i).setIcon(self.account_icon(account))
        self.list.blockSignals(False)
        self.list.setCurrentRow(row)
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

    def ask_profile(self, title, current=None):
        current = current or {'name':'', 'icon':'user'}
        result = edit_profile_dialog(self, title, current['name'], current.get('icon', 'user'))
        if result is None:
            return None
        name, preset = result
        name = name.strip()
        if not name or len(name) > 60:
            QMessageBox.information(self, 'Nome inválido', 'Informe um nome entre 1 e 60 caracteres.')
            return None
        if any(a['id'] != current.get('id') and a['name'].casefold() == name.casefold() for a in self.accounts):
            QMessageBox.information(self, 'Nome já usado', 'Escolha outro nome para o perfil.')
            return None
        return name, preset

    def add(self):
        result = self.ask_profile('Adicionar perfil')
        if result is None:return
        name, preset = result
        accounts = self.accounts + [{'id':str(uuid.uuid4()), 'name':name, 'icon':preset}]
        if not self.save(accounts=accounts):return
        self.accounts = accounts
        self.refresh(len(accounts)-1)

    def rename(self):
        row = self.list.currentRow()
        if row < 0:return
        result = self.ask_profile('Editar perfil', self.accounts[row])
        if result is None:return
        name, preset = result
        accounts = [dict(a) for a in self.accounts]
        accounts[row].update(name=name, icon=preset)
        if not self.save(accounts=accounts):return
        self.accounts = accounts
        self.refresh(row)

    def remove(self):
        row = self.list.currentRow()
        if row < 0:return
        account = self.accounts[row]
        answer = QMessageBox.question(self, 'Arquivar perfil', f'Arquivar {account["name"]}?\nA conta deixará de funcionar nesta central até ser restaurada. A sessão local será preservada.\nPara desvincular, use Aparelhos conectados no celular.')
        if answer != QMessageBox.StandardButton.Yes:return
        accounts = self.accounts[:row] + self.accounts[row+1:]
        archived = self.archived + [dict(account, archived=True)]
        if not self.save(accounts, archived):return
        self.accounts, self.archived = accounts, archived
        item = self.views.pop(account['id'], None)
        if item:
            view, profile = item
            view.loadStarted.disconnect(); view.loadFinished.disconnect()
            self.stack.removeWidget(view); view.stop()
            view.page().deleteLater(); view.deleteLater()
            # Reutilizar o mesmo perfil ao restaurar evita abrir dois armazenamentos iguais.
        self.load_states.pop(account['id'], None)
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
        if self.list.currentRow() < 0:return
        account = self.accounts[self.list.currentRow()]
        if account['id'] != key:return
        suffix = {'loading':' — Carregando…', 'error':' — Falha ao carregar. Verifique a conexão e recarregue.'}.get(self.load_states.get(key), '')
        self.status.setText(account['name'] + suffix)
        self.status.setToolTip(account['name'] + suffix)

    def loading(self, key):
        if key not in self.views:return
        self.load_states[key] = 'loading'
        self.update_status(key)

    def select(self,row):
        if row<0:
            self.update_actions(); return
        account=self.accounts[row]; key=account['id']
        if key not in self.views:
            try:
                folder = self.store.session_path(key)
            except (ValueError, OSError) as error:
                self.stack.setCurrentIndex(0)
                self.load_states[key] = 'error'
                self.update_status(key); self.update_actions()
                QMessageBox.critical(self, 'Não foi possível abrir o perfil', f'A sessão foi preservada. {error}')
                return
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
            view=QWebEngineView(); page=Page(profile,view);view.setPage(page)
            page.permissionRequested.connect(lambda permission,k=key:self.permission(k,permission))
            view.loadStarted.connect(lambda k=key:self.loading(k))
            view.loadFinished.connect(lambda ok,k=key:self.loaded(k,ok))
            self.views[key]=(view,profile);self.stack.addWidget(view)
            self.load_states[key] = 'loading'
            view.load(QUrl('https://web.whatsapp.com/'))
        self.stack.setCurrentWidget(self.views[key][0])
        self.update_status(key)
        self.update_actions()

    def loaded(self,key,ok):
        if key not in self.views:return
        self.load_states[key] = 'ready' if ok else 'error'
        self.update_status(key)
        if ok:
            QTimer.singleShot(1500, lambda k=key:self.refresh_avatar(k))

    def account_icon(self, account):
        fallback = icon(account.get('icon', 'user'))
        if account.get('avatar_mode', 'auto') == 'icon':return fallback
        return self.avatar_manager.icon(account['id'], fallback)

    def update_avatar_icon(self, key):
        for row, account in enumerate(self.accounts):
            if account['id'] == key:self.list.item(row).setIcon(self.account_icon(account))

    def selected_account(self):
        row=self.list.currentRow()
        return self.accounts[row] if 0 <= row < len(self.accounts) else None

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
        if not account or account.get('avatar_mode','auto')!='auto' or key not in self.views or key in self.avatar_pending:return
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
                        'Não foi possível identificar sua própria foto nesta tela. Confira se a conta está conectada e sua foto aparece na barra do WhatsApp. Você também pode usar Menu → Foto do perfil → Usar foto do computador.')
        page.runJavaScript('JSON.stringify('+OWN_AVATAR_SCRIPT+')',received)

    def permission(self,key,permission):
        if key not in self.views or permission.origin().scheme()!='https' or permission.origin().host()!='web.whatsapp.com':permission.deny();return
        kind=permission.permissionType()
        allowed={QWebEnginePermission.PermissionType.Notifications:'mostrar notificações',QWebEnginePermission.PermissionType.MediaAudioCapture:'usar o microfone',QWebEnginePermission.PermissionType.MediaVideoCapture:'usar a câmera',QWebEnginePermission.PermissionType.MediaAudioVideoCapture:'usar câmera e microfone'}
        if kind not in allowed:permission.deny();return
        name=next((a['name'] for a in self.accounts if a['id']==key),'Perfil')
        if QMessageBox.question(self,'Permissão do WhatsApp',f'{name}: permitir {allowed[kind]}?')==QMessageBox.StandardButton.Yes:permission.grant()
        else:permission.deny()

    def notify(self,key,notification):
        if key not in self.views or key in self.settings['muted_profiles']:
            notification.close(); return
        name=next((a['name'] for a in self.accounts if a['id']==key),'WhatsApp')
        self.notifications.append(notification); notification.show()
        try:
            if shutil.which('notify-send'):
                subprocess.Popen(['notify-send','--app-name=Central Chats','--icon=central-whatsapp',name+' · '+notification.title(),notification.message()],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            elif shutil.which('gdbus'):
                subprocess.Popen(['gdbus','call','--session','--dest','org.freedesktop.Notifications','--object-path','/org/freedesktop/Notifications','--method','org.freedesktop.Notifications.Notify',json.dumps('Central Chats'),'0',json.dumps('central-whatsapp'),json.dumps(name+' · '+notification.title(),ensure_ascii=False),json.dumps(notification.message(),ensure_ascii=False),'[]','{}','-1'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            else:
                self.tray.showMessage(name+' · '+notification.title(),notification.message())
        except OSError:
            self.tray.showMessage(name+' · '+notification.title(),notification.message())
        QTimer.singleShot(15000,lambda:self.finish_notification(notification))

    def finish_notification(self,n):
        try: n.close()
        except RuntimeError: pass
        if n in self.notifications:self.notifications.remove(n)

    def download(self,item):
        path,_=QFileDialog.getSaveFileName(self,'Salvar arquivo',str(Path.home()/'Downloads'/Path(item.downloadFileName()).name))
        if not path:item.cancel();return
        item.stateChanged.connect(lambda state, request=item:self.download_state(request, state))
        target=Path(path);item.setDownloadDirectory(str(target.parent));item.setDownloadFileName(target.name);item.accept()

    def download_state(self, item, state):
        if state == item.DownloadState.DownloadInterrupted:
            QMessageBox.warning(self, 'Download interrompido', 'Não foi possível concluir o download. Tente novamente pelo WhatsApp.')

    def reload(self):
        widget=self.stack.currentWidget()
        if isinstance(widget,QWebEngineView):widget.reload()

    def cleanup(self):
        if self._cleaned:
            return
        self._cleaned = True
        self.avatar_timer.stop()
        self.tray.hide()
        for notification in list(self.notifications):
            self.finish_notification(notification)
        for view, profile in self.views.values():
            view.stop()
            view.page().deleteLater()
            view.deleteLater()
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
