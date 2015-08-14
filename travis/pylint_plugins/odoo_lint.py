# ~/.local/lib/python2.7/site-packages/odoolint.py

import os

from pylint.interfaces import IAstroidChecker
from pylint.checkers import BaseChecker
from pylint.checkers import utils


MANIFEST_FILES = ['__odoo__.py', '__openerp__.py', '__terp__.py']
ODOO_MODULE_MSGS = {
    # Using prefix EO for errors
    #  and WO for warnings from odoo_lint
    'WO100': (
        'Missing icon',
        'missing-icon',
        'Your odoo module should be a icon image '
        'in subfolder ./static/description/icon.png',
    ),
}


class OdooLintAstroidChecker(BaseChecker):

    __implements__ = IAstroidChecker

    name = 'odoo_lint'

    msgs = ODOO_MODULE_MSGS

    def is_odoo_module(self, module_file):
        '''Check if directory of py module is a odoo module too.
        if exists a MANIFEST_FILES is a odoo module.
        :param module_file: String with full path of a
            python module file.
            If is a folder py module then will receive
                `__init__.py file path.
            A normal py file is a module too.
        :return: True if is a odoo module else False
        '''
        return os.path.basename(module_file) == '__init__.py' and \
            any([
                filename
                for filename in os.listdir(
                    os.path.dirname(module_file))
                if filename in MANIFEST_FILES
            ])

    @utils.check_messages(*(ODOO_MODULE_MSGS.keys()))
    def visit_module(self, node):
        '''
        Call methods named with name_key from ODOO_MODULE_MSGS
        Method should be named with next standard:
            def _check_{MSG_NAME_KEY}(self, module_path)
        by example: def _check_missing_icon(self, module_path)
                    to check missing-icon message name key
        And should return True if all fine else False.
        If is false then method of pylint add_message will invoke
        :param node: A astroid.scoped_nodes.Module from visit*
            standard method of pylint.
        :return: None
        '''
        if self.is_odoo_module(node.file):
            for msg_code, (title, name_key, description) in \
                    ODOO_MODULE_MSGS.iteritems():
                check_method = getattr(
                    self, '_check_' + name_key.replace('-', '_'))
                if not check_method(os.path.dirname(node.file)):
                    self.add_message('missing-icon', node=node)

    def _check_missing_icon(self, odoo_module_path):
        """Check if a odoo module has a icon image
        :param odoo_module_path: Full path directory of odoo module
        :return: True if icon is found else False.
        """
        icon_path = os.path.join(
            odoo_module_path, 'static', 'description', 'icon.png')
        return os.path.exists(icon_path)


def register(linter):
    """Required method to auto register this checker"""
    linter.register_checker(OdooLintAstroidChecker(linter))
