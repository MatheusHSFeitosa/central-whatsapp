"""Native CEF input remains usable, and Alt+drag can move its Qt ancestor."""
import ctypes,functools,json,os,sys,tempfile,time,uuid
from pathlib import Path
from threading import Thread
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from cef_split_smoke import js,wait
class Handler(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass
with tempfile.TemporaryDirectory(prefix='central-chrome-') as directory:
    root=Path(directory);data=root/'data';data.mkdir();web=root/'web';web.mkdir()
    (web/'index.html').write_text('<!doctype html><body style="margin:0"><button style="position:absolute;left:20px;top:20px;width:180px;height:70px" onclick="window.clicks++">Native fixture</button><script>window.clicks=0</script>')
    record={'id':str(uuid.uuid4()),'name':'Fixture','service':'whatsapp','avatar_mode':'service','icon':'user','archived':False}
    (data/'profiles.json').write_text(json.dumps([record]))
    server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Handler,directory=str(web)));Thread(target=server.serve_forever,daemon=True).start()
    local=f'http://127.0.0.1:{server.server_port}/index.html'
    os.environ['CENTRAL_WHATSAPP_DATA']=str(data);os.environ['CENTRAL_CEF_TEST_URL']=local;os.environ['CENTRAL_CEF_TEST_MEDIA']='1'
    import central
    central.service_url=lambda _:local
    app=QApplication([]);app.setQuitOnLastWindowClosed(False)
    window=central.Window();window.confirm_close=False;window.resize(950,650);window.show_window();window.list.setCurrentRow(0);window.select(0)
    try:
        wait(lambda:window.load_states.get(record['id'])=='ready')
        view=window.views[record['id']][0]
        x=view.x11;display=view.display;t=ctypes.CDLL('libXtst.so.6')
        x.XDefaultRootWindow.argtypes=[ctypes.c_void_p];x.XDefaultRootWindow.restype=ctypes.c_ulong
        x.XTranslateCoordinates.argtypes=[ctypes.c_void_p,ctypes.c_ulong,ctypes.c_ulong,ctypes.c_int,ctypes.c_int,ctypes.POINTER(ctypes.c_int),ctypes.POINTER(ctypes.c_int),ctypes.POINTER(ctypes.c_ulong)]
        x.XKeysymToKeycode.argtypes=[ctypes.c_void_p,ctypes.c_ulong];x.XKeysymToKeycode.restype=ctypes.c_uint
        t.XTestFakeMotionEvent.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_ulong]
        t.XTestFakeButtonEvent.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.c_int,ctypes.c_ulong]
        t.XTestFakeKeyEvent.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.c_int,ctypes.c_ulong]
        xx,yy,ch=ctypes.c_int(),ctypes.c_int(),ctypes.c_ulong()
        x.XTranslateCoordinates(display,view.child,x.XDefaultRootWindow(display),70,45,ctypes.byref(xx),ctypes.byref(yy),ctypes.byref(ch))
        # Focus our own CEF surface first, outside its button. COSMIC may deny
        # focus-stealing activation from a newly opened test window.
        t.XTestFakeMotionEvent(display,-1,xx.value+230,yy.value+100,0);x.XFlush(display);QTest.qWait(250)
        t.XTestFakeButtonEvent(display,1,1,0);t.XTestFakeButtonEvent(display,1,0,0);x.XFlush(display);QTest.qWait(200)
        t.XTestFakeMotionEvent(display,-1,xx.value,yy.value,0);x.XFlush(display);QTest.qWait(250)
        t.XTestFakeButtonEvent(display,1,1,0);t.XTestFakeButtonEvent(display,1,0,0);x.XFlush(display);QTest.qWait(300)
        assert js(view,'window.clicks')==1,'Normal chat click was swallowed'
        requested=[];window.chrome.alt.moveRequested.connect(lambda a,b:requested.append(('start',a,b)))
        before=window.pos();alt=x.XKeysymToKeycode(display,0xffe9)
        t.XTestFakeKeyEvent(display,alt,1,0);x.XFlush(display);QTest.qWait(100)
        t.XTestFakeButtonEvent(display,1,1,0);x.XFlush(display);QTest.qWait(150)
        t.XTestFakeMotionEvent(display,-1,xx.value+15,yy.value+10,0);x.XFlush(display);QTest.qWait(120)
        t.XTestFakeMotionEvent(display,-1,xx.value+55,yy.value+35,0);x.XFlush(display);QTest.qWait(200)
        t.XTestFakeButtonEvent(display,1,0,0);t.XTestFakeKeyEvent(display,alt,0,0);x.XFlush(display);QTest.qWait(250)
        after=window.pos()
        assert abs(after.x()-before.x())>=20 or abs(after.y()-before.y())>=20,(before,after,requested)
        assert js(view,'window.clicks')==1,'Alt-drag clicked web content'
        print('PASS: physical CEF click preserved; Alt+drag moved the single Qt window from native web content without activating its button')
    finally:
        window.cleanup();window.close();server.shutdown()
