# coding: utf-8

import os
import tempfile
import time
import requests
import json

from travis_helpers import red, yellow, yellow_light


class Request(object):

    def __init__(self):
        self.session = requests.Session()

    def _check(self):
        if not self._token:
            print(yellow_light("WARNING! Token not defined- "
                               "exiting early."))
            exit(1)
        self.session.headers.update({
            'Accept': 'application/json',
            'User-Agent': 'mqt',
            'Authorization': 'Token %s' % self._token
        })
        self._request(self.host)

    def _request(self, url, payload=None, is_json=True, files={}):
        try:
            if not payload and not files:
                response = self.session.get(url)
            else:
                response = self.session.post(url, data=payload, files=files)
            response.raise_for_status()
        except requests.RequestException as error:
            print(red(str(error)))
            exit(1)
        return response.json() if is_json else response


class WeblateApi(Request):

    def __init__(self):
        super(WeblateApi, self).__init__()
        self.repo_slug = None
        self._token = os.environ.get("WEBLATE_TOKEN")
        self.host = os.environ.get(
            "WEBLATE_HOST", "https://weblate.vauxoo.com/api")
        self.tempdir = os.path.join(tempfile.gettempdir(), 'weblate_api')
        self._check()

    def get_project(self, repo_slug):
        self.repo_slug = repo_slug
        projects = self._request(self.host + '/projects')
        for project in projects['results']:
            if project['web'].endswith(repo_slug):
                return project
        print(yellow(str('No project found in "%s" for this path "%s"' %
                         (self.host, repo_slug))))
        exit(1)

    def load_project(self, repo_slug):
        self.project = self.get_project(repo_slug)
        self.load_components()

    def get_components(self):
        components = []
        values = self._request(
            self.host + '/projects/%s/components/' % self.project['slug'])
        if not values['results']:
            print(yellow(str('No components found in the project "%s"' %
                             self.project['slug'])))
            exit(1)
        for value in values['results']:
            if (value['repo'].endswith(self.repo_slug) or
                    value['repo'].endswith(self.repo_slug + '.git')):
                components.append(value)
        return components

    def load_components(self):
        self.components = self.get_components()

    def pull(self):
        pull = self._request(
            self.host + '/projects/%s/repository/' % self.project['slug'],
            {'operation': 'pull'})
        return pull['result']

    def component_repository(self, component, operation):
        result = self._request(self.host + '/components/%s/%s/repository/' %
                               (self.project['slug'], component['slug']),
                               {'operation': operation})
        return result['result']

    def component_lock(self, component):
        while True:
            url = (self.host + '/components/%s/%s/lock/' %
                   (self.project['slug'], component['slug']))
            lock = self._request(url)
            if not lock['locked']:
                lock = self._request(url, {'lock': True})
                if lock['locked']:
                    break
            time.sleep(60)
        return True

    def component_unlock(self, component):
        lock = self._request(self.host + '/components/%s/%s/lock/' %
                             (self.project['slug'], component['slug']),
                             {'lock': False})
        return lock['locked']


class GitHubApi(Request):

    def __init__(self):
        super(GitHubApi, self).__init__()
        self._token = os.environ.get("GITHUB_TOKEN")
        self.host = "https://api.github.com"
        self._owner, self._repo = os.environ.get("TRAVIS_REPO_SLUG").split('/')
        self.session = requests.Session()
        self._check()

    def get_user_info(self, email):
        user_info = self._request(self.host + '/search/users?type=user&q=%s' %
                                  email)
        return user_info['items'][0] if (user_info['total_count'] == 1 and
                                         len(user_info['items']) == 1) else {}

    def create_pull_request(self, data):
        pull = self._request(self.host + '/repos/%s/%s/pulls' %
                             (self._owner, self._repo), json.dumps(data))
        return pull
