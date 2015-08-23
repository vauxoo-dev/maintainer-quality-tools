
from pylint.checkers import BaseChecker, utils
from pylint.interfaces import IAstroidChecker

from .. import settings


OCA_MSGS = {
    # C->convention R->refactor W->warning E->error F->fatal

    'R%d01' % settings.BASE_NOMODULE_ID: (
        'Import `Warning` should be renamed as UserError '
        '`from openerp.exceptions import Warning as UserError`',
        'openerp-exception-warning',
        'ToDo: Msg tmpl...'
    ),
    'W%d01' % settings.BASE_NOMODULE_ID: (
        'Detected api.one and api.multi decorators together.',
        'api-one-multi-together',
        'ToDo: Msg tmpl...'
    ),
    'W%d02' % settings.BASE_NOMODULE_ID: (
        'Missing api.one in copy function.',
        'copy-wo-api-one',
        'ToDo: Msg tmpl...'
    ),
}


class NoModuleChecker(BaseChecker):

    __implements__ = IAstroidChecker

    name = settings.CFG_SECTION
    msgs = OCA_MSGS

    @utils.check_messages('api-one-multi-together',
                          'copy-wo-api-one')
    def visit_function(self, node):
        '''Check that `api.one` and `api.multi` decorators not exists together
        Check that method `copy` exists `api.one` decorator
        '''
        decor_names = self.get_decorators_names(node.decorators)
        decor_lastnames = [
            decor.split('.')[-1]
            for decor in decor_names]
        if self.linter.is_message_enabled('api-one-multi-together'):
            if 'one' in decor_lastnames \
                    and 'multi' in decor_lastnames:
                self.add_message('api-one-multi-together',
                                 node=node)

        if self.linter.is_message_enabled('copy-wo-api-one'):
            if 'copy' == node.name and 'one' not in decor_lastnames:
                self.add_message('copy-wo-api-one', node=node)

    @utils.check_messages('openerp-exception-warning')
    def visit_from(self, node):
        if node.modname == 'openerp.exceptions':
            for (import_name, import_as_name) in node.names:
                if import_name == 'Warning' \
                        and import_as_name != 'UserError':
                    self.add_message(
                        'openerp-exception-warning', node=node)

    def get_decorators_names(self, decorators):
        nodes = []
        if decorators:
            nodes = decorators.nodes
        return [getattr(decorator, 'attrname', '')
                for decorator in nodes if decorator is not None]
