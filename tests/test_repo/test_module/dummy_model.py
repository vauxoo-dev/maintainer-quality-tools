# -*- coding: utf-8 -*-

from openerp.osv import fields, orm
import sys

try:
    from openerp.exceptions import Warning as UserError
except ImportError:
    UserError = None


class DummyModel(orm.Model):
    # expect "no access rules" error
    _name = 'dummy.model'
    _columns = {
        'name': fields.char('Dummy', size=100),
    }

    def using_user_error(self):
        return UserError


# printout non-ASCII text to check unicode issues
# (from Monty Python's "Italian Lesson"...)
sys.stdout.write("Eeeeeee! Milano è tanto meglio di Napoli. "
                 "Milano è la citta la più bella di tutti ... nel mondo...\n")
