"""Persistência de perfis sem dependência de Qt nem acesso às sessões."""
import json
import os
import tempfile
import uuid
from services import SERVICES, normalize_custom_url
from pathlib import Path

ICONS = {'user': 'Pessoal', 'briefcase': 'Trabalho', 'store': 'Loja',
         'building': 'Empresa', 'headset': 'Atendimento', 'home': 'Casa'}

def _canonical_id(value):
    if not isinstance(value, str):
        raise ValueError('Identificador de perfil inválido')
    try:
        canonical = str(uuid.UUID(value))
    except (ValueError, AttributeError) as error:
        raise ValueError('Identificador de perfil inválido') from error
    if value != canonical:
        raise ValueError('Identificador de perfil deve ser UUID canônico')
    return canonical


def _validate(records):
    if not isinstance(records, list):
        raise ValueError('A configuração deve conter uma lista de perfis')
    result, identifiers, active_names = [], set(), set()
    for record in records:
        if not isinstance(record, dict):
            raise ValueError('Perfil inválido')
        identifier = _canonical_id(record.get('id'))
        name = record.get('name')
        archived = record.get('archived', False)
        icon = record.get('icon', 'user')
        service = record.get('service', 'whatsapp')
        if not isinstance(service, str) or service not in SERVICES:
            raise ValueError('Serviço de perfil inválido')
        avatar_mode = record.get('avatar_mode', 'auto')
        if not isinstance(avatar_mode, str) or avatar_mode not in ('auto', 'file', 'icon', 'service'):
            raise ValueError('Modo de foto de perfil inválido')
        if not isinstance(icon, str) or icon not in ICONS:
            raise ValueError('Ícone de perfil inválido')
        if not isinstance(name, str) or not name.strip() or len(name.strip()) > 60:
            raise ValueError('Nome de perfil deve ter entre 1 e 60 caracteres')
        if not isinstance(archived, bool):
            raise ValueError('Estado de arquivamento inválido')
        name = name.strip()
        if identifier in identifiers:
            raise ValueError('Identificadores de perfil duplicados')
        if not archived and name.casefold() in active_names:
            raise ValueError('Nomes de perfis ativos duplicados')
        identifiers.add(identifier)
        if not archived:
            active_names.add(name.casefold())
        client = record.get('telegram_client','a')
        if service == 'telegram' and client not in ('a','k'):
            raise ValueError('Cliente do Telegram inválido')
        result.append({'id': identifier, 'name': name, 'archived': archived,
                       'icon': icon, 'avatar_mode': avatar_mode, 'service': service})
        if service == 'telegram':result[-1]['telegram_client'] = client
        if service == 'custom' or (service=='chatwoot' and record.get('custom_url')):result[-1]['custom_url'] = normalize_custom_url(record.get('custom_url'))
    return result


class ProfileStore:
    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.data_dir.chmod(0o700)
        self.config = self.data_dir / 'profiles.json'

    def load(self):
        try:
            content = self.config.read_text(encoding='utf-8')
        except FileNotFoundError:
            # A broken symlink is not a missing configuration to overwrite.
            if self.config.is_symlink():
                raise
            return []
        return _validate(json.loads(content))

    def save(self, records):
        candidate = _validate(records)
        serialized = json.dumps(candidate, ensure_ascii=False, indent=2) + '\n'
        temporary = None
        try:
            descriptor, filename = tempfile.mkstemp(prefix='.profiles-', suffix='.tmp', dir=self.data_dir)
            temporary = Path(filename)
            with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
                stream.write(serialized)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.config)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    def session_path(self, identifier):
        identifier = _canonical_id(identifier)
        sessions = self.data_dir / 'sessions'
        sessions.mkdir(mode=0o700, exist_ok=True)
        sessions.chmod(0o700)
        folder = sessions / identifier
        folder.mkdir(mode=0o700, exist_ok=True)
        folder.chmod(0o700)
        return folder
