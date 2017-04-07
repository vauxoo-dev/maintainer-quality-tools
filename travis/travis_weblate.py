#!/usr/bin/env python
# coding: utf-8

import os
import glob

from odoo_connection import Odoo10Context, context_mapping
from test_server import (get_test_dependencies as get_depends, get_addons_path,
                         get_addons_to_check, get_server_path, parse_list)
from apis import WeblateApi, GitHubApi
from travis_helpers import yellow
from git_run import GitRun


class TravisWeblateUpdate(object):

    def __init__(self):
        self.repo_slug = os.environ.get("TRAVIS_REPO_SLUG")
        self.wl_api = WeblateApi()
        self.wl_api.load_project(self.repo_slug)
        self.gh_api = GitHubApi()
        self._git = GitRun(os.path.join(os.getcwd(), '.git'))
        self._travis_home = os.environ.get("HOME", "~/")
        self._travis_build_dir = os.environ.get("TRAVIS_BUILD_DIR", "../..")
        self._odoo_exclude = os.environ.get("EXCLUDE")
        self._odoo_include = os.environ.get("INCLUDE")
        self._odoo_version = os.environ.get("VERSION")
        self._odoo_branch = os.environ.get("ODOO_BRANCH")
        self._langs = (parse_list(os.environ.get("LANG_ALLOWED")) if
                       os.environ.get("LANG_ALLOWED", False) else [])
        self._odoo_full = os.environ.get("ODOO_REPO", "odoo/odoo")
        self._server_path = get_server_path(self._odoo_full,
                                            (self._odoo_branch or
                                             self._odoo_version),
                                            self._travis_home)
        self._addons_path = get_addons_path(self._travis_home,
                                            self._travis_build_dir,
                                            self._server_path)
        self._addons_list = get_addons_to_check(self._travis_build_dir,
                                                self._odoo_include,
                                                self._odoo_exclude)
        self._all_depends = (
            get_depends(self._addons_path, self._addons_list) +
            self._addons_list)
        self._main_modules = set(os.listdir(self._travis_build_dir))
        self._main_depends = self._main_modules & set(self._all_depends)
        self._addons_list = list(self._main_depends)
        #TODO Calculated another context
        self._connection_context = context_mapping.get(
            self._odoo_version, Odoo10Context)

    def _get_po_models(self, po_content):
        po_models = []
        for line in po_content.splitlines():
            if line.startswith('#:'):
                po_models.append(line)
        return po_models

    def _generate_odoo_po_files(self):
        with self._connection_context(self._server_path, self._addons_path,
                                      "openerp_test") as odoo_context:
            for module in self._addons_list:
                print("\n", yellow("Obtaining POT file for %s" % module))
                i18n_folder = os.path.join(self._travis_build_dir, module,
                                           'i18n')
                if not os.path.isdir(i18n_folder):
                    os.makedirs(i18n_folder)
                # Put git add for letting known git which translations to update
                po_files = glob.glob(os.path.join(i18n_folder, '*.po'))
                for lang in self._langs:
                    if os.path.isfile(os.path.join(i18n_folder, lang + '.po')):
                        continue
                    with open(os.path.join(i18n_folder, lang + '.po'), 'wb') \
                            as f_po:
                        f_po.write(odoo_context.get_pot_contents(module, lang))
                for po_file_name in po_files:
                    lang = os.path.basename(os.path.splitext(po_file_name)[0])
                    if self._langs and lang not in self._langs:
                        # Limit just allowed languages if is defined
                        continue
                    po_file_path = os.path.join(i18n_folder, po_file_name)
                    with open(po_file_path, 'r') as f_po:
                        current_content = f_po.read()
                        odoo_context.load_po(f_po, lang)
                    new_content = odoo_context.get_pot_contents(module, lang)
                    if (self._get_po_models(current_content) ==
                            self._get_po_models(new_content)):
                        continue
                    with open(po_file_path, 'wb') as f_po:
                        f_po.write(new_content)


    def _add_odoo_po_files(self, component):
        po_files = glob.glob(os.path.join(self._travis_build_dir,
                                          component['filemask']))
        self._git.run(["add"] + po_files)

    def _register_pull_request(self, component, status):
        branch_name = 'conflict-%s-weblate' % (component['branch'])
        self._add_odoo_po_files(component)
        self._git.run(["commit", "--no-verify",
                       "--author='Weblate bot <weblate@bot>'",
                       "-m", "[REF] i18n: Conflict on the daily cron",
                       "-m", status])
        self._git.run(["branch", "-m", branch_name])
        self._git.run(["push", "-f", "origin", branch_name])
        self._git.run(["branch", "-m", component['branch']])
        pull = self.gh_api.create_pull_request({
            'title': '[REF] i18n: Conflict on the daily cron',
            'head': '%s:%s' % (self.repo_slug.split('/')[0], branch_name),
            'base': component['branch'],
            'body': status
        })
        print(yellow("The pull request register is: %s" % pull['html_url']))
        return 0

    def update(self):
        self.wl_api.pull()
        for component in self.wl_api.components:
            if component['vcs'] == 'git':
                name = '%s-weblate' % component['branch']
                remote = (self.wl_api.host.replace('api', 'git') + '/' +
                          self.wl_api.project['slug'] + '/' +
                          component['slug'])
                self.wl_api.component_unlock(component)
                self.wl_api.component_lock(component)
                self.wl_api.component_repository(component, 'pull')
                self._git.run(["remote", "remove", name])
                self._git.run(["remote", "add", name, remote])
                self._git.run(["fetch", "--all"])
                self._git.run(["reset", "--hard"])
                self._git.run(["checkout", "-b", component['branch'],
                               "origin/%s" % component['branch']])
                self._generate_odoo_po_files()
                self._git.run(["merge",
                               "%s/%s" % (name, component['branch'])])
                status = self._git.run(["status"])
                if 'both modified' in status:
                    return self._register_pull_request(component, status)
                self._add_odoo_po_files(component)
                self._git.run(["commit", "--no-verify",
                               "--author='Weblate bot <weblate@bot>'",
                               "-m", "[REF] i18n: Updating translation"
                               "terms from weblate [ci skip]"])
                self._git.run(["push", "origin", component['branch']])
                self.wl_api.component_repository(component, 'reset')
                self.wl_api.component_unlock(component)
        return 0


def main(argv=None):
    exit(TravisWeblateUpdate().update())


if __name__ == "__main__":
    exit(TravisWeblateUpdate().update())
