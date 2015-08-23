
import os

from pylint.checkers import utils

from .. import settings, misc


OCA_MSGS = {
    # C->convention R->refactor W->warning E->error F->fatal

    # Visit py module
    'C%d01' % settings.BASE_PYMODULE_ID: (
        'No UTF-8 coding found: Use `# -*- coding: utf-8 -*-` '
        'in first or second line.',
        'no-utf8-coding-comment',
        settings.DESC_DFLT
    ),
    'W%d01' % settings.BASE_PYMODULE_ID: (
        'Incoherent interpreter comment and executable permission. '
        'Interpreter: [%s] Exec perm: %s',
        'incoherent-interpreter-exec-perm',
        settings.DESC_DFLT
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

    def _check_incoherent_interpreter_exec_perm(self):
        'Check coherence of interpreter comment vs executable permission'
        interpreter_bin, coding = self.get_interpreter_and_coding()
        access_x_ok = os.access(self.node.file, os.X_OK)
        self.msg_args = (interpreter_bin, access_x_ok)
        return bool(interpreter_bin) == access_x_ok
