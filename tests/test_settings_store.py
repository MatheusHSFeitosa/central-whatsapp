from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from settings_store import PreferencesStore, AutostartManager, DEFAULTS, MARKER


class SettingsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = PreferencesStore(self.root / 'data')
        self.manager = AutostartManager(self.root / 'config with spaces', ['/tmp/app with spaces', 'quoted"arg', '$var', '100%'])

    def test_defaults_and_independent_lists(self):
        self.assertEqual(self.store.load(), DEFAULTS)
        settings = self.store.load()
        settings['startup_profiles'].append(str(uuid.uuid4()))
        self.assertEqual(self.store.load()['startup_profiles'], [])
        self.store.save({})
        self.assertEqual(self.store.load(), DEFAULTS)
        self.assertEqual(stat.S_IMODE(self.store.config.stat().st_mode), 0o600)

    def test_invalid_preserved(self):
        self.store.save({})
        previous = self.store.config.read_bytes()
        identifier = str(uuid.uuid4())
        for settings in ([], {'startup_enabled': 1}, {'start_hidden': 'yes'},
                         {'close_action': 'hide'}, {'startup_mode': 'invalid'},
                         {'startup_profiles': ['bad']}, {'muted_profiles': [identifier, identifier]},
                         {'sidebar_collapsed': None}, {'collapsed_groups':'bad'}, {'collapsed_groups':['unknown:X']}, {'collapsed_groups':['service:Telegram','service:Telegram']}, {'theme':'blue'}, {'bar_position':'right'},
                         {'group_mode':'invalid'}, {'profile_groups':{'bad':'Work'}},
                         {'profile_groups':{identifier:'a'*41}}, {'unknown': True}):
            with self.subTest(settings=settings):
                with self.assertRaises(ValueError):
                    self.store.save(settings)
                self.assertEqual(self.store.config.read_bytes(), previous)
        self.store.config.write_bytes(b'{invalid')
        with self.assertRaises(ValueError):
            self.store.load()
        self.assertEqual(self.store.config.read_bytes(), b'{invalid')

    def test_appearance_and_custom_groups_roundtrip(self):
        identifier = str(uuid.uuid4())
        settings = dict(DEFAULTS, theme='light', bar_position='top', group_mode='custom', profile_groups={identifier:'Trabalho'})
        self.store.save(settings)
        self.assertEqual(self.store.load(), settings)

    def test_selected_and_muted_profiles_roundtrip(self):
        identifier = str(uuid.uuid4())
        settings = dict(DEFAULTS, startup_enabled=True, start_hidden=True,
                        close_action='exit', startup_mode='all',
                        startup_profiles=[identifier], muted_profiles=[identifier],
                        sidebar_collapsed=True)
        self.store.save(settings)
        self.assertEqual(self.store.load(), settings)

    def test_autostart_enable_disable_and_escaping(self):
        self.assertIsNone(self.manager.capture())
        self.manager.sync(True)
        text = self.manager.path.read_text()
        self.assertIn('Exec="/tmp/app with spaces"', text)
        self.assertIn('"--autostart"', text)
        self.assertIn('100%%', text)
        self.assertIn('quoted\\\\"arg', text)
        self.assertIn(MARKER, text)
        self.assertIn('X-GNOME-Autostart-enabled=true', text)
        self.manager.sync(False)
        self.assertFalse(self.manager.path.exists())

    def test_foreign_entry_never_replaced_or_deleted(self):
        self.manager.path.parent.mkdir(parents=True)
        foreign = b'[Desktop Entry]\nName=Other\n'
        self.manager.path.write_bytes(foreign)
        self.manager.sync(False)
        with self.assertRaises(OSError):
            self.manager.sync(True)
        self.assertEqual(self.manager.capture(), foreign)

    def test_failed_save_rolls_back_new_and_existing_autostart(self):
        self.store.save({})
        for existing in (False, True):
            with self.subTest(existing=existing):
                self.manager.sync(existing)
                snapshot = self.manager.capture()
                previous = self.store.config.read_bytes()
                self.manager.sync(not existing)
                with patch('settings_store.os.replace', side_effect=OSError('disk full')):
                    with self.assertRaises(OSError):
                        self.store.save(dict(DEFAULTS, startup_enabled=not existing))
                self.manager.restore(snapshot)
                self.assertEqual(self.manager.capture(), snapshot)
                self.assertEqual(self.store.config.read_bytes(), previous)
                self.assertEqual(list(self.store.data_dir.glob('.settings.json-*')), [])

    def test_missing_installed_launcher_fails_without_creating_entry(self):
        manager = AutostartManager(self.root / 'other config')
        with patch('settings_store.os.access', return_value=False):
            with self.assertRaises(OSError):
                manager.sync(True)
        self.assertFalse(manager.path.exists())

    def test_fsync_failure_preserves_previous(self):
        self.store.save({})
        previous = self.store.config.read_bytes()
        with patch('settings_store.os.fsync', side_effect=OSError('failed')):
            with self.assertRaises(OSError):
                self.store.save({'start_hidden': True})
        self.assertEqual(self.store.config.read_bytes(), previous)


if __name__ == '__main__':
    unittest.main()
