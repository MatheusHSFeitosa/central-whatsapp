#!/usr/bin/env python3
import json
import re
import shutil
import subprocess
import os
import sys
import uuid
from pathlib import Path
from profile_store import ProfileStore
from PySide6.QtCore import QUrl, QLockFile, QTimer
from PySide6.QtGui import QDesktopServices, QIcon
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
 QListWidget, QPushButton, QLabel, QStackedWidget, QInputDialog, QMessageBox, QFileDialog, QSystemTrayIcon)
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

class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Central WhatsApp')
        self.resize(1250, 820)
        self.setWindowIcon(QIcon(str(Path(__file__).with_name('whatsapp-web.svg'))))
        self.views = {}
        self.profiles = {}
        self.load_states = {}
        self.setStyleSheet("QMainWindow { background: #172126; color: #e9efed; } QWidget { font-size: 14px; } QListWidget { background: #202e34; color: #e9efed; border: none; border-radius: 8px; padding: 6px; } QListWidget::item { padding: 13px 10px; } QListWidget::item:selected { background: #145c47; color: #ffffff; border-radius: 6px; } QPushButton { background: #263a40; color: #e9efed; border: 1px solid #43545a; border-radius: 7px; padding: 8px; } QPushButton:hover { background: #345149; } QPushButton:disabled { background: #202d32; color: #89969b; border-color: #344349; } QLabel { color: #e9efed; }")
        self.notifications = []
        self.confirm_close = True
        try:
            self.store = ProfileStore(DATA)
            records = self.store.load()
            self.accounts = [a for a in records if not a.get('archived', False)]
            self.archived = [a for a in records if a.get('archived', False)]
        except Exception as e:
            QMessageBox.critical(self, 'Configuração inválida', f'Os perfis foram preservados. Não foi possível ler a configuração: {e}')
            raise SystemExit(1)
        root = QWidget(); self.setCentralWidget(root)
        layout = QHBoxLayout(root)
        side = QVBoxLayout(); layout.addLayout(side)
        title = QLabel('Central WhatsApp'); title.setStyleSheet('font-size:20px;font-weight:600;padding:12px 0')
        side.addWidget(title)
        self.list = QListWidget(); self.list.setAccessibleName('Perfis do WhatsApp'); self.list.setFixedWidth(205); side.addWidget(self.list)
        self.rename_button = QPushButton('Renomear')
        self.archive_button = QPushButton('Arquivar perfil')
        self.restore_button = QPushButton('Restaurar perfil')
        add_button = QPushButton('+ Adicionar perfil')
        for button, fn in [(add_button,self.add),(self.rename_button,self.rename),(self.archive_button,self.remove),(self.restore_button,self.restore)]:
            button.setMinimumHeight(36); button.clicked.connect(fn); side.addWidget(button)
        hint = QLabel('Contas carregadas permanecem\nativas enquanto a central estiver aberta.')
        hint.setWordWrap(True); hint.setMaximumWidth(205)
        side.addWidget(hint)
        right=QVBoxLayout(); layout.addLayout(right,1)
        bar=QHBoxLayout(); right.addLayout(bar)
        self.status=QLabel('Selecione ou adicione um perfil'); bar.addWidget(self.status,1)
        self.reload_button=QPushButton('Recarregar'); self.reload_button.clicked.connect(self.reload); bar.addWidget(self.reload_button)
        self.stack=QStackedWidget(); right.addWidget(self.stack,1)
        welcome=QLabel('Seus WhatsApps, em um só lugar.\n\nAdicione um perfil e conecte pelo QR Code.'); welcome.setStyleSheet('padding:40px;font-size:18px')
        self.stack.addWidget(welcome)
        self.tray=QSystemTrayIcon(self.windowIcon(),self)
        self.tray.setToolTip('Central WhatsApp')
        self.tray.activated.connect(lambda reason: (self.showNormal(), self.raise_(), self.activateWindow()))
        if QSystemTrayIcon.isSystemTrayAvailable(): self.tray.show()
        self.list.currentRowChanged.connect(self.select)
        self.refresh()

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
        self.rename_button.setEnabled(selected)
        self.archive_button.setEnabled(selected)
        self.reload_button.setEnabled(selected and isinstance(self.stack.currentWidget(), QWebEngineView))
        self.restore_button.setEnabled(bool(self.archived))

    def refresh(self, row=-1):
        self.list.blockSignals(True); self.list.clear()
        self.list.addItems([a['name'] for a in self.accounts])
        for i, account in enumerate(self.accounts):
            self.list.item(i).setToolTip(account['name'])
        self.list.blockSignals(False)
        self.list.setCurrentRow(row)
        if row < 0:
            self.stack.setCurrentIndex(0)
            self.status.setText('Selecione ou adicione um perfil')
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

    def add(self):
        name = self.ask_name('Adicionar perfil')
        if name is None:return
        accounts = self.accounts + [{'id':str(uuid.uuid4()), 'name':name}]
        if not self.save(accounts=accounts):return
        self.accounts = accounts
        self.refresh(len(accounts)-1)

    def rename(self):
        row = self.list.currentRow()
        if row < 0:return
        name = self.ask_name('Renomear perfil', self.accounts[row]['name'], self.accounts[row]['id'])
        if name is None:return
        accounts = [dict(a) for a in self.accounts]
        accounts[row]['name'] = name
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

    def permission(self,key,permission):
        if key not in self.views or permission.origin().host()!='web.whatsapp.com':permission.deny();return
        kind=permission.permissionType()
        allowed={QWebEnginePermission.PermissionType.Notifications:'mostrar notificações',QWebEnginePermission.PermissionType.MediaAudioCapture:'usar o microfone',QWebEnginePermission.PermissionType.MediaVideoCapture:'usar a câmera',QWebEnginePermission.PermissionType.MediaAudioVideoCapture:'usar câmera e microfone'}
        if kind not in allowed:permission.deny();return
        name=next((a['name'] for a in self.accounts if a['id']==key),'Perfil')
        if QMessageBox.question(self,'Permissão do WhatsApp',f'{name}: permitir {allowed[kind]}?')==QMessageBox.StandardButton.Yes:permission.grant()
        else:permission.deny()

    def notify(self,key,notification):
        if key not in self.views:
            notification.close(); return
        name=next((a['name'] for a in self.accounts if a['id']==key),'WhatsApp')
        self.notifications.append(notification); notification.show()
        try:
            if shutil.which('notify-send'):
                subprocess.Popen(['notify-send','--app-name=Central WhatsApp','--icon=central-whatsapp',name+' · '+notification.title(),notification.message()],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            elif shutil.which('gdbus'):
                subprocess.Popen(['gdbus','call','--session','--dest','org.freedesktop.Notifications','--object-path','/org/freedesktop/Notifications','--method','org.freedesktop.Notifications.Notify',json.dumps('Central WhatsApp'),'0',json.dumps('central-whatsapp'),json.dumps(name+' · '+notification.title(),ensure_ascii=False),json.dumps(notification.message(),ensure_ascii=False),'[]','{}','-1'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
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

    def closeEvent(self,event):
        if self.confirm_close and self.views and QMessageBox.question(self,'Fechar central','Fechar todas as contas? As notificações param ao sair.')!=QMessageBox.StandardButton.Yes:
            event.ignore();return
        # Páginas precisam ser destruídas antes dos perfis.
        for view,profile in self.views.values():
            view.page().deleteLater();view.deleteLater()
        event.accept()

if __name__=='__main__':
    app=QApplication(sys.argv);app.setApplicationName('central-whatsapp');app.setDesktopFileName(os.environ.get('FLATPAK_ID','central-whatsapp'))
    try:
        ProfileStore(DATA)
    except OSError as error:
        QMessageBox.critical(None, 'Dados indisponíveis', f'Não foi possível abrir a pasta da central. {error}'); sys.exit(1)
    lock=QLockFile(str(DATA/'app.lock'))
    if not lock.tryLock(100):
        QMessageBox.information(None,'Central WhatsApp','A central já está aberta. Procure a janela no sistema.');sys.exit(0)
    window=Window();window.show()
    sys.exit(app.exec())
