# Copyright (c) 2021 SUSE Linux GmbH.  All rights reserved.
#
# This file is part of kiwi.
#
# kiwi is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# kiwi is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with kiwi.  If not, see <http://www.gnu.org/licenses/>
#
import os
import yaml
from tempfile import NamedTemporaryFile

# project
from kiwi.repository.base import RepositoryBase
from kiwi.path import Path
from kiwi.exceptions import KiwiRepositorySetupError


class RepositoryLuet(RepositoryBase):
    """
    **Implements repo handling for luet package manager**

    :param str shared_luet_dir: shared directory between image root
        and build system root
    :param str runtime_luet_config_file: luet runtime config file name
    :param list luet_args: luet caller args plus additional custom args
    :param dict command_env: customized os.environ for luet
    """
    def post_init(self, custom_args=None):
        """
        Post initialization method

        Store custom pacman arguments and create runtime configuration
        and environment

        :param list custom_args: zypper arguments
        """
        self.custom_args = custom_args
        self.check_signatures = False
        self.repo_names = []
        if not custom_args:
            self.custom_args = []

        self.runtime_luet_config_file = NamedTemporaryFile(
            dir=self.root_dir
        )

        if 'check_signatures' in self.custom_args:
            self.custom_args.remove('check_signatures')
            self.check_signatures = True

        manager_base = self.shared_location + '/luet'

        self.shared_luet_dir = {
            'cache-dir': manager_base + '/cache',
            'repos-dir': manager_base + '/repos'
        }
        Path.create(self.shared_pacman_dir['repos-dir'])

        self.luet_args = [
            '--config', self.runtime_luet_config_file.name
        ]
        self._write_runtime_config(
            self.root_dir, self.shared_luet_dir['repos-dir']
        )

    def use_default_location(self):
        """
        Setup luet repository operations to store all data
        in the default places
        """
        self.shared_luet_dir['repos-dir'] = \
            self.root_dir + '/etc/luet/repos.conf.d'
        self._write_runtime_config()
        # TODO verify the use of this method, what should actually change?

    def runtime_config(self):
        """
        luet runtime configuration and environment
        """
        return {
            'luet_args': self.luet_args,
            'command_env': os.environ
        }

    def add_repo(
        self, name, uri, repo_type=None,
        prio=None, dist=None, components=None,
        user=None, secret=None, credentials_file=None,
        repo_gpgcheck=None, pkg_gpgcheck=None,
        sourcetype=None, use_for_bootstrap=False
    ):
        """
        Add luet repository

        :param str name: repository base file name
        :param str uri: repository URI
        :param repo_type: unused
        :param int prio: repository priority
        :param dist: unused
        :param components: unused
        :param user: unused
        :param secret: unused
        :param credentials_file: unused
        :param bool repo_gpgcheck: unused
        :param bool pkg_gpgcheck: unused
        :param str sourcetype: unused
        :param bool use_for_bootstrap: unused
        """
        repo_file = '{0}/{1}.yaml'.format(
            self.shared_luet_dir['repos-dir'], name
        )
        self.repo_names.append(name + '.yaml')
        if uri.startswith('http'):
            repo_type = 'http'
        elif not Uri(uri).is_remote():
            repo_type = 'dir'
        else:
            raise KiwiRepositorySetupError(
                'luet does not support this repo URI: {}'.format(uri)
            )
        repo_config = {
            'name': name,
            'type': repo_type,
            'enable': True,
            'cached': True,
            'tree_path': '{}/{}/treefs'.format(
                self.shared_luet_dir['repos-dir'], name
            ),
            'meta_path' '{}/{}/meta'.format(
                self.shared_luet_dir['repos-dir'], name
            ),
            'urls': [uri]
        }
        if prio:
            repo_config['priority'] = prio
        with open(repo_file, 'w') as config:
            yaml.dump(repo_config, config)

    def import_trusted_keys(self, signing_keys):
        """
        luet runtime configuration and environment

        unused, not implemented
        """
        pass

    def delete_repo(self, name):
        """
        Delete luet repository

        :param str name: repository name
        """
        Path.wipe(
            '{0}/{1}.yaml'.format(self.shared_luet_dir['repos-dir'], name)
        )

    def delete_all_repos(self):
        """
        Delete all luet repositories
        """
        Path.wipe(self.shared_luet_dir['repos-dir'])
        Path.create(self.shared_luet_dir['repos-dir'])

   def delete_repo_cache(self, name):
        """
        Delete luet repository cache

        The method deletes these directories to cleanup the
        cache information

        :param str name: repository name
        """
        treefs = '{}/{}/treefs'.format(self.shared_luet_dir['repos-dir'], name)
        meta = '{}/{}/meta'.format(self.shared_luet_dir['repos-dir'], name)
        Path.wipe(treefs)
        Path.wipe(meta)

    def setup_package_database_configuration(self):
        """
        unused
        """
        pass

    def cleanup_unused_repos(self):
        """
        Delete unused luet repositories

        Repository configurations which are not used for this build
        must be removed otherwise they are taken into account for
        the package installations
        """
        repos_dir = self.shared_pacman_dir['repos-dir']
        repo_files = list(os.walk(repos_dir))[0][2]
        for repo_file in repo_files:
            if repo_file not in self.repo_names:
                Path.wipe(repos_dir + '/' + repo_file)

    def _write_runtime_config(self):
        luet_config = {
            'logging': {
                'enable_logfile': False,
                'path': '',
                'level': 'info',
                'color': False,
                'enable_emoji': False
            },
            'general': {
                'concurrency': 1,
                'debug': False,
            },
            'repos_confdir': self.shared_luet_dir['repos-dir']
        }
        with open(self.runtime_dnf_config_file.name, 'w') as config:
            yaml.dump(luet_config, config)
