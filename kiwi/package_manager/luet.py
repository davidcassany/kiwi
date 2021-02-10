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
import logging
import yaml

# project
from kiwi.command import Command
from kiwi.package_manager.base import PackageManagerBase
from kiwi.exceptions import KiwiRequestError
from kiwi.path import Path


log = logging.getLogger('kiwi')


class PackageManagerLuet(PackageManagerBase):
    """
    **Implements base class for installation/deletion of
    packages and collections using luet**

    :param list luet_args: luet arguments from repository runtime
        configuration
    :param dict command_env: luet command environment from repository
        runtime configuration
    """
    def post_init(self, custom_args=None):
        """
        Post initialization method

        Store custom luet arguments

        :param list custom_args: custom luet arguments
        """
        self.custom_args = custom_args
        if not custom_args:
            self.custom_args = []

        runtime_config = self.repository.runtime_config()
        self.luet_args = runtime_config['luet_args']
        self.command_env = runtime_config['command_env']

    def request_package(self, name):
        """
        Queue a package request

        :param str name: package name
        """
        self.package_requests.append(name)

    def request_collection(self, name):
        """
        Queue a collection request

        luet does not distinguish the installation of pacakges
        and collections. Because of that collections are listed together
        with package requests and a warning message is shown.
        :param str name: luet group name
        """
        log.warning((
            'luet treats collection installations as regular packages.'
            'It is preferred to list them as regular packages'
        ))
        self.package_requests.append(name)

    def request_product(self, name):
        """
        Queue a product request

        There is no product definition for luet package manager

        :param str name: unused
        """
        pass

    def request_package_exclusion(self, name):
        """
        Queue a package exclusion(skip) request

        There is no package exclusion concept fot luet package manager

        :param str name: unused
        """
        pass

    def process_install_requests_bootstrap(self, root_bind=None):
        """
        Process package install requests for bootstrap phase (no chroot)

        :param object root_bind: unused

        :return: process results in command type

        :rtype: namedtuple
        """
        Command.run(
            ['luet'] + self.luet_args + [
                'repo', 'update'
            ]
        )
        bash_command = [
            'luet'
        ] + self.luet_args + self.custom_args + [
            'install', '-y', '--system-target', self.root_dir
        ] + self.package_requests
        self.cleanup_requests()
        return Command.call(
            ['bash', '-c', ' '.join(bash_command)], self.command_env
        )

    def process_install_requests(self):
        """
        Process package install requests for image phase (chroot)

        :return: process results in command type

        :rtype: namedtuple
        """
        chroot_luet_args = Path.move_to_root(self.root_dir, self.luet_args)
        bash_command = [
            'chroot', self.root_dir, 'luet'
        ] + chroot_luet_args + self.custom_args + [
            'install', '-y',
        ] + self.package_requests
        self.cleanup_requests()
        return Command.call(
            ['bash', '-c', ' '.join(bash_command)], self.command_env
        )

    def process_delete_requests(self, force=False):
        """
        Process package delete requests (chroot)

        :param bool force: force deletion: true|false

        :raises KiwiRequestError: if none of the packages to delete is
            installed
        :return: process results in command type

        :rtype: namedtuple
        """
        delete_items = []
        installed_pkgs = []
        chroot_luet_args = Path.move_to_root(self.root_dir, self.luet_args)

        yml = yaml.safe_load(
            Command.run(
                ['chroot', self.root_dir, 'luet'] + chroot_luet_args + [
                    'search', '--installed', '-o', 'yaml'
                ]
            ).output
        )
        if 'packages' in yml:
            for pkg in yml['packages']:
                installed_pkgs.append(
                    '{}/{}'.format(yml['category'], yaml['name'])
                )
        delete_items = [
            pkg for pkg in self.package_requests if pkg in installed_pkgs
        ]
        if not delete_items:
            raise KiwiRequestError(
                'None of the requested packages to delete are installed'
            )
        force_args = ['--force', '--nodeps'] if force else []
        self.cleanup_requests()
        return Command.call(
            [
                'chroot', self.root_dir, 'luet'
            ] + chroot_luet_args + self.custom_args + [
                'uninstall', '-y',
            ] + force_args + delete_items,
            self.command_env
        )

    def update(self):
        """
        Process package update requests (chroot)

        :return: process results in command type

        :rtype: namedtuple
        """
        chroot_luet_args = Path.move_to_root(self.root_dir, self.luet_args)
        return Command.call(
            [
                'chroot', self.root_dir, 'luet'
            ] + chroot_luet_args + self.custom_args + [
                'upgrade', '-y'
            ],
            self.command_env
        )

    def process_only_required(self):
        """
        Setup package processing only for required packages.

        This is the only option in luet, nothing to do here.
        """
        pass

    def process_plus_recommended(self):
        """
        Setup package processing to also include recommended dependencies.

        There is no such concept of recommended dependencies in luet.
        """
        pass

    def match_package_installed(self, package_name, luet_output):
        """
        Match expression to indicate a package has been installed

        This match for the package to be installed in the output
        of the luet command is not 100% accurate. There might
        be false positives due to sub package names starting with
        the same base package name

        :param list package_list: list of all packages
        :param str log_line: dnf status line

        :returns: match or None if there isn't any match

        :rtype: match object, None
        """
        pass

    def match_package_deleted(self, package_name, luet_output):
        """
        Match expression to indicate a package has been deleted

        :param list package_list: list of all packages
        :param str log_line: luet status line

        :returns: match or None if there isn't any match

        :rtype: match object, None
        """
        pass
