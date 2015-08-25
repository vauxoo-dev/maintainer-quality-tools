
'''
Visit module to add odoo checks
'''

import os

from pylint.checkers import utils

from .. import misc, settings

OCA_MSGS = {
    # C->convention R->refactor W->warning E->error F->fatal

    # Visit odoo module with settings.BASE_OMODULE_ID
    'C%d02' % settings.BASE_OMODULE_ID: (
        'Missing ./README.rst file. Template here: %s',
        'missing-readme',
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


DFTL_README_TMPL_URL = 'https://github.com/OCA/maintainer-tools' + \
    '/blob/master/template/module/README.rst'


class ModuleChecker(misc.WrapperModuleChecker):
    name = settings.CFG_SECTION
    msgs = OCA_MSGS
    options = (
        ('readme_template_url', {
            'type': 'string',
            'metavar': '<string>',
            'default': DFTL_README_TMPL_URL,
            'help': 'URL of README.rst template file',
        }),
    )

    @utils.check_messages(*(OCA_MSGS.keys()))
    def visit_module(self, node):
        self.wrapper_visit_module(node)

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
