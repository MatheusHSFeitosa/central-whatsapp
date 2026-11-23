import tempfile
import unittest
from pathlib import Path
from cef_storage import prepare_cef_storage


class CefMigrationTests(unittest.TestCase):
    def test_copies_session_once_and_preserves_original(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);old=root/'storage';old.mkdir()
            (old/'Cookies').write_bytes(b'synthetic-cookie')
            (old/'LOCK').write_text('not copied')
            result=prepare_cef_storage(root)
            self.assertEqual((result/'profile/Cookies').read_bytes(),b'synthetic-cookie')
            self.assertFalse((result/'profile/LOCK').exists())
            (result/'profile/Cookies').write_bytes(b'new-session')
            self.assertEqual(prepare_cef_storage(root),result)
            self.assertEqual((result/'profile/Cookies').read_bytes(),b'new-session')
            self.assertEqual((old/'Cookies').read_bytes(),b'synthetic-cookie')
            self.assertEqual(result.stat().st_mode&0o777,0o700)
    def test_symlink_destination_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'other').mkdir();(root/'cef').symlink_to(root/'other')
            with self.assertRaises(ValueError):prepare_cef_storage(root)
    def test_new_account_has_private_empty_profile(self):
        with tempfile.TemporaryDirectory() as directory:
            result=prepare_cef_storage(directory)
            self.assertTrue((result/'migration.json').exists())
