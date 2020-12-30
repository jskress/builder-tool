"""
This file contains all the unit tests for our basic Java support.
"""
import os
from pathlib import Path
from subprocess import CompletedProcess
from typing import Tuple, Callable, Sequence

from builder.java import JavaConfiguration, PackageConfiguration, get_javac_version
# noinspection PyProtectedMember
from builder.java.java import _add_verbose_options, _add_class_path, build_names
from builder.models import Dependency, DependencyPathSet
from builder.project import Project
from tests.test_support import Options, FakeProcess, FakeProcessContext


class TestJavaConfig(object):
    @staticmethod
    def _make_config(tmpdir) -> Tuple[Path, JavaConfiguration, PackageConfiguration]:
        directory = Path(str(tmpdir))
        project = Project.from_dir(directory)

        with Options(project=project):
            return directory, JavaConfiguration(), PackageConfiguration()

    @staticmethod
    def _verify_path_attr(directory: Path, config: JavaConfiguration, attr_name: str,
                          accessor: Callable[[], Path], *path_parts: str):
        expected = directory

        for part in path_parts:
            expected = expected / Path(getattr(config, part))

        assert getattr(config, attr_name) is None

        result = accessor()

        assert isinstance(result, Path)
        assert result == expected
        assert getattr(config, attr_name) == expected

    def test_code_dir(self, tmpdir):
        directory, config, _ = self._make_config(tmpdir)

        self._verify_path_attr(directory, config, '_code_dir', config.code_dir, 'source', 'code_source')

    def test_resources_dir(self, tmpdir):
        directory, config, _ = self._make_config(tmpdir)

        self._verify_path_attr(directory, config, '_resources_dir', config.resources_dir, 'source', 'code_resources')

    def test_tests_dir(self, tmpdir):
        directory, config, _ = self._make_config(tmpdir)

        self._verify_path_attr(directory, config, '_tests_dir', config.tests_dir, 'source', 'tests_source')

    def test_test_resources_dir(self, tmpdir):
        directory, config, _ = self._make_config(tmpdir)

        self._verify_path_attr(
            directory, config, '_test_resources_dir', config.test_resources_dir, 'source', 'test_resources'
        )

    def test_build_dir(self, tmpdir):
        directory, config, _ = self._make_config(tmpdir)

        self._verify_path_attr(directory, config, '_build_dir', config.build_dir, 'build')

    def test_classes_dir(self, tmpdir):
        directory, config, _ = self._make_config(tmpdir)

        self._verify_path_attr(directory, config, '_classes_dir', config.classes_dir, 'build', 'code_target')

    def test_doc_dir(self, tmpdir):
        directory, config, _ = self._make_config(tmpdir)

        self._verify_path_attr(directory, config, '_doc_dir', config.doc_dir, 'build', 'code_doc')

    def test_dist_dir(self, tmpdir):
        directory, config, _ = self._make_config(tmpdir)

        self._verify_path_attr(directory, config, '_dist_dir', config.dist_dir, 'dist')

    def test_library_dist_dir(self, tmpdir):
        directory, config, _ = self._make_config(tmpdir)

        self._verify_path_attr(directory, config, '_lib_dir', config.library_dist_dir, 'dist', 'lib_target')

    def test_application_dist_dir(self, tmpdir):
        directory, config, _ = self._make_config(tmpdir)

        self._verify_path_attr(directory, config, '_app_dir', config.application_dist_dir, 'dist', 'app_target')

    def test_entry_point(self, tmpdir):
        _, _, package_config = self._make_config(tmpdir)

        assert package_config.get_entry_point() is None

        package_config.entry_point = 'entry point'

        assert package_config.get_entry_point() == 'entry point'

    def test_package_sources(self, tmpdir):
        _, java_config, package_config = self._make_config(tmpdir)

        assert package_config.package_sources(java_config) is True

        java_config.type = 'application'

        assert package_config.package_sources(java_config) is False

        package_config.sources = True

        assert package_config.package_sources(java_config) is True

        java_config.type = 'library'

        assert package_config.package_sources(java_config) is True

    def test_package_doc(self, tmpdir):
        _, java_config, package_config = self._make_config(tmpdir)

        assert package_config.package_doc(java_config) is True

        java_config.type = 'application'

        assert package_config.package_doc(java_config) is False

        package_config.doc = True

        assert package_config.package_doc(java_config) is True

        java_config.type = 'library'

        assert package_config.package_doc(java_config) is True


class TestGetJavaCVersion(object):
    def test_working_javac_version_call(self):
        for version in ['14', '14.3', '14.2.1']:
            process = FakeProcess(['javac', '-version'], stdout=f'Java {version}\n')

            with FakeProcessContext(process):
                assert get_javac_version() == (version, 14)

    def test_javac_version_call_failure(self):
        # noinspection PyUnusedLocal
        def failing_call(args: Sequence[str], capture: bool, cwd: Path) -> CompletedProcess:
            raise FileNotFoundError('no javac!')

        with FakeProcessContext(failing_call):
            assert get_javac_version() == (None, None)


class TestVerboseOptions(object):
    def test_add_verbose_options_not_verbose_enough(self):
        options = []

        _add_verbose_options(options)

        assert options == []

    def test_add_verbose_options_no_extras(self):
        options = []

        with Options(verbose=2):
            _add_verbose_options(options)

        assert options == []

        with Options(verbose=3):
            _add_verbose_options(options)

        assert options == ['-verbose']

    def test_add_verbose_options_with_extras_only(self):
        options = []

        with Options(verbose=2):
            _add_verbose_options(options, '-bogus1', '-bogus2')

        assert options == ['-bogus1', '-bogus2']

    def test_add_verbose_options_inserted_first(self):
        options = ['--flag', 'other-thing']

        with Options(verbose=3):
            _add_verbose_options(options)

        assert options == ['-verbose', '--flag', 'other-thing']

        options = ['--flag', 'other-thing']

        with Options(verbose=3):
            _add_verbose_options(options, '-bogus1', '-bogus2')

        assert options == ['-verbose', '-bogus1', '-bogus2', '--flag', 'other-thing']


class TestAddClassPath(object):
    def test_add_class_path(self):
        dep = Dependency('dep', {
            'location': 'local',
            'version': '4.5.6',
            'scope': 'scope'
        })
        dps_list = [
            DependencyPathSet(dep, Path('a.jar')),
            DependencyPathSet(dep, Path('b.jar')),
            DependencyPathSet(dep, Path('c.jar'))
        ]
        expected_class_path = os.pathsep.join(['a.jar', 'b.jar', 'c.jar'])
        options = []

        _add_class_path(options, dps_list)

        assert options == ['--class-path', expected_class_path]


class TestBuildNames(object):
    def test_build_names(self):
        dependency = Dependency('dep', {
            'location': 'remote',
            'version': '4.5.6',
            'scope': 'scope'
        })

        assert build_names(dependency) == (
            'https://repo1.maven.org/maven2/dep/dep/4.5.6', Path('dep'), 'dep-4.5.6'
        )
