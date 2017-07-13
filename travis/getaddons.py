#!/usr/bin/env python
"""
Usage: get-addons [-m] path1 [path2 ...]
Given a list  of paths, finds and returns a list of valid addons paths.
With -m flag, will return a list of modules names instead.
"""

from __future__ import print_function
import ast
import os
import sys

from itertools import ifilter, imap

from git_run import GitRun

MANIFEST_FILES = [
    '__manifest__.py',
    '__odoo__.py',
    '__openerp__.py',
    '__terp__.py',
]


def is_module(path):
    """return False if the path doesn't contain an odoo module, and the full
    path to the module manifest otherwise"""

    if not os.path.isdir(path):
        return False
    files = os.listdir(path)
    filtered = [x for x in files if x in (MANIFEST_FILES + ['__init__.py'])]
    if len(filtered) == 2 and '__init__.py' in filtered:
        return os.path.join(
            path, next(x for x in filtered if x != '__init__.py'))
    else:
        return False


def find_module(module, paths):
    '''Find module in paths
    :param module: String with name of module to find in paths.
    :param paths: List of strings with paths to search.
    :return: String with full path of manifest file found'''
    for path in paths:
        module_path = is_module(os.path.join(path, module))
        if module_path:
            return module_path


def is_installable_module(path):
    """return False if the path doesn't contain an installable odoo module,
    and the full path to the module manifest otherwise"""
    manifest_path = is_module(path)
    if manifest_path:
        manifest = ast.literal_eval(open(manifest_path).read())
        if manifest.get('installable', True):
            return manifest_path
    return False


def get_modules(path):

    # Avoid empty basename when path ends with slash
    if not os.path.basename(path):
        path = os.path.dirname(path)

    res = []
    if os.path.isdir(path):
        res = [x for x in os.listdir(path)
               if is_installable_module(os.path.join(path, x))]
    return res


def is_addons(path):
    res = get_modules(path) != []
    return res


def get_addons(path):
    if is_addons(path):
        res = [path]
    else:
        res = [os.path.join(path, x)
               for x in os.listdir(path)
               if is_addons(os.path.join(path, x))]
    deps = dict([(addon, get_dependencies(addon))
                 for addon in res])
    sorted_addons = get_sorted_addons_by_level(deps)
    return sorted_addons


def get_dependencies(path):
    """Gets the dependencies of an addon reading the `oca_dependencies.txt`
    file.

    :param path: The addon path
    :rtype: str

    :returns: The dependency list
    :rtype: list
    """
    deps = []
    dep_files = ['oca_dependencies.txt']
    for dep_file in dep_files:
        dep_path = os.path.join(path, dep_file)
        try:
            with open(dep_path) as dep:
                for line in dep:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    deps.append(line.split()[0])
        except IOError:
            continue
    return deps


def get_sorted_addons_by_level(addons):
    """Sorts a list of addons according to its level, and followed
    by its dependencies also sorted by level.

    It first sorts the addons using `sort_addons_by_level` and then
    it puts the dependencies after their parents. This to keep the addons
    with higher dependency level first and then its addons also sorted by
    level.

    :param addons: The addons with their dependencies.
    :type addons: dict

    :returns: The addons sorted by level
    :rtype: list

    Example::

        get_sorted_addons_by_level({
            "e": [],
            "r": ["x"],
            "c": [],
            "t": ["r", "c"],
            "x": ["e"],
        })

    Returns::

        ["t", "r", "c", "x", "e"]

    """
    sorted_addons = []
    addons_by_level = sort_addons_by_level(addons)
    addons_list = sorted(addons_by_level.keys(),
                         key=lambda dep: -addons_by_level.get(dep))
    for addon in addons_list:
        if addon not in sorted_addons:
            sorted_addons.append(addon)
        for dep in addons.get(addon, []):
            dep_addon = os.path.join(os.path.dirname(addon), dep)
            if dep_addon not in sorted_addons:
                sorted_addons.append(dep_addon)
    return sorted_addons


def sort_addons_by_level(addons, _key=False, _res=False):
    """Reads a dict of addons with dependencies and assigns a "level" that
    represents how deep its dependencies go.

    :param addons: The addons with their dependencies.
    :type addons: dict

    :param _key: This is for recursion purposes. Do not pass when calling
        from the outside.
    :param _res: This is for recursion purposes. Do not pass when calling
        from the outside.

    :returns: The addons with the level
    :rtype: dict

    Example::

        sort_addons_by_level({
            "e": [],
            "r": ["x"],
            "c": [],
            "t": ["r", "c"],
            "x": ["e"],
        })

    Returns::

        {
            "t": 3,
            "r": 2,
            "x": 1,
            "c": 0,
            "e": 0,
        }

    In this example "t" depends on "r" that depends on "x" that depends on "e".
    There are three "levels" of dependencies below "t".
    """
    _res = _res or {}
    if not _key:
        for _key in addons:
            _res.update(sort_addons_by_level(addons, _key, _res))
        return _res
    if _res.get(_key, -1) > -1:
        return _res
    for dep in addons.get(_key, []):
        _res.update(sort_addons_by_level(
            addons, os.path.join(os.path.dirname(_key), dep), _res))
    _res[_key] = (max([
        _res.get(os.path.join(os.path.dirname(_key), dep), -1)
        for dep in addons.get(_key, [])
    ] or [-1]) + 1)
    return _res


def get_modules_changed(path, ref='HEAD'):
    '''Get modules changed from git diff-index {ref}
    :param path: String path of git repo
    :param ref: branch or remote/branch or sha to compare
    :return: List of paths of modules changed
    '''
    git_run_obj = GitRun(os.path.join(path, '.git'))
    git_run_obj.run(['fetch'] + ref.split('/'))
    items_changed = git_run_obj.get_items_changed(ref)
    folders_changed = set([
        item_changed.split('/')[0]
        for item_changed in items_changed
        if '/' in item_changed]
    )
    modules = set(get_modules(path))
    modules_changed = list(modules & folders_changed)
    modules_changed_path = [
        os.path.join(path, module_changed)
        for module_changed in modules_changed]
    return modules_changed_path


def get_depends(addons_path_list, modules_list):
    """Get recursive depends from addons_paths and modules list
    :param modules_list: List of strings with name of modules
    :param addons_path_list: List of strings with path of modules
    :return set: Unsorted set of recursive dependencies of modules
    """
    modules = set(modules_list)
    addons_paths = set(addons_path_list)
    visited = set()
    while modules != visited:
        module = (modules - visited).pop()
        visited.add(module)
        manifest_path = find_module(module, addons_path_list)
        assert manifest_path, "Module not found %s in addons_paths %s" % (
            module, addons_path_list)
        try:
            manifest_filename = next(ifilter(
                os.path.isfile,
                imap(lambda p: os.path.join(p, manifest_path), addons_paths)
            ))
        except StopIteration:
            # For some reason the module wasn't found
            continue
        manifest = eval(open(manifest_filename).read())
        modules.update(manifest.get('depends', []))
    return modules


def main(argv=None):
    if argv is None:
        argv = sys.argv
    params = argv[1:]
    if not params:
        print(__doc__)
        return 1

    list_modules = False
    exclude_modules = []

    while params and params[0].startswith('-'):
        param = params.pop(0)
        if param == '-m':
            list_modules = True
        if param == '-e':
            exclude_modules = [x for x in params.pop(0).split(',')]

    func = get_modules if list_modules else get_addons
    lists = [func(x) for x in params]
    res = [x for l in lists for x in l]  # flatten list of lists
    if exclude_modules:
        res = [x for x in res if x not in exclude_modules]
    print(','.join(res))


if __name__ == "__main__":
    sys.exit(main())
