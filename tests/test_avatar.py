import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import base64
import stat
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage, QIcon
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from avatar_manager import AvatarManager
APP=QApplication.instance() or QApplication([])

class AvatarTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.manager=AvatarManager(self.root/'data');self.key=str(uuid.uuid4())
        self.source=self.root/'photo.png'
        image=QImage(480,320,QImage.Format.Format_RGB32);image.fill(0xffba2020);image.save(str(self.source))
    def test_normalized_private_and_circular(self):
        self.manager.import_file(self.key,self.source)
        image=self.manager.load(self.key)
        self.assertEqual((image.width(),image.height()),(256,256))
        self.assertEqual(stat.S_IMODE(self.manager.path(self.key).stat().st_mode),0o600)
        icon=self.manager.icon(self.key,QIcon());self.assertFalse(icon.isNull())
        self.assertEqual(icon.pixmap(64,64).toImage().pixelColor(0,0).alpha(),0)
    def test_rejects_svg_malformed_large_and_bad_identifier(self):
        for name,data in [('bad.png',b'bad'),('vector.svg',b'<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40"/>')]:
            path=self.root/name;path.write_bytes(data)
            with self.assertRaises(ValueError):self.manager.import_file(self.key,path)
        huge=self.root/'huge.png'
        with huge.open('wb') as stream:stream.truncate(10*1024*1024+1)
        with self.assertRaises(ValueError):self.manager.import_file(self.key,huge)
        with self.assertRaises(ValueError):self.manager.import_file('../escape',self.source)
        self.assertFalse(self.manager.path(self.key).exists())
    def test_failed_write_keeps_previous(self):
        self.manager.import_file(self.key,self.source);previous=self.manager.path(self.key).read_bytes()
        with patch('avatar_manager.os.replace',side_effect=OSError('disk error')):
            with self.assertRaises(OSError):self.manager.import_file(self.key,self.source)
        self.assertEqual(self.manager.path(self.key).read_bytes(),previous)
        self.assertEqual(list(self.manager.folder.glob('.avatar-*')),[])
    def test_data_url_and_fallback(self):
        data='data:image/png;base64,'+base64.b64encode(self.source.read_bytes()).decode()
        self.manager.save_data_url(self.key,data)
        self.assertFalse(self.manager.load(self.key).isNull())
        for value in ('https://example.org/photo.png','data:image/png;base64,???','data:image/png;base64,YWJj'):
            with self.assertRaises(ValueError):self.manager.save_data_url(self.key,value)
        self.manager.remove(self.key);self.assertTrue(self.manager.icon(self.key,QIcon()).isNull())
