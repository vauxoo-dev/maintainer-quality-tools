from openerp.osv import orm, fields


class test_model(orm.Model):
    _name = "test.model"
    _columns = {
        'name': fields.char('Title', 100),
    }
