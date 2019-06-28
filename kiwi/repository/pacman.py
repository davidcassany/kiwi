# Copyright (c) 2019 SUSE Linux GmbH.  All rights reserved.
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
from six.moves.configparser import ConfigParser
from tempfile import NamedTemporaryFile

# project
from kiwi.repository.base import RepositoryBase
from kiwi.path import Path
from kiwi.command import Command


class RepositoryPacman(RepositoryBase):

    def post_init(self, custom_args=None):

        self.custom_args = custom_args
        self.check_signatures = False
        self.repo_names = []
        if not custom_args:
            self.custom_args = []

        self.runtime_pacman_config_file = NamedTemporaryFile(
            dir=self.root_dir
        )

        if 'check_signatures' in self.custom_args:
            self.custom_args.remove('check_signatures')
            self.check_signatures = True

        manager_base = self.shared_location + '/pacman'

        self.shared_pacman_dir = {
            'cache-dir': manager_base + '/cache',
            'repos-dir': manager_base + '/repos'
        }
        Path.create(self.shared_pacman_dir['repos-dir'])

        self.pacman_args = [
            '--config', self.runtime_pacman_config_file.name,
            '--noconfirm', '--needed'
        ]

        self._write_runtime_config()

    def use_default_location(self):
        self.shared_pacman_dir['cache-dir'] = self.root_dir + '/var/cache/pacman/pkg'
        self.shared_pacman_dir['repos-dir'] = self.root_dir + '/etc/pacman.d'

    def runtime_config(self):
        return {
            'pacman_args': self.pacman_args,
            'command_env': os.environ
        }

    def _add_repo_section(
        self, config_parser, name, uri, repo_gpgcheck=None, pkg_gpgcheck=None
    ):
        config_parser.add_section(name)
        config_parser.set(name, 'Server', uri)
        config_parser.set(
            name, 'SigLevel', '{0} {1}'.format(
                'Required' if pkg_gpgcheck else 'Never',
                'DatabaseRequired' if repo_gpgcheck else 'DatabaseNever'
            )
        )

    def add_repo(
        self, name, uri, repo_type=None,
        prio=None, dist=None, components=None,
        user=None, secret=None, credentials_file=None,
        repo_gpgcheck=None, pkg_gpgcheck=None
    ):
        """
        Add pacman repository

        :param str name: repository base file name
        :param str uri: repository URI
        :param repo_type: unused
        :param int prio: unused
        :param dist: unused
        :param components: components to be used from this repository
        :param user: unused
        :param secret: unused
        :param credentials_file: unused
        :param bool repo_gpgcheck: enable database signature validation
        :param bool pkg_gpgcheck: enable package signature validation
        """
        repo_file = '{0}/{1}.repo'.format(
            self.shared_pacman_dir['repos-dir'], name
        )
        self.repo_names.append(name + '.repo')
        repo_config = ConfigParser()
        repo_config.optionxform = str
        if components is None:
            self._add_repo_section(
                repo_config, name, uri, repo_gpgcheck,
                pkg_gpgcheck
            )
        else:
            for component in components.split():
                self._add_repo_section(
                    repo_config, component, uri, repo_gpgcheck,
                    pkg_gpgcheck
                )

        with open(repo_file, 'w') as config:
            repo_config.write(config)

    def import_trusted_keys(self, signing_keys):
        for signing_key in signing_keys:
            if os.path.exists(signing_key):
                Command.run(
                    ['pacman-key', '--recv-keys', signing_key]
                )
            else:
                Command.run(
                    ['pacman-key', '--add', signing_key]
                )

    def delete_repo(self, name):
        Path.wipe(
            '{0}/{1}.repo'.format(self.shared_pacman_dir['repos-dir'], name)
        )

    def delete_all_repos(self):
        Path.wipe(self.shared_pacman_dir['repos-dir'])
        Path.create(self.shared_pacman_dir['repos-dir'])

    def delete_repo_cache(self, name):
        Path.wipe(self.shared_pacman_dir['cache-dir'])

    def setup_package_database_configuration(self):
        Path.create(os.sep.join([self.root_dir, 'var/lib/pacman']))

    def cleanup_unused_repos(self):
        """
        Delete unused pacman repositories

        Repository configurations which are not used for this build
        must be removed otherwise they are taken into account for
        the package installations
        """
        pass
        repos_dir = self.shared_pacman_dir['repos-dir']
        repo_files = list(os.walk(repos_dir))[0][2]
        for repo_file in repo_files:
            if repo_file not in self.repo_names:
                Path.wipe(repos_dir + '/' + repo_file)

    def _write_runtime_config(self):
        runtime_pacman_config = ConfigParser()
        runtime_pacman_config.optionxform = str
        runtime_pacman_config.add_section('options')

        runtime_pacman_config.set(
            'options', 'Architecture', 'auto'
        )
        runtime_pacman_config.set(
            'options', 'CacheDir', self.shared_pacman_dir['cache-dir']
        )

        if self.check_signatures:
            runtime_pacman_config.set(
                'options', 'SigLevel', 'Required DatabaseRequired'
            )
            runtime_pacman_config.set(
                'options', 'LocalFileSigLevel', 'Required DatabaseRequired'
            )
        else:
            runtime_pacman_config.set(
                'options', 'SigLevel', 'Never DatabaseNever'
            )
            runtime_pacman_config.set(
                'options', 'LocalFileSigLevel', 'Never DatabaseNever'
            )

        runtime_pacman_config.set(
            'options', 'Include', '{0}/*.repo'.format(
                self.shared_pacman_dir['repos-dir']
            )
        )

        with open(self.runtime_pacman_config_file.name, 'w') as config:
            runtime_pacman_config.write(config)
