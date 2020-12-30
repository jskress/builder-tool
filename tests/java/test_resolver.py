"""
This file contains all the unit tests for our resolver support.
"""
from pathlib import Path

from builder.java import JavaConfiguration, project_to_lib_dir
from builder.project import Project
from tests.test_support import Options


class TestResolver(object):
    def test_project_to_lib_dir(self):
        path = Path('/path/to/project')
        expected = path / 'dist' / 'lib'
        project = Project.from_dir(path)

        with Options(project=project):
            config = JavaConfiguration()

        assert project_to_lib_dir(config) == expected
