#!/usr/bin/env python
# coding: utf-8

import os
import glob
import subprocess

from odoo_connection import Odoo10Context, context_mapping
from test_server import (get_test_dependencies as get_depends, get_addons_path,
                         get_addons_to_check, get_server_path, parse_list)
from weblate_api import WeblateApi
from travis_helpers import yellow


class TravisWeblateUpdate(object):

    def __init__(self):
        self.repo_slug = os.environ.get("TRAVIS_REPO_SLUG")
        self.api = WeblateApi()
        self.api.load_project(self.repo_slug)
        self._travis_home = os.environ.get("HOME", "~/")
        self._travis_build_dir = os.environ.get("TRAVIS_BUILD_DIR", "../..")
        self._odoo_exclude = os.environ.get("EXCLUDE")
        self._odoo_include = os.environ.get("INCLUDE")
        self._odoo_version = os.environ.get("VERSION")
        self._langs = (parse_list(os.environ.get("LANG_ALLOWED")) if
                       os.environ.get("LANG_ALLOWED", False) else [])
        self._odoo_full = os.environ.get("ODOO_REPO", "odoo/odoo")
        self._server_path = get_server_path(self._odoo_full,
                                            self._odoo_version,
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

    def update(self):
        self.api.pull()
        for component in self.api.components:
            if component['vcs'] == 'git':
                name = 'wl_%s' % component['branch']
                remote = (self.api.host.replace('api', 'git') + '/' +
                          self.api.project['slug'] + '/' + component['slug'])
                self.api.component_unlock(component)
                self.api.component_lock(component)
                self.api.component_repository(component, 'pull')
                subprocess.call(["git", "remote", "remove", name])
                subprocess.call(["git", "remote", "add", name, remote])
                subprocess.call(["git", "fetch", "--all"])
                subprocess.call(["git", "reset", "--hard"])
                subprocess.call(["git", "checkout", "-b", component['branch'],
                                 "origin/%s" % component['branch']])
                self._generate_odoo_po_files()
                po_files = glob.glob(os.path.join(self._travis_build_dir,
                                                  component['filemask']))
                #TODO Define when exist one conflict
                subprocess.call(["git", "merge", "--squash",
                                 "%s/%s" % (name, component['branch'])])
                subprocess.call(["git", "add"] + po_files)
                subprocess.call(["git", "commit", "--no-verify",
                                 "--author='Weblate bot <weblate@bot>'",
                                 "-m", "[REF] i18n: Updating translation"
                                 "terms from weblate [ci skip]"])
                subprocess.call(["git", "push", "origin", component['branch']])
                self.api.component_repository(component, 'reset')
                self.api.component_unlock(component)
        return 0


def main(argv=None):
    exit(TravisWeblateUpdate().update())


if __name__ == "__main__":
    exit(TravisWeblateUpdate().update())
