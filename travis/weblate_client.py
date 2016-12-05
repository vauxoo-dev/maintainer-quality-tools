import os

import requests


weblate_token = os.environ.get("WEBLATE_TOKEN")
weblate_host = os.environ.get(
    "WEBLATE_HOST", "https://weblate.vauxoo.com/api/")


def weblate(url, payload=None):
    if url.startswith('http://weblate:8000/api/'):
        url = url.replace('http://weblate:8000/api/', weblate_host)
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
    return data


# print weblate('projects')
data = weblate('components')
# import pdb;pdb.set_trace()
print "data", data
# print weblate('lock')
# weblate('https://weblate.vauxoo.com/api/components/Vauxoo-yoytec-8-0/yoytec_stock/lock/')
