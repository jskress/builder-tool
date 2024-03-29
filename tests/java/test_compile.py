"""
This file contains all the unit tests for our compilation support.
"""
import os
from pathlib import Path

# noinspection PyPackageRequirements
import pytest

from builder.java import JavaConfiguration
# noinspection PyProtectedMember
from builder.java.compile import _build_compiler_options, run_compiler, java_compile
from builder.models import DependencyPathSet, Dependency
from builder.project import Project
from tests.test_support import Options, Regex, FakeProcessContext, FakeProcess


class TestBuildOptions(object):
    def test_build_options_no_class_path(self):
        """Make sure we build options correctly with no extra class path."""
        classes_dir = Path('classes')
        options = _build_compiler_options(classes_dir, [])

        assert options == ['-d', 'classes']

    def test_build_options_with_verbose(self):
        """Make sure we build options correctly with no class path but verbosely."""
        path = Path('classes')

        with Options(verbose=3):
            options = _build_compiler_options(path, [])

        # noinspection SpellCheckingInspection
        assert options == ['-verbose', '-Xdiags:verbose', '-d', 'classes']

    def test_build_options_with_class_path(self):
        """Make sure we build options correctly with no extra class path."""
        classes_dir = Path('classes')
        dep = Dependency('dep', {
            'location': 'local',
            'version': '1.2.3',
            'scope': 'scope'
        })
        dps_list = [
            DependencyPathSet(dep, Path('a.jar')),
            DependencyPathSet(dep, Path('b.jar')),
            DependencyPathSet(dep, Path('c.jar'))
        ]
        expected_class_path = os.pathsep.join(['a.jar', 'b.jar', 'c.jar'])
        options = _build_compiler_options(classes_dir, dps_list)

        assert options == ['-d', 'classes', '--class-path', expected_class_path]


class TestRunJavaC(object):
    def test_good_javac(self):
        java_directory = Path('src')
        classes_directory = Path('classes')
        expected = ['javac', '-d', str(classes_directory), Regex(r'@.*')]

        with FakeProcessContext(FakeProcess(expected)):
            run_compiler(java_directory, classes_directory, [])

    def test_javac_compile_error(self):
        java_directory = Path('src')
        classes_directory = Path('classes')
        expected = ['javac', '-d', str(classes_directory), Regex(r'@.*')]

        with FakeProcessContext(FakeProcess(expected, rc=1)):
            with pytest.raises(ValueError) as info:
                run_compiler(java_directory, classes_directory, [])

        assert info.value.args[0] == 'Java source could not be compiled.'


class TestJavaCompile(object):
    def test_simple_java_compile(self, tmpdir):
        project_dir = Path(str(tmpdir))
        project = Project.from_dir(project_dir)

        with Options(project=project):
            config = JavaConfiguration()

        # This needs to exist for the test to work.
        _ = config.code_dir(ensure=True)

        expected = ['javac', '-d', str(config.classes_dir()), Regex(r'@.*')]

        with FakeProcessContext(FakeProcess(expected)):
            java_compile(config, [])
