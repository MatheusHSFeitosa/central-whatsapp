"""Groups and profile creation use real Qt with synthetic files, no network/accounts."""
import os,sys,tempfile,uuid,json
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
with tempfile.TemporaryDirectory() as directory:
 os.environ['CENTRAL_WHATSAPP_DATA']=directory;os.environ['XDG_CONFIG_HOME']=directory
 from central import QApplication,Window,QWebEngineView,QInputDialog,QMessageBox
 from desktop_ui import GROUP_ROLE,GROUP_COLOR_ROLE,GROUP_KEY_ROLE,EMPTY_GROUP_ROLE
 from PySide6.QtCore import QTimer,Qt,QEvent,QCoreApplication,QEventLoop
 from PySide6.QtWidgets import QLineEdit,QComboBox,QPushButton,QDialogButtonBox,QCheckBox
 from PySide6.QtGui import QColor,QImage
 from shiboken6 import delete
 app=QApplication([])
 with patch.object(QWebEngineView,'load',lambda *args:None):
  window=Window();window.confirm_close=False
  for name,service in [('Pessoal','whatsapp'),('Suporte','chatwoot')]:
   with patch('central.edit_profile_dialog',return_value=(name,'user',service)):window.add()
  first,second=[a['id'] for a in window.accounts]
  window.apply_preferences({'group_mode':'custom','profile_groups':{first:'Equipe',second:'Pessoal'}})
  window.show();app.processEvents()
  assert set(window.group_catalog())=={'Equipe','Pessoal'}
  window.populate_groups_menu()
  assert {'Equipe','Pessoal','Novo grupo…'}<=set(action.text() for action in window.groups_menu.actions())
  with patch.object(QInputDialog,'getText',return_value=('Vazio',True)):window.create_group()
  empty=next(window.list.item(i) for i in range(window.list.count()) if window.list.item(i).data(EMPTY_GROUP_ROLE))
  assert empty.data(GROUP_ROLE)=='Vazio'
  previous=dict(window.views);window.list.setCurrentItem(empty)
  assert window.views==previous
  with patch.object(QInputDialog,'getText',return_value=('Comercial',True)):window.rename_group('Equipe')
  assert window.settings['profile_groups'][first]=='Comercial'
  with patch('central.QColorDialog.getColor',return_value=QColor('#e66100')):window.choose_group_color('Comercial')
  assert window.settings['groups']['Comercial']['color']=='#e66100'
  row=next(i for i,a in enumerate(window.accounts) if a['id']==first)
  assert window.list.item(row).data(GROUP_COLOR_ROLE)=='#e66100'
  window.list.setCurrentRow(row);window.populate_profile_groups()
  assert {'Sem grupo','Comercial','Pessoal','Vazio','Novo grupo…'}<=set(a.text() for a in window.profile_groups_menu.actions())
  # Add an existing tab without creating/changing any web profile.
  def choose_existing():
   dialog=app.activeModalWidget()
   for checkbox in dialog.findChildren(QCheckBox):checkbox.setChecked(True)
   dialog.findChild(QDialogButtonBox).button(QDialogButtonBox.StandardButton.Ok).click()
  QTimer.singleShot(0,choose_existing);window.add_profiles_to_group('Comercial')
  assert window.settings['profile_groups'][second]=='Comercial' and window.views==previous
  image=QImage(100,80,QImage.Format.Format_RGB32);image.fill(QColor('#e66100'));photo=Path(directory)/'chosen.png';image.save(str(photo))
  # Real create dialog: select group and photo before saving the profile.
  def fill_dialog():
   dialog=app.activeModalWidget()
   dialog.findChild(QLineEdit,'profileName').setText('Telegram foto')
   provider=dialog.findChild(QComboBox,'profileService');provider.setCurrentIndex(provider.findData('telegram'))
   groups=dialog.findChild(QComboBox,'profileGroup');groups.setCurrentIndex(groups.findData('Comercial'))
   modes=dialog.findChild(QComboBox,'profileImageMode');modes.setCurrentIndex(modes.findData('file'))
   dialog.findChild(QPushButton,'chooseProfileImage').click()
   dialog.findChild(QDialogButtonBox).button(QDialogButtonBox.StandardButton.Ok).click()
  with patch('desktop_ui.QFileDialog.getOpenFileName',return_value=(str(photo),'PNG')):
   QTimer.singleShot(0,fill_dialog);window.add()
  account=next(a for a in window.accounts if a['name']=='Telegram foto')
  assert account['avatar_mode']=='file' and window.settings['profile_groups'][account['id']]=='Comercial'
  assert window.avatar_manager.load(account['id']).width()==256
  with patch('central.edit_profile_dialog',return_value=('Telegram padrão','user','telegram')):window.add()
  assert next(a for a in window.accounts if a['name']=='Telegram padrão')['avatar_mode']=='service'
  # Settings failure rolls back profile metadata and the staged photo.
  before=window.store.load();before_settings=window.preferences_store.load()
  draft=dict(name='Falha',icon='user',service='whatsapp',avatar_mode='file',photo_path=str(photo),group='Comercial',group_touched=True,new_group=False)
  files=set(window.avatar_manager.folder.glob('*.png'))
  with patch.object(window.preferences_store,'save',side_effect=OSError('simulação')),patch.object(QMessageBox,'critical'):
   # Choose a new group so settings definitely changes.
   draft['group']='Transação';draft['new_group']=True
   assert not window.commit_profile(draft)
  assert window.store.load()==before and window.preferences_store.load()==before_settings
  assert set(window.avatar_manager.folder.glob('*.png'))==files
  window.close();QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)
  for profile in window.profiles.values():profile.deleteLater()
  QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete);delete(window)
 loop=QEventLoop();QTimer.singleShot(500,loop.quit);loop.exec();delete(app)
print('PASS: grupos existentes/vazios, menus, cor, renomear, adicionar abas, criação com foto e rollback')
