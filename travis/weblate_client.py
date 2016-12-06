import os
from contextlib import contextmanager
from urllib import urlencode

import simplejson
import requests

from travis_helpers import yellow

weblate_token = os.environ.get("WEBLATE_TOKEN")
weblate_host = os.environ.get(
    "WEBLATE_HOST", "https://weblate.vauxoo.com/api/")


def weblate(url, payload=None):
    if not url.startswith('http'):
        url = weblate_host + url
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
        full_url = ("%s%s" % (url, url_next)).encode('UTF-8')
        if payload:
            # payload_json = urlencode(payload).encode('UTF-8')
            payload_json = simplejson.dumps(payload).encode('UTF-8')
            # import pdb;pdb.set_trace()
            response = session.post(
                full_url, json=simplejson.loads(payload_json), data=payload)
        else:
            response = session.get(full_url)
        response.raise_for_status()
        res_j = response.json()
        data['results'].extend(res_j.pop('results', []))
        data['count'] += res_j.pop('count', 0)
        data.update(res_j)
        url_next = res_j.get('next')
    return data.pop('results', None) or data


def get_components(wlproject, filter_modules=None):
    for component in weblate(wlproject['components_list_url']):
        if filter_modules and component['name'] not in filter_modules:
            continue
        yield component


def get_projects(project=None, branch=None):
    for wlproject in weblate('projects'):
        # Using standard name: project-name (branch.version)
        project_name = wlproject['name'].split('(')[0].strip()
        if project and project_name != project:
            continue
        branch_name = wlproject['name'].split('(')[1].strip(' )')
        if branch and branch != branch_name:
            continue
        yield wlproject


def wl_push(project):
    if weblate(project['repository_url'])['needs_push']:
        print(yellow("Weblate push %s" % project['repository_url']))
        weblate(project['repository_url'], {'operation': 'commit'})
        return weblate(project['repository_url'], {'operation': 'push'})
    print(yellow("Don't needs weblate push %s" % project['repository_url']))
    return None


def wl_pull(project):
    print(yellow("Weblate pull %s" % project['repository_url']))
    return weblate(project['repository_url'], {'operation': 'pull'})


@contextmanager
def lock(project, filter_modules=None):
    components = [component['lock_url']
                  for component in get_components(project, filter_modules)]
    try:
        for component in components:
            print(yellow("Lock %s" % component))
            res = weblate(component, {'lock': True})
            print("..%s" % res)
            if not res['locked']:
                raise ValueError("Project not locked %s token **%s. %s" % (
                    component, weblate_token[-4:], res))
        yield
    finally:
        for component in components:
            print(yellow("unlock %s" % component))
            res = weblate(component, {'lock': False})
            print("..%s" % res)


if __name__ == '__main__':
    project = 'openacademy-project'
    branch = 'master'
    modules = ['openacademy']

    projects = get_projects(project, branch)
    # first project
    project = projects.next()
    with lock(project, modules):
        pass
        # weblate('push', {'project': project})
        # git pull
        # regenerate po
        # git commit
        # git push
        ### optional: wlc(['pull', component])

# print weblate('projects')
# data = weblate('components')
# import pdb;pdb.set_trace()
# print "data", data
# lock_url = 'components/Vauxoo-yoytec-8-0/yoytec_stock/lock/'
# print weblate(lock_url, {'lock': False})
# weblate('https://weblate.vauxoo.com/api/components/Vauxoo-yoytec-8-0/yoytec_stock/lock/')
