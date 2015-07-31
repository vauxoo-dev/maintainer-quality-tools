import os

from git_run import GitRun
from getaddons import get_modules


def get_modules_changed(path, ref, ref_base=None):
    git_run_obj = GitRun(os.path.join(path, '.git'))
    items_changed = git_run_obj.get_items_changed(ref, ref_base)
    folders_changed = set([
        item_changed.split('/')[0]
        for item_changed in items_changed
        if '/' in item_changed]
    )
    modules = set(get_modules(path))
    modules_changed = list(modules & folders_changed)
    return modules_changed


if __name__ == '__main__':
    import os
    modules_changed = get_modules_changed(
        os.path.join(os.environ['TRAVIS_BUILD_DIR']),
        os.environ['TRAVIS_BRANCH'], 'master')
    print modules_changed
