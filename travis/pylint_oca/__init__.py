
from . import checkers


def register(linter):
    """Required method to auto register this checker"""
    linter.register_checker(checkers.modules_odoo.ModuleChecker(linter))
    linter.register_checker(checkers.no_modules.NoModuleChecker(linter))
    linter.register_checker(checkers.format.FormatChecker(linter))
    linter.register_checker(checkers.base.CustomBasicChecker(linter))
