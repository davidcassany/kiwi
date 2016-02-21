import sys
import mock
from nose.tools import *
from mock import patch
from mock import call
import kiwi

from . import nose_helper
from kiwi.exceptions import *
from kiwi.result_bundle_task import ResultBundleTask
from kiwi.result import Result


class TestResultBundleTask(object):
    def setup(self):
        sys.argv = [
            sys.argv[0], 'result', 'bundle', '--target-dir', 'target_dir',
            '--bundle-dir', 'bundle_dir', '--id', 'Build_42'
        ]
        self.context_manager_mock = mock.Mock()
        self.file_mock = mock.Mock()
        self.enter_mock = mock.Mock()
        self.exit_mock = mock.Mock()
        self.enter_mock.return_value = self.file_mock
        setattr(self.context_manager_mock, '__enter__', self.enter_mock)
        setattr(self.context_manager_mock, '__exit__', self.exit_mock)

        self.file_mock.read.return_value = b'data'

        self.xml_state = mock.Mock()
        self.xml_state.get_image_version = mock.Mock(
            return_value='1.2.3'
        )

        self.result = Result(self.xml_state)
        self.result.add(
            key='keyname', filename='filename-1.2.3',
            use_for_bundle=True, compress=True, shasum=True
        )

        kiwi.result_bundle_task.Help = mock.Mock(
            return_value=mock.Mock()
        )
        self.task = ResultBundleTask()

    def __init_command_args(self):
        self.task.command_args = {}
        self.task.command_args['help'] = False
        self.task.command_args['bundle'] = False
        self.task.command_args['--target-dir'] = 'target_dir'
        self.task.command_args['--bundle-dir'] = 'bundle_dir'
        self.task.command_args['--id'] = 'Build_42'

    @raises(KiwiBundleError)
    def test_process_invalid_bundle_directory(self):
        self.__init_command_args()
        self.task.command_args['--bundle-dir'] = \
            self.task.command_args['--target-dir']
        self.task.command_args['bundle'] = True
        self.task.process()

    @patch('kiwi.result_bundle_task.Result.load')
    @patch('kiwi.result_bundle_task.Command.run')
    @patch('kiwi.result_bundle_task.Path.create')
    @patch('kiwi.result_bundle_task.Compress')
    @patch('kiwi.result_bundle_task.hashlib.sha256')
    @patch('os.path.exists')
    @patch('builtins.open')
    def test_process_result_bundle(
        self, mock_open, mock_exists, mock_sha256, mock_compress,
        mock_path, mock_command, mock_load
    ):
        sha256 = mock.Mock()
        mock_sha256.return_value = sha256
        mock_exists.return_value = False
        mock_open.return_value = self.context_manager_mock
        mock_load.return_value = self.result
        self.__init_command_args()
        self.task.command_args['bundle'] = True

        self.task.process()

        mock_load.assert_called_once_with('target_dir/kiwi.result')
        mock_path.assert_called_once_with('bundle_dir')
        mock_command.assert_called_once_with(
            [
                'cp', '-l', 'filename-1.2.3',
                'bundle_dir/filename-1.2.3-Build_42'
            ]
        )
        mock_compress.assert_called_once_with(
            'bundle_dir/filename-1.2.3-Build_42'
        )
        mock_sha256.assert_called_once_with(b'data')
        sha256.hexdigest.assert_called_once_with()

    def test_process_result_bundle_help(self):
        self.__init_command_args()
        self.task.command_args['help'] = True
        self.task.command_args['bundle'] = True
        self.task.process()
        self.task.manual.show.assert_called_once_with(
            'kiwi::result::bundle'
        )
