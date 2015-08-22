from pylint.checkers import utils

from pylint_oca import settings, misc

OCA_MSGS = {
    'C%d01' % settings.BASE_OMODULE_ID: (
        'Missing author required "%s"',
        'missing-required-author',
        'ToDo: Msg tmpl...',
    ),
}

DFTL_AUTHOR_REQUIRED = 'Odoo Community Association (OCA)'


class ModuleChecker(misc.WrapperModuleChecker):
    name = settings.CFG_SECTION
    options = (('manifest_author_required', {
        'type': 'string',
        'metavar': '<string>',
        'default': DFTL_AUTHOR_REQUIRED,
        'help': 'Name of author required in manifest file.'
        }),
    )

    @utils.check_messages(*(OCA_MSGS.keys()))
    def visit_module(self, node):
        import pdb
        pdb.set_trace()
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
