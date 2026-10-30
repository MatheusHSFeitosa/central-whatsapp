#!/usr/bin/env python3
import json
import re
import shutil
import subprocess
import os
import sys
import uuid
from pathlib import Path
from PySide6.QtCore import QUrl, QLockFile, QTimer
from PySide6.QtGui import QDesktopServices, QIcon
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
 QListWidget, QPushButton, QLabel, QStackedWidget, QInputDialog, QMessageBox, QFileDialog, QSystemTrayIcon)
from PySide6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage, QWebEnginePermission
from PySide6.QtWebEngineWidgets import QWebEngineView

DATA = Path(os.environ.get('CENTRAL_WHATSAPP_DATA', str(Path(os.environ.get('XDG_DATA_HOME',str(Path.home()/'.local/share')))/'central-whatsapp-data')))
DATA.mkdir(parents=True, exist_ok=True, mode=0o700)
os.chmod(DATA, 0o700)
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
        self.setStyleSheet("QMainWindow { background: #172126; color: #e9efed; } QWidget { font-size: 14px; } QListWidget { background: #202e34; color: #e9efed; border: none; border-radius: 8px; padding: 6px; } QListWidget::item { padding: 13px 10px; } QListWidget::item:selected { background: #145c47; color: #ffffff; border-radius: 6px; } QPushButton { background: #263a40; color: #e9efed; border: 1px solid #43545a; border-radius: 7px; padding: 8px; } QPushButton:hover { background: #345149; } QLabel { color: #e9efed; }")
        self.notifications = []
        self.confirm_close = True
        try:
            self.accounts = json.loads(CONFIG.read_text()) if CONFIG.exists() else []
            if not isinstance(self.accounts, list): raise ValueError('Lista inválida')
            if any(not isinstance(a, dict) or not isinstance(a.get('name'), str) or str(uuid.UUID(a['id'])) != a['id'] for a in self.accounts):
                raise ValueError('Perfil inválido')
            if len({a['id'] for a in self.accounts}) != len(self.accounts): raise ValueError('IDs duplicados')
        except Exception as e:
            QMessageBox.critical(self, 'Configuração inválida', f'Os perfis foram preservados. Não foi possível ler a configuração: {e}')
            raise SystemExit(1)
        root = QWidget(); self.setCentralWidget(root)
        layout = QHBoxLayout(root)
        side = QVBoxLayout(); layout.addLayout(side)
        title = QLabel('Central WhatsApp'); title.setStyleSheet('font-size:20px;font-weight:600;padding:12px 0')
        side.addWidget(title)
        self.list = QListWidget(); self.list.setFixedWidth(205); side.addWidget(self.list)
        for text, fn in [('+ Adicionar perfil',self.add),('Renomear',self.rename),('Remover da lista',self.remove)]:
            b=QPushButton(text); b.setMinimumHeight(36); b.clicked.connect(fn); side.addWidget(b)
        side.addWidget(QLabel('Contas carregadas permanecem\nativas enquanto a central estiver aberta.'))
        right=QVBoxLayout(); layout.addLayout(right,1)
        bar=QHBoxLayout(); right.addLayout(bar)
        self.status=QLabel('Selecione ou adicione um perfil'); bar.addWidget(self.status,1)
        reload_button=QPushButton('Recarregar'); reload_button.clicked.connect(self.reload); bar.addWidget(reload_button)
        self.stack=QStackedWidget(); right.addWidget(self.stack,1)
        welcome=QLabel('Seus WhatsApps, em um só lugar.\n\nAdicione um perfil e conecte pelo QR Code.'); welcome.setStyleSheet('padding:40px;font-size:18px')
        self.stack.addWidget(welcome)
        self.tray=QSystemTrayIcon(self.windowIcon(),self)
        self.tray.setToolTip('Central WhatsApp')
        self.tray.activated.connect(lambda reason: (self.showNormal(), self.raise_(), self.activateWindow()))
        if QSystemTrayIcon.isSystemTrayAvailable(): self.tray.show()
        self.list.currentRowChanged.connect(self.select)
        self.refresh()

    def save(self):
        temp=CONFIG.with_suffix('.tmp'); temp.write_text(json.dumps(self.accounts,ensure_ascii=False,indent=2)); os.chmod(temp,0o600); temp.replace(CONFIG)

    def refresh(self, row=-1):
        self.list.blockSignals(True); self.list.clear()
        self.list.addItems([a['name'] for a in self.accounts]); self.list.blockSignals(False)
        self.list.setCurrentRow(row)

    def add(self):
        name,ok=QInputDialog.getText(self,'Adicionar perfil','Nome do perfil:')
        if not ok or not name.strip(): return
        name=name.strip()[:60]
        if any(a['name'].casefold()==name.casefold() for a in self.accounts):
            QMessageBox.information(self,'Nome já usado','Escolha outro nome.'); return
        self.accounts.append({'id':str(uuid.uuid4()),'name':name}); self.save(); self.refresh(len(self.accounts)-1)

    def rename(self):
        row=self.list.currentRow()
        if row<0:return
        name,ok=QInputDialog.getText(self,'Renomear perfil','Nome:',text=self.accounts[row]['name'])
        if not ok or not name.strip():return
        name=name.strip()[:60]
        if any(i!=row and a['name'].casefold()==name.casefold() for i,a in enumerate(self.accounts)):
            QMessageBox.information(self,'Nome já usado','Escolha outro nome.');return
        self.accounts[row]['name']=name; self.save(); self.refresh(row)

    def remove(self):
        row=self.list.currentRow()
        if row<0:return
        account=self.accounts[row]
        answer=QMessageBox.question(self,'Remover da lista',f'Remover {account["name"]} da central?\nA sessão local será preservada. Para desvincular, use Aparelhos conectados no celular.')
        if answer!=QMessageBox.StandardButton.Yes:return
        item=self.views.pop(account['id'],None)
        if item:
            view,profile=item
            self.stack.removeWidget(view); view.page().deleteLater(); view.deleteLater()
            # Perfil permanece vivo até a saída para garantir gravação e destruição após a página.
        del self.accounts[row]; self.save(); self.refresh(); self.stack.setCurrentIndex(0); self.status.setText('Selecione ou adicione um perfil')

    def select(self,row):
        if row<0:return
        account=self.accounts[row]; key=account['id']; self.status.setText(account['name'])
        if key not in self.views:
            folder=DATA/'sessions'/key; folder.mkdir(parents=True,exist_ok=True,mode=0o700)
            profile=QWebEngineProfile(key,self)
            # O WhatsApp rejeita o identificador QtWebEngine; mantém a versão real do Chromium.
            ua = re.sub(r'\sQtWebEngine/[^ ]+', '', profile.httpUserAgent())
            ua = re.sub(r'\scentral-whatsapp/[^ ]+', '', ua)
            profile.setHttpUserAgent(ua)
            profile.setPersistentStoragePath(str(folder/'storage')); profile.setCachePath(str(folder/'cache'))
            profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies)
            profile.setHttpCacheMaximumSize(100*1024*1024)
            profile.setHttpAcceptLanguage('pt-BR,pt;q=0.9,en;q=0.7')
            profile.setNotificationPresenter(lambda n,k=key:self.notify(k,n))
            profile.downloadRequested.connect(self.download)
            view=QWebEngineView(); page=Page(profile,view);view.setPage(page)
            page.permissionRequested.connect(lambda permission,k=key:self.permission(k,permission))
            view.loadFinished.connect(lambda ok,k=key:self.loaded(k,ok))
            self.views[key]=(view,profile);self.stack.addWidget(view)
            view.load(QUrl('https://web.whatsapp.com/'))
        self.stack.setCurrentWidget(self.views[key][0])

    def loaded(self,key,ok):
        if key in self.views and self.stack.currentWidget() is self.views[key][0]:
            self.status.setText(next((a['name'] for a in self.accounts if a['id']==key),'Perfil')+('' if ok else ' — Falha ao carregar. Verifique a conexão e recarregue.'))

    def permission(self,key,permission):
        if permission.origin().host()!='web.whatsapp.com':permission.deny();return
        kind=permission.permissionType()
        allowed={QWebEnginePermission.PermissionType.Notifications:'mostrar notificações',QWebEnginePermission.PermissionType.MediaAudioCapture:'usar o microfone',QWebEnginePermission.PermissionType.MediaVideoCapture:'usar a câmera',QWebEnginePermission.PermissionType.MediaAudioVideoCapture:'usar câmera e microfone'}
        if kind not in allowed:permission.deny();return
        name=next((a['name'] for a in self.accounts if a['id']==key),'Perfil')
        if QMessageBox.question(self,'Permissão do WhatsApp',f'{name}: permitir {allowed[kind]}?')==QMessageBox.StandardButton.Yes:permission.grant()
        else:permission.deny()

    def notify(self,key,notification):
        name=next((a['name'] for a in self.accounts if a['id']==key),'WhatsApp')
        self.notifications.append(notification); notification.show()
        if shutil.which('notify-send'):
            subprocess.Popen(['notify-send','--app-name=Central WhatsApp','--icon=central-whatsapp',name+' · '+notification.title(),notification.message()],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        elif shutil.which('gdbus'):
            subprocess.Popen(['gdbus','call','--session','--dest','org.freedesktop.Notifications','--object-path','/org/freedesktop/Notifications','--method','org.freedesktop.Notifications.Notify',json.dumps('Central WhatsApp'),'0',json.dumps('central-whatsapp'),json.dumps(name+' · '+notification.title(),ensure_ascii=False),json.dumps(notification.message(),ensure_ascii=False),'[]','{}','-1'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        else:
            self.tray.showMessage(name+' · '+notification.title(),notification.message())
        QTimer.singleShot(15000,lambda:self.finish_notification(notification))

    def finish_notification(self,n):
        n.close()
        if n in self.notifications:self.notifications.remove(n)

    def download(self,item):
        path,_=QFileDialog.getSaveFileName(self,'Salvar arquivo',str(Path.home()/'Downloads'/Path(item.downloadFileName()).name))
        if not path:item.cancel();return
        target=Path(path);item.setDownloadDirectory(str(target.parent));item.setDownloadFileName(target.name);item.accept()

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
    lock=QLockFile(str(DATA/'app.lock'))
    if not lock.tryLock(100):
        QMessageBox.information(None,'Central WhatsApp','A central já está aberta. Procure a janela no sistema.');sys.exit(0)
    window=Window();window.show()
    sys.exit(app.exec())
