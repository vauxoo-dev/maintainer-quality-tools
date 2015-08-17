# -*- coding: utf-8 -*-

import openerp

from openerp import api
from openerp.api import one


class ApiOne(object):
    @api.one
    def copy():
        pass


class One(object):
    @one
    def copy():
        pass


class OpenerpApiOne(object):
    @openerp.api.one
    def copy():
        pass


class WOApiOne(object):
    # copy without api.one decorator
    def copy():
        pass


class ApiOneMultiTogether(object):

    @api.multi
    @api.one
    def copy():
        pass
