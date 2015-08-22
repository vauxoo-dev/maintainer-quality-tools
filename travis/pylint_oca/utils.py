

class BaseModuleChecker(BaseChecker):

    __implements__ = IAstroidChecker

    name = 'oca-module-checker'

    def __init__(self, linter=None):
        super(BaseModelChecker).__init__(linter)

    def is_odoo_module(self, module_file):
        '''Check if directory of py module is a odoo module too.
        if exists a MANIFEST_FILES is a odoo module.
        :param module_file: String with full path of a
            python module file.
            If is a folder python module then will receive
            `__init__.py` file path.
        :return: List of names files matched with MANIFEST_FILES
        '''
        return os.path.basename(module_file) == '__init__.py' and \
            [
                filename
                for filename in os.listdir(
                    os.path.dirname(module_file))
                if filename in MANIFEST_FILES
            ]

    def visit_module(self, node):
        '''Call methods named with name-key from self.msgs
        Method should be named with next standard:
            def _check_{NAME_KEY}(self, module_path)
        by example: def _check_missing_icon(self, module_path)
                    to check missing-icon message name key
            And should return True if all fine else False.
        if a False is returned then add message of name-key.
        You can use `self.module_path` variable in those methods
            to get full path of odoo module directory.
        You can use `self.manifest_file` variable in those methods
            to get full path of MANIFEST_FILE found (__openerp__.py)
        You can use `self.manifest_content` variable in those methods
            to get full content of MANIFEST_FILE found.
        :param node: A astroid.scoped_nodes.Module
        :return: None
        '''
        odoo_files = self.is_odoo_module(node.file)
        self.module_path = os.path.dirname(node.file)
        self.node = node
        for msg_code, (title, name_key, description) in \
                sorted(self.msgs.iteritems()):
            if not self.linter.is_message_enabled(name_key):
                continue
            check_method = getattr(
                self, '_check_' + name_key.replace('-', '_'),
                None)
            self.name_key = msg_code
            if callable(check_method):
                self.manifest_file = None
                self.manifest_content = None
                if odoo_files:
                    self.manifest_file = os.path.join(
                        self.module_path, odoo_files[0])
                    self.manifest_content = open(self.manifest_file).read()
                elif msg_code in ODOO_MODULE_MSGS.keys():
                    # If is a check of odoo_module
                    # but no is odoo module
                    continue
                check_method()
