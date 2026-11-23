import json
import sys
import tempfile
import unittest
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services import normalize_custom_url, service_url
from profile_store import ProfileStore


class CustomServiceTests(unittest.TestCase):
    def test_links_and_canonical_forms(self):
        cases = {
            'chat.example.com': 'https://chat.example.com/',
            ' https://CHAT.example.com:443/inbox?a=1#/chat ': 'https://chat.example.com/inbox?a=1#/chat',
            'https://chat.example.com:8443/': 'https://chat.example.com:8443/',
            'https://éxample.com/': 'https://xn--xample-9ua.com/',
            'https://[::1]:8443/inbox': 'https://[::1]:8443/inbox',
        }
        for value, expected in cases.items():
            with self.subTest(value=value):
                self.assertEqual(normalize_custom_url(value), expected)
                self.assertEqual(service_url(dict(service='custom',custom_url=value)), expected)

    def test_unsafe_or_malformed_links(self):
        cases = [None, [], '', 'http://example.com', 'file:///tmp/a', 'javascript:alert(1)',
                 'https://user:password@example.com', 'https://user@example.com',
                 'https://example.com:0/', 'https://example.com:99999/', 'https://',
                 'https://example.com/a b', 'https://example.com/\nfoo',
                 'https://example.com\\@evil.test', 'https://bad..host/', 'x'*2049]
        for value in cases:
            with self.subTest(value=value), self.assertRaises(ValueError):
                normalize_custom_url(value)

    def test_save_reload_and_failed_save_preserves_profile(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ProfileStore(Path(directory))
            record = dict(id=str(uuid.uuid4()), name='Minha central', service='custom',
                          custom_url='chat.example.test/conta')
            store.save([record])
            loaded = store.load()
            self.assertEqual(loaded[0]['custom_url'], 'https://chat.example.test/conta')
            previous = store.config.read_bytes()
            for bad in (None, '', 'http://example.test'):
                with self.assertRaises(ValueError):
                    store.save([dict(record, custom_url=bad)])
                self.assertEqual(store.config.read_bytes(), previous)
            loaded[0]['archived'] = True
            store.save(loaded)
            self.assertEqual(store.load()[0]['custom_url'], loaded[0]['custom_url'])

    def test_builtin_profile_and_its_session_are_not_changed(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ProfileStore(Path(directory))
            old = dict(id=str(uuid.uuid4()), name='Antigo', service='whatsapp')
            store.save([old])
            session = store.session_path(old['id'])
            marker = session / 'preserve'
            marker.write_text('existing session')
            custom = dict(id=str(uuid.uuid4()), name='Novo', service='custom', custom_url='https://chat.example.test/')
            store.save([old, custom])
            self.assertEqual(store.load()[0]['id'], old['id'])
            self.assertEqual(marker.read_text(), 'existing session')
            self.assertNotEqual(store.session_path(custom['id']), session)


if __name__ == '__main__':
    unittest.main()
