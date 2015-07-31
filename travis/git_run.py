#!/usr/bin/python
# -*- encoding: utf-8 -*-
###########################################################################
#    Module Writen to OpenERP, Open Source Management Solution
#
#    Copyright (c) 2013 Vauxoo - http://www.vauxoo.com/
#    All Rights Reserved.
#    info Vauxoo (info@vauxoo.com)
############################################################################
#    Coded by: moylop260 (moylop260@vauxoo.com)
############################################################################
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import subprocess


class GitRun(object):
    def __init__(self, repo_path):
        self.repo_path = repo_path

    def run(self, command):
        """Execute git command in bash
        :param list command: Git cmd to execute in self.repo_path
        :return: String output of command executed.
        """
        cmd = ['git', '--git-dir=' + self.repo_path] + command
        try:
            res = subprocess.check_output(cmd)
        except subprocess.CalledProcessError:
            res = None
        if isinstance(res, basestring):
            res = res.strip('\n')
        return res

    def get_items_changed(self, base_ref, ref=None):
        """Get name of items changed in self.repo_path
        of base_ref..ref
        This is a wrapper method of git command:
            git diff --name-only {base_ref}..{ref}
        :param base_ref: String of branch or sha base.
            e.g. "master" or "SHA_NUMBER"
        :param ref: Optional string of branch or sha
            to compare with base_ref.
            Default: Current ref of self.repo_path.
            e.g. "feature/x" or "SHA_NUMBER"
        :return: List of name of items changed
            detected with diff of base_ref..ref
        """
        command = ['diff', '--name-only', base_ref + '..']
        if ref:
            command.append(ref)
        res = self.run(command)
        items = res.split('\n') if res else []
        return items
