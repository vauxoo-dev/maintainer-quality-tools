#!/usr/bin/env python
# coding: utf-8

from __future__ import print_function
from __future__ import unicode_literals
import os
import sys
import time
import subprocess
from slumber import API, exceptions
from odoo_connection import context_mapping, Odoo10Context
from test_server import setup_server, get_addons_path, \
    get_server_path, get_addons_to_check, create_server_conf, \
    get_server_script, parse_list, get_depends
from travis_helpers import yellow, yellow_light, red
from txclib import utils, commands


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
    # travis_repo_owner = travis_repo_slug.split("/")[0]
    # travis_repo_shortname = travis_repo_slug.split("/")[1]
    # odoo_unittest = False
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
    # addons = ','.join(addons_list)
    # create_server_conf({'addons_path': addons_path}, odoo_version)

    # print("\nWorking in %s" % travis_build_dir)
    # print("Using repo %s and addons path %s" % (odoo_full, addons_path))

    # if not addons:
    #     print(yellow_light("WARNING! Nothing to translate- exiting early."))
    #     return 0

    # # Create weblate project if it doesn't exist
    # print()
    # print(yellow("Creating weblate project if it doesn't exist"))
    # auth = (weblate_user, weblate_password)
    # api_url = "https://www.weblate.com/api/2/"
    # api = API(api_url, auth=auth)
    # project_data = {"slug": weblate_project_slug,
    #                 "name": weblate_project_name,
    #                 "source_language_code": "en",
    #                 "description": weblate_project_name,
    #                 "repository_url": repository_url,
    #                 "organization": weblate_organization,
    #                 "license": "permissive_open_source",
    #                 "fill_up_resources": weblate_fill_up_resources,
    #                 "team": weblate_team,
    #                 }
    # try:
    #     api.project(weblate_project_slug).get()
    #     print('This weblate project already exists.')
    # except exceptions.HttpClientError:
    #     try:
    #         api.projects.post(project_data)
    #         print('weblate project has been successfully created.')
    #     except exceptions.HttpClientError:
    #         print('weblate organization: %s' % weblate_organization)
    #         print('weblate username: %s' % weblate_user)
    #         print('weblate project slug: %s' % weblate_project_slug)
    #         print(red('Error: Authentication failed. Please verify that '
    #                   'weblate organization, user and password are '
    #                   'correct. You can change these variables in your '
    #                   '.travis.yml file.'))
    #         raise

    # print("\nModules to translate: %s" % addons)

    # Install the modules on the database
    database = "openerp_test"
    # script_name = get_server_script(odoo_version)
    # setup_server(database, odoo_unittest, addons, server_path, script_name,
    #              addons_path, install_options, addons_list)

    # Initialize weblate project
    # print()
    # print(yellow('Initializing weblate project'))
    # init_args = ['--host=https://www.weblate.com',
    #              '--user=%s' % weblate_user,
    #              '--pass=%s' % weblate_password]
    # commands.cmd_init(init_args, path_to_tx=None)
    # path_to_tx = utils.find_dot_tx()

    # Use by default version 10 connection context
    connection_context = context_mapping.get(odoo_version, Odoo10Context)
    with connection_context(server_path, addons_path, database) \
            as odoo_context:
        for module in addons_list:
            print()
            print(yellow("Obtaining POT file for %s" % module))
            i18n_folder = os.path.join(travis_build_dir, module, 'i18n')
            source_filename = os.path.join(i18n_folder, module + ".pot")
            # Create i18n/ directory if doesn't exist
            if not os.path.exists(os.path.dirname(source_filename)):
                os.makedirs(os.path.dirname(source_filename))
            with open(source_filename, 'w') as f:
                f.write(odoo_context.get_pot_contents(module))
            # Put the correct timestamp for letting known tx client which
            # translations to update
            for po_file_name in os.listdir(i18n_folder):
                if not po_file_name.endswith('.po'):
                    continue
                if langs and os.path.splitext(po_file_name)[0] not in langs:
                    # Limit just allowed languages if is defined
                    # TODO: Don't delete better revert from git
                    os.remove(os.path.join(i18n_folder, po_file_name))
                    continue
                po_file_name = os.path.join(i18n_folder, po_file_name)
                command = ['git', 'log', '--pretty=format:%cd', '-n1',
                           '--date=raw', po_file_name]
                timestamp = float(subprocess.check_output(command).split()[0])
                # This converts to UTC the timestamp
                timestamp = time.mktime(time.gmtime(timestamp))
                os.utime(po_file_name, (timestamp, timestamp))
        return 0


if __name__ == "__main__":
    exit(main())
