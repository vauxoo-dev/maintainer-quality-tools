from openerp.osv import orm, fields


class test_model(orm.Model):
    _name = "test.model"
    _columns = {
        'name': fields.char('Title', 100),
    }

    def __init__(self):
        return None

    def method_test(self, param1, param2):
        pass

    def method_e1124(self):
        self.method1('value_param1', param1='value_param1')

    def method_e1306(self):
        return "%s %s"%('value1')

