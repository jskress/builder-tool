"""
This file contains all the unit tests for our packaging support.
"""
from pathlib import Path

# noinspection PyPackageRequirements
import pytest

from builder.java import JavaConfiguration
# noinspection PyProtectedMember
from builder.java.package import _build_jar_options, _include_directory, _get_packaging_dirs, _find_entry_point, \
    _create_manifest, _run_packager, java_package
from builder.project import Project
from tests.test_utils import Options, FakeProcessContext, FakeProcess, get_test_path, Regex


class TestBuildOptions(object):
    def test_build_options_no_entry_point(self):
        """Make sure we build options correctly with no entry point."""
        path = Path('path/to/file.jar')
        options = _build_jar_options(path, None)

        assert options == ['--create', '--file', 'path/to/file.jar']

    def test_build_options_with_verbose(self):
        """Make sure we build options correctly with no entry point but verbosely."""
        path = Path('path/to/file.jar')

        with Options(verbose=3):
            options = _build_jar_options(path, None)

        assert options == ['-verbose', '--create', '--file', 'path/to/file.jar']

    def test_build_options_with_entry_point(self):
        """Make sure we build options correctly with an entry point."""
        path = Path('path/to/file.jar')
        options = _build_jar_options(path, 'com.me.Main')

        assert options == ['--create', '--file', 'path/to/file.jar', '--main-class', 'com.me.Main']

    def test_include_dir(self):
        """Make sure adding a directory to the jar options works correctly."""
        path = Path('path/to/dir')
        options = []

        _include_directory(options, path)

        assert options == ['-C', 'path/to/dir', '.']


class TestGetPackageDirs(object):
    @staticmethod
    def _test_for_type(tmpdir, project_type, dist_dir):
        project_dir = Path(str(tmpdir))
        project = Project.from_dir(project_dir)
        code_dir = project_dir / Path('src/code')
        classes_dir = project_dir / Path('build/code/classes')
        resources_dir = project_dir / Path('src/resources')
        output_dir = project_dir / Path(f'dist/{dist_dir}')
        expected = (code_dir, classes_dir, resources_dir, output_dir)

        classes_dir.mkdir(parents=True)

        with Options(project=project):
            config = JavaConfiguration()

        config.type = project_type
        result = _get_packaging_dirs(config)

        assert isinstance(result, tuple)
        assert result == expected

    def test_get_library_packaging_dirs(self, tmpdir):
        """Make sure we generate the right project directories for libraries."""
        self._test_for_type(tmpdir, 'library', 'lib')

    def test_get_application_packaging_dirs(self, tmpdir):
        """Make sure we generate the right project directories for applications."""
        self._test_for_type(tmpdir, 'application', 'app')


class TestFindEntryPoint(object):
    def test_no_entry_point_found(self):
        path = Path('.')  # Doesn't matter what it is.
        process = FakeProcess(None, get_test_path('java/javap/one-class-no-main.txt'), check_args=False)

        with FakeProcessContext(process):
            with pytest.raises(ValueError) as info:
                _find_entry_point(path, None)

        assert info.value.args[0] == 'No entry point found for the application.'

    def test_too_many_entry_points_found(self):
        path = Path('.')  # Doesn't matter what it is.
        process = FakeProcess(None, get_test_path('java/javap/many-classes-multi-mains.txt'), check_args=False)

        with FakeProcessContext(process):
            with pytest.raises(ValueError) as info:
                _find_entry_point(path, None)

        assert info.value.args[0] == 'Too many entry points found: com.example.ui.UIUtils, com.example.App.  You ' \
                                     'will need to specify one.'

    def test_one_entry_point_found(self):
        path = Path('.')  # Doesn't matter what it is.
        process = FakeProcess(None, get_test_path('java/javap/one-class-with-main.txt'), check_args=False)

        with FakeProcessContext(process):
            assert _find_entry_point(path, None) == 'com.example.ui.UIUtils'

    def test_specified_entry_point_not_found_zero_discovered(self):
        path = Path('.')  # Doesn't matter what it is.
        process = FakeProcess(None, get_test_path('java/javap/one-class-no-main.txt'), check_args=False)

        with FakeProcessContext(process):
            with pytest.raises(ValueError) as info:
                _find_entry_point(path, 'com.bad.EntryPoint')

        assert info.value.args[0] == 'Specified entry point com.bad.EntryPoint not found in compiled classes.'

    def test_specified_entry_point_not_found_one_discovered(self):
        path = Path('.')  # Doesn't matter what it is.
        process = FakeProcess(None, get_test_path('java/javap/one-class-with-main.txt'), check_args=False)

        with FakeProcessContext(process):
            with pytest.raises(ValueError) as info:
                _find_entry_point(path, 'com.bad.EntryPoint')

        assert info.value.args[0] == 'Specified entry point com.bad.EntryPoint not found in compiled classes.'

    def test_specified_entry_point_matches_one_discovered(self):
        path = Path('.')  # Doesn't matter what it is.
        process = FakeProcess(None, get_test_path('java/javap/one-class-with-main.txt'), check_args=False)

        with FakeProcessContext(process):
            assert _find_entry_point(path, 'com.example.ui.UIUtils') == 'com.example.ui.UIUtils'

    def test_specified_entry_point_matches_many_discovered(self):
        path = Path('.')  # Doesn't matter what it is.
        process = FakeProcess(None, get_test_path('java/javap/many-classes-multi-mains.txt'), check_args=False)

        with FakeProcessContext(process):
            assert _find_entry_point(path, 'com.example.App') == 'com.example.App'


class TestCreateManifest(object):
    def test_create_manifest(self):
        info = {'version': '1.2.3'}

        lines = _create_manifest(info, 'my desc')

        assert lines == [
            'Manifest-Version: 1.0',
            Regex(r'Created-By: \d+(?:\.\d+(?:\.\d+)?)? [(]Builder, v\d+\.\d+\.\d+[)]'),
            'Specification-Title: my desc',
            'Specification-Version: 1.2.3',
            'Implementation-Title: my desc',
            'Implementation-Version: 1.2.3'
        ]


# noinspection DuplicatedCode
class TestRunJar(object):
    def test_jar_no_resources_no_signing(self):
        jar_file = Path('file.jar')
        directory = Path('classes')
        expected = [
            'jar', '--create', '--file', str(jar_file), '--manifest', Regex('.*'), '-C', str(directory), '.'
        ]
        info = {'version': '1.2.3'}
        manifest = _create_manifest(info, 'my desc')

        with FakeProcessContext(FakeProcess(expected)):
            _run_packager(manifest, None, jar_file, directory, None, None)

    def test_jar_no_resources_with_signing(self):
        jar_file = get_test_path('java/junit.pom.xml')
        signed_file = jar_file.parent / f'{jar_file.name}.sha1'
        directory = Path('classes')
        expected = [
            'jar', '--create', '--file', str(jar_file), '--manifest', Regex('.*'), '-C', str(directory), '.'
        ]
        info = {'version': '1.2.3'}
        manifest = _create_manifest(info, 'my desc')

        with FakeProcessContext(FakeProcess(expected)):
            try:
                _run_packager(manifest, None, jar_file, directory, None, 'sha1')

                assert signed_file.is_file()
            finally:
                if signed_file.is_file():
                    signed_file.unlink()

    def test_jar_with_resources_no_signing(self):
        jar_file = Path('file.jar')
        directory = Path('classes')
        resources = get_test_path('java/javap')
        expected = [
            'jar', '--create', '--file', str(jar_file), '--manifest', Regex('.*'), '-C', str(directory), '.',
            '-C', str(resources), '.'
        ]
        info = {'version': '1.2.3'}
        manifest = _create_manifest(info, 'my desc')

        with FakeProcessContext(FakeProcess(expected)):
            _run_packager(manifest, None, jar_file, directory, resources, None)

    def test_jar_with_resources_with_signing(self):
        jar_file = get_test_path('java/junit.pom.xml')
        signed_file = jar_file.parent / f'{jar_file.name}.sha1'
        directory = Path('classes')
        resources = get_test_path('java/javap')
        expected = [
            'jar', '--create', '--file', str(jar_file), '--manifest', Regex('.*'), '-C', str(directory), '.',
            '-C', str(resources), '.'
        ]
        info = {'version': '1.2.3'}
        manifest = _create_manifest(info, 'my desc')

        with FakeProcessContext(FakeProcess(expected)):
            try:
                _run_packager(manifest, None, jar_file, directory, resources, 'sha1')

                assert signed_file.is_file()
            finally:
                if signed_file.is_file():
                    signed_file.unlink()


# noinspection DuplicatedCode
class TestJavaPackage(object):
    def test_no_source(self, tmpdir):
        project_dir = Path(str(tmpdir))
        project = Project.from_dir(project_dir)

        project.info['name'] = 'test'
        project.info['version'] = '1.2.3'

        with Options(project=project):
            config = JavaConfiguration()

        # Make sure we don't ask for a sources jar.
        config.packaging['sources'] = False

        jar_file = config.library_dist_dir() / 'test-1.2.3.jar'
        directory = config.classes_dir()
        expected = [
            'jar', '--create', '--file', str(jar_file), '--manifest', Regex('.*'), '-C', str(directory), '.'
        ]

        with FakeProcessContext(FakeProcess(expected)):
            java_package(project, config)

    def test_sources_no_dir(self, tmpdir):
        project_dir = Path(str(tmpdir))
        project = Project.from_dir(project_dir)

        project.info['name'] = 'test'
        project.info['version'] = '1.2.3'

        with Options(project=project):
            config = JavaConfiguration()

        jar_file = config.library_dist_dir() / 'test-1.2.3.jar'
        directory = config.classes_dir()
        code_dir = config.code_dir()
        expected = [
            'jar', '--create', '--file', str(jar_file), '--manifest', Regex('.*'), '-C', str(directory), '.'
        ]

        with FakeProcessContext(FakeProcess(expected)):
            with pytest.raises(ValueError) as info:
                java_package(project, config)

            assert info.value.args[0] == f'Cannot build a sources archive since {code_dir} does not exist.'

    def test_sources_with_dir(self, tmpdir):
        project_dir = Path(str(tmpdir))
        project = Project.from_dir(project_dir)

        project.info['name'] = 'test'
        project.info['version'] = '1.2.3'

        with Options(project=project):
            config = JavaConfiguration()

        jar_file = config.library_dist_dir() / 'test-1.2.3.jar'
        sources_jar_file = config.library_dist_dir() / 'test-1.2.3-sources.jar'
        directory = config.classes_dir()
        code_dir = config.code_dir(ensure=True)
        expected_jar = [
            'jar', '--create', '--file', str(jar_file), '--manifest', Regex('.*'), '-C', str(directory), '.'
        ]
        expected_sources = [
            'jar', '--create', '--file', str(sources_jar_file), '--manifest', Regex('.*'), '-C', str(code_dir), '.'
        ]

        with FakeProcessContext([FakeProcess(expected_jar), FakeProcess(expected_sources)]):
            java_package(project, config)
