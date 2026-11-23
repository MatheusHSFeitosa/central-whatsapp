"""Real CEF split panes and optional public mockups; synthetic profiles only."""
import ctypes,functools,json,os,sys,tempfile,time,uuid
from pathlib import Path
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from threading import Thread
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import QUrl,Qt
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest

class Handler(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass

def wait(predicate,seconds=15):
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        if predicate():return
        QTest.qWait(30)
    raise AssertionError('Timed out waiting for CEF')

def js(view,script):
    result=[];view.runJavaScript(script,lambda value:result.append(value))
    wait(lambda:bool(result));return result[0]


def capture(window,path):
    class ImageData(ctypes.Structure):
        _fields_=[('width',ctypes.c_int),('height',ctypes.c_int),('xoffset',ctypes.c_int),('format',ctypes.c_int),('data',ctypes.c_void_p),('byte_order',ctypes.c_int),('bitmap_unit',ctypes.c_int),('bitmap_bit_order',ctypes.c_int),('bitmap_pad',ctypes.c_int),('depth',ctypes.c_int),('bytes_per_line',ctypes.c_int),('bits_per_pixel',ctypes.c_int),('red_mask',ctypes.c_ulong),('green_mask',ctypes.c_ulong),('blue_mask',ctypes.c_ulong)]
    x=ctypes.CDLL('libX11.so.6');x.XOpenDisplay.restype=ctypes.c_void_p;display=x.XOpenDisplay(None)
    x.XGetImage.argtypes=[ctypes.c_void_p,ctypes.c_ulong,ctypes.c_int,ctypes.c_int,ctypes.c_uint,ctypes.c_uint,ctypes.c_ulong,ctypes.c_int];x.XGetImage.restype=ctypes.POINTER(ImageData)
    x.XDestroyImage.argtypes=[ctypes.c_void_p];x.XCloseDisplay.argtypes=[ctypes.c_void_p]
    image=x.XGetImage(display,int(window.winId()),0,0,window.width(),window.height(),ctypes.c_ulong(-1),2)
    assert image and image.contents.bits_per_pixel==32
    info=image.contents;raw=ctypes.string_at(info.data,info.bytes_per_line*info.height)
    result=QImage(raw,info.width,info.height,info.bytes_per_line,QImage.Format.Format_RGB32).copy()
    x.XDestroyImage(image);x.XCloseDisplay(display)
    path.parent.mkdir(parents=True,exist_ok=True);assert result.save(str(path))


def demo_html(account,light=False):
    colors={'whatsapp':'#168c62','telegram':'#2388be','chatwoot':'#2873d2','custom':'#7554af'}
    service=account['service'];accent=colors[service]
    bg,side,text,muted,border,bubble=('#f4f6f8','#ffffff','#172638','#647287','#dce2e9','#e0edf9') if light else ('#111c26','#1b2936','#e8edf3','#94a6b8','#2b3c4b','#213d55')
    label={'whatsapp':'WhatsApp','telegram':'Telegram','chatwoot':'Chatwoot','custom':'Chat personalizado'}[service]
    return f'''<!doctype html><meta charset="utf-8"><style>*{{box-sizing:border-box}}body{{margin:0;font:14px system-ui;background:{bg};color:{text};height:100vh;display:flex;flex-direction:column}}header{{padding:18px;display:flex;align-items:center;gap:12px;background:{side};border-bottom:1px solid {border}}}.avatar{{background:{accent};width:38px;height:38px;border-radius:50%;display:grid;place-items:center;color:white;font-weight:600}}small{{display:block;color:{muted};margin-top:3px;font-size:12px}}main{{padding:22px;flex:1;overflow:hidden;display:flex;flex-direction:column;gap:16px}}.date{{text-align:center;font-size:11px;color:{muted}}}.msg{{max-width:88%;padding:12px 14px;border-radius:12px;background:{side};line-height:1.5;border:1px solid {border}}}.out{{align-self:flex-end;background:{bubble}}}time{{display:block;text-align:right;font-size:10px;color:{muted};margin-top:6px}}footer{{padding:16px;background:{side};border-top:1px solid {border}}}.input{{padding:12px 15px;border:1px solid {border};border-radius:9px;color:{muted}}}.mock{{padding:7px;text-align:center;font-size:10px;letter-spacing:.08em;color:{muted};background:{side}}}</style><header><div class=avatar>{label[0]}</div><div><b>{account['name']}</b><small>{label} · conversa de demonstração</small></div></header><main><div class=date>HOJE · DADOS FICTÍCIOS</div><div class=msg>Podemos revisar os próximos passos por aqui?<time>10:24</time></div><div class="msg out">Sim! Já deixei tudo organizado neste perfil.<time>10:25 ✓✓</time></div><div class=msg>Ótimo. A divisão de tela ajuda a acompanhar as equipes ao mesmo tempo.<time>10:26</time></div></main><footer><div class=input>Escreva uma mensagem…</div></footer><div class=mock>MOCKUP · CONTEÚDO FICTÍCIO · NENHUMA CONTA CONECTADA</div>'''


def main():
    output=os.environ.get('CENTRAL_DEMO_OUTPUT')
    with tempfile.TemporaryDirectory(prefix='central-split-') as folder:
        root=Path(folder);data=root/'data';data.mkdir();web=root/'web';web.mkdir()
        (web/'index.html').write_text('<!doctype html><body>Split fixture</body>')
        services=['whatsapp','telegram','chatwoot','custom'];names=['Pessoal','Equipe de produto','Atendimento','Projeto']
        accounts=[dict(id=str(uuid.uuid4()),name=name,service=service,avatar_mode='service',icon='user',archived=False,**({'custom_url':'https://chat.example.test/'} if service in ('chatwoot','custom') else {})) for name,service in zip(names,services)]
        (data/'profiles.json').write_text(json.dumps(accounts))
        server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Handler,directory=str(web)))
        Thread(target=server.serve_forever,daemon=True).start()
        local=f'http://127.0.0.1:{server.server_port}/index.html'
        os.environ['CENTRAL_WHATSAPP_DATA']=str(data);os.environ['CENTRAL_CEF_TEST_URL']=local;os.environ['CENTRAL_CEF_TEST_MEDIA']='1'
        import central
        central.service_url=lambda _:local
        central.allows_url=lambda service,url,custom='':url.host()=='127.0.0.1' and url.port()==server.server_port
        app=QApplication([]);app.setStyle('Fusion');app.setQuitOnLastWindowClosed(False)
        window=central.Window();window.confirm_close=False;window._startup_ready.update(a['id'] for a in accounts)
        screen=app.primaryScreen().availableGeometry()
        window.resize(min(1400,screen.width()-40),min(850,screen.height()-60));window.move(screen.topLeft());window.show();QTest.qWait(250)
        ids=[a['id'] for a in accounts]
        try:
            window.apply_preferences({'group_mode':'custom','profile_groups':{a['id']:('Pessoal' if i==0 else 'Trabalho') for i,a in enumerate(accounts)},'bar_position':'top','theme':'dark'})
            assert window.activate_split(ids[:2],'columns')
            wait(lambda:all(window.load_states.get(key)=='ready' for key in ids[:2]))
            original={key:(int(window.views[key][0].winId()),window.views[key][0].process.processId()) for key in ids[:2]}
            views=[window.views[key][0] for key in ids[:2]]
            assert all(window.stack.isDisplayed(view) for view in views)
            assert not views[0].geometry().intersects(views[1].geometry())
            QTest.qWait(250)
            for view in views:
                size=js(view,'[innerWidth,innerHeight]');assert size==[view.width(),view.height()],(size,view.size())
            window.stack.ratio_x=.62;window.stack.arrange();QTest.qWait(250)
            assert views[0].width()>views[1].width()
            window.stack.setCurrentWidget(views[1]);assert window.stack.is_split()
            window.stack.leave_split(views[0]);QTest.qWait(200)
            assert not window.stack.is_split()
            assert window.activate_split(ids,'grid')
            wait(lambda:all(window.load_states.get(key)=='ready' for key in ids));QTest.qWait(250)
            for key in ids[:2]:assert original[key]==(int(window.views[key][0].winId()),window.views[key][0].process.processId()),'Browser was reparented or restarted'
            rects=[window.views[key][0].geometry() for key in ids]
            for i,rect in enumerate(rects):
                for other in rects[i+1:]:assert not rect.intersects(other)
            window.stack.begin_fullscreen(window.views[ids[2]][0]);window.stack.end_fullscreen();assert window.stack.is_split()
            window.stack.set_split([window.views[key][0] for key in ids[:2]],'rows');QTest.qWait(200)
            assert views[1].y()>views[0].y()
            if output:
                target=Path(output)
                def inject(light=False):
                    for account in accounts:
                        view=window.views[account['id']][0]
                        js(view,'document.open();document.write('+json.dumps(demo_html(account,light))+');document.close();true')
                    QTest.qWait(350)
                inject(False);window.stack.leave_split(views[0]);QTest.qWait(200);capture(window,target/'overview-dark.png')
                window.stack.set_split([window.views[key][0] for key in ids[:2]],'columns');window.stack.ratio_x=.5;window.stack.arrange();QTest.qWait(250);capture(window,target/'split-dark.png')
                window.apply_preferences({'theme':'light','bar_position':'left'});inject(True)
                window.stack.set_split([window.views[key][0] for key in ids],'grid');QTest.qWait(250);capture(window,target/'grid-light.png')
                from split_workspace import SplitDialog
                dialog=SplitDialog(window,window.accounts,window.profile_group,ids);dialog.show();QTest.qWait(250)
                assert dialog.grab().save(str(target/'split-picker.png'));dialog.close()
            print('PASS split: mixed groups, two/four native CEF panes, geometry, divider, single mode, stable native parents/processes, rows/grid and fullscreen restore')
        finally:
            window.cleanup();window.close();server.shutdown()

if __name__=='__main__':main()
