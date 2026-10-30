"""Exercita remoção apenas em HOME e diretórios XDG temporários."""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


class UninstallTests(unittest.TestCase):
    def run_uninstall(self, root, content):
        config = root / 'config'
        (root / '.local/share/applications').mkdir(parents=True)
        autostart = config / 'autostart/central-whatsapp.desktop'
        autostart.parent.mkdir(parents=True)
        autostart.write_text(content)
        application = root / '.local/share/central-whatsapp'
        application.mkdir(parents=True)
        (application / 'central.py').write_text('fixture')
        data = root / 'data/central-whatsapp-data'
        data.mkdir(parents=True)
        session = data / 'session-marker'
        session.write_text('preservar')
        env = dict(os.environ, HOME=str(root), XDG_CONFIG_HOME=str(config),
                   XDG_DATA_HOME=str(root/'data'), CENTRAL_WHATSAPP_DATA=str(data))
        script = Path(__file__).resolve().parents[1] / 'scripts/uninstall-user.sh'
        result = subprocess.run(['sh', str(script)], env=env, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(application.exists())
        self.assertEqual(session.read_text(), 'preservar')
        return autostart

    def test_removes_only_managed_autostart(self):
        with tempfile.TemporaryDirectory(prefix='central-uninstall-test-') as directory:
            path = self.run_uninstall(Path(directory), '[Desktop Entry]\nX-CentralWhatsApp-Managed=true\n')
            self.assertFalse(path.exists())

    def test_preserves_foreign_autostart(self):
        with tempfile.TemporaryDirectory(prefix='central-uninstall-test-') as directory:
            content = '[Desktop Entry]\nName=Entrada externa\n'
            path = self.run_uninstall(Path(directory), content)
            self.assertEqual(path.read_text(), content)


if __name__ == '__main__':
    unittest.main()
