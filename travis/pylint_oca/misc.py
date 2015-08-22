
import os

from pylint.checkers import BaseChecker
from pylint.interfaces import IAstroidChecker

from . import settings


class WrapperModuleChecker(BaseChecker):

    __implements__ = IAstroidChecker

    node = None
    manifest_file = None
    manifest_dict = None
    msg_args = None
    msg_code = None
    msg_name_key = None

    def get_manifest_file(self, node_file):
        '''Return manifest file path
        :param node_file: String with full path of a python module file.
        :return: Full path of manifest file if exists else return None'''
        if os.path.basename(node_file) == '__init__.py':
            for manifest_basename in settings.MANIFEST_FILES:
                manifest_file = os.path.join(
                    os.path.dirname(node_file), manifest_basename)
                if os.path.isfile(manifest_file):
                    return manifest_file

    def get_manifest_dict(self):
        if self.manifest_file:
            with open(self.manifest_file, 'rb') as mfp:
                try:
                    manifest_dict = eval(mfp.read())
                    return manifest_dict
                except BaseException:  # Why can be any exception
                    return None

    def wrapper_visit_module(self, node):
        '''Call methods named with name-key from self.msgs
        Method should be named with next standard:
            def _check_{NAME_KEY}(self, module_path)
        by example: def _check_missing_icon(self, module_path)
                    to check missing-icon message name key
            And should return True if all fine else False.
        if a False is returned then add message of name-key.
        You can use `self.module_path` variable in those methods
            to get full path of odoo module directory.
        You can use `self.manifest_file` variable in those methods
            to get full path of MANIFEST_FILE found (__openerp__.py)
        You can use `self.manifest_content` variable in those methods
            to get full content of MANIFEST_FILE found.
        :param node: A astroid.scoped_nodes.Module
        :return: None
        '''
        self.manifest_file = self.get_manifest_file(node.file)
        self.manifest_dict = self.get_manifest_dict()
        self.node = node
        for msg_code, (title, name_key, description) in \
                sorted(self.msgs.iteritems()):
            self.msg_code = msg_code
            self.msg_name_key = name_key
            self.msg_args = None
            if not self.linter.is_message_enabled(msg_code):
                continue
            check_method = getattr(
                self, '_check_' + name_key.replace('-', '_'),
                None)
            if callable(check_method):
                if not check_method():
                    self.add_message(msg_code, node=node,
                                     args=self.msg_args)
