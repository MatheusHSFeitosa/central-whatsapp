"""Logo, preferências, grupos recolhidos, recuperação e cliente alternativo, sem rede."""
import os,sys,tempfile,uuid
from pathlib import Path
from unittest.mock import patch,Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
with tempfile.TemporaryDirectory() as data:
 os.environ['CENTRAL_WHATSAPP_DATA']=data;os.environ['XDG_CONFIG_HOME']=data
 from central import QApplication,Window,QWebEngineView
 from desktop_ui import GROUP_ROLE,COLLAPSED_ROLE,GROUP_COUNT_ROLE,PreferencesDialog
 from PySide6.QtCore import Qt,QPoint,QEvent,QEventLoop,QTimer,QCoreApplication
 from PySide6.QtTest import QTest
 from shiboken6 import delete
 app=QApplication([])
 with patch.object(QWebEngineView,'load') as load:
  window=Window();window.confirm_close=False
  for name,service in [('Pessoal','whatsapp'),('Equipe','telegram'),('Atendimento','chatwoot')]:
   with patch('central.edit_profile_dialog',return_value=(name,'user',service,{'custom_url':'https://support.example.test/'} if service=='chatwoot' else {})):window.add()
  groups={a['id']:'Trabalho' for a in window.accounts}
  window.apply_preferences(dict(group_mode='custom',profile_groups=groups))
  window.show();app.processEvents()
  original=dict(window.views);page=window.stack.currentWidget()
  first=window.list.item(0);rect=window.list.visualItemRect(first)
  QTest.mouseClick(window.list.viewport(),Qt.MouseButton.LeftButton,pos=QPoint(rect.left()+25,rect.top()+5))
  assert first.data(COLLAPSED_ROLE) and first.data(GROUP_COUNT_ROLE)==3
  assert all(window.list.item(i).isHidden() for i in (1,2))
  assert window.stack.currentWidget() is page and window.views==original
  assert window.preferences_store.load()['collapsed_groups']==['custom:Trabalho']
  assert window.list.profile_at(window.list.visualItemRect(first).center()) is None
  window.toggle_group('custom:Trabalho')
  assert not first.data(COLLAPSED_ROLE) and not any(window.list.item(i).isHidden() for i in range(3))
  for position in ('top','bottom','left'):
   window.apply_preferences({'bar_position':position})
   window.toggle_group('custom:Trabalho');app.processEvents()
   assert window.list.item(0).data(COLLAPSED_ROLE)
   assert window.stack.currentWidget() is page
   window.toggle_group('custom:Trabalho')
  assert window.app_name.isVisible()
  window.toggle_sidebar();assert window.app_name.isHidden()
  logo=window.sidebar_toggle.logo_icon.cacheKey()
  app.sendEvent(window.sidebar_toggle,QEvent(QEvent.Type.Enter))
  assert window.sidebar_toggle.icon().cacheKey()==window.sidebar_toggle.action_icon.cacheKey()
  window.sidebar_toggle.clearFocus();app.sendEvent(window.sidebar_toggle,QEvent(QEvent.Type.Leave))
  assert window.sidebar_toggle.icon().cacheKey()==logo
  dialog=PreferencesDialog(window,window.settings,window.accounts,True)
  assert dialog.tabs.count()==3 and dialog.values()['collapsed_groups']==window.settings['collapsed_groups']
  delete(dialog)
  row=next(i for i,a in enumerate(window.accounts) if a['service']=='telegram');key=window.accounts[row]['id']
  profile=window.views[key][1]
  window.list.setCurrentRow(row)
  window.set_telegram_client('k')
  assert load.call_args.args[0].toString()=='https://web.telegram.org/k/'
  assert window.views[key][1] is profile and window.store.load()[row]['telegram_client']=='k'
  # Ready sessions are never reloaded because of later resource errors.
  window._startup_ready.add(key)
  with patch('central.QTimer.singleShot') as timer:window.recover_initial_load(key)
  timer.assert_not_called()
  window._startup_ready.discard(key);window._retry_counts[key]=0
  with patch('central.QTimer.singleShot') as timer:
   window.recover_initial_load(key)
   callback=timer.call_args.args[1]
   assert window._retry_counts[key]==1
   window.set_telegram_client('a',key)
   calls=load.call_count
   callback()
   assert load.call_count==calls,'A recuperação antiga não pode recarregar um cliente recém escolhido'
  window._retry_pending.clear();window._retry_counts[key]=2
  window.recover_initial_load(key)
  assert window.views[key][0].loading_panel.isVisible() and window.load_states[key]=='error'
  window.close();QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)
  for profile in window.profiles.values():profile.deleteLater()
  QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete);delete(window)
 flush=QEventLoop();QTimer.singleShot(500,flush.quit);flush.exec();delete(app)
print('PASS: grupos recolhidos sem suspender contas, logo/hover, preferências e Telegram alternativo')
