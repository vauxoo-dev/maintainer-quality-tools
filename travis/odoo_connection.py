"""
Odoo connection classes which describe how to connect to odoo to export PO
files.
One class per version is defined and mapped in context_mapping.
To add a new version, create a subclass of _OdooBaseContext with name
OdooXContext, implement __enter__ and add to context_mapping.
"""

import inspect
import sys
from contextlib import closing
from cStringIO import StringIO


class _OdooBaseContext(object):
    """
    Abstract class for odoo connections and translation export without
    version specification.
    Inherit from this class to implement version specific connection
    parameters.
    """

    def __init__(self, server_path, addons_path, dbname):
        """
        Create context object. Stock odoo server path and database name.
        :param str server_path: path to odoo root
        :param str addons_path: comma separated list of addon paths
        :param str dbname: database name with odoo installation
        """
        self.server_path = server_path
        self.addons_path = addons_path
        self.dbname = dbname
        self.cr = None

    def __enter__(self):
        raise NotImplementedError("The class %s is an abstract class which"
                                  "doesn't have __enter__ implemented."
                                  % self.__class__.__name__)

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Cleanly close cursor
        """
        if self.cr is not None:
            self.cr.close()

    def get_pot_contents(self, addon, lang=None):
        """
        Export source translation files from addon.
        :param str addon: Addon name
        :returns str: Gettext from addon .pot content
        """
        with closing(StringIO()) as buf:
            self.trans_export(lang, [addon], buf, 'po', self.cr)
            return buf.getvalue()

    def load_po(self, po, lang):
        self.trans_load_data(self.cr, po, 'po', lang)

    def create_db(self, db_name, demo, lang, country_code=None):
        """Wrapper method of odoo.service.db
        8.0 - exp_create_database(db_name, demo, lang, user_password='admin')
        9.0 - exp_create_database(db_name, demo, lang, user_password='admin',
                                  login='admin', country_code=None)
        10.0 - exp_create_database(db_name, demo, lang, user_password='admin',
                                   login='admin', country_code=None)
        """
        extra_kwargs = {
            'db_name': db_name,
            'demo': demo,
            'lang': lang,
        }
        if 'country_code' in inspect.getargs(self.exp_create_database.func_code
                                             ).args:
            extra_kwargs['country_code'] = country_code
        try:
            self.exp_create_database(**extra_kwargs)
            return False
        except self.DatabaseExists:
            return True

    def duplicate_db(self, db_original_name, db_name):
        self.exp_duplicate_database(db_original_name, db_name)


class Odoo10Context(_OdooBaseContext):
    """A context for connecting to a odoo 10 server with function to export
    .pot files.
    """

    def __enter__(self):
        """
        Context enter function.
        Temporarily add odoo 10 server path to system path and pop afterwards.
        Import odoo 10 server from path as library.
        Init logger, registry and environment.
        Add addons path to config.
        :returns Odoo10Context: This instance
        """
        sys.path.append(self.server_path)
        from odoo import netsvc, api
        from odoo.modules.registry import RegistryManager
        from odoo.tools import trans_export, config, trans_load_data
        from openerp.service.db import (exp_create_database, DatabaseExists,
                                        exp_duplicate_database)
        self.trans_export = trans_export
        self.trans_load_data = trans_load_data
        self.exp_duplicate_database = exp_duplicate_database
        self.exp_create_database = exp_create_database
        self.DatabaseExists = DatabaseExists
        sys.path.pop()
        netsvc.init_logger()
        config['addons_path'] = (
            config.get('addons_path') + ',' + self.addons_path
        )
        if self.dbname:
            registry = RegistryManager.new(self.dbname)
            self.cr = registry.cursor()
        self.environment_manage = api.Environment.manage()
        self.environment_manage.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Context exit function.
        Cleanly close environment manage and cursor.
        """
        self.environment_manage.__exit__(exc_type, exc_val, exc_tb)
        super(Odoo10Context, self).__exit__(exc_type, exc_val, exc_tb)


class Odoo8Context(_OdooBaseContext):
    """
    A context for connecting to a odoo 8 server with function to export .pot
    """

    def __enter__(self):
        """
        Context enter function.
        Temporarily add odoo 8 server path to system path and pop afterwards.
        Import odoo 8 server from path as library.
        Init logger, registry and environment.
        Add addons path to config.
        :returns Odoo8Context: This instance
        """
        sys.path.append(self.server_path)
        from openerp import netsvc, api
        from openerp.modules.registry import RegistryManager
        from openerp.tools import trans_export, config, trans_load_data
        from openerp.service.db import (exp_create_database, DatabaseExists,
                                        exp_duplicate_database)
        self.trans_export = trans_export
        self.trans_load_data = trans_load_data
        self.exp_create_database = exp_create_database
        self.exp_duplicate_database = exp_duplicate_database
        self.DatabaseExists = DatabaseExists
        sys.path.pop()
        netsvc.init_logger()
        config['addons_path'] = (
            config.get('addons_path') + ',' + self.addons_path
        )
        if self.dbname:
            registry = RegistryManager.new(self.dbname)
            self.cr = registry.cursor()
        self.environment_manage = api.Environment.manage()
        self.environment_manage.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Context exit function.
        Cleanly close environment manage and cursor.
        """
        self.environment_manage.__exit__(exc_type, exc_val, exc_tb)
        super(Odoo8Context, self).__exit__(exc_type, exc_val, exc_tb)


class Odoo7Context(_OdooBaseContext):
    """
    A context for connecting to a odoo 7 server with function to export .pot
    """

    def __enter__(self):
        """
        Context enter function.
        Temporarily add odoo 7 server path to system path and pop afterwards.
        Import odoo 7 server from path as library.
        Init logger and pool.
        Add addons path to config.
        :returns Odoo8Context: This instance
        """
        sys.path.append(self.server_path)
        from openerp import netsvc
        from openerp.tools import trans_export, config, trans_load_data
        from openerp.pooler import get_db
        from openerp.service.web_services import db
        self.trans_export = trans_export
        self.trans_load_data = trans_load_data
        db_obj = db(self.dbname)
        self.exp_create_database = db_obj.exp_create_database
        self.exp_duplicate_database = db_obj.exp_duplicate_database
        self.DatabaseExists = BaseException
        sys.path.pop()
        netsvc.init_logger()
        config['addons_path'] = str(
            config.get('addons_path') + ',' + self.addons_path
        )
        if self.dbname:
            self.cr = get_db(self.dbname).cursor()
        return self


context_mapping = {
    "7.0": Odoo7Context,
    "8.0": Odoo8Context,
    "9.0": Odoo8Context,
    "10.0": Odoo10Context,
}
