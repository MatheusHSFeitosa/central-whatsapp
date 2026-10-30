"""Extração em DOM fictício local; não acessa WhatsApp nem contas reais."""
import base64
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch
from PySide6.QtCore import QEventLoop, QTimer, QUrl
from PySide6.QtWidgets import QApplication
from PySide6.QtWebEngineWidgets import QWebEngineView
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from avatar_manager import OWN_AVATAR_SCRIPT
app=QApplication([])
view=QWebEngineView();view.resize(600,400);view.show()
def evaluate(script):
    loop=QEventLoop();results=[]
    view.page().runJavaScript(script,lambda value:(results.append(value),loop.quit()))
    QTimer.singleShot(5000,loop.quit);loop.exec()
    assert results,'JavaScript timeout'
    return results[0]
def extract():
    return json.loads(evaluate('JSON.stringify('+OWN_AVATAR_SCRIPT+')'))

def document(html):
    loop=QEventLoop()
    def ready(ok):loop.quit()
    view.loadFinished.connect(ready)
    view.setHtml(html,QUrl('https://web.whatsapp.com/'))
    QTimer.singleShot(5000,loop.quit);loop.exec();view.loadFinished.disconnect(ready)
# Imagens geradas dentro do DOM, sem carregar nenhuma URL.
create="""const png = color => { const c=document.createElement('canvas'); c.width=c.height=64;const ctx=c.getContext('2d');ctx.fillStyle=color;ctx.fillRect(0,0,64,64);return c.toDataURL('image/png'); };"""
document('<header id="contact"></header><div role="grid" id="chats"></div><nav><button aria-label="Perfil" id="own"></button></nav>')
evaluate("(()=>{"+create+"document.querySelector('#contact').innerHTML='<img src=\"'+png('blue')+'\">';document.querySelector('#chats').innerHTML='<button aria-label=\"Perfil\"><img src=\"'+png('blue')+'\"></button>';document.querySelector('#own').innerHTML='<img src=\"'+png('red')+'\">';return true;})()")
loop=QEventLoop();QTimer.singleShot(250,loop.quit);loop.exec()
result=extract()
assert isinstance(result,str) and result.startswith('data:image/png;base64,')
from PySide6.QtGui import QImage
image=QImage.fromData(base64.b64decode(result.split(',',1)[1]));assert image.pixelColor(128,128).red()>200 and image.pixelColor(128,128).blue()<50
# Foto de contato isolada nunca é selecionada.
evaluate("document.querySelector('nav').remove();true;")
assert extract()['status']=='not-found'
# Dois candidatos explícitos são ambíguos, portanto devem resultar em fallback.
evaluate("(()=>{"+create+"document.body.innerHTML='<nav><button aria-label=\"Perfil\"><img src=\"'+png('red')+'\"></button><button aria-label=\"Profile\"><img src=\"'+png('blue')+'\"></button></nav>';return true;})()")
loop=QEventLoop();QTimer.singleShot(250,loop.quit);loop.exec()
assert extract()['status']=='ambiguous'
# Variante de acessibilidade: tablist e div role=button também são aceitos.
evaluate("(()=>{"+create+"document.body.innerHTML='<div role=\"tablist\"><div role=\"button\" aria-label=\"Sua foto de perfil\"><img src=\"'+png('red')+'\"></div></div><header><div role=\"button\" aria-label=\"Perfil\"><img src=\"'+png('blue')+'\"></div></header>';return true;})()")
loop=QEventLoop();QTimer.singleShot(250,loop.quit);loop.exec()
result=extract()
assert isinstance(result,str) and result.startswith('data:image/png;base64,')
# Restaura um candidato único para testar a captura local quando canvas é bloqueado.
evaluate("(()=>{"+create+"document.body.innerHTML='<nav><button aria-label=\"Perfil\"><img src=\"'+png('red')+'\"></button><button aria-label=\"Profile\"><img src=\"'+png('blue')+'\"></button></nav>';return true;})()")
loop=QEventLoop();QTimer.singleShot(250,loop.quit);loop.exec()
# Falha de canvas (ex. CORS) não tenta baixar por fora da sessão.
evaluate("document.querySelector('nav button:last-child').remove();HTMLCanvasElement.prototype.toDataURL=function(){throw Error('tainted');};true;")
capture=extract()
assert capture['status']=='capture'
from PySide6.QtCore import QRect
r=capture['rect'];pix=view.grab(QRect(round(r['x']),round(r['y']),round(r['width']),round(r['height']))).toImage()
assert pix.pixelColor(pix.width()//2,pix.height()//2).red()>200
assert 'fetch(' not in OWN_AVATAR_SCRIPT
view.close()
print('PASS: somente própria foto, contatos excluídos, ambiguidade e canvas bloqueado usam fallback; sem rede')
