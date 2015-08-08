#!/usr/bin/env python
# coding: utf-8

from __future__ import print_function

import os
import subprocess
import sys

from test_server import get_default_server_path
from getaddons import get_addons, get_modules
from sys_propagate_test import sys_propagate_test


def run_pylint(paths_to_check, conf_file,
               odoo_path=None, addons_path=None):
    """
    Execute pylint command with extra parameters.
    :param paths_to_check: List of paths to check pylint.
        pylint will include recursive childs paths.
    :param conf_file: String with file name of config file to use.
    :param odoo_path: String of odoo path to check `import openerp*`
    :param addons_path: String of all addons paths separated by comma
   """
    if isinstance(paths_to_check, basestring):
        paths_to_check = [paths_to_check]
    # local_env = os.environ
    # local_env.setdefault('PYTHONPATH', '')
    # local_env['PYTHONPATH'] += os.pathsep + odoo_path
    # print("local_env", local_env['PYTHONPATH'])
    # todo: Add support to work with import openerp.addons
    command = ['pylint', '--rcfile=' + conf_file] # + paths_to_check
    # command = ['unbuffer'] + command
    # print("command:", ' '.join(command))
    # pipe = subprocess.Popen(
    #    command,
    #    stderr=subprocess.STDOUT,
    #    stdout=subprocess.PIPE,
    #    env=local_env)
    # with open('pylint_stdout.log', 'w') as stdout:
    #    for line in pipe.stdout:
    #        stdout.write(line)
    #        print(line.strip())
    #returncode = pipe.wait()
    #return returncode
    # sys.argv = command
    # os.environ = local_env
    # os.putenv('PYTHONPATH', odoo_path)
    from addons_import_hook import initialize_sys_path
    initialize_sys_path(addons_path)
    # command.append('--init-hook="from addons_import_hook import initialize_sys_path;initialize_sys_path(%s);import sys;print(sorted(sys.modules.keys()))"'%(addons_path))
    command.append('--init-hook=import sys;print(sorted(sys.modules.keys()))')
    command.extend(paths_to_check)
    sys.argv = command
    print("sys.argv: ", ' '.join(sys.argv))
    # __import__('openerp.addons.sale')
    from pylint import run_pylint
    run_pylint()


def setup_server_symlink(symlink_path, server_path,
                         addons_paths=None):
    """
    Setup server with symlinks to allow execute
    `from openerp.addons import {MODULE_OTHER_PATH}` with pylint.
    We can't to use `sys.modules` in pylint because by next issue:
        https://bitbucket.org/logilab/pylint/issues/616/modules-renamed-with-sysmodules-are-unable
    But we can use symlink to work with this case
    """

def main():
    conf_file = os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        'cfg',
        "travis_run_pylint.cfg")
    paths_to_check = os.environ['TRAVIS_BUILD_DIR']
    paths_to_check += '/' + 'website_variants_extra'
    odoo_path = get_default_server_path()
    addons_path = get_addons(os.environ['HOME']) + \
        get_addons(os.environ['TRAVIS_BUILD_DIR']) + \
        get_addons(os.path.join(odoo_path, 'addons')) + \
        get_addons(os.path.join(odoo_path, 'openerp', 'addons'))
    sys.path.append(odoo_path)

    # import pdb;pdb.set_trace()
    res = run_pylint(paths_to_check, conf_file, odoo_path, addons_path)
    return res

if __name__ == '__main__':
    exit(main())

