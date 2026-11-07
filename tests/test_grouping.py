import unittest,uuid
from copy import deepcopy
from grouping import known_groups,custom_settings,renamed_group
from settings_store import DEFAULTS,_validated

class GroupingTests(unittest.TestCase):
 def setUp(self):
  self.a,self.b=str(uuid.uuid4()),str(uuid.uuid4())
  self.records=[dict(id=self.a,service='whatsapp'),dict(id=self.b,service='telegram',archived=True)]
 def test_legacy_groups_recognized_and_empty_registry_retained(self):
  settings=deepcopy(DEFAULTS);settings.update(group_mode='custom',profile_groups={self.a:'Equipe',self.b:'Pessoal'},groups={'Vazio':{'color':'#112233'}})
  self.assertEqual(set(known_groups(settings,self.records)),{'Equipe','Pessoal','Vazio'})
  self.assertEqual(known_groups(settings,self.records)['Vazio']['color'],'#112233')
 def test_service_switch_preserves_existing_custom_assignments(self):
  settings=deepcopy(DEFAULTS);settings.update(group_mode='service',profile_groups={self.a:'Antigo'})
  candidate=custom_settings(settings,self.records)
  self.assertEqual(candidate['profile_groups'][self.a],'Antigo')
  self.assertEqual(candidate['profile_groups'][self.b],'Telegram')
 def test_rename_includes_archived_color_and_collapsed_state(self):
  settings=deepcopy(DEFAULTS);settings.update(group_mode='custom',profile_groups={self.a:'Equipe',self.b:'equipe'},groups={'Equipe':{'color':'#e66100'}},collapsed_groups=['custom:Equipe'])
  candidate=renamed_group(settings,self.records,'Equipe','Comercial')
  self.assertEqual(set(candidate['profile_groups'].values()),{'Comercial'})
  self.assertEqual(candidate['groups']['Comercial']['color'],'#e66100')
  self.assertEqual(candidate['collapsed_groups'],['custom:Comercial'])
  self.assertEqual(settings['profile_groups'][self.a],'Equipe')
 def test_registry_validation_and_duplicate_rename(self):
  for groups in ({'A':{'color':'red'}},{'A':{'color':'#000000'},'a':{'color':'#ffffff'}},{' A ':{'color':'#000000'}}):
   with self.assertRaises(ValueError):_validated({'groups':groups})
  settings=deepcopy(DEFAULTS);settings['groups']={'A':{'color':'#123456'},'B':{'color':'#abcdef'}}
  with self.assertRaises(ValueError):renamed_group(settings,[],'A','b')
