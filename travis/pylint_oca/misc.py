
import os
import subprocess

from pylint.checkers import BaseChecker
from pylint.interfaces import IAstroidChecker

from . import settings


class WrapperModuleChecker(BaseChecker):

    __implements__ = IAstroidChecker

    node = None
    manifest_file = None
    manifest_dict = None
    module_path = None
    msg_args = None
    msg_code = None
    msg_name_key = None

    def get_manifest_file(self, node_file):
        '''Get manifest file path
        :param node_file: String with full path of a python module file.
        :return: Full path of manifest file if exists else return None'''
        if os.path.basename(node_file) == '__init__.py':
            for manifest_basename in settings.MANIFEST_FILES:
                manifest_file = os.path.join(
                    os.path.dirname(node_file), manifest_basename)
                if os.path.isfile(manifest_file):
                    return manifest_file

    def get_manifest_dict(self):
        '''Get manifest dict object
        if self.manifest_file is assigned then read it and transform to dict
        :return: Dict object with content of manifest file.
        '''
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
        Assign object variables to use in methods.
        :param node: A astroid.scoped_nodes.Module
        :return: None
        '''
        self.manifest_file = self.get_manifest_file(node.file)
        self.manifest_dict = self.get_manifest_dict()
        self.node = node
        self.module_path = os.path.dirname(node.file)
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
            is_odoo_check = self.manifest_file and \
                msg_code[1:3] == str(settings.BASE_OMODULE_ID)
            is_py_check = msg_code[1:3] == str(settings.BASE_PYMODULE_ID)
            if callable(check_method) and (is_odoo_check or is_py_check):
                if not check_method():
                    if not isinstance(self.msg_args, list):
                        self.msg_args = [self.msg_args]
                    for msg_args in self.msg_args:
                        self.add_message(msg_code, node=node,
                                         args=msg_args)

    def filter_files_ext(self, fext):
        '''Filter files of odoo modules with a file extension.
        :param fext: Extension name of files to filter.
        :return: List of relative path of files matched
                 with extension fext.
        '''
        if not fext.startswith('.'):
            fext = '.' + fext
        fnames_filtered = []
        if not self.manifest_file:
            return fnames_filtered

        for root, dirnames, filenames in os.walk(
                self.module_path, followlinks=True):
            for filename in filenames:
                if os.path.splitext(filename)[1] == fext:
                    fnames_filtered.append(os.path.relpath(
                        os.path.join(root, filename), self.module_path))
        return fnames_filtered

    def check_rst_syntax(self, fname):
        '''Check syntax in rst files.
        :param fname: String with file name path to check
        :return: Return errors. Empty string if not errors. 
        '''
        cmd = ['rst2html.py', fname, '/dev/null', '-r', '1']
        errors = subprocess.Popen(
            cmd, stderr=subprocess.STDOUT,
            stdout=subprocess.PIPE).stdout.read()
        return errors