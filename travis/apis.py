# coding: utf-8

import base64
import os
import tempfile
import time
import json
import urllib
from contextlib import contextmanager
import requests


class ApiException(Exception):
    pass


class Request(object):

    def __init__(self):
        self.session = requests.Session()

    def _get_headers(self):
        return {'Authorization': 'Token %s' % self._token}

    def _check(self, url=''):
        if not self._token:
            raise ApiException("WARNING! Token not defined exiting early.")
        self.session.headers.update(dict({
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'User-Agent': 'mqt',
        }.items() + self._get_headers().items()))
        self._request('%s/%s' % (self.host, url))

    def _request(self, url, payload=None, is_json=True, patch=False):
        try:
            if not payload and not patch:
                response = self.session.get(url)
            elif patch:
                response = self.session.patch(url, data=json.dumps(payload))
            else:
                response = self.session.post(url, data=json.dumps(payload))
            response.raise_for_status()
        except requests.RequestException as error:
            raise ApiException(str(error))
        return response.json() if is_json else response


class WeblateApi(Request):

    def __init__(self):
        super(WeblateApi, self).__init__()
        self.repo_slug = None
        self.branch = None
        self._token = os.environ.get("WEBLATE_TOKEN")
        self.host = os.environ.get(
            "WEBLATE_HOST", "https://weblate.vauxoo.com/api")
        self.tempdir = os.path.join(tempfile.gettempdir(), 'weblate_api')

    def get_project(self, repo_slug, branch):
        self.branch = branch
        projects = self._request(self.host + '/projects')
        for project in projects['results']:
            if project['name'] == repo_slug:
                self.repo_slug = project['slug']
                return project
        raise ApiException('No project found in "%s" for this path "%s"' %
                           (self.host, repo_slug))

    def load_project(self, repo_slug, branch):
        self.project = self.get_project(repo_slug, branch)
        self.load_components()

    def get_components(self):
        components = []
        values = self._request(
            self.host + '/projects/%s/components/' % self.project['slug'])
        if not values['results']:
            raise ApiException('No components found in the project "%s"' %
                               self.project['slug'])
        for value in values['results']:
            if value['branch'] and value['branch'] != self.branch:
                continue
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

    @contextmanager
    def componet_lock(self):
        try:
            for component in self.components:
                self._component_lock(component)
            yield
        finally:
            for component in self.components:
                self._component_lock(component, lock=False)

    def _component_lock(self, component, lock=True):
        url = (self.host + '/components/%s/%s/lock/' %
               (self.project['slug'], component['slug']))
        for i in range(10):
            new_lock = self._request(url, {'lock': lock})
            if new_lock['locked'] == lock:
                break
            time.sleep(60)
        return True


class Api(Request):

    def __init__(self, host=''):
        super(Api, self).__init__()
        self._token = os.environ.get("GITHUB_TOKEN")
        self._owner, self._repo = os.environ.get("TRAVIS_REPO_SLUG").split('/')
        self.host = host

    def _check(self, url=''):
        super(Api, self)._check('user')

    @staticmethod
    def get(git):
        host = ''
        protocol = 'https'
        remote = git.run(["remote", "get-url", "origin"])
        if '@' in remote:
            host = remote.split('@')[1].split(':')[0].split('/')[0]
        elif any([pro for pro in ['https://', 'http://'] if pro in remote]):
            protocol = remote.split(':')[0]
            host = remote.replace('https://', '').replace('http://', '')
            host = host.split('/')[0]
        if 'github.com' in host:
            return GitHubApi()
        return GitLabApi("%s://%s/api/v3" % (protocol, host))


class GitHubApi(Api):

    def __init__(self, host='https://api.github.com'):
        super(GitHubApi, self).__init__(host)

    def create_commit(self, message, branch, files):
        tree = []
        info_branch = self._request(
            self.host + '/repos/%s/%s/git/refs/heads/%s' %
            (self._owner, self._repo, branch))
        branch_commit = self._request(
            self.host + '/repos/%s/%s/git/commits/%s' %
            (self._owner, self._repo, info_branch['object']['sha']))
        for item in files:
            with open(item) as f_po:
                blob_data = {
                    'content': base64.b64encode(f_po.read()),
                    'encoding': 'base64'
                }
                blob_sha = self._request(
                    self.host + '/repos/%s/%s/git/blobs' %
                    (self._owner, self._repo), blob_data)
                tree.append({
                    'path': item,
                    'mode': '100644',
                    'type': 'blob',
                    'sha': blob_sha['sha']
                })
        tree_data = {
            'base_tree': branch_commit['tree']['sha'],
            'tree': tree
        }
        info_tree = self._request(self.host + '/repos/%s/%s/git/trees' %
                                  (self._owner, self._repo), tree_data)
        commit_data = {
            'message': message,
            'tree': info_tree['sha'],
            'parents': [branch_commit['sha']]
        }
        info_commit = self._request(self.host + '/repos/%s/%s/git/commits' %
                                    (self._owner, self._repo), commit_data)
        update_branch = self._request(
            self.host + '/repos/%s/%s/git/refs/heads/%s' %
            (self._owner, self._repo, branch),
            {'sha': info_commit['sha']},
            patch=True)
        return info_commit['sha'] == update_branch['object']['sha']


class GitLabApi(Api):

    def __init__(self, host='https://gitlab.com/api/v3'):
        super(GitLabApi, self).__init__(host)
        self.name_project = urllib.quote('%s/%s' % (self._owner, self._repo),
                                         safe='')

    def _get_headers(self):
        return {'PRIVATE-TOKEN': '%s' % self._token}

    def create_commit(self, message, branch, files):
        actions = []
        for item in files:
            with open(item) as f_po:
                actions.append({
                    'action': 'update',
                    'file_path': item,
                    'encoding': 'base64',
                    'content': base64.b64encode(f_po.read())
                })
        data = {
            'branch_name': branch,
            'commit_message': message,
            'actions': actions
        }
        info_commit = self._request(self.host +
                                    '/projects/%s/repository/commits' %
                                    (self.name_project), data)
        return 'id' in info_commit
