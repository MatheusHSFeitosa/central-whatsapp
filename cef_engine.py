"""CEF native X11 views with isolated host processes and private line-based IPC."""
import ctypes
import json
import os
from pathlib import Path
from PySide6.QtCore import QObject, QProcess, QTimer, QUrl, Signal, Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
from PySide6.QtGui import QDesktopServices
from cef_storage import prepare_cef_storage
from ui_widgets import FileDialog
from services import allows_url


class Permission(QObject):
    class PermissionType:
        Notifications = 0
        MediaAudioCapture = 1
        MediaVideoCapture = 2
        MediaAudioVideoCapture = 3
    def __init__(self, view, request):
        super().__init__(view)
        self.view, self.request = view, request
        self.valid = True
    def origin(self):return QUrl(self.request['origin'])
    def permissionType(self):return self.request['flags']
    def isValid(self):return self.valid
    def answer(self, allow):
        if self.valid:
            self.valid=False
            self.view.send(action='permission',id=self.request['id'],allow=allow)
    def grant(self):self.answer(True)
    def deny(self):self.answer(False)
    def reset(self):pass  # Media grants are deliberately requested on each call.


class FullscreenRequest:
    def __init__(self, view, on):self.view,self.on=view,on
    def toggleOn(self):return self.on
    def accept(self):pass
    def reject(self):self.view.runJavaScript('document.exitFullscreen?.()')


class Notification(QObject):
    closed=Signal()
    def __init__(self,view,data):
        super().__init__(view)
        self.view,self.data=view,data
        self.done=False
    def title(self):return self.data.get('title','')
    def message(self):return self.data.get('body','')
    def show(self):pass
    def click(self):
        if not self.done:self.view.send(action='click',token=self.data['token'])
    def close(self):
        if not self.done:
            self.done=True
            self.view.send(action='close-notification',token=self.data['token'])
            self.closed.emit()


class Download(QObject):
    stateChanged=Signal(int)
    class DownloadState:
        DownloadInterrupted=1
        DownloadCompleted=2
    def __init__(self,view,data):
        super().__init__(view)
        self.view,self.identifier=view,data['id']
        self.filename=Path(data['name']).name or 'arquivo'
        self.directory=''
    def downloadFileName(self):return self.filename
    def downloadDirectory(self):return self.directory
    def setDownloadFileName(self,name):self.filename=Path(name).name
    def setDownloadDirectory(self,directory):self.directory=directory
    def accept(self):self.view.send(action='download',id=self.identifier,path=str(Path(self.directory)/self.filename))
    def cancel(self):self.view.send(action='download',id=self.identifier,path='')


class Profile(QObject):
    downloadRequested=Signal(object)
    def __init__(self,parent=None):
        super().__init__(parent)
        self.presenter=None
    def setNotificationPresenter(self,presenter):self.presenter=presenter


class ServiceView(QWidget):
    loadStarted=Signal()
    loadFinished=Signal(bool)
    permissionRequested=Signal(object)
    fullScreenRequested=Signal(object)
    initialResourceFailed=Signal()
    engineFailed=Signal(str)
    def __init__(self,folder,account,profile,parent=None):
        super().__init__(parent)
        self.account,self.profile=account,profile
        self.folder=prepare_cef_storage(folder)
        self.current_url=QUrl()
        self.child=0;self.buffer=b'';self.callbacks={};self.sequence=0
        self.web_notifications={};self.downloads={};self.closing=False
        self.pending=[];self.ready=False;self.runtime=None
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_NativeWindow)
        self.loading_panel=QWidget(self)
        self.loading_panel.setAttribute(Qt.WidgetAttribute.WA_NativeWindow)
        self.loading_panel.setObjectName('serviceLoadingPanel')
        layout=QVBoxLayout(self.loading_panel);layout.addStretch()
        self.loading_title=QLabel();self.loading_title.setWordWrap(True);self.loading_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.loading_title)
        self.retry_button=QPushButton('Tentar novamente');self.alternative_button=QPushButton('Usar outro cliente do Telegram')
        self.alternative_button.setVisible(account.get('service')=='telegram')
        for button in (self.retry_button,self.alternative_button):layout.addWidget(button,0,Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch();self.loading_panel.hide()
        self.x11=ctypes.CDLL('libX11.so.6')
        self.x11.XOpenDisplay.restype=ctypes.c_void_p;self.x11.XOpenDisplay.argtypes=[ctypes.c_char_p]
        self.x11.XResizeWindow.argtypes=[ctypes.c_void_p,ctypes.c_ulong,ctypes.c_uint,ctypes.c_uint]
        self.x11.XFlush.argtypes=[ctypes.c_void_p];self.x11.XCloseDisplay.argtypes=[ctypes.c_void_p]
        self.display=self.x11.XOpenDisplay(None)
        self.process=QProcess(self)
        self.process.readyReadStandardOutput.connect(self.output)
        self.process.readyReadStandardError.connect(self.stderr)
        self.process.finished.connect(self.finished)
        self.process.errorOccurred.connect(lambda _:self.fail('Não foi possível iniciar o motor CEF.') if not self.closing else None)
        self.resize_timer=QTimer(self);self.resize_timer.timeout.connect(self.resize_child);self.resize_timer.start(150)
    def stderr(self):
        data=bytes(self.process.readAllStandardError())
        if os.environ.get("CENTRAL_CEF_TEST_TRACE")=="1":print(data.decode(errors="replace"),flush=True)
    def page(self):return self
    def url(self):return self.current_url
    def zoomFactor(self):return 1.0
    def runJavaScript(self,script,callback=None):
        self.sequence+=1
        identifier=self.sequence
        if callback:
            self.callbacks[identifier]=callback
            QTimer.singleShot(15000,lambda:self.resolve(identifier,None))
        self.send(action='eval',id=identifier,script=script)
    def resolve(self,identifier,value):
        callback=self.callbacks.pop(identifier,None)
        if callback:callback(value)
    def send(self,**message):
        if self.closing:return
        if not self.ready and message['action'] not in ('quit',):self.pending.append(message);return
        if self.process.state()!=QProcess.ProcessState.NotRunning:
            self.process.write((json.dumps(message,ensure_ascii=True)+'\n').encode())
    def load(self,url):
        if not allows_url(self.account.get('service','whatsapp'),url,self.account.get('custom_url','')) and not os.environ.get('CENTRAL_CEF_TEST_URL')==url.toString():return
        self.current_url=url
        if self.process.state()!=QProcess.ProcessState.NotRunning:
            self.send(action='load',url=url.toString());return
        self.closing=False;self.ready=False;self.buffer=b""
        if not self.display:self.display=self.x11.XOpenDisplay(None)
        self.resize_timer.start(150)
        self.runtime=Path(os.environ.get('CENTRAL_CEF_RUNTIME',str(Path(__file__).with_name('cef-runtime')))).resolve()
        executable=self.runtime/'central-cef-host'
        if not executable.is_file():self.fail('Motor CEF indisponível. Reinstale a Central Chats.');return
        arguments=['--runtime='+str(self.runtime),'--profile='+str(self.folder),'--parent='+str(int(self.winId())),
                   '--url='+url.toString(),'--ozone-platform=x11','--disable-setuid-sandbox','--no-first-run','--no-default-browser-check','--autoplay-policy=no-user-gesture-required','--lang=pt-BR']
        if os.environ.get('CENTRAL_CEF_TEST_MEDIA')=='1':arguments+=['--use-fake-device-for-media-stream','--disable-gpu']
        self.process.start(str(executable),arguments)
    def reload(self):
        if self.process.state()==QProcess.ProcessState.NotRunning:self.load(self.current_url)
        else:self.send(action='reload')
    def stop(self):self.send(action='stop')
    def triggerAction(self,action):self.runJavaScript('document.exitFullscreen?.()')
    def output(self):
        self.buffer+=bytes(self.process.readAllStandardOutput())
        if len(self.buffer)>8*1024*1024:self.buffer=b'';self.fail('Resposta inválida do motor.');return
        while b'\n' in self.buffer:
            line,self.buffer=self.buffer.split(b'\n',1)
            try:data=json.loads(line)
            except (ValueError,UnicodeError):continue
            self.event_received(data)
    def event_received(self,data):
        if os.environ.get('CENTRAL_CEF_TEST_TRACE')=='1':print(data,flush=True)
        kind=data.get('event')
        if kind=='window':
            self.child=int(data['id']);self.ready=True;self.resize_child()
            pending,self.pending=self.pending,[]
            for message in pending:self.send(**message)
        elif kind=='loading':
            for notification in list(self.web_notifications.values()):
                if not notification.done:notification.done=True;notification.closed.emit()
            self.web_notifications.clear()
            self.loadStarted.emit()
        elif kind=='loaded':
            if data.get('ok'):self.loading_panel.hide()
            self.loadFinished.emit(bool(data.get('ok')))
        elif kind=='url':self.current_url=QUrl(data['url'])
        elif kind=='result':
            result=data.get('data') or {}
            value=result.get('result',{}).get('value') if data.get('success') else None
            self.resolve(data['id'],value)
        elif kind=='external':
            url=QUrl(data.get('url',''))
            if url.isValid() and not url.userInfo() and ((url.scheme() in ('http','https') and url.host()) or url.scheme()=='mailto'):
                QDesktopServices.openUrl(url)
        elif kind=='permission':
            permission=Permission(self,data)
            QTimer.singleShot(0,lambda:self.permissionRequested.emit(permission) if not self.closing else permission.deny())
        elif kind=='fullscreen':self.fullScreenRequested.emit(FullscreenRequest(self,bool(data.get('on'))))
        elif kind=='bridge':
            value=data.get('data',{});token=value.get('token','')
            if value.get('kind')=='notification' and isinstance(token,str) and len(token)<80:
                value['title']=str(value.get('title',''))[:512];value['body']=str(value.get('body',''))[:4096]
                if len(self.web_notifications)>=256:
                    oldest=next(iter(self.web_notifications));self.web_notifications.pop(oldest).close()
                notification=Notification(self,value);self.web_notifications[token]=notification
                if self.profile.presenter:self.profile.presenter(notification)
            elif value.get('kind')=='notification-close':
                notification=self.web_notifications.pop(token,None)
                if notification and not notification.done:notification.done=True;notification.closed.emit()
        elif kind=='file-dialog':
            QTimer.singleShot(0,lambda:self.file_dialog(data))
        elif kind=='download':
            item=Download(self,data);self.downloads[item.identifier]=item
            QTimer.singleShot(0,lambda:self.profile.downloadRequested.emit(item))
        elif kind=='download-state':
            item=self.downloads.pop(data['id'],None)
            if item:item.stateChanged.emit(item.DownloadState.DownloadCompleted if data.get('complete') else item.DownloadState.DownloadInterrupted)
    def file_dialog(self,data):
        if self.closing:return
        dialog=FileDialog(self.window(),'Selecionar arquivo')
        dialog.setOption(FileDialog.Option.DontUseNativeDialog,True)
        mode=data.get('mode',0)
        if mode==3:dialog.setAcceptMode(FileDialog.AcceptMode.AcceptSave)
        dialog.setFileMode(FileDialog.FileMode.ExistingFiles if mode==1 else FileDialog.FileMode.Directory if mode==2 else FileDialog.FileMode.AnyFile if mode==3 else FileDialog.FileMode.ExistingFile)
        paths=dialog.selectedFiles() if dialog.exec()==dialog.DialogCode.Accepted else []
        self.send(action='files',id=data['id'],paths=paths)
        dialog.deleteLater()
    def fail(self,message):
        if not self.closing:
            self.show_loading(message);self.loadFinished.emit(False);self.engineFailed.emit(message)
    def finished(self,code,status):
        if os.environ.get("CENTRAL_CEF_TEST_TRACE")=="1":print("HOST EXIT",code,status,flush=True)
        self.ready=False;self.child=0
        for identifier in list(self.callbacks):self.resolve(identifier,None)
        if not self.closing:self.fail('O motor do perfil foi encerrado. Clique em Tentar novamente.')
    def show_loading(self,message):
        self.loading_title.setText(message);self.loading_panel.setGeometry(self.rect());self.loading_panel.show();self.loading_panel.raise_()
    def resize_child(self):
        if self.child and self.display:
            factor=self.devicePixelRatioF()
            self.x11.XResizeWindow(self.display,self.child,max(1,round(self.width()*factor)),max(1,round(self.height()*factor)))
            self.x11.XFlush(self.display)
    def resizeEvent(self,event):
        super().resizeEvent(event);self.loading_panel.setGeometry(self.rect());self.resize_child()
    def focusInEvent(self,event):super().focusInEvent(event);self.send(action='focus')
    def shutdown(self):
        if self.closing:return
        self.send(action='quit');self.closing=True;self.pending.clear();self.resize_timer.stop()
        for notification in list(self.web_notifications.values()):
            if not notification.done:notification.done=True;notification.closed.emit()
        self.web_notifications.clear()
        if self.process.state()!=QProcess.ProcessState.NotRunning:
            self.process.waitForBytesWritten(500)
            if not self.process.waitForFinished(6000):
                self.process.terminate()
                if not self.process.waitForFinished(2000):self.process.kill();self.process.waitForFinished(1000)
        if self.display:self.x11.XCloseDisplay(self.display);self.display=None
    def deleteLater(self):self.shutdown();super().deleteLater()
