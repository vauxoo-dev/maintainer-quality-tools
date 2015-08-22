
'''
Visit module to add odoo checks
'''

import os

from pylint.checkers import utils

from .. import misc, settings

OCA_MSGS = {
    # C->convention R->refactor W->warning E->error F->fatal

    # Visit odoo module with settings.BASE_OMODULE_ID
    'C%d01' % settings.BASE_OMODULE_ID: (
        'Missing author required "%s"',
        'missing-required-author',
        settings.DESC_DFLT
    ),
    'C%d02' % settings.BASE_OMODULE_ID: (
        'Missing ./README.rst file. Template here: %s',
        'missing-readme',
        settings.DESC_DFLT
    ),
    'C%d03' % settings.BASE_OMODULE_ID: (
        'Missing required %s keys in manifest file',
        'manifest-missing-key',
        settings.DESC_DFLT
    ),
    'C%d04' % settings.BASE_OMODULE_ID: (
        'Deprecated description in manifest file',
        'deprecated-description',
        settings.DESC_DFLT
    ),
    'E%d01' % settings.BASE_OMODULE_ID: (
        'RST syntax error %s',
        'rst-syntax-error',
        settings.DESC_DFLT
    ),
    'W%d01' % settings.BASE_OMODULE_ID: (
        'Dangerous filter without explicit `user_id` in xml_id %s',
        'dangerous-filter-wo-user',
        settings.DESC_DFLT
    ),
    'W%d02' % settings.BASE_OMODULE_ID: (
        'Duplicate xml record id %s',
        'duplicate-xml-record-id',
        settings.DESC_DFLT
    ),
}


DFTL_AUTHOR_REQUIRED = 'Odoo Community Association (OCA)'
DFTL_README_TMPL_URL = 'https://github.com/OCA/maintainer-tools' + \
    '/blob/master/template/module/README.rst'
DFTL_MANIFEST_REQUIRED_KEYS = ['license']


class ModuleChecker(misc.WrapperModuleChecker):
    name = settings.CFG_SECTION
    msgs = OCA_MSGS
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
            'default': DFTL_MANIFEST_REQUIRED_KEYS,
            'help': 'List of keys required in manifest ' +
                    'odoo file __openerp__.py, ' +
                    'separated by a comma.'
        }),
    )

    @utils.check_messages(*(OCA_MSGS.keys()))
    def visit_module(self, node):
        self.wrapper_visit_module(node)

    def _check_missing_required_author(self):
        '''Check if manifest file has required author
        :return: True if is found else False'''
        if not self.manifest_dict:
            return True
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

    def _check_deprecated_description(self):
        '''Check if deprecated description is defined in manifest file
        :return: False if is defined else True
        '''
        return 'description' not in self.manifest_dict \
            if self.manifest_dict else True

    def _check_duplicate_xml_record_id(self):
        all_xml_ids = []
        for xml_file in self.filter_files_ext('xml', relpath=False):
            all_xml_ids.extend(self.get_xml_record_ids(xml_file, self.module))
        duplicated_xml_ids = self.get_duplicated_items(all_xml_ids)
        if duplicated_xml_ids:
            self.msg_args = (duplicated_xml_ids,)
            return False
        return True

    def _check_dangerous_filter_wo_user(self):
        xml_files = self.filter_files_ext('xml')
        for xml_file in xml_files:
            ir_filter_records = self.get_xml_records(
                os.path.join(self.module_path, xml_file), model='ir.filters')
            for ir_filter_record in ir_filter_records:
                ir_filter_fields = ir_filter_record.xpath(
                    "field[@name='name' or @name='user_id']")
                # if exists field="name" then is a new record
                # then should be field="user_id" too
                if ir_filter_fields and len(ir_filter_fields) == 1:
                    self.msg_args = (
                        xml_file + ':' + ir_filter_record.get('id'),)
                    return False
        return True
