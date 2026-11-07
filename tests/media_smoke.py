"""Decode synthetic media and enter/exit fullscreen, without accounts or network."""
import os,sys,json,base64,tempfile,io,wave,math,struct
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import QTimer,QUrl,QEventLoop,Qt,QPoint,QCoreApplication,QEvent
from PySide6.QtWebEngineCore import QWebEngineProfile,QWebEnginePage,QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtTest import QTest
from central import QApplication,Window
from shiboken6 import delete
with tempfile.TemporaryDirectory() as data:
 os.environ['CENTRAL_WHATSAPP_DATA']=data;os.environ['XDG_CONFIG_HOME']=data
 # central constants were imported above; override only the isolated fixture paths.
 import central
 central.DATA=Path(data);central.CONFIG=Path(data)/'profiles.json'
 app=QApplication([]);window=Window();window.confirm_close=False
 profile=QWebEngineProfile(window);view=QWebEngineView();page=QWebEnginePage(profile,view);view.setPage(page)
 page.settings().setAttribute(QWebEngineSettings.WebAttribute.PlaybackRequiresUserGesture,False)
 page.settings().setAttribute(QWebEngineSettings.WebAttribute.FullScreenSupportEnabled,True)
 window.views['media']=(view,profile);window.profiles['media']=profile;window.stack.addWidget(view);window.stack.setCurrentWidget(view)
 page.fullScreenRequested.connect(lambda request:window.media_fullscreen('media',request))
 buffer=io.BytesIO()
 with wave.open(buffer,'wb') as audio:
  audio.setnchannels(1);audio.setsampwidth(2);audio.setframerate(8000)
  audio.writeframes(b''.join(struct.pack('<h',int(300*math.sin(2*math.pi*440*n/8000))) for n in range(16000)))
 records=[dict(name='tone.wav',mime='audio/wav',url='data:audio/wav;base64,'+base64.b64encode(buffer.getvalue()).decode())]
 for name,mime in [('tone.mp3','audio/mpeg'),('tone.ogg','audio/ogg;codecs=opus'),('sample.webm','video/webm;codecs="vp8,opus"'),('sample.mp4','video/mp4;codecs="avc1.42E01E,mp4a.40.2"')]:
  raw=(Path(__file__).parent/'fixtures'/name).read_bytes()
  records.append(dict(name=name,mime=mime,url='data:'+mime.split(';')[0]+';base64,'+base64.b64encode(raw).decode()))
 script='''window.results=[];(async()=>{for(const item of ITEMS){const media=document.createElement(item.mime.startsWith('video')?'video':'audio');media.muted=true;media.controls=true;document.body.append(media);const result={name:item.name,supported:media.canPlayType(item.mime)};try{media.src=item.url;await Promise.race([media.play(),new Promise((_,reject)=>setTimeout(()=>reject(Error('timeout')),5000))]);await new Promise(resolve=>setTimeout(resolve,600));result.time=media.currentTime;result.width=media.videoWidth||0;result.error=media.error&&media.error.code}catch(error){result.failure=error.name+': '+error.message;result.error=media.error&&media.error.code}media.pause();media.removeAttribute('src');media.load();media.remove();window.results.push(result)}window.finished=true})()'''.replace('ITEMS',json.dumps(records))
 result=[];loop=QEventLoop()
 def received(raw):
  if not raw:return
  value=json.loads(raw)
  if value['done']:result.extend(value['results']);loop.quit()
 timer=QTimer();timer.timeout.connect(lambda:page.runJavaScript('JSON.stringify({done:!!window.finished,results:window.results||[]})',received));timer.start(250)
 view.setHtml('<html><body><script>'+script+'</script></body></html>',QUrl('https://web.whatsapp.com/'))
 window.show();QTimer.singleShot(30000,loop.quit);loop.exec();timer.stop()
 assert len(result)==5,result
 for entry in result[:4]:assert entry.get('time',0)>0 and entry.get('error') is None,entry
 # MP4 availability is a measured build capability, not a claimed pass when unsupported.
 if result[4]['supported']:assert result[4].get('time',0)>0,result[4]
 print('Media capability:',json.dumps(result,ensure_ascii=False),flush=True)
 html='<html><body><button style="width:220px;height:60px" onclick="document.documentElement.requestFullscreen()">Tela cheia</button></body></html>'
 loaded=QEventLoop();view.loadFinished.connect(loaded.quit);view.setHtml(html,QUrl('https://web.whatsapp.com/'));QTimer.singleShot(5000,loaded.quit);loaded.exec();view.loadFinished.disconnect(loaded.quit)
 for position in ('top', 'left', 'bottom'):
  window.apply_preferences(dict(bar_position=position))
  window.stack.setCurrentWidget(view)
  if position == 'left':
   window.showMaximized()
  else:
   window.showNormal()
  view.setFocus();window.activateWindow();QTest.qWait(500)
  was_maximized=window.isMaximized()
  QTest.mouseClick(view.focusProxy() or view,Qt.MouseButton.LeftButton,pos=QPoint(70,35));QTest.qWait(500)
  assert window.isFullScreen(),f'Pedido de tela cheia deve entrar na janela: {position}'
  assert window.title_bar.isHidden() and window.sidebar.isHidden()
  page.triggerAction(QWebEnginePage.WebAction.ExitFullScreen);QTest.qWait(350)
  assert not window.isFullScreen(),f'Sair de tela cheia deve restaurar a janela: {position}'
  assert window.isMaximized()==was_maximized
  assert window.title_bar.isVisible() and window.sidebar.isVisible()
 if os.environ.get('CENTRAL_MEDIA_REPORT'):Path(os.environ['CENTRAL_MEDIA_REPORT']).write_text(json.dumps(result,ensure_ascii=False,indent=2))
 window.close();QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete);profile.deleteLater();QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete);delete(window)
 flush=QEventLoop();QTimer.singleShot(300,flush.quit);flush.exec();delete(app)
print('PASS: WAV, MP3, Opus, WebM e fullscreen; capacidade MP4 registrada separadamente')
