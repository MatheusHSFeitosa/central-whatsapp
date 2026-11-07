import json
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from profile_store import ProfileStore


class ProfileStoreTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.store = ProfileStore(Path(self.directory.name) / 'data')
        self.record = {'id': str(uuid.uuid4()), 'name': 'Pessoal'}

    def test_missing_and_old_format(self):
        self.assertEqual(self.store.load(), [])
        self.store.config.write_text(json.dumps([self.record]), encoding='utf-8')
        expected = dict(self.record, archived=False, icon='user', avatar_mode='auto', service='whatsapp')
        self.assertEqual(self.store.load(), [expected])
        loaded = self.store.load()
        loaded[0]['name'] = 'Outro'
        self.assertEqual(self.store.load(), [expected])

    def test_services_roundtrip_and_reject_unknown(self):
        for service in ('whatsapp', 'telegram', 'chatwoot'):
            self.store.save([dict(self.record, service=service)])
            self.assertEqual(self.store.load()[0]['service'], service)
            self.assertEqual(self.store.load()[0]['id'], self.record['id'])
        previous = self.store.config.read_bytes()
        with self.assertRaises(ValueError):
            self.store.save([dict(self.record, service='arbitrary')])
        self.assertEqual(self.store.config.read_bytes(), previous)

    def test_telegram_client_roundtrip(self):
        for client in ('a','k'):
            self.store.save([dict(self.record,service='telegram',telegram_client=client)])
            self.assertEqual(self.store.load()[0]['telegram_client'],client)
        with self.assertRaises(ValueError):
            self.store.save([dict(self.record,service='telegram',telegram_client='external')])

    def test_invalid_file_preserved(self):
        for content in ('{', '{}', '[{"id": "../escape", "name":"Conta"}]'):
            with self.subTest(content=content):
                self.store.config.write_text(content, encoding='utf-8')
                with self.assertRaises(ValueError):
                    self.store.load()
                self.assertEqual(self.store.config.read_text(), content)

    def test_validation_preserves_previous(self):
        self.store.save([self.record])
        previous = self.store.config.read_bytes()
        invalid = [None, {}, [dict(self.record, id='wrong')],
                   [dict(self.record, id='AAAAAAAA-AAAA-4AAA-8AAA-AAAAAAAAAAAA')],
                   [dict(self.record, name=' ')], [dict(self.record, name='a' * 61)],
                   [dict(self.record, archived=1)], [self.record, self.record],
                   [dict(self.record, icon='unknown')],
                   [self.record, dict(self.record, id=str(uuid.uuid4()), name='pEsSoAl')]]
        for records in invalid:
            with self.subTest(records=records):
                with self.assertRaises(ValueError):
                    self.store.save(records)
                self.assertEqual(self.store.config.read_bytes(), previous)

    def test_archived_restore_same_identifier(self):
        archived = dict(self.record, archived=True)
        self.store.save([archived, {'id': str(uuid.uuid4()), 'name': 'pessoal'}])
        self.assertTrue(self.store.load()[0]['archived'])
        self.store.save([dict(archived, archived=False)])
        self.assertEqual(self.store.load()[0]['id'], self.record['id'])
        self.assertFalse(self.store.load()[0]['archived'])

    def test_permissions_and_session_preserved(self):
        self.store.save([self.record])
        folder = self.store.session_path(self.record['id'])
        marker = folder / 'session-marker'
        marker.write_text('preserve')
        self.store.save([dict(self.record, archived=True)])
        self.assertEqual(marker.read_text(), 'preserve')
        for path in (self.store.data_dir, folder.parent, folder):
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE(self.store.config.stat().st_mode), 0o600)
        with self.assertRaises(ValueError):
            self.store.session_path('../escape')

    def test_failure_before_replace_preserves_previous_and_cleans(self):
        self.store.save([self.record])
        previous = self.store.config.read_bytes()
        for operation in ('profile_store.os.fsync', 'profile_store.os.replace'):
            with self.subTest(operation=operation):
                with patch(operation, side_effect=OSError('simulated disk failure')):
                    with self.assertRaises(OSError):
                        self.store.save([dict(self.record, name='Changed')])
                self.assertEqual(self.store.config.read_bytes(), previous)
                self.assertEqual(list(self.store.data_dir.glob('.profiles-*.tmp')), [])

    def test_names_normalized_without_mutating_input(self):
        record = dict(self.record, name='  Pessoal  ')
        self.store.save([record])
        self.assertEqual(self.store.load()[0]['name'], 'Pessoal')
        self.assertEqual(record['name'], '  Pessoal  ')
        self.assertNotIn('archived', record)

    def test_icon_presets_persist(self):
        from profile_store import ICONS
        for icon in ICONS:
            self.store.save([dict(self.record, icon=icon)])
            self.assertEqual(self.store.load()[0]['icon'], icon)

    def test_avatar_modes_preserve_metadata_without_paths(self):
        for mode in ('auto', 'file', 'icon'):
            record = dict(self.record, icon='home', archived=True, avatar_mode=mode,
                          avatar_path='/tmp/private.png', avatar_url='https://example.invalid/photo',
                          avatar_data='data:image/png;base64,PRIVATE')
            self.store.save([record])
            loaded = self.store.load()[0]
            self.assertEqual(loaded, dict(self.record, icon='home', archived=True, avatar_mode=mode, service='whatsapp'))
            self.assertEqual(set(loaded), {'id', 'name', 'icon', 'archived', 'avatar_mode', 'service'})
            self.assertNotIn('PRIVATE', self.store.config.read_text())
        self.assertFalse((self.store.data_dir / 'avatars').exists())
        self.assertFalse((self.store.data_dir / 'sessions').exists())

    def test_invalid_avatar_modes_preserve_previous(self):
        self.store.save([self.record])
        previous = self.store.config.read_bytes()
        for mode in (None, True, 1, [], {}, 'photo', 'AUTO', '/tmp/photo.png'):
            with self.subTest(mode=mode):
                with self.assertRaises(ValueError):
                    self.store.save([dict(self.record, avatar_mode=mode)])
                self.assertEqual(self.store.config.read_bytes(), previous)
                self.store.config.write_text(json.dumps([dict(self.record, avatar_mode=mode)]))
                with self.assertRaises(ValueError):
                    self.store.load()
                self.store.config.write_bytes(previous)


if __name__ == '__main__':
    unittest.main()
