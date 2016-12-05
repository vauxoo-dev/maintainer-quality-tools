import os

import requests


weblate_token = os.environ.get("WEBLATE_TOKEN")
weblate_host = os.environ.get(
    "WEBLATE_HOST", "https://weblate.vauxoo.com/api/").strip('/') + '/'


def replace_host(server_url, data):
    server_host = server_url[:server_url.find('/api/') + 5]
    for key, value in data.items():
        if isinstance(value, dict):
            data[key] = replace_host(server_url, value)
        elif isinstance(value, str) and value.startswith(server_host):
            data[key] = value.replace(server_host, weblate_host)


def weblate(url, payload=None):
    session = requests.Session()
    session.headers.update({
        'Accept': 'application/json',
        'User-Agent': 'mqt',
        'Authorization': 'Token %s' % weblate_token
    })
    url = url and url.strip('/') + '/' or url
    url_next = ''
    data = {'results': [], 'count': 0}
    while url_next is not None:
        response = session.get(weblate_host + url + url_next)
        response.raise_for_status()
        res_j = response.json()
        data['results'].extend(res_j.pop('results', []))
        data['count'] += res_j.pop('count', 0)
        data.update(res_j)
        url_next = (res_j.get('next') or '').split('/')[-1] or None
    response = session.get(weblate_host)
    response.raise_for_status()
    main_info = response.json()
    server_url = main_info['projects']
    server_url = server_url[:server_url.find('/api/') + 5]
    replace_host(server_url, data)
    return data


print weblate('projects')
# print weblate('components')
# print weblate('lock')
