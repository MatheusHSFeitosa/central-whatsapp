"""Serviços permitidos e origens de navegação de cada perfil."""
SERVICES = {
    'whatsapp': {'name': 'WhatsApp', 'url': 'https://web.whatsapp.com/', 'host': 'web.whatsapp.com'},
    'telegram': {'name': 'Telegram', 'url': 'https://web.telegram.org/a/', 'host': 'web.telegram.org'},
    'chatwoot': {'name': 'Chatwoot G3', 'url': 'https://chatwoot.g3pi.app.br/', 'host': 'chatwoot.g3pi.app.br'},
}


def allows_url(service, url):
    return (service in SERVICES and url.scheme() == 'https'
            and url.host() == SERVICES[service]['host'] and url.port(443) == 443
            and not url.userInfo())


def service_url(account):
    service = account.get('service','whatsapp')
    if service == 'telegram':
        client = account.get('telegram_client','a')
        return 'https://web.telegram.org/' + ('k' if client == 'k' else 'a') + '/'
    return SERVICES[service]['url']
