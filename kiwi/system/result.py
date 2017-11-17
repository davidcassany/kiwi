# Copyright (c) 2015 SUSE Linux GmbH.  All rights reserved.
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
from collections import namedtuple
import pickle
import os

# project
from kiwi.logger import log
from kiwi.runtime_config import RuntimeConfig
from kiwi.utils.size import StringToSize


from kiwi.exceptions import (
    KiwiResultError
)

# must be global to allow pickle to find it
result_file_type = namedtuple(
    'result_file_type', ['filename', 'use_for_bundle', 'compress', 'shasum']
)


class Result(object):
    """
    Collect image building results

    Attributes

    * :attr:`result_files`
        List of result files

    * :attr:`class_version`
        Result class version

    * :attr:`xml_state`
        Instance of XMLState
    """
    def __init__(self, xml_state):
        self.result_files = {}

        # Instances of this class are stored as result reference.
        # In order to handle class format changes any instance
        # provides a version information
        self.class_version = 1

        self.xml_state = xml_state
        self.runtime_config = RuntimeConfig()

    def add(
        self, key, filename, use_for_bundle=True, compress=False, shasum=True
    ):
        """
        Add result tuple to result_files list

        :param string key: name
        :param string filename: file path name
        :param boot use_for_bundle: use when bundling results true|false
        :param bool compress: compress when bundling true|false
        :param bool shasum: create shasum when bundling true|false
        """
        if key and filename:
            self._verify_build_constraints(filename, key)
            self.result_files[key] = result_file_type(
                filename=filename,
                use_for_bundle=use_for_bundle,
                compress=compress,
                shasum=shasum
            )

    def get_results(self):
        """
        Current list of result tuples
        """
        return self.result_files

    def print_results(self):
        """
        Print results human readable
        """
        if self.result_files:
            log.info('Result files:')
            for key, value in sorted(list(self.result_files.items())):
                log.info('--> %s: %s', key, value.filename)

    def dump(self, filename):
        """
        Picke dump this instance to a file

        :param string filename: file path name
        """
        try:
            with open(filename, 'wb') as result:
                pickle.dump(self, result)
        except Exception as e:
            raise KiwiResultError(
                'Failed to pickle dump results: %s' % format(e)
            )

    @classmethod
    def load(self, filename):
        """
        Load pickle dumped filename into a Result instance

        :param string filename: file path name
        """
        if not os.path.exists(filename):
            raise KiwiResultError(
                'No result information %s found' % filename
            )
        try:
            with open(filename, 'rb') as result:
                return pickle.load(result)
        except Exception as e:
            raise KiwiResultError(
                'Failed to pickle load results: %s' % type(e).__name__
            )

    def _verify_build_constraints(self, filename, key):
        max_size = self.runtime_config.get_max_size_constraint()
        if max_size:
            max_size_bytes = StringToSize.to_bytes(max_size)
            if os.path.getsize(filename) > max_size_bytes:
                raise KiwiResultError(
                    'Build constraint failed: {0} {1} is bigger than {2}'
                    .format(key, filename, max_size)
                )
