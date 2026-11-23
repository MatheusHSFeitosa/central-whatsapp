"""Two-way WebRTC with fake devices and real permission callbacks; no real microphone/camera."""
import json
import os
import sys
import tempfile
import uuid
from pathlib import Path
from unittest.mock import patch

os.environ['QTWEBENGINE_CHROMIUM_FLAGS'] = (
    os.environ.get('QTWEBENGINE_CHROMIUM_FLAGS', '') +
    ' --use-fake-device-for-media-stream'
)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

with tempfile.TemporaryDirectory(prefix='central-webrtc-') as directory:
    os.environ['CENTRAL_WHATSAPP_DATA'] = directory
    os.environ['XDG_CONFIG_HOME'] = directory
    from central import Window, Page, QMessageBox
    from PySide6.QtCore import QUrl, QEventLoop, QTimer, QCoreApplication, QEvent
    from PySide6.QtWebEngineCore import QWebEngineProfile, QWebEnginePermission, QWebEngineSettings
    from PySide6.QtWebEngineWidgets import QWebEngineView
    from PySide6.QtWidgets import QApplication
    from PySide6.QtTest import QTest
    from shiboken6 import delete

    class FixturePage(Page):
        def acceptNavigationRequest(self, url, kind, main):
            if url.scheme() == 'data':
                return True
            return super().acceptNavigationRequest(url, kind, main)

    app = QApplication([])
    with patch.object(Window, 'select', lambda *args, **kwargs: None):
        window = Window()
        window.confirm_close = False
        key = str(uuid.uuid4())
        account = dict(id=key, name='Teste local', icon='user', service='custom',
                       custom_url='https://calls.example.test/chat', avatar_mode='service')
        window.accounts = [account]
        window.refresh(0)
        profile = QWebEngineProfile(key, window)
        profile.setPersistentStoragePath(str(Path(directory)/'storage'))
        view = QWebEngineView()
        page = FixturePage(profile, view, 'custom', account['custom_url'])
        view.setPage(page)
        page.settings().setAttribute(QWebEngineSettings.WebAttribute.PlaybackRequiresUserGesture, False)
        window.views[key] = (view, profile)
        window.profiles[key] = profile
        window.stack.addWidget(view)
        window.stack.setCurrentWidget(view)
        requests = []
        def permission_requested(permission):
            requests.append((permission.origin().toString(), permission.permissionType()))
            window.permission(key, permission)
        page.permissionRequested.connect(permission_requested)
        window.show()

        html = """<button onclick="capture()">Capturar</button><script>
window.statusResult = {};
window.capture = async () => {
 try {
  window.testStream = await navigator.mediaDevices.getUserMedia({audio:true,video:true});
  window.statusResult = {captured:true};
 } catch(e) { window.statusResult = {failure:e.name,message:e.message}; }
};
window.duplex = async () => {
 try {
  const stream = window.testStream;
  const peers = [new RTCPeerConnection({iceServers:[]}),new RTCPeerConnection({iceServers:[]})];
  window.testPeers = peers;
  const videos = peers.map(() => {
   const v = document.createElement('video');
   v.muted = true; v.autoplay = true; v.srcObject = new MediaStream();
   document.body.append(v); return v;
  });
  peers.forEach((peer,i) => {
   peer.ontrack = e => videos[i].srcObject.addTrack(e.track);
   stream.getTracks().forEach(track => peer.addTrack(track,stream));
  });
  const ice = peer => peer.iceGatheringState === 'complete' ? Promise.resolve() :
   new Promise((resolve,reject) => {
    const timer=setTimeout(()=>reject(Error('ice timeout')),6000);
    peer.addEventListener('icegatheringstatechange',()=>{
     if(peer.iceGatheringState === 'complete'){clearTimeout(timer);resolve();}
    });
   });
  await peers[0].setLocalDescription(await peers[0].createOffer());
  await ice(peers[0]);
  await peers[1].setRemoteDescription(peers[0].localDescription);
  await peers[1].setLocalDescription(await peers[1].createAnswer());
  await ice(peers[1]);
  await peers[0].setRemoteDescription(peers[1].localDescription);
  const deadline=Date.now()+10000;
  while(Date.now()<deadline && !peers.every(p=>p.connectionState === 'connected'))
   await new Promise(r=>setTimeout(r,100));
  await new Promise(r=>setTimeout(r,1000));
  const inbound=[];
  for(const peer of peers){
   const stats=await peer.getStats();
   inbound.push([...stats.values()].filter(s=>s.type==='inbound-rtp').map(s=>({kind:s.kind,packets:s.packetsReceived})));
  }
  window.statusResult = {
   connections:peers.map(p=>p.connectionState),
   tracks:videos.map(v=>v.srcObject.getTracks().map(t=>t.kind).sort()),
   inbound,
   codecVideo:RTCRtpSender.getCapabilities('video').codecs.map(c=>c.mimeType)
  };
 } catch(e){window.statusResult={failure:e.name+': '+e.message};}
};
window.stopTest = () => {
 window.testStream?.getTracks().forEach(t=>t.stop());
 window.testPeers?.forEach(p=>p.close());
};
</script>"""
        loaded = QEventLoop()
        view.loadFinished.connect(loaded.quit)
        view.setHtml(html, QUrl(account['custom_url']))
        QTimer.singleShot(6000, loaded.quit)
        loaded.exec()
        view.loadFinished.disconnect(loaded.quit)

        def evaluate(script):
            loop = QEventLoop()
            output = []
            page.runJavaScript(script, lambda result: (output.append(result), loop.quit()))
            QTimer.singleShot(3000, loop.quit)
            loop.exec()
            assert output, 'JavaScript did not return'
            return output[0]

        def await_result():
            loop = QEventLoop()
            output = []
            def received(raw):
                if raw:
                    result = json.loads(raw)
                    if result:
                        output.append(result)
                        loop.quit()
            timer = QTimer()
            timer.timeout.connect(lambda: page.runJavaScript('JSON.stringify(window.statusResult)', received))
            timer.start(150)
            QTimer.singleShot(20000, loop.quit)
            loop.exec()
            timer.stop()
            assert output, 'WebRTC timeout'
            return output[0]

        with patch('central.QMessageBox.question', return_value=QMessageBox.StandardButton.No):
            evaluate('window.statusResult={};capture();null')
            denied = await_result()
        print('Denied capture:', denied, 'permission requests:', requests, flush=True)
        assert denied.get('failure') in ('NotAllowedError','AbortError'), denied
        assert requests, 'must use the real permission presenter'

        reloaded = QEventLoop()
        view.loadFinished.connect(reloaded.quit)
        with (
            patch('central.QMessageBox.question', return_value=QMessageBox.StandardButton.Yes),
            patch('central.QMessageBox.information'),
            patch.object(view, 'reload', side_effect=lambda: view.setHtml(html, QUrl(account['custom_url']))),
        ):
            window.reset_call_permissions()
            QTimer.singleShot(6000, reloaded.quit)
            reloaded.exec()
            evaluate('window.statusResult={};capture();null')
            captured = await_result()
        view.loadFinished.disconnect(reloaded.quit)
        assert captured == {'captured': True}, captured
        assert len(requests) >= 2, 'reset must cause a new permission request'

        evaluate('window.statusResult={};duplex();null')
        result = await_result()
        assert result.get('connections') == ['connected', 'connected'], result
        assert result['tracks'] == [['audio', 'video'], ['audio', 'video']], result
        for inbound in result['inbound']:
            assert {s['kind'] for s in inbound if s['packets'] > 0} == {'audio', 'video'}, result
        print('WebRTC result:', json.dumps(result), flush=True)
        # A page from another origin must never gain capture through this profile.
        forbidden = profile.queryPermission(QUrl('https://other.example.test'), QWebEnginePermission.PermissionType.MediaAudioCapture)
        window.permission(key, forbidden)
        assert forbidden.state() == QWebEnginePermission.State.Denied
        evaluate('stopTest();null')
        window.close()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        profile.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        app.processEvents()
        delete(window)
    flush = QEventLoop();QTimer.singleShot(300, flush.quit);flush.exec()
print('PASS: deny/reset/grant, duplex audio/video and cross-origin permission isolation')
