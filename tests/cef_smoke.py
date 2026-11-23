"""Real CEF process integration with synthetic loopback content; no accounts."""
import os
import sys
import tempfile
import json
import functools
import shutil
from pathlib import Path
from threading import Thread
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
sys.path.insert(0,os.environ.get('CENTRAL_TEST_APP_ROOT',str(Path(__file__).resolve().parents[1])))
from PySide6.QtCore import QTimer,QUrl
from PySide6.QtWidgets import QApplication,QMainWindow
from cef_engine import ServiceView,Profile

class Handler(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass
    def end_headers(self):
        self.send_header('Permissions-Policy','camera=(self), microphone=(self)')
        super().end_headers()

app=QApplication([])
with tempfile.TemporaryDirectory(prefix='central-cef-smoke-') as temporary:
    root=Path(temporary)
    page='''<!doctype html><title>CEF fixture</title><body>Local test</body><script>
    localStorage.setItem('isolated','first');
    window.called=0;window.notice=null;
    </script>'''
    (root/'index.html').write_text(page)
    shutil.copy2(Path(__file__).parent/'fixtures/sample.mp4',root/'sample.mp4')
    (root/'attachment.bin').write_bytes(b'central-download-fixture')
    server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Handler,directory=str(root)))
    Thread(target=server.serve_forever,daemon=True).start()
    url='http://127.0.0.1:'+str(server.server_port)+'/index.html'
    os.environ['CENTRAL_CEF_TEST_URL']=url
    os.environ['CENTRAL_CEF_TEST_MEDIA']='1'
    folder=root/'session';folder.mkdir()
    profile=Profile();view=ServiceView(folder,{'service':'custom','custom_url':'https://example.org/'},profile)
    window=QMainWindow();window.setCentralWidget(view);window.resize(950,650);window.show()
    completed=[];errors=[];notices=[];permissions=[]
    profile.setNotificationPresenter(lambda n:notices.append(n))
    def permitted(permission):
        permissions.append(permission.permissionType());permission.grant()
    view.permissionRequested.connect(permitted)
    def fail(message):errors.append(str(message));app.quit()
    view.engineFailed.connect(fail)
    def evaluate(script,callback):view.runJavaScript(script,callback)
    def verify_result(value):
        try:
            assert value and value['media']==['audio','video'],value
            assert value['ua'].find('Chrome/152.')>=0,value
            assert value['notification']=='granted',value
            assert value['isolated']=='first',value
            evaluate((Path(__file__).parent/'fixtures/cef-call.js').read_text(),media_verified)
        except Exception as error:fail(error)
    def media_verified(value):
        try:
            assert 'failure' not in value,value
            assert value['mp4']['time']>0 and value['mp4']['width']>0,value
            assert value['connections']==['connected','connected'],value
            for direction in value['inbound']:
                assert any(item['kind']=='audio' and item['packets']>0 and item['codec']=='audio/opus' for item in direction),direction
                assert any(item['kind']=='video' and item['packets']>0 and item.get('frames',0)>0 and item['codec']=='video/H264' for item in direction),direction
            evaluate("window.notice=new Notification('Synthetic title',{body:'Synthetic body'});notice.onclick=()=>{window.called++};true",notification_created)
        except Exception as error:fail(error)
    def notification_created(value):QTimer.singleShot(300,check_notification)
    def check_notification():
        try:
            assert len(notices)==1,notices
            assert notices[0].title()=='Synthetic title'
            notices[0].click()
            QTimer.singleShot(200,lambda:evaluate('window.called',check_click))
        except Exception as error:fail(error)
    def check_click(value):
        try:
            assert value==1,value
            notices[0].close()
            # The helper reports external links only for a user gesture; direct
            # hostile cross-origin navigation must be blocked without opening it.
            evaluate("location.href='http://localhost:1/blocked';true",lambda _:None)
            QTimer.singleShot(400,lambda:evaluate('location.origin',finish))
        except Exception as error:fail(error)
    def finish(value):
        try:
            assert value=='http://127.0.0.1:'+str(server.server_port),value
            assert 3 in permissions and 0 in permissions,permissions
            renderers=[]
            for item in Path('/proc').iterdir():
                if not item.name.isdecimal():continue
                try:
                    command=(item/'cmdline').read_bytes()
                    if str(folder/'cef').encode() in command and b'--type=renderer' in command:
                        status=(item/'status').read_text()
                        assert 'NoNewPrivs:\t1' in status and 'Seccomp:\t2' in status,status
                        assert b'--no-sandbox' not in command
                        renderers.append(item.name)
                except (FileNotFoundError,PermissionError):pass
            assert renderers,'No isolated renderer found'
            completed.append(True)
        except Exception as error:errors.append(str(error))
        app.quit()
    def loaded(ok):
        if not ok:return fail('Load failed')
        if view.url().toString()!=url:return
        view.loadFinished.disconnect(loaded)
        QTimer.singleShot(500,lambda:evaluate('''(async()=>{const stream=await navigator.mediaDevices.getUserMedia({audio:true,video:true});const media=stream.getTracks().map(t=>t.kind).sort();stream.getTracks().forEach(t=>t.stop());const notification=await Notification.requestPermission();return {media,notification,ua:navigator.userAgent,isolated:localStorage.getItem('isolated')}})()''',verify_result))
    view.loadFinished.connect(loaded)
    QTimer.singleShot(35000,lambda:fail('CEF test timed out'))
    view.load(QUrl(url));app.exec()
    view.shutdown();window.close();server.shutdown()
    assert not errors,errors
    assert completed,'Test did not complete'
    assert view.process.state()==view.process.ProcessState.NotRunning
    print('CEF: native embedding, evaluation, media permission, H264/AAC playback, bidirectional H264/Opus calls, notification permission, routed click, origin blocking, private storage and clean shutdown passed')
