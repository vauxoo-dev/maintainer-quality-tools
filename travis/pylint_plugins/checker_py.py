
from pylint.interfaces import IAstroidChecker
from pylint.checkers import BaseChecker
from pylint.checkers import utils


'''
Module to add custom python checkers to odoo guidelines.
This module can to visit all astroid nodes.
'''


class PyAstroidChecker(BaseChecker):

    __implements__ = IAstroidChecker

    name = 'odoolintpy'

    msgs ={
        'EO510': (
            'Missing coding comment',
            'missing-coding-comment',
            'More info here: '
            'https://www.python.org/dev/peps/pep-0263/'
        ),
        'EO520': (
            'No UTF-8 coding found: Use `# -*- coding: utf-8 -*-` '
            'in first or second line of your file.',
            'no-utf8-coding',
            'Check guidelines of contribution',
        )
    }

    @utils.check_messages('EO510', 'EO520')
    def visit_module(self, node):
        '''
        Visit module to check other py files different to __init__.py
        '''
        coding_found = False
        coding_utf8_found = False
        for line in node.file_stream.readlines()[:2]:
            if '# -*- coding: utf-8 -*-' in line:
                coding_utf8_found = True
            elif '# -*- coding:' in line:
                coding_found = True
        if not coding_found:
            self.add_message('EO510', node=node)
        elif not coding_utf8_found:
            self.add_message('EO520', node=node)
