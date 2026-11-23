"""Serviços permitidos e origens de navegação de cada perfil."""
from urllib.parse import urlsplit, urlunsplit
import ipaddress
import re


SERVICES = {
    'whatsapp': {'name': 'WhatsApp', 'url': 'https://web.whatsapp.com/', 'host': 'web.whatsapp.com'},
    'telegram': {'name': 'Telegram', 'url': 'https://web.telegram.org/a/', 'host': 'web.telegram.org'},
    'chatwoot': {'name': 'Chatwoot'},
    'custom': {'name': 'Chat personalizado'},
}


def normalize_custom_url(value):
    if not isinstance(value, str):
        raise ValueError('Informe o endereço HTTPS do chat.')
    value = value.strip()
    if not value or len(value) > 2048 or any(c.isspace() or ord(c) < 32 for c in value) or '\\' in value:
        raise ValueError('Informe um endereço válido, sem espaços.')
    if '://' not in value:
        value = 'https://' + value
    try:
        parsed = urlsplit(value)
        host = parsed.hostname
        port = parsed.port
        if parsed.scheme.lower() != 'https' or not host or parsed.username is not None or parsed.password is not None:
            raise ValueError()
        if ':' in host:
            host = '[' + ipaddress.IPv6Address(host).compressed + ']'
        else:
            host = host.encode('idna').decode('ascii').lower()
            labels = host.rstrip('.').split('.')
            if len(host) > 253 or any(not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', label) for label in labels):
                raise ValueError()
        if port is not None and port == 0:
            raise ValueError()
    except (ValueError, UnicodeError):
        raise ValueError('Use um endereço HTTPS válido, sem usuário ou senha no link.') from None
    authority = host + (':' + str(port) if port not in (None, 443) else '')
    return urlunsplit(('https', authority, parsed.path or '/', parsed.query, parsed.fragment))


def allows_url(service, url, custom_url=''):
    if service not in SERVICES or url.scheme() != 'https' or url.userInfo():
        return False
    if service in ('custom','chatwoot'):
        try:
            expected = urlsplit(normalize_custom_url(custom_url))
        except ValueError:
            return False
        try:
            host = url.host()
            host = ipaddress.IPv6Address(host).compressed if ':' in host else host.encode('idna').decode('ascii').lower()
        except (ValueError, UnicodeError):
            return False
        return host == expected.hostname and url.port(443) == (expected.port or 443)
    return url.host() == SERVICES[service]['host'] and url.port(443) == 443


def service_url(account):
    service = account.get('service','whatsapp')
    if service in ('custom','chatwoot'):
        return normalize_custom_url(account.get('custom_url', ''))
    if service == 'telegram':
        client = account.get('telegram_client','a')
        return 'https://web.telegram.org/' + ('k' if client == 'k' else 'a') + '/'
    return SERVICES[service]['url']
