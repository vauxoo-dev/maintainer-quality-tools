# coding: utf-8

import base64
import os
import tempfile
import time
import json
from contextlib import contextmanager
import requests
import urllib
import re


class ApiException(Exception):
    pass


class Request(object):

    def __init__(self):
        self.session = requests.Session()

    def _get_headers(self):
        return {'Authorization': 'Token %s' % self._token}

    def _check(self):
        if not self._token:
            raise ApiException("WARNING! Token not defined exiting early.")
        self.session.headers.update({
            'Accept': 'application/json',
            'User-Agent': 'mqt',
            'Authorization': 'Token %s' % self._token
        })
        self.session.headers.update(self._get_headers())
        self._request(self.host)

    def _request(self, url, payload=None, is_json=True, patch=False):
        try:
            if not payload and not patch:
                response = self.session.get(url)
            elif patch:
                response = self.session.patch(url, data=payload)
            else:
                response = self.session.post(url, data=payload)
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
        projects = []
        page = 1
        while True:
            data = self._request(self.host + '/projects/?page=%s' % page)
            projects.extend(data['results'] or [])
            if not data['next']:
                break
            page += 1
        for project in projects:
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


class GitHubApi(Request):

    def __init__(self):
        super(GitHubApi, self).__init__()
        self._token = os.environ.get("GITHUB_TOKEN")
        self.host = "https://api.github.com"
        self._owner, self._repo = os.environ.get("TRAVIS_REPO_SLUG").split('/')

    def create_pull_request(self, data):
        pull = self._request(self.host + '/repos/%s/%s/pulls' %
                             (self._owner, self._repo), json.dumps(data))
        return pull

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
                blob_data = json.dumps({
                    'content': base64.b64encode(f_po.read()),
                    'encoding': 'base64'
                })
                blob_sha = self._request(
                    self.host + '/repos/%s/%s/git/blobs' %
                    (self._owner, self._repo), blob_data)
                tree.append({
                    'path': item,
                    'mode': '100644',
                    'type': 'blob',
                    'sha': blob_sha['sha']
                })
        tree_data = json.dumps({
            'base_tree': branch_commit['tree']['sha'],
            'tree': tree
        })
        info_tree = self._request(self.host + '/repos/%s/%s/git/trees' %
                                  (self._owner, self._repo), tree_data)
        commit_data = json.dumps({
            'message': message,
            'tree': info_tree['sha'],
            'parents': [branch_commit['sha']]
        })
        info_commit = self._request(self.host + '/repos/%s/%s/git/commits' %
                                    (self._owner, self._repo), commit_data)
        update_branch = self._request(
            self.host + '/repos/%s/%s/git/refs/heads/%s' %
            (self._owner, self._repo, branch),
            json.dumps({'sha': info_commit['sha']}),
            patch=True)
        return info_commit['sha'] == update_branch['object']['sha']


class GitLabApi(Request):

    def __init__(self, host="https://git.vauxoo.com"):
        super(GitLabApi, self).__init__()
        self.host = host
        self.url = host+"/api/v4"
        self._token = os.environ.get("CI_TOKEN")
        self._id = os.environ.get("CI_PROJECT_ID")
        self.branch_ref = os.environ.get('CI_COMMIT_REF_NAME')
        self.remote_url = None

    def _get_headers(self):
        return {'PRIVATE-TOKEN': '%s' % self._token}

    def get_project(self):
        res = {}
        url_project = urllib.quote('/projects/%s' % self._id)
        data = self._request(self.url+url_project)
        fork_project = data.get('forked_from_project', {})
        res.update({'id': fork_project.get('id', data.get('id')),
                    'remote': fork_project.get('http_url_to_repo',
                                               data.get('http_url_to_repo'))})
        return res

    def get_merge_request(self):
        res = {}
        project = self.get_project()
        self.remote_url = project.get('remote')
        url_merge = urllib.quote("/projects/%s/merge_requests" %
                                 project.get('id'))
        merge_request = self._request(self.url+url_merge)
        for data in merge_request:
            if data.get('source_branch') == self.branch_ref:
                res = data
                break
        return res

    def get_environments(self):
        self._check()
        environments = {'CI_MERGE_REQUEST': False,
                        'CI_BRANCH': None}
        data = self.get_merge_request()
        if data.get('state') == 'opened':
            environments['CI_MERGE_REQUEST'] = True
        environments['CI_BRANCH'] = data.get('target_branch')
        return environments

    def get_gitlab_remote(self):
        remote = re.sub(r'https?://', '', self.remote_url)
        url = "https://{register}:{token}@{remote}"
        url = url.format(register=os.environ.get('CI_REGISTRY_USER'),
                         token=os.environ.get('CI_JOB_TOKEN'),
                         remote=re.sub(r'https?://', '', remote))
        return url
