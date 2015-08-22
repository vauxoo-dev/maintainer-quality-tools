
'''
Enable checkers to visit all nodes different to modules.
You can use:
    visit_arguments
    visit_assattr
    visit_assert
    visit_assign
    visit_assname
    visit_backquote
    visit_binop
    visit_boolop
    visit_break
    visit_callfunc
    visit_class
    visit_compare
    visit_continue
    visit_default
    visit_delattr
    visit_delname
    visit_dict
    visit_dictcomp
    visit_discard
    visit_excepthandler
    visit_exec
    visit_extslice
    visit_for
    visit_from
    visit_function
    visit_genexpr
    visit_getattr
    visit_global
    visit_if
    visit_ifexp
    visit_import
    visit_index
    visit_lambda
    visit_listcomp
    visit_name
    visit_pass
    visit_print
    visit_project
    visit_raise
    visit_return
    visit_setcomp
    visit_slice
    visit_subscript
    visit_tryexcept
    visit_tryfinally
    visit_unaryop
    visit_while
    visit_yield
for more info visit pylint doc
'''

from pylint.checkers import BaseChecker, utils
from pylint.interfaces import IAstroidChecker

from .. import settings

OCA_MSGS = {
    # C->convention R->refactor W->warning E->error F->fatal

    'R%d01' % settings.BASE_NOMODULE_ID: (
        'Import `Warning` should be renamed as UserError '
        '`from openerp.exceptions import Warning as UserError`',
        'openerp-exception-warning',
        settings.DESC_DFLT
    ),
    'W%d01' % settings.BASE_NOMODULE_ID: (
        'Detected api.one and api.multi decorators together.',
        'api-one-multi-together',
        settings.DESC_DFLT
    ),
    'W%d02' % settings.BASE_NOMODULE_ID: (
        'Missing api.one in copy function.',
        'copy-wo-api-one',
        settings.DESC_DFLT
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
