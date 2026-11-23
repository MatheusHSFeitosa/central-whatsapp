"""Complete CEF Window with two synthetic profiles and local media only."""
import os,sys,tempfile,json,uuid,functools,traceback,subprocess,re
from unittest.mock import patch
from pathlib import Path
from threading import Thread
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
sys.path.insert(0,os.environ.get('CENTRAL_TEST_APP_ROOT',str(Path(__file__).resolve().parents[1])))
from PySide6.QtCore import QTimer,QUrl,Qt,QPoint
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QDesktopServices

class Handler(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass
    def end_headers(self):
        if self.path.endswith('attachment.bin'):self.send_header('Content-Disposition','attachment; filename="fixture.bin"')
        super().end_headers()

with tempfile.TemporaryDirectory(prefix='central-cef-window-') as directory:
    root=Path(directory);data=root/'data';data.mkdir()
    accounts=[{'id':str(uuid.uuid4()),'name':name,'service':'whatsapp','avatar_mode':'service','icon':'user','archived':False} for name in ('Perfil um','Perfil dois')]
    (data/'profiles.json').write_text(json.dumps(accounts))
    fixture=root/'web';fixture.mkdir();(fixture/'index.html').write_text('<!doctype html><body>Fixture</body>')
    (fixture/'attachment.bin').write_bytes(b'central-download-fixture')
    server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Handler,directory=str(fixture)))
    Thread(target=server.serve_forever,daemon=True).start()
    local='http://127.0.0.1:'+str(server.server_port)+'/index.html'
    os.environ['CENTRAL_WHATSAPP_DATA']=str(data)
    os.environ['CENTRAL_CEF_TEST_URL']=local
    os.environ['CENTRAL_CEF_TEST_MEDIA']='1'
    import central
    central.service_url=lambda _:local
    central.allows_url=lambda service,url,custom='':url.host()=='127.0.0.1' and url.port()==server.server_port
    app=QApplication([])
    central.QMessageBox.question=lambda *a,**kw:central.QMessageBox.StandardButton.Yes
    central.QFileDialog.getSaveFileName=lambda *a,**kw:(str(root/'download.bin'),'')
    errors=[];completed=[];received=[]
    window=central.Window();window.confirm_close=False;window.show()
    with patch.object(central,'CefServiceView',side_effect=OSError('synthetic migration failure')),patch.object(central.QMessageBox,'critical') as message:
        window.select(0)
        assert message.called and accounts[0]['id'] not in window.views
        assert accounts[0]['id'] not in window.profiles
    window.list.setCurrentRow(0);window.select(0)
    window.desktop_notifications.send=lambda token,*args:received.append(token)
    def fail(message):errors.append(str(message)+"\n"+traceback.format_exc());app.quit()
    def wait_for(predicate,callback,attempt=0):
        if predicate():callback()
        elif attempt>100:fail('Wait condition timed out')
        else:QTimer.singleShot(100,lambda:wait_for(predicate,callback,attempt+1))
    def first_ready():
        try:
            key=accounts[0]['id'];view=window.views[key][0]
            view.runJavaScript("document.body.style.background='rgb(230,60,60)';localStorage.setItem('account','one');Notification.requestPermission().then(()=>{window.clicked=0;window.notice=new Notification('fixture',{body:'message'});notice.onclick=()=>window.clicked++});true",lambda _:wait_for(lambda:bool(received),second_profile))
        except Exception as e:fail(e)
    def second_profile():
        window.list.setCurrentRow(1);window.select(1)
        wait_for(lambda:window.load_states.get(accounts[1]['id'])=='ready',check_isolation)
    def assert_visible_profile(index,color):
        view=window.views[accounts[index]['id']][0]
        for i,account in enumerate(accounts):
            other=window.views[account['id']][0]
            info=subprocess.run(['xwininfo','-id',str(other.child),'-stats'],capture_output=True,text=True,check=True).stdout
            assert ('Map State: IsViewable' in info)==(i==index),f'Native visibility mismatch for profile {i}'
        # Read one pixel from our synthetic window through X11. This avoids
        # requiring xwd/ImageMagick on installations upgraded to COSMIC.
        import ctypes
        point=view.mapTo(window,QPoint(view.width()//2,view.height()//2))
        x11=view.x11
        x11.XGetImage.argtypes=[ctypes.c_void_p,ctypes.c_ulong,ctypes.c_int,ctypes.c_int,ctypes.c_uint,ctypes.c_uint,ctypes.c_ulong,ctypes.c_int]
        x11.XGetImage.restype=ctypes.c_void_p
        x11.XGetPixel.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_int];x11.XGetPixel.restype=ctypes.c_ulong
        x11.XDestroyImage.argtypes=[ctypes.c_void_p]
        image=x11.XGetImage(view.display,int(window.winId()),point.x(),point.y(),1,1,ctypes.c_ulong(-1),2)
        assert image,'Could not capture synthetic window pixel'
        pixel=x11.XGetPixel(image,0,0);x11.XDestroyImage(image)
        actual=[(pixel>>16)&255,(pixel>>8)&255,pixel&255]
        expected=[int(value) for value in color.split(',')]
        assert len(actual)==3 and all(abs(a-b)<=2 for a,b in zip(actual,expected)),f'Wrong profile painted: {pixel}; expected {color}'
    def check_isolation():
        view=window.views[accounts[1]['id']][0]
        view.runJavaScript("document.body.style.background='rgb(50,100,220)';true",lambda _:QTimer.singleShot(350,blue_visible))
    def blue_visible():
        try:assert_visible_profile(1,'50,100,220')
        except Exception as e:return fail(e)
        window.views[accounts[1]['id']][0].runJavaScript("localStorage.getItem('account')",isolated)
    def isolated(value):
        try:
            assert value is None,value
            window.hide();window.open_notification(received[0])
            assert window.isVisible()
            assert window.selected_account()['id']==accounts[0]['id']
            window.views[accounts[0]['id']][0].runJavaScript('window.clicked',clicked)
        except Exception as e:fail(e)
    def clicked(value):
        QTimer.singleShot(350,lambda:clicked_visible(value))
    def clicked_visible(value):
        try:
            assert_visible_profile(0,'230,60,60')
            assert value==1,value
            window.apply_preferences({'bar_position':'top'})
            window.apply_preferences({'bar_position':'bottom'})
            window.apply_preferences({'bar_position':'left'})
            window.showMaximized();window.showNormal()
            view=window.views[accounts[0]['id']][0]
            view.runJavaScript("document.body.innerHTML='<a id=download href=attachment.bin download>download</a>';document.getElementById('download').click();true",lambda _:wait_for(lambda:(root/'download.bin').exists() and not view.downloads,downloaded))
        except Exception as e:fail(e)
    def native_eval(view,script,callback):
        view.sequence+=1
        identifier=view.sequence;view.callbacks[identifier]=callback
        view.send(action='eval',id=identifier,script=script,gesture=True)
    def downloaded():
        try:
            assert (root/'download.bin').read_bytes()==b'central-download-fixture'
            view=window.views[accounts[0]['id']][0]
            import cef_engine
            class FixtureFileDialog:
                Option=cef_engine.FileDialog.Option;FileMode=cef_engine.FileDialog.FileMode;AcceptMode=cef_engine.FileDialog.AcceptMode;DialogCode=cef_engine.FileDialog.DialogCode
                def __init__(self,*a):pass
                def setOption(self,*a):pass
                def setAcceptMode(self,*a):pass
                def setFileMode(self,*a):pass
                def exec(self):return self.DialogCode.Accepted
                def selectedFiles(self):return [str(fixture/'attachment.bin')]
                def deleteLater(self):pass
            cef_engine.FileDialog=FixtureFileDialog
            native_eval(view,"document.body.innerHTML='<input id=upload type=file>';upload.showPicker();true",lambda _:wait_for(lambda:not view.downloads,lambda:QTimer.singleShot(300,lambda:view.runJavaScript('upload.files[0]?.text()',uploaded))))
        except Exception as e:fail(e)
    def uploaded(value):
        try:
            assert value=='central-download-fixture',value
            view=window.views[accounts[0]['id']][0]
            native_eval(view,'document.documentElement.requestFullscreen().then(()=>true)',fullscreen_entered)
        except Exception as e:fail(e)
    def fullscreen_entered(value):
        try:
            assert window.isFullScreen(),"Fullscreen enter event not applied"
            view=window.views[accounts[0]['id']][0]
            view.runJavaScript('document.exitFullscreen().then(()=>true)',fullscreen_exited)
        except Exception as e:fail(e)
    def fullscreen_exited(value):
        try:
            assert not window.isFullScreen(),"Fullscreen exit event not applied"
            view=window.views[accounts[0]['id']][0]
            opened=[]
            import cef_engine
            cef_engine.QDesktopServices.openUrl=lambda url:opened.append(url.toString()) or True
            native_eval(view,"window.open('https://example.org/central-fixture','_blank');true",lambda _:QTimer.singleShot(200,lambda:external_opened(opened)))
        except Exception as e:fail(e)
    def external_opened(opened):
        try:
            assert opened==['https://example.org/central-fixture'],opened
            view=window.views[accounts[0]['id']][0]
            view.shutdown();view.reload()
            wait_for(lambda:view.ready,after_restart)
        except Exception as e:fail(e)
    def after_restart():
        # restart loads asynchronously; don't inspect an about:blank context.
        QTimer.singleShot(600,lambda:window.views[accounts[0]['id']][0].runJavaScript("localStorage.getItem('account')",persisted))
    def persisted(value):
        try:assert value=='one',value;completed.append(True)
        except Exception as e:errors.append(str(e))
        app.quit()
    QTimer.singleShot(100,lambda:wait_for(lambda:window.load_states.get(accounts[0]['id'])=='ready',first_ready))
    QTimer.singleShot(40000,lambda:fail('Window test timed out'))
    app.exec()
    window.cleanup();window.close();server.shutdown()
    assert not errors,errors
    assert completed,'Window test incomplete'
    assert json.loads((data/'profiles.json').read_text())==accounts
    print('CEF full window: two isolated profiles, notification activation and exact JS click, three bar positions, window state, download, file upload, fullscreen, external link, engine restart, persistent session, configuration preservation and shutdown passed')
