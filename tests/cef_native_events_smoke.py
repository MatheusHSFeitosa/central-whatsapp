"""Exercise real X11 ConfigureNotify and mouse input in our synthetic CEF page."""
import ctypes
import functools
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from threading import Thread
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
sys.path.insert(0,os.environ.get('CENTRAL_TEST_APP_ROOT',str(Path(__file__).resolve().parents[1])))
from PySide6.QtCore import QTimer,QUrl
from PySide6.QtWidgets import QApplication,QMainWindow
from cef_engine import ServiceView,Profile

class Handler(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass

app=QApplication([])
with tempfile.TemporaryDirectory(prefix='central-native-events-') as directory:
    root=Path(directory)
    (root/'index.html').write_text('''<!doctype html><style>body{margin:0;background:#eef3fa}button{position:absolute;left:20px;top:20px;width:180px;height:80px}</style><button onclick="window.nativeClicks++;document.getElementById('typing').focus()">Teste local de clique</button><input id="typing" style="position:absolute;left:20px;top:130px"><script>window.nativeClicks=0</script>''')
    server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Handler,directory=str(root)))
    Thread(target=server.serve_forever,daemon=True).start()
    local=f'http://127.0.0.1:{server.server_port}/index.html'
    os.environ['CENTRAL_CEF_TEST_URL']=local
    os.environ['CENTRAL_CEF_TEST_MEDIA']='1'
    folder=root/'session';folder.mkdir()
    view=ServiceView(folder,{'service':'custom','custom_url':'https://example.org/'},Profile())
    window=QMainWindow();window.setWindowTitle('Central Chats — teste fictício de cliques e tamanho')
    window.setCentralWidget(view);window.resize(1170,710);window.show();window.raise_();window.activateWindow()
    errors=[];done=[]
    def fail(value):errors.append(str(value));app.quit()
    def measure(callback):view.runJavaScript('({width:innerWidth,height:innerHeight,clicks:window.nativeClicks,text:document.getElementById("typing").value})',callback)
    def verify_size(value,callback):
        if not value or value['width']!=view.width() or value['height']!=view.height():
            fail(f'Viewport {value} does not match native canvas {view.width()}x{view.height()}')
        else:callback()
    def loaded(ok):
        if not ok:return fail('Initial load failed')
        view.loadFinished.disconnect(loaded)
        QTimer.singleShot(400,lambda:measure(lambda value:verify_size(value,resize_again)))
    def resize_again():
        window.resize(835,565)
        QTimer.singleShot(400,lambda:measure(lambda value:verify_size(value,click_real_window)))
    def click_real_window():
        try:
            x11=view.x11
            x11.XTranslateCoordinates.argtypes=[ctypes.c_void_p,ctypes.c_ulong,ctypes.c_ulong,ctypes.c_int,ctypes.c_int,ctypes.POINTER(ctypes.c_int),ctypes.POINTER(ctypes.c_int),ctypes.POINTER(ctypes.c_ulong)]
            x11.XDefaultRootWindow.argtypes=[ctypes.c_void_p];x11.XDefaultRootWindow.restype=ctypes.c_ulong
            x,y,child=ctypes.c_int(),ctypes.c_int(),ctypes.c_ulong()
            x11.XTranslateCoordinates(view.display,view.child,x11.XDefaultRootWindow(view.display),60,50,ctypes.byref(x),ctypes.byref(y),ctypes.byref(child))
            xtest=ctypes.CDLL('libXtst.so.6')
            xtest.XTestFakeMotionEvent.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_ulong]
            xtest.XTestFakeButtonEvent.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.c_int,ctypes.c_ulong]
            xtest.XTestFakeMotionEvent(view.display,-1,x.value,y.value,0)
            x11.XFlush(view.display)
            # XWayland forwards pointer movement/focus through the compositor.
            # Allow that round trip before the button event, as a real gesture does.
            def press():
                xtest.XTestFakeButtonEvent(view.display,1,1,0)
                xtest.XTestFakeButtonEvent(view.display,1,0,0)
                x11.XFlush(view.display)
                QTimer.singleShot(400,lambda:measure(clicked))
            QTimer.singleShot(200,press)
        except Exception as error:fail(error)
    def clicked(value):
        if not value or value['clicks']!=1:return fail(f'Native physical click was not processed: {value}')
        xtest=ctypes.CDLL('libXtst.so.6')
        xtest.XTestFakeKeyEvent.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.c_int,ctypes.c_ulong]
        view.x11.XKeysymToKeycode.argtypes=[ctypes.c_void_p,ctypes.c_ulong];view.x11.XKeysymToKeycode.restype=ctypes.c_uint
        for letter in 'abc':
            key=view.x11.XKeysymToKeycode(view.display,ord(letter))
            xtest.XTestFakeKeyEvent(view.display,key,1,0);xtest.XTestFakeKeyEvent(view.display,key,0,0)
        view.x11.XFlush(view.display)
        QTimer.singleShot(400,lambda:measure(typed))
    def typed(value):
        if not value or value['text']!='abc':return fail(f'Native keyboard input was not processed: {value}')
        done.append(True);app.quit()
    view.engineFailed.connect(fail);view.loadFinished.connect(loaded)
    QTimer.singleShot(20000,lambda:fail('Native event test timed out'))
    view.load(QUrl(local));app.exec();view.shutdown();window.close();server.shutdown()
    assert not errors,errors
    assert done,'Native event test incomplete'
    print('PASS: actual Chromium viewport follows two native window sizes and processes a physical X11 click and keyboard input')
