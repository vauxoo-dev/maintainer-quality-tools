
from pylint.checkers import utils

from .. import settings, misc


OCA_MSGS = {
    # C->convention R->refactor W->warning E->error F->fatal

    # Visit py module
    'C%d01' % settings.BASE_PYMODULE_ID: (
        'No UTF-8 coding found: Use `# -*- coding: utf-8 -*-` '
        'in first or second line of your py file.',
        'no-utf8-coding-comment',
        'ToDo: Msg tmpl...'
    ),
}


class ModuleChecker(misc.WrapperModuleChecker):
    name = settings.CFG_SECTION
    msgs = OCA_MSGS

    @utils.check_messages(*(OCA_MSGS.keys()))
    def visit_module(self, node):
        self.wrapper_visit_module(node)

    def get_interpreter_and_coding(self):
        """Get '#!/bin' comment and '# -*- coding:' comment.
        :return: Return a tuple with two string
            (interpreter_bin, coding_comment)
            if not found then use empty string
        """
        interpreter_bin = ''
        coding_comment = ''
        with self.node.stream() as fstream:
            cont = 0
            for line in fstream:
                cont += 1
                if "#!" == line[:2]:
                    interpreter_bin = line.strip('\n')
                if "# -*- coding: " in line:
                    coding_comment = line.strip('\n')
                if cont == 2:
                    break
        return interpreter_bin, coding_comment

    def _check_no_utf8_coding_comment(self):
        'Check that the coding utf-8 comment exists'
        interpreter_bin, coding = self.get_interpreter_and_coding()
        if coding == '# -*- coding: utf-8 -*-':
            return True
        return False
