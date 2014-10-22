#!/usr/bin/env python
# coding: utf-8

"""
This module make custom fails to sourcecode of odoo modules.
"""

import logging
import os
import sys

import ast


def odoo_lint(dir_path):
    """
    Core method to check fails.
    @dir_path: Full path or relative path to *.py files to check
    """
    count_fails = 0
    for dirname, dummy, filenames in os.walk(dir_path):
        for filename in filenames:
            fext = os.path.splitext(filename)[1]
            if fext == '.py':
                fname_path = os.path.join(dirname, filename)
                try:
                    with open(fname_path) as fin:
                        parsed = ast.parse(fin.read())
                except SyntaxError:
                    parsed = False
                    # Syntax error is not a goal of fail for this script
                if parsed:
                    for node in ast.walk(parsed):
                        # Fail "print" sentence
                        if isinstance(node, ast.Print):
                            count_fails += 1
                            message = '{}:{}: [print sentence] "print" '\
                                      'sentence detected'\
                                      '\n'.format(fname_path, node.lineno)
                            sys.stdout.write(message)
    return count_fails


def main():
    """
    Main method to run core method
    """
    if len(sys.argv) == 2 and os.path.isdir(sys.argv[1]):
        return odoo_lint(sys.argv[1])
    else:
        logging.warning("First param should be directoy path to check")
        return -1

if __name__ == '__main__':
    exit(main())
