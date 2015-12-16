#!/usr/bin/env python

from __future__ import print_function

import re
import os
import subprocess
import sys
import time

from getaddons import get_addons, get_depends, get_modules, is_module
from travis_helpers import success_msg, fail_msg


def has_test_errors(fname, dbname, odoo_version, check_loaded=True):
    """
    Check a list of log lines for test errors.
    Extension point to detect false positives.
    """
    # Rules defining checks to perform
    # this can be
    # - a string which will be checked in a simple substring match
    # - a regex object that will be matched against the whole message
    # - a callable that receives a dictionary of the form
    #     {
    #         'loglevel': ...,
    #         'message': ....,
    #     }
    errors_ignore = [
        'Mail delivery failed',
        'failed sending mail',
        ]
    errors_report = [
        lambda x: x['loglevel'] == 'CRITICAL',
        'At least one test failed',
        'no access rules, consider adding one',
        'invalid module names, ignored',
        ]
    # Only check ERROR lines before 7.0
    if odoo_version < '7.0':
        errors_report.append(
            lambda x: x['loglevel'] == 'ERROR')

    def make_pattern_list_callable(pattern_list):
        for i in range(len(pattern_list)):
            if isinstance(pattern_list[i], basestring):
                regex = re.compile(pattern_list[i])
                pattern_list[i] = lambda x: regex.match(x['message'])
            elif hasattr(pattern_list[i], 'match'):
                regex = pattern_list[i]
                pattern_list[i] = lambda x: regex.match(x['message'])

    make_pattern_list_callable(errors_ignore)
    make_pattern_list_callable(errors_report)

    print("-"*10)
    # Read log file removing ASCII color escapes:
    # http://serverfault.com/questions/71285
    color_regex = re.compile(r'\x1B\[([0-9]{1,2}(;[0-9]{1,2})?)?[m|K]')
    log_start_regex = re.compile(
        r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} \d+ (?P<loglevel>\w+) '
        '(?P<db>(%s)|([?])) (?P<logger>\S+): (?P<message>.*)$' % dbname)
    log_records = []
    last_log_record = dict.fromkeys(log_start_regex.groupindex.keys())
    with open(fname) as log:
        for line in log:
            line = color_regex.sub('', line)
            match = log_start_regex.match(line)
            if match:
                last_log_record = match.groupdict()
                log_records.append(last_log_record)
            else:
                last_log_record['message'] = '%s\n%s' % (
                    last_log_record['message'], line.rstrip('\n')
                )
    errors = []
    for log_record in log_records:
        ignore = False
        for ignore_pattern in errors_ignore:
            if ignore_pattern(log_record):
                ignore = True
                break
        if ignore:
            break
        for report_pattern in errors_report:
            if report_pattern(log_record):
                errors.append(log_record)
                break

    if check_loaded:
        if not [r for r in log_records if 'Modules loaded.' == r['message']]:
            errors.append({'message': "Modules loaded message not found."})

    if errors:
        for e in errors:
            print(e['message'])
        print("-"*10)
    return len(errors)


def parse_list(comma_sep_list):
    return [x.strip() for x in comma_sep_list.split(',') if x.strip()]


def str2bool(string):
    return str(string or '').lower() in ['1', 'true', 'yes']


def get_server_path(odoo_full, odoo_version, travis_home):
    """
    Calculate server path
    :param odoo_full: Odoo repository path
    :param odoo_version: Odoo version
    :param travis_home: Travis home directory
    :return: Server path
    """
    odoo_org, odoo_repo = odoo_full.split('/')
    server_dirname = "%s-%s" % (odoo_repo, odoo_version)
    server_path = os.path.join(travis_home, server_dirname)
    return server_path


def get_addons_path(travis_home, travis_build_dir, server_path):
    """
    Calculate addons path
    :param travis_home: Travis home directory
    :param travis_build_dir: Travis build directory
    :param server_path: Server path
    :return: Addons path
    """
    addons_path_list = get_addons(travis_home)
    addons_path_list.insert(0, travis_build_dir)
    addons_path_list.append(server_path + "/addons")
    addons_path_list.append(server_path + "/openerp/addons")
    addons_path = ','.join(addons_path_list)
    return addons_path


def get_addons_to_check(travis_build_dir, odoo_include, odoo_exclude):
    """
    Get the list of modules that need to be installed
    :param travis_build_dir: Travis build directory
    :param odoo_include: addons to include (travis parameter)
    :param odoo_exclude: addons to exclude (travis parameter)
    :return: List of addons to test
    """
    if odoo_include:
        addons_list = parse_list(odoo_include)
    else:
        addons_list = get_modules(travis_build_dir)

    if odoo_exclude:
        exclude_list = parse_list(odoo_exclude)
        addons_list = [
            x for x in addons_list
            if x not in exclude_list]
    return addons_list


def get_test_dependencies(addons_path, addons_list):
    """
    Get the list of core and external modules dependencies
    for the modules to test.
    :param addons_path: string with a comma separated list of addons paths
    :param addons_list: list of the modules to test
    """
    if not addons_list:
        return ['base']
    else:
        for path in addons_path.split(','):
            manif_path = is_module(os.path.join(path, addons_list[0]))
            if not manif_path:
                continue
            manif = eval(open(manif_path).read())
            return list(
                set(manif.get('depends', []))
                | set(get_test_dependencies(addons_path, addons_list[1:]))
                - set(addons_list))


def setup_server(db, odoo_unittest, tested_addons, server_path,
                 addons_path, install_options, preinstall_modules=None):
    """
    Setup the base module before running the tests
    :param db: Template database name
    :param odoo_unittest: Boolean for unit test (travis parameter)
    :param tested_addons: List of modules that need to be installed
    :param server_path: Server path
    :param travis_build_dir: path to the modules to be tested
    :param addons_path: Addons path
    :param install_options: Install options (travis parameter)
    """
    if preinstall_modules is None:
        preinstall_modules = ['base']
    print("\nCreating instance:")
    db_tmpl_created = False
    try:
        db_tmpl_created = subprocess.check_call(["createdb", db])
    except subprocess.CalledProcessError:
        db_tmpl_created = True

    if not db_tmpl_created:
        cmd_odoo = ["%s/openerp-server" % server_path,
                    "-d", db,
                    "--log-level=warn",
                    "--stop-after-init",
                    "--init", ','.join(preinstall_modules),
                    ] + install_options
        print(" ".join(cmd_odoo))
        subprocess.check_call(cmd_odoo)
    else:
        print("Using current openerp_template database.")
    return 0


def start_shippable_psql_service():
    if os.environ.get('TRAVIS', "false") != "true":
        subprocess.call(["shippable_start_service"])
        print("Waiting to start psql service...")
        while True:
            psql_subprocess = subprocess.Popen(
                ["psql", '-l'], stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)
            psql_subprocess.wait()
            if not bool(psql_subprocess.stderr.read()):
                break
            time.sleep(2)
        print("...psql service started.")
        try:
            subprocess.Popen([
                "psql", 'openerp_test', '-c',
                'REINDEX INDEX ir_translation_src_hash_idx'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)
        except BaseException:
            pass


def hidden_line(line):
    """Hidden line that no want show in log"""
    if "no translation for language" in line:
        # TODO: Add validation of module not in repo
        return True
    return False


def create_server_conf(data, version=None):
    '''Create default configuration file of odoo
    :params data: Dict with all info to save in file'''
    fname_conf = os.path.expanduser('~/.openerp_serverrc')
    print("Generating file: ", fname_conf)
    with open(fname_conf, "w") as fconf:
        fconf.write('[options]\n')
        for key, value in data.iteritems():
            fconf.write(key + ' = ' + os.path.expanduser(value) + '\n')
    print("Configuration file generated.")


def copy_attachments(dbtemplate, dbdest, data_dir):
    attach_dir = os.path.join(os.path.expanduser(data_dir), 'filestore')
    attach_tmpl_dir = os.path.join(attach_dir, dbtemplate)
    if os.path.isdir(attach_tmpl_dir):
        attach_dest_dir = os.path.join(attach_dir, dbdest)
        print("TODO: copy", attach_tmpl_dir, attach_dest_dir)


def main(argv=None):
    start_shippable_psql_service()
    if argv is None:
        argv = sys.argv
    travis_home = os.environ.get("HOME", "~/")
    travis_build_dir = os.environ.get("TRAVIS_BUILD_DIR", "../..")
    odoo_unittest = str2bool(os.environ.get("UNIT_TEST"))
    odoo_exclude = os.environ.get("EXCLUDE")
    odoo_include = os.environ.get("INCLUDE")
    options = os.environ.get("OPTIONS", "").split()
    install_options = os.environ.get("INSTALL_OPTIONS", "").split()
    expected_errors = int(os.environ.get("SERVER_EXPECTED_ERRORS", "0"))
    odoo_version = os.environ.get("VERSION")
    test_other_projects = parse_list(os.environ.get("TEST_OTHER_PROJECTS", ''))
    instance_alive = str2bool(os.environ.get('INSTANCE_ALIVE'))
    is_runbot = str2bool(os.environ.get('RUNBOT'))
    data_dir = os.environ.get("DATA_DIR", '~/data_dir')
    if not odoo_version:
        # For backward compatibility, take version from parameter
        # if it's not globally set
        odoo_version = argv[1]
        print("WARNING: no env variable set for VERSION. "
              "Using '%s'" % odoo_version)
    test_loghandler = None
    if odoo_version == "6.1":
        install_options += ["--test-disable"]
        test_loglevel = 'test'
    else:
        options += ["--test-enable"]
        if odoo_version == '7.0':
            test_loglevel = 'test'
        else:
            test_loglevel = 'info'
            test_loghandler = 'openerp.tools.yaml_import:DEBUG'
    odoo_full = os.environ.get("ODOO_REPO", "odoo/odoo")
    server_path = get_server_path(odoo_full, odoo_version, travis_home)
    addons_path = get_addons_path(travis_home, travis_build_dir, server_path)
    create_server_conf({
        'addons_path': addons_path,
        'data_dir': data_dir,
    }, odoo_version)
    tested_addons_list = get_addons_to_check(travis_build_dir,
                                             odoo_include,
                                             odoo_exclude)
    addons_path_list = parse_list(addons_path)
    all_depends = get_depends(addons_path_list, tested_addons_list)
    test_other_projects = map(
        lambda other_project: os.path.join(travis_home, other_project),
        test_other_projects)
    tested_addons = ','.join(tested_addons_list)

    print("Working in %s" % travis_build_dir)
    print("Using repo %s and addons path %s" % (odoo_full, addons_path))

    if not tested_addons:
        print("WARNING!\nNothing to test- exiting early.")
        return 0
    else:
        print("Modules to test: %s" % tested_addons)

    # setup the base module without running the tests
    dbtemplate = "openerp_template"
    preinstall_modules = get_test_dependencies(addons_path,
                                               tested_addons_list)
    preinstall_modules = list(
        set(preinstall_modules) - set(get_modules(travis_build_dir)))
    modules_other_projects = {}
    for test_other_project in test_other_projects:
        modules_other_projects[test_other_project] = get_modules(
            os.path.join(travis_home, test_other_project))
    main_projects = modules_other_projects.copy()
    main_projects[travis_build_dir] = get_modules(travis_build_dir)
    primary_modules = []
    for path, modules in main_projects.items():
        primary_modules.extend(modules)
    primary_modules = set(primary_modules) & all_depends

    primary_path_modules = {}
    for path, modules in main_projects.items():
        for module in modules:
            if module in primary_modules:
                primary_path_modules[module] = os.path.join(path, module)
    fname_coveragerc = ".coveragerc"
    if os.path.exists(fname_coveragerc):
        with open(fname_coveragerc) as fp_coveragerc:
            coverage_data = fp_coveragerc.read()
        with open(fname_coveragerc, "w") as fpw_coveragerc:
            fpw_coveragerc.write(coverage_data.replace(
                '    */build/*', '\t' +
                '/*\n\t'.join(primary_path_modules.values()) + '/*'
            ))
    secondary_addons_path_list = set(addons_path_list) - set(
        [travis_build_dir] + test_other_projects)
    secondary_modules = []
    for secondary_addons_path in secondary_addons_path_list:
        secondary_modules.extend(get_modules(secondary_addons_path))
    secondary_modules = set(secondary_modules) & all_depends
    secondary_depends_primary = []
    for secondary_module in secondary_modules:
        for secondary_depend in get_depends(
                addons_path_list, [secondary_module]):
            if secondary_depend in primary_modules:
                secondary_depends_primary.append(secondary_module)
    preinstall_modules = list(
        secondary_modules - set(secondary_depends_primary))

    print("Modules to preinstall: %s" % preinstall_modules)
    setup_server(dbtemplate, odoo_unittest, tested_addons, server_path,
                 addons_path, install_options, preinstall_modules)

    # Running tests
    database = "openerp_test"

    cmd_odoo_test = ["coverage", "run",
                     "%s/openerp-server" % server_path,
                     "-d", database,
                     "--stop-after-init",
                     "--log-level", test_loglevel,
                     ]

    if test_loghandler is not None:
        cmd_odoo_test += ['--log-handler', test_loghandler]
    cmd_odoo_test += options + ["--init", None]

    if odoo_unittest:
        to_test_list = tested_addons_list
        cmd_odoo_install = ["%s/openerp-server" % server_path,
                            "-d", database,
                            "--stop-after-init",
                            "--log-level=warn",
                            ] + install_options + ["--init", None]
        commands = ((cmd_odoo_install, False),
                    (cmd_odoo_test, True),
                    )
    else:
        to_test_list = [tested_addons]
        commands = ((cmd_odoo_test, True),
                    )
    all_errors = []
    counted_errors = 0
    for to_test in to_test_list:
        print("\nTesting %s:" % to_test)
        db_odoo_created = False
        try:
            db_odoo_created = subprocess.call(
                ["createdb", "-T", dbtemplate, database])
            copy_attachments(dbtemplate, database, data_dir)
        except subprocess.CalledProcessError:
            db_odoo_created = True
        for command, check_loaded in commands:
            if db_odoo_created and instance_alive:
                command_start = commands[0][0]
                rm_items = [
                    'coverage', 'run', '--stop-after-init',
                    '--test-enable', '--init', None,
                    '--log-handler', 'openerp.tools.yaml_import:DEBUG',
                ]
                for rm_item in rm_items:
                    try:
                        command_start.remove(rm_item)
                    except ValueError:
                        pass
                command_call = command_start + ['--db-filter=^%s$' % database]
            else:
                command[-1] = to_test
                if is_runbot:
                    command_call = []
                else:
                    # Run test command; unbuffer keeps output colors
                    command_call = ["unbuffer"]
                command_call += command
            print(' '.join(command_call))
            pipe = subprocess.Popen(command_call,
                                    stderr=subprocess.STDOUT,
                                    stdout=subprocess.PIPE)
            with open('stdout.log', 'w') as stdout:
                for line in pipe.stdout:
                    if hidden_line(line):
                        continue
                    stdout.write(line)
                    print(line.strip())
            returncode = pipe.wait()
            # Find errors, except from failed mails
            errors = has_test_errors(
                "stdout.log", database, odoo_version, check_loaded)
            if returncode != 0:
                all_errors.append(to_test)
                print(fail_msg, "Command exited with code %s" % returncode)
                # If not exists errors then
                # add an error when returcode!=0
                # because is really a error.
                if not errors:
                    errors += 1
            if errors:
                counted_errors += errors
                all_errors.append(to_test)
                print(fail_msg, "Found %d lines with errors" % errors)
        if not instance_alive:
            subprocess.call(["dropdb", database])

    print('Module test summary')
    for to_test in to_test_list:
        if to_test in all_errors:
            print(fail_msg, to_test)
        else:
            print(success_msg, to_test)
    if expected_errors and counted_errors != expected_errors:
        print("Expected %d errors, found %d!"
              % (expected_errors, counted_errors))
        return 1
    elif counted_errors != expected_errors:
        return 1
    # if we get here, all is OK
    return 0

if __name__ == '__main__':
    exit(main())
