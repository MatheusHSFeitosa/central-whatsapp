"""Group names and migration, with no Qt or session access."""
from copy import deepcopy
from services import SERVICES

DEFAULT_GROUP_COLOR = '#72767a'
SERVICE_COLORS = {'whatsapp':'#25d366','telegram':'#26a5e4','chatwoot':'#1f93ff','custom':'#3584e4'}


def group_name(value):
    if not isinstance(value,str):raise ValueError('Nome de grupo inválido')
    value=value.strip()
    if not value or len(value)>40 or any(c in value for c in '\n\r\x00'):
        raise ValueError('Informe um nome de grupo entre 1 e 40 caracteres.')
    return value


def known_groups(settings, records=()):
    result={};names={}
    def add(name,color=DEFAULT_GROUP_COLOR):
        if not isinstance(name,str) or not name.strip():return
        name=name.strip();folded=name.casefold()
        if folded not in names:
            names[folded]=name;result[name]={'color':color}
    for name,options in settings.get('groups',{}).items():add(name,options.get('color',DEFAULT_GROUP_COLOR))
    for name in settings.get('profile_groups',{}).values():add(name)
    if settings.get('group_mode')=='service':
        for record in records:
            service=record.get('service','whatsapp')
            if service in SERVICES:add(SERVICES[service]['name'],SERVICE_COLORS[service])
    return dict(sorted(result.items(),key=lambda item:item[0].casefold()))


def canonical_name(settings, name, records=()):
    for existing in known_groups(settings,records):
        if existing.casefold()==name.casefold():return existing
    return name


def custom_settings(settings, records=()):
    """Materialize automatic service groups before assigning a custom group."""
    candidate=deepcopy(settings)
    candidate.setdefault('profile_groups',{})
    candidate['groups']=known_groups(settings,records)
    if settings.get('group_mode')=='service':
        for record in records:
            service=record.get('service','whatsapp')
            candidate['profile_groups'].setdefault(record['id'],SERVICES[service]['name'])
    candidate['group_mode']='custom'
    return candidate


def renamed_group(settings, records, old, new):
    new=group_name(new)
    groups=known_groups(settings,records)
    if any(name.casefold()==new.casefold() and name.casefold()!=old.casefold() for name in groups):
        raise ValueError('Já existe um grupo com esse nome.')
    candidate=custom_settings(settings,records)
    options=next((options for name,options in groups.items() if name.casefold()==old.casefold()),{'color':DEFAULT_GROUP_COLOR})
    candidate['groups']={name:options for name,options in candidate['groups'].items() if name.casefold()!=old.casefold()}
    candidate['groups'][new]=options
    for key,previous in list(candidate['profile_groups'].items()):
        if previous.strip().casefold()==old.casefold():candidate['profile_groups'][key]=new
    for record in records:
        previous=SERVICES[record.get('service','whatsapp')]['name'] if settings.get('group_mode')=='service' else (candidate['profile_groups'].get(record['id'],'').strip() or 'Sem grupo')
        if previous.casefold()==old.casefold():candidate['profile_groups'][record['id']]=new
    was_collapsed=any(key.partition(':')[2].casefold()==old.casefold() for key in settings.get('collapsed_groups',[]))
    candidate['collapsed_groups']=[key for key in candidate.get('collapsed_groups',[]) if key.partition(':')[2].casefold() not in (old.casefold(),new.casefold())]
    if was_collapsed:candidate['collapsed_groups'].append('custom:'+new)
    return candidate
