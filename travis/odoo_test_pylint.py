#!/usr/bin/env python
# coding: utf-8

from __future__ import print_function

import os
import subprocess

from test_server import get_default_server_path


def run_pylint(paths_to_check, conf_file, odoo_path=None):
    """
    Execute pylint command with extra parameters.
    :param paths_to_check: List of paths to check pylint.
        pylint will include recursive childs paths.
    :param conf_file: String with file name of config file to use.
    :param odoo_path: String of odoo path to check `import openerp*`
    """
    if isinstance(paths_to_check, basestring):
        paths_to_check = [paths_to_check]
    local_env = os.environ
    local_env.setdefault('PYTHONPATH', '')
    local_env['PYTHONPATH'] += os.pathsep + odoo_path
    print("local_env", local_env['PYTHONPATH'])
    # todo: Add support to work with import openerp.addons
    command = ['pylint', '--rcfile=' + conf_file] + paths_to_check
    command = ['unbuffer'] + command
    print("command:", ' '.join(command))
    pipe = subprocess.Popen(
        command,
        stderr=subprocess.STDOUT,
        stdout=subprocess.PIPE,
        env=local_env)
    with open('pylint_stdout.log', 'w') as stdout:
        for line in pipe.stdout:
            stdout.write(line)
            print(line.strip())
    returncode = pipe.wait()
    return returncode


def main():
    conf_file = os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        'cfg',
        "travis_run_pylint.cfg")
    paths_to_check = os.environ['TRAVIS_BUILD_DIR']
    paths_to_check += '/' + 'website_customer_also_purchased'

    odoo_path = get_default_server_path()
    res = run_pylint(paths_to_check, conf_file, odoo_path)
    return res

if __name__ == '__main__':
    exit(main())
