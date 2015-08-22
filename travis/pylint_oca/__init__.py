
from __future__ import absolute_import

from . import checkers


def register(linter):
    """Required method to auto register this checker"""
    linter.register_checker(checkers.modules.ModuleChecker(linter))
