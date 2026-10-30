"""Fotos locais por UUID; nenhuma requisição externa ou acesso a contatos."""
import base64
import binascii
import os
import tempfile
from pathlib import Path
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QImage, QImageReader, QIcon, QPixmap, QPainter, QPainterPath
from profile_store import _canonical_id

# Somente controles explicitamente identificados como o próprio perfil.
# Não usa imagens de conversas, painel do contato, rede ou APIs privadas.
OWN_AVATAR_SCRIPT = r'''(() => {
 try {
  const matches = new Set();
  const labels = new Set(['perfil','profile','meu perfil','seu perfil','your profile','tu perfil','sua foto do perfil','sua foto de perfil','foto do seu perfil','your profile photo','foto de perfil']);
  document.querySelectorAll('[data-testid="menu-bar-profile"]').forEach(el => matches.add(el));
  const bars = 'nav, [role="navigation"], [role="tablist"], [data-testid="navbar"], #side > header';
  document.querySelectorAll(bars).forEach(bar => {
   bar.querySelectorAll('button, [role="button"], [role="tab"]').forEach(el => {
    const label = (el.getAttribute('aria-label') || el.getAttribute('title') || '').trim().toLowerCase();
    if (labels.has(label)) matches.add(el);
   });
  });
  const images = new Set();
  for (const el of matches) {
   if (el.getBoundingClientRect().width <= 0) continue;
   for (const image of el.querySelectorAll('img')) {
    if (image.complete && image.naturalWidth >= 32 && image.naturalHeight >= 32 && image.getBoundingClientRect().width > 0 && !image.src.startsWith('data:image/svg')) images.add(image);
   }
  }
  if (images.size !== 1) return {status: images.size ? 'ambiguous' : 'not-found'};
  const image = [...images][0];
  const canvas = document.createElement('canvas'); canvas.width = canvas.height = 256;
  const size = Math.min(image.naturalWidth, image.naturalHeight);
  try {
   canvas.getContext('2d').drawImage(image,(image.naturalWidth-size)/2,(image.naturalHeight-size)/2,size,size,0,0,256,256);
   return canvas.toDataURL('image/png');
  } catch (_) {
   // Se o site bloqueia ler pixels do canvas, fornece apenas o retângulo
   // visível da própria foto para captura local pela janela Qt.
   const rect=image.getBoundingClientRect();
   const top=document.elementFromPoint(rect.x+rect.width/2,rect.y+rect.height/2);
   if ((top !== image && !image.contains(top)) || rect.x<0 || rect.y<0 || rect.right>innerWidth || rect.bottom>innerHeight) return {status:'blocked'};
   return {status:'capture',rect:{x:rect.x,y:rect.y,width:rect.width,height:rect.height}};
  }
 } catch (_) { return {status:'unavailable'}; }
})()'''

class AvatarManager:
    def __init__(self, data_dir):
        self.folder = Path(data_dir)/'avatars'

    def path(self, identifier):
        return self.folder/(_canonical_id(identifier)+'.png')

    def load(self, identifier):
        path = self.path(identifier)
        if not path.is_file() or path.stat().st_size > 10*1024*1024:
            return QImage()
        return self._read(path)

    def _read(self, path):
        if Path(path).stat().st_size > 10*1024*1024:
            raise ValueError('A imagem deve ter no máximo 10 MB.')
        QImageReader.setAllocationLimit(64)
        reader = QImageReader(str(path)); reader.setDecideFormatFromContent(True); reader.setAutoTransform(True)
        if bytes(reader.format()).lower() not in (b'png',b'jpeg',b'jpg',b'webp'):
            raise ValueError('Escolha uma imagem PNG, JPEG ou WebP.')
        size=reader.size()
        if size.width()<=0 or size.height()<=0 or size.width()>4096 or size.height()>4096 or size.width()*size.height()>8_000_000:
            raise ValueError('A imagem é grande demais ou tem dimensões inválidas.')
        image=reader.read()
        if image.isNull(): raise ValueError('Não foi possível ler esta imagem.')
        return image

    def _save(self, identifier, image):
        target=self.path(identifier)
        image=image.scaled(256,256,Qt.AspectRatioMode.KeepAspectRatioByExpanding,Qt.TransformationMode.SmoothTransformation)
        image=image.copy((image.width()-256)//2,(image.height()-256)//2,256,256)
        # Uma imagem nova não carrega metadados do arquivo original.
        clean=QImage(256,256,QImage.Format.Format_ARGB32);clean.fill(Qt.GlobalColor.transparent)
        painter=QPainter(clean);painter.drawImage(0,0,image);painter.end()
        self.folder.mkdir(parents=True,exist_ok=True,mode=0o700);self.folder.chmod(0o700)
        fd,name=tempfile.mkstemp(prefix='.avatar-',suffix='.png',dir=self.folder);os.close(fd)
        try:
            if not clean.save(name,'PNG'):raise OSError('Não foi possível salvar a foto.')
            with open(name,'rb') as stream:os.fsync(stream.fileno())
            os.replace(name,target)
        finally:Path(name).unlink(missing_ok=True)

    def import_file(self, identifier, path):
        self.path(identifier)
        self._save(identifier,self._read(path))

    def save_data_url(self, identifier, data_url):
        if not isinstance(data_url,str) or not data_url.startswith('data:image/png;base64,') or len(data_url)>600_000:
            raise ValueError('Foto automática inválida.')
        try:raw=base64.b64decode(data_url.split(',',1)[1],validate=True)
        except (ValueError,binascii.Error) as error:raise ValueError('Foto automática inválida.') from error
        if not raw.startswith(b'\x89PNG\r\n\x1a\n'):raise ValueError('Foto automática inválida.')
        # Reutiliza o mesmo leitor com limites antes de decodificar os pixels.
        self.path(identifier)
        with tempfile.TemporaryDirectory(prefix='central-avatar-') as directory:
            path=Path(directory)/'image.png';path.write_bytes(raw)
            image=self._read(path)
        self._save(identifier,image)

    def remove(self, identifier):
        self.path(identifier).unlink(missing_ok=True)

    def icon(self, identifier, fallback):
        try:image=self.load(identifier)
        except (ValueError,OSError):return fallback
        if image.isNull():return fallback
        canvas=QPixmap(64,64);canvas.fill(Qt.GlobalColor.transparent)
        painter=QPainter(canvas);painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        clip=QPainterPath();clip.addEllipse(QRectF(1,1,62,62));painter.setClipPath(clip)
        painter.drawImage(QRectF(0,0,64,64),image);painter.end()
        return QIcon(canvas)
