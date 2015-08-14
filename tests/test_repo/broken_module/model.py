
from openerp.osv import orm, fields

import os
import os  # W0404 - duplicated import

import __openerp__  # W0403 - relative import

# w0402 - deprecated module
import pdb, pudb, ipdb  #pylint: disable=W0403

class test_model(orm.Model):
    _name = "test.model"
    _columns = {
        'name': fields.char('Title', 100),
    }

    def __init__(self):
        return 'E0101'

    def method_test(self, arg1, arg2):
        return None

    def method_e1124(self):
        value = self.method_test(
            'arg_param1', arg1='arg_param1')
        return value

    def method_e1306(self):
        return "%s %s"%('value1')

    def method_e1601(self):
        print "Hello world!"

    def method_w0101(self):
        return True
        return False

    def method_w0102(self, arg1, arg2=[]):
        pass

    def method_w0104_w0105(self):
        any_effect
        "str any effect"

    def method_w0109(self):
        my_duplicated_key_dict = {
            'key1': 'value1',
            'key2': 'value2',
            'key1': 'value3',
        }

    def method_w1401(self):
        my_str = r'\d'


def method_w1111(self):
    return None


VAR1 = method_w1111()
