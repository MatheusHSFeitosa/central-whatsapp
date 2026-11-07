"""Preferências e autostart; importar este módulo não altera o sistema.

Para salvar uma preferência com autostart: snapshot = manager.capture();
manager.sync(candidate['startup_enabled']); store.save(candidate).
Se save falhar, manager.restore(snapshot) e mantenha o estado anterior na UI.
"""
import copy
import json
import os
import tempfile
import re
from grouping import group_name
from pathlib import Path

from profile_store import _canonical_id

DEFAULTS = {
    'startup_enabled': False, 'start_hidden': False, 'close_action': 'background',
    'startup_mode': 'selected', 'startup_profiles': [], 'muted_profiles': [],
    'sidebar_collapsed': False, 'theme': 'system', 'bar_position': 'left',
    'group_mode': 'none', 'profile_groups': {}, 'collapsed_groups': [], 'groups': {},
}
MARKER = 'X-CentralWhatsApp-Managed=true'


def _validated(settings):
    if not isinstance(settings, dict):
        raise ValueError('Preferências devem ser um objeto')
    if set(settings) - set(DEFAULTS):
        raise ValueError('Preferência desconhecida')
    result = copy.deepcopy(DEFAULTS)
    result.update(settings)
    for key in ('startup_enabled', 'start_hidden', 'sidebar_collapsed'):
        if type(result[key]) is not bool:
            raise ValueError('Preferência booleana inválida: ' + key)
    if result['close_action'] not in ('background', 'exit'):
        raise ValueError('Ação de fechamento inválida')
    if result['startup_mode'] not in ('all', 'selected', 'none'):
        raise ValueError('Modo de inicialização inválido')
    for key, allowed in [('theme', ('system','light','dark')), ('bar_position', ('left','top','bottom')), ('group_mode', ('none','service','custom'))]:
        if result[key] not in allowed:
            raise ValueError('Preferência inválida: ' + key)
    collapsed = result['collapsed_groups']
    if not isinstance(collapsed, list) or any(not isinstance(key, str) or not key.startswith(('service:', 'custom:')) or len(key)>100 or any(c in key for c in '\n\r\x00') for key in collapsed):
        raise ValueError('Grupos recolhidos inválidos')
    if len(collapsed) != len(set(collapsed)):
        raise ValueError('Grupos recolhidos duplicados')
    registry = result['groups']
    if not isinstance(registry,dict):raise ValueError('Cadastro de grupos inválido')
    seen=set()
    for name,options in registry.items():
        if group_name(name)!=name or name.casefold() in seen:raise ValueError('Nome de grupo duplicado ou inválido')
        seen.add(name.casefold())
        if not isinstance(options,dict) or set(options)!={'color'} or not isinstance(options['color'],str) or not re.fullmatch(r'#[0-9a-fA-F]{6}',options['color']):
            raise ValueError('Cor de grupo inválida')
    groups = result['profile_groups']
    if not isinstance(groups, dict):
        raise ValueError('Grupos inválidos')
    for key, value in groups.items():
        _canonical_id(key)
        if not isinstance(value, str) or len(value) > 40 or any(c in value for c in '\n\r\x00'):
            raise ValueError('Nome de grupo inválido')
    for key in ('startup_profiles', 'muted_profiles'):
        values = result[key]
        if not isinstance(values, list):
            raise ValueError('Lista de perfis inválida: ' + key)
        canonical = [_canonical_id(value) for value in values]
        if len(canonical) != len(set(canonical)):
            raise ValueError('Perfis duplicados: ' + key)
        result[key] = canonical
    return result


def _atomic_write(path, content):
    temporary = None
    try:
        descriptor, name = tempfile.mkstemp(prefix='.' + path.name + '-', dir=path.parent)
        temporary = Path(name)
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


class PreferencesStore:
    def __init__(self, data_dir):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.data_dir.chmod(0o700)
        self.config = self.data_dir / 'settings.json'

    def load(self):
        try:
            content = self.config.read_text(encoding='utf-8')
        except FileNotFoundError:
            if self.config.is_symlink():
                raise
            return copy.deepcopy(DEFAULTS)
        return _validated(json.loads(content))

    def save(self, settings):
        candidate = _validated(settings)
        _atomic_write(self.config, (json.dumps(candidate, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))


def _exec_argument(argument):
    # Desktop Entry Exec quoting has two layers: string escapes and Exec escapes.
    # Percent is a field-code introducer even inside double quotes.
    argument = argument.replace('%', '%%')
    argument = ''.join(('\\' + char) if char in '\\"`$' else char for char in argument)
    argument = argument.replace('\\', '\\\\')
    return '"' + argument + '"'


class AutostartManager:
    def __init__(self, config_home=None, launch_command=None):
        root = Path(config_home) if config_home is not None else Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config')))
        self.path = root / 'autostart' / 'central-whatsapp.desktop'
        self.launch_command = launch_command

    def _command(self):
        command = self.launch_command
        if command is None:
            command = next(([str(path)] for path in (Path.home() / '.local/bin/central-whatsapp', Path('/usr/bin/central-whatsapp'))
                            if path.is_file() and os.access(path, os.X_OK)), None)
        if not isinstance(command, (tuple, list)) or not command:
            raise OSError('Instale a Central Chats antes de ativar a inicialização automática')
        if any(not isinstance(arg, str) or not arg or any(char in arg for char in '\n\r\x00') for arg in command):
            raise ValueError('Comando de inicialização inválido')
        return list(command)

    def capture(self):
        try:
            return self.path.read_bytes()
        except FileNotFoundError:
            if self.path.is_symlink():
                raise
            return None

    def _owned(self, content):
        return content is not None and MARKER.encode() in content.splitlines()

    def sync(self, enabled):
        if type(enabled) is not bool:
            raise ValueError('Inicialização automática deve ser booleana')
        current = self.capture()
        if current is not None and not self._owned(current):
            if enabled:
                raise OSError('Já existe uma entrada de inicialização de outro aplicativo; ela foi preservada')
            return
        if not enabled:
            if current is not None:
                self.path.unlink()
            return
        command = self._command()
        content = ('[Desktop Entry]\nType=Application\nName=Central Chats\n'
                   'Exec=' + ' '.join(_exec_argument(arg) for arg in command + ['--autostart']) + '\n'
                   'Icon=central-whatsapp\nTerminal=false\nX-GNOME-Autostart-enabled=true\n' + MARKER + '\n')
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        _atomic_write(self.path, content.encode('utf-8'))

    def restore(self, snapshot):
        if snapshot is not None and not isinstance(snapshot, bytes):
            raise ValueError('Snapshot inválido')
        current = self.capture()
        if current == snapshot:
            return
        if current is not None and not self._owned(current):
            raise OSError('Entrada externa modificada; restauração recusada')
        if snapshot is None:
            if current is not None:
                self.path.unlink()
        else:
            self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            _atomic_write(self.path, snapshot)
