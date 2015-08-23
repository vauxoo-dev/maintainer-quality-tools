
import os

from pylint.checkers import utils

from .. import settings, misc


OCA_MSGS = {
    # C->convention R->refactor W->warning E->error F->fatal

    # Visit odoo module with settings.BASE_OMODULE_ID
    'C%d01' % settings.BASE_OMODULE_ID: (
        'Missing author required "%s"',
        'missing-required-author',
        'ToDo: Msg tmpl...'
    ),
    'C%d02' % settings.BASE_OMODULE_ID: (
        'Missing ./README.rst file. Template here: %s',
        'missing-readme',
        'ToDo: Msg tmpl...'
    ),
    'C%d03' % settings.BASE_OMODULE_ID: (
        'Missing required %s keys in manifest file',
        'manifest-missing-key',
        'ToDo: Msg tmpl...'
    ),
    'E%d01' % settings.BASE_OMODULE_ID: (
        'RST syntax error %s',
        'rst-syntax-error',
        'ToDo: Msg tmpl...'
    ),
}


DFTL_AUTHOR_REQUIRED = 'Odoo Community Association (OCA)'
DFTL_README_TMPL_URL = 'https://github.com/OCA/maintainer-tools' + \
    '/blob/master/template/module/README.rst'
DFTL_MANIFEST_REQUIRED_KEYS = ['license']


class ModuleChecker(misc.WrapperModuleChecker):
    name = settings.CFG_SECTION
    options = (
        ('manifest_author_required', {
            'type': 'string',
            'metavar': '<string>',
            'default': DFTL_AUTHOR_REQUIRED,
            'help': 'Name of author required in manifest file.'
        }),
        ('readme_template_url', {
            'type': 'string',
            'metavar': '<string>',
            'default': DFTL_README_TMPL_URL,
            'help': 'URL of README.rst template file',
        }),
        ('manifest_required_keys', {
            'type': 'csv',
            'metavar': '<comma separated values>',
            'default': DFLT_MANIFEST_REQUIRED_KEYS,
            'help': 'List of keys required in manifest ' +
                    'odoo file __openerp__.py, ' +
                    'separated by a comma.'
        }),
    )
    msgs = OCA_MSGS

    @utils.check_messages(*(OCA_MSGS.keys()))
    def visit_module(self, node):
        self.wrapper_visit_module(node)

    def _check_missing_required_author(self):
        '''Check if manifest file has required author
        :return: True if is found else False'''
        authors = self.manifest_dict.get('author', '').split(',')
        author_required = self.config.manifest_author_required
        for author in authors:
            if author_required in author:
                return True
        self.msg_args = (author_required,)
        return False

    def _check_rst_syntax_error(self):
        '''Check if rst file has syntax error
        :return: False if exists errors and
                 add list of errors in self.msg_args
        '''
        rst_files = self.filter_files_ext('rst')
        self.msg_args = []
        for rst_file in rst_files:
            errors = self.check_rst_syntax(
                os.path.join(self.module_path, rst_file))
            if errors:
                self.msg_args.append(
                    "{rst_file} {errors}".format(
                        rst_file=rst_file, errors=errors))
        if self.msg_args:
            return False
        return True

    def _check_missing_readme(self):
        '''Check if exists ./README.rst file
        :return: If exists return True else False
        '''
        self.msg_args = (self.config.readme_template_url,)
        return os.path.isfile(os.path.join(self.module_path, 'README.rst'))

    def _check_manifest_missing_key(self):
        '''Check if a required key is missing in manifest file
        :return: False if key required is missing else True
        '''
        if not self.manifest_dict:
            return True
        required_keys = self.config.manifest_required_keys
        self.msg_args = (required_keys,)
        return set(required_keys).issubset(
            set(self.manifest_dict.keys()))
