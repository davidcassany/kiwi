
from mock import patch
from mock import call

from .test_helper import patch_open

import mock
import os

from kiwi.repository.pacman import RepositoryPacman


class TestRepositorPacman(object):
    @patch('kiwi.repository.pacman.NamedTemporaryFile')
    @patch_open
    @patch('kiwi.repository.pacman.ConfigParser')
    @patch('kiwi.repository.pacman.Path.create')
    @patch('kiwi.logger.log.warning')
    def setup(self, mock_warn, mock_path, mock_config, mock_open, mock_temp):
        runtime_pacman_config = mock.Mock()
        mock_config.return_value = runtime_pacman_config
        tmpfile = mock.Mock()
        tmpfile.name = 'tmpfile'
        mock_temp.return_value = tmpfile
        root_bind = mock.Mock()
        root_bind.move_to_root = mock.Mock(
            return_value=['root-moved-arguments']
        )
        root_bind.root_dir = '../data'
        root_bind.shared_location = '/shared-dir'
        self.repo = RepositoryPacman(root_bind)

        assert runtime_pacman_config.set.call_args_list == [
            call('options', 'Architecture', 'auto'),
            call('options', 'CacheDir', '/shared-dir/pacman/cache'),
            call('options', 'SigLevel', 'Never DatabaseNever'),
            call('options', 'LocalFileSigLevel', 'Never DatabaseNever'),
            call('options', 'Include', '/shared-dir/pacman/repos/*.repo')
        ]

    @patch_open
    @patch('kiwi.repository.pacman.NamedTemporaryFile')
    @patch('kiwi.repository.pacman.Path.create')
    def test_post_init_with_custom_args(self, mock_path, mock_temp, mock_open):
        self.repo.post_init(['check_signatures'])
        assert self.repo.custom_args == []
        assert self.repo.check_signatures

    def test_runtime_config(self):
        assert self.repo.runtime_config()['pacman_args'] == \
            self.repo.pacman_args
        assert self.repo.runtime_config()['command_env'] == \
            os.environ

    @patch('kiwi.repository.pacman.ConfigParser')
    @patch('os.path.exists')
    @patch_open
    def test_add_repo_with_comonents(
        self, mock_open, mock_exists, mock_config
    ):
        repo_config = mock.Mock()
        mock_config.return_value = repo_config
        mock_exists.return_value = True

        self.repo.add_repo(
            'foo', 'some_uri', components='core extra',
            repo_gpgcheck=False, pkg_gpgcheck=True
        )

        assert repo_config.add_section.call_args_list == [
            call('core'), call('extra')
        ]
        assert repo_config.set.call_args_list == [
            call('core', 'Server', 'some_uri'),
            call('core', 'SigLevel', 'Required DatabaseNever'),
            call('extra', 'Server', 'some_uri'),
            call('extra', 'SigLevel', 'Required DatabaseNever'),
        ]
        mock_open.assert_called_once_with(
            '/shared-dir/pacman/repos/foo.repo', 'w'
        )

    @patch('kiwi.repository.pacman.ConfigParser')
    @patch('os.path.exists')
    @patch_open
    def test_add_repo_without_comonents(
        self, mock_open, mock_exists, mock_config
    ):
        repo_config = mock.Mock()
        mock_config.return_value = repo_config
        mock_exists.return_value = True

        self.repo.add_repo('foo', 'some_uri', pkg_gpgcheck=False)

        assert repo_config.add_section.call_args_list == [
            call('foo')
        ]
        assert repo_config.set.call_args_list == [
            call('foo', 'Server', 'some_uri'),
            call('foo', 'SigLevel', 'Never DatabaseNever'),
        ]
        mock_open.assert_called_once_with(
            '/shared-dir/pacman/repos/foo.repo', 'w'
        )

    @patch('kiwi.repository.pacman.Path.create')
    def test_setup_package_database_configuration(self, mock_path_create):
        self.repo.setup_package_database_configuration()
        mock_path_create.assert_called_once_with(
            '../data/var/lib/pacman'
        )

    @patch('kiwi.repository.pacman.os.path.exists')
    @patch('kiwi.repository.pacman.Command.run')
    def test_import_trusted_keys(self, mock_cmd, mock_exists):
        exists = [True, False]
        mock_exists.side_effect = lambda x: exists.pop()
        signing_keys = ['key-file-a.asc', 'key-file-b_ID']
        self.repo.import_trusted_keys(signing_keys)
        assert mock_cmd.call_args_list == [
            call(['pacman-key', '--add', 'key-file-a.asc']),
            call(['pacman-key', '--recv-keys', 'key-file-b_ID'])
        ]
