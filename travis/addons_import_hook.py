import sys
import imp
import os


# addons path as a list
ad_paths = []
hooked = False


class AddonsImportHook(object):
     """
    Import hook to load OpenERP addons from multiple paths.
    OpenERP implements its own import-hook to load its addons. OpenERP
    addons are Python modules. Originally, they were each living in their
    own top-level namespace, e.g. the sale module, or the hr module. For
    backward compatibility, `import <module>` is still supported. Now they
    are living in `openerp.addons`. The good way to import such modules is
    thus `import openerp.addons.module`.
    """

     def find_module(self, module_name, package_path):
        # print "aqui voy 1", module_name, package_path
        module_parts = module_name.split('.')
        # print "module_parts", module_parts
        if len(module_parts) == 3 and module_name.startswith('openerp.addons.'):
            return self # We act as a loader too.

     def load_module(self, module_name):
        # print "aqui voy 2", module_name
        if module_name in sys.modules:
            return sys.modules[module_name]

        _1, _2, module_part = module_name.split('.')
        # Note: we don't support circular import.
        f, path, descr = imp.find_module(module_part, ad_paths)
        mod = imp.load_module('openerp.addons.' + module_part, f, path, descr)
        sys.modules['openerp.addons.' + module_part] = mod
        # print "aqui voy 3", module_part, mod
        return mod

def initialize_sys_path(addons_path):
    """
    Setup an import-hook to be able to import OpenERP addons from the different
    addons paths.
    This ensures something like ``import crm`` (or even
    ``import openerp.addons.crm``) works even if the addons are not in the
    PYTHONPATH.
    """
    global ad_paths
    global hooked

    # import pdb;pdb.set_trace()
    for ad in addons_path:
        ad = os.path.abspath(ad.strip())
        if ad not in ad_paths:
            ad_paths.append(ad)

    if not hooked:
        sys.meta_path.append(AddonsImportHook())
        hooked = True
    __import__('openerp.addons.base')
    print "si se pudo importa openerp.addons.base"

