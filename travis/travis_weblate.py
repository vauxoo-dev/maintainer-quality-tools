#!/usr/bin/env python
# coding: utf-8

from __future__ import print_function

import os
import subprocess
import sys

from odoo_connection import Odoo10Context, context_mapping
from test_server import (get_addons_path, get_addons_to_check, get_depends,
                         get_server_path, parse_list)
from travis_helpers import red, yellow, yellow_light
from weblate_client import lock, get_projects, wl_push, wl_pull


def po_rm_header(po_content):
    is_header = True
    rm_header = str()
    header = str()
    for line in po_content.splitlines():
        if line.startswith('#.'):
            is_header = False
        if is_header:
            header += line + '\n'
            continue
        rm_header += line + '\n'
    return header, rm_header


def main(argv=None):
    """
    Export translation files and push them to weblate
    The weblate token should be encrypted in .travis.yml
    If not, export exits early.
    """
    if argv is None:
        argv = sys.argv

    weblate_token = os.environ.get("WEBLATE_TOKEN")
    weblate_host = os.environ.get(
        "WEBLATE_HOST", "https://weblate.vauxoo.com/api/")

    if not weblate_token:
        print(yellow_light("WARNING! Weblate token not defined- "
              "exiting early."))
        return 1

    if not weblate_host:
        print(yellow_light("WARNING! Weblate host not recognized- "
              "exiting early."))
        return 1

    travis_home = os.environ.get("HOME", "~/")
    travis_build_dir = os.environ.get("TRAVIS_BUILD_DIR", "../..")
    travis_repo_slug = os.environ.get("TRAVIS_REPO_SLUG")
    gh_token = os.environ.get("GH_TOKEN")
    travis_branch = os.environ.get("TRAVIS_BRANCH")
    travis_repo_owner = travis_repo_slug.split("/")[0]
    travis_repo_shortname = travis_repo_slug.split("/")[1]
    odoo_exclude = os.environ.get("EXCLUDE")
    odoo_include = os.environ.get("INCLUDE")
    # install_options = os.environ.get("INSTALL_OPTIONS", "").split()
    odoo_version = os.environ.get("VERSION")
    langs = parse_list(os.environ.get("LANG_ALLOWED", ""))

    # if not odoo_version:
    #     # For backward compatibility, take version from parameter
    #     # if it's not globally set
    #     odoo_version = argv[1]
    #     print(yellow_light("WARNING: no env variable set for VERSION. "
    #           "Using '%s'" % odoo_version))

    # default_project_slug = "%s-%s" % (travis_repo_slug.replace('/', '-'),
    #                                   odoo_version.replace('.', '-'))
    # weblate_project_slug = os.environ.get("weblate_PROJECT_SLUG",
    #                                         default_project_slug)
    # weblate_project_name = "%s (%s)" % (travis_repo_shortname, odoo_version)
    # weblate_organization = os.environ.get("weblate_ORGANIZATION",
    #                                         travis_repo_owner)
    # repository_url = "https://github.com/%s" % travis_repo_slug

    odoo_full = os.environ.get("ODOO_REPO", "odoo/odoo")
    server_path = get_server_path(odoo_full, odoo_version, travis_home)
    addons_path = get_addons_path(travis_home, travis_build_dir, server_path)
    addons_list = get_addons_to_check(travis_build_dir, odoo_include,
                                      odoo_exclude)
    addons_path_list = parse_list(addons_path)
    all_depends = get_depends(addons_path_list, addons_list)
    main_modules = set(os.listdir(travis_build_dir))
    main_depends = main_modules & all_depends
    addons_list = list(main_depends)
    database = "openerp_test"
    # Use by default version 10 connection context
    connection_context = context_mapping.get(odoo_version, Odoo10Context)
    command = ['git', 'branch']
    current_branch = subprocess.check_output(command).strip('\n *')
    wlprojects = get_projects(travis_repo_shortname, current_branch)
    # first project found
    wlproject = wlprojects.next()
    with connection_context(server_path, addons_path, database) \
            as odoo_context, lock(wlproject, addons_list):
        if wl_push(wlproject):
            command = ['git', 'pull', 'origin', current_branch]
            res = subprocess.check_output(command).strip('\n ')
            command = ['git', 'log', '-r', '-1', '--oneline']
            sha = subprocess.check_output(command).strip('\n ')
            print(yellow("git pull result: %s with sha %s" % (res, sha)))

        for module in addons_list:
            print("\n", yellow("Obtaining POT file for %s" % module))
            i18n_folder = os.path.join(travis_build_dir, module, 'i18n')
            # # TODO: Add empty es.po files if non exists
            # source_filename = os.path.join(i18n_folder, module + ".pot")
            # # Create i18n/ directory if doesn't exist
            # if not os.path.exists(os.path.dirname(source_filename)):
            #     os.makedirs(os.path.dirname(source_filename))
            # with open(source_filename, 'w') as f:
            #     f.write(odoo_context.get_pot_contents(module))

            # Put git add for letting known git which translations to update
            for po_file_name in os.listdir(i18n_folder):
                if not po_file_name.endswith('.po'):
                    continue
                lang = os.path.splitext(po_file_name)[0]
                if langs and lang not in langs:
                    # Limit just allowed languages if is defined
                    continue
                po_file_path = os.path.join(i18n_folder, po_file_name)
                with open(po_file_path, 'r') as f_po:
                    current_content = f_po.read()
                    odoo_context.load_po(f_po, lang)
                new_content = odoo_context.get_pot_contents(module, lang)
                current_header, current_content = po_rm_header(current_content)
                _, new_content = po_rm_header(new_content)
                if current_content == new_content:
                    # Skip unchanged po file (Removing headers)
                    continue
                with open(po_file_path, 'wb') as f_po:
                    f_po.write(current_header + new_content)
                # Maybe removing header and checking if there is a difference
                command = ['git', 'add', po_file_path]
                subprocess.check_output(command)
        command = ['git', 'diff', '--cached', '--exit-code']
        try:
            subprocess.check_output(command)
        except subprocess.CalledProcessError:
            print(yellow("No changes for languages %s" % langs))
            return 0
        command = ['git', 'commit', '--no-verify',
                   '-m', '[REF] i18n: Updating translation terms [ci skip]']
        subprocess.check_output(command)
        subprocess.check_output([
            'git', 'remote', 'add', 'travis'
            'https://%(GH_TOKEN)s@github.com/%(REPO_SLUG)s' % dict(
                GH_TOKEN=gh_token, REPO_SLUG=travis_repo_slug)])
        subprocess.check_output(['git', 'push', 'travis', current_branch])
        wl_pull(wlproject)
        return 0


if __name__ == "__main__":
    exit(main())
