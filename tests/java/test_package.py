"""
This file contains all the unit tests for our packaging support.
"""
import json
from pathlib import Path
from unittest.mock import patch, call

# noinspection PyPackageRequirements
import pytest
from builder.java.modules import ModuleData, Variant, API_ELEMENTS, SOURCE_ELEMENTS

from builder.java import JavaConfiguration, PackageConfiguration
# noinspection PyProtectedMember
from builder.java.package import _build_jar_options, _include_directory, _get_packaging_dirs, _find_entry_point, \
    _create_manifest, _run_packager, java_package, _create_module_data, _set_file_attributes, _add_variant
from builder.models import Dependency, DependencyPathSet
from builder.project import Project
from tests.test_support import Options, FakeProcessContext, FakeProcess, get_test_path, Regex


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
        doc_dir = project_dir / Path('build/code/javadoc')
        resources_dir = project_dir / Path('src/resources')
        output_dir = project_dir / Path(f'dist/{dist_dir}')
        expected = (code_dir, classes_dir, doc_dir, resources_dir, output_dir)

        classes_dir.mkdir(parents=True)
        doc_dir.mkdir(parents=True)

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
        lines = _create_manifest('1.2.3', 'my desc')

        assert lines == [
            'Manifest-Version: 1.0',
            Regex(r'Created-By: \d+(?:\.\d+(?:\.\d+)?)? [(]Builder, v\d+\.\d+\.\d+[)]'),
            'Specification-Title: my desc',
            'Specification-Version: 1.2.3',
            'Implementation-Title: my desc',
            'Implementation-Version: 1.2.3'
        ]


class TestModuleDataCreation(object):
    @staticmethod
    def _compare_to_file(module_data: ModuleData, name):
        path = get_test_path(f'java/package/{name}.json')
        actual = module_data.to_dict()
        expected = json.loads(path.read_text(encoding='utf-8'))

        assert actual == expected

    def test_create_module_data(self):
        project = Project.from_dir(Path('/path/to/project'), version='1.3.4')

        with Options(project=project):
            module_data = _create_module_data()

        self._compare_to_file(module_data, 'basic_module')

    def test_set_file_attributes_not_docs(self):
        variant = Variant(API_ELEMENTS)

        _set_file_attributes(variant, "library", "api", None)

        assert variant.to_dict() == {
            'name': API_ELEMENTS,
            'attributes': {
                'org.gradle.category': 'library',
                'org.gradle.dependency.bundling': 'external',
                'org.gradle.jvm.version': 15,
                'org.gradle.libraryelements': 'jar',
                'org.gradle.usage': 'java-api'
            }
        }

    def test_set_file_attributes_docs(self):
        variant = Variant(SOURCE_ELEMENTS)

        _set_file_attributes(variant, 'documentation', 'runtime', 'sources')

        assert variant.to_dict() == {
            'name': SOURCE_ELEMENTS,
            'attributes': {
                'org.gradle.category': 'documentation',
                'org.gradle.dependency.bundling': 'external',
                'org.gradle.docstype': 'sources',
                'org.gradle.usage': 'java-runtime'
            }
        }

    def test_add_variant_no_dependencies(self, tmpdir):
        path = Path(str(tmpdir)) / 'fake.jar'
        project = Project.from_dir(Path('/path/to/project'), version='1.3.4')

        path.write_text("Testing\n", encoding='utf-8')

        with Options(project=project):
            module_data = _create_module_data()

        _add_variant(module_data, API_ELEMENTS, path, {}, 'library', 'api', None, [])

        self._compare_to_file(module_data, 'variant_1')

    def test_add_variant_with_dependencies(self, tmpdir):
        path = Path(str(tmpdir)) / 'fake.jar'
        project = Project.from_dir(Path('/path/to/project'), version='1.3.4')

        path.write_text("Testing\n", encoding='utf-8')

        with Options(project=project):
            module_data = _create_module_data()

        dependency = Dependency('dep', {
            'location': 'remote',
            'version': '1.2.3',
            'scope': 'scope'
        })

        transient = dependency.derive_from('group', 'name', '1.2.4')
        transient.transient = True
        path_sets = [DependencyPathSet(dependency, path), DependencyPathSet(transient, path)]

        _add_variant(module_data, API_ELEMENTS, path, {}, 'library', 'api', None, path_sets)

        self._compare_to_file(module_data, 'variant_2')


# noinspection DuplicatedCode
class TestRunJar(object):
    def test_jar_no_resources(self):
        jar_file = Path('file.jar')
        directory = Path('classes')
        expected = [
            'jar', '--create', '--file', str(jar_file), '--manifest', Regex('.*'), '-C', str(directory), '.'
        ]
        manifest = _create_manifest('1.2.3', 'my desc')

        with FakeProcessContext(FakeProcess(expected)):
            with patch('builder.java.package.sign_path') as mock_signer:
                mock_signer.return_value = {}

                result = _run_packager(manifest, None, jar_file, directory, None)

            mock_signer.assert_called_once_with(jar_file)

            assert result == {}

    def test_jar_no_manifest(self):
        jar_file = Path('file.jar')
        directory = Path('classes')
        expected = [
            'jar', '--create', '--file', str(jar_file), '-C', str(directory), '.'
        ]

        with FakeProcessContext(FakeProcess(expected)):
            with patch('builder.java.package.sign_path') as mock_signer:
                mock_signer.return_value = {}

                result = _run_packager(None, None, jar_file, directory, None)

            mock_signer.assert_called_once_with(jar_file)

            assert result == {}

    def test_jar_with_resources(self):
        jar_file = Path('file.jar')
        directory = Path('classes')
        resources = get_test_path('java/javap')
        expected = [
            'jar', '--create', '--file', str(jar_file), '--manifest', Regex('.*'), '-C', str(directory), '.',
            '-C', str(resources), '.'
        ]
        manifest = _create_manifest('1.2.3', 'my desc')

        with FakeProcessContext(FakeProcess(expected)):
            with patch('builder.java.package.sign_path') as mock_signer:
                mock_signer.return_value = {}

                result = _run_packager(manifest, None, jar_file, directory, resources)

            mock_signer.assert_called_once_with(jar_file)

            assert result == {}


# noinspection DuplicatedCode
class TestJavaPackage(object):
    def test_no_source(self, tmpdir):
        project_dir = Path(str(tmpdir))
        project = Project.from_dir(project_dir, name='test', version='1.2.3')

        with Options(project=project):
            java_config = JavaConfiguration()
            task_config = PackageConfiguration()

        task_config.sources = False
        task_config.doc = False

        jar_file = java_config.library_dist_dir(ensure=True) / 'test-1.2.3.jar'
        directory = java_config.classes_dir()
        expected = [
            'jar', '--create', '--file', str(jar_file), '--manifest', Regex('.*'), '-C', str(directory), '.'
        ]

        with FakeProcessContext(FakeProcess(expected)):
            with Options(project=project):
                with patch('builder.java.package.sign_path') as mock_signer:
                    mock_signer.return_value = {}

                    java_package(java_config, task_config, [])

        mock_signer.assert_called_once_with(jar_file)

    def test_sources_no_dir(self, tmpdir):
        project_dir = Path(str(tmpdir))
        project = Project.from_dir(project_dir, name='test', version='1.2.3')

        with Options(project=project):
            config = JavaConfiguration()
            task_config = PackageConfiguration()

        task_config.doc = False

        jar_file = config.library_dist_dir(ensure=True) / 'test-1.2.3.jar'
        directory = config.classes_dir()
        code_dir = config.code_dir()
        expected = [
            'jar', '--create', '--file', str(jar_file), '--manifest', Regex('.*'), '-C', str(directory), '.'
        ]

        with FakeProcessContext(FakeProcess(expected)):
            with pytest.raises(ValueError) as info:
                with Options(project=project):
                    with patch('builder.java.package.sign_path') as mock_signer:
                        mock_signer.return_value = {}

                        java_package(config, task_config, [])

        mock_signer.assert_called_once_with(jar_file)

        assert info.value.args[0] == f'Cannot build a sources archive since {code_dir} does not exist.'

    def test_sources_with_dir(self, tmpdir):
        project_dir = Path(str(tmpdir))
        project = Project.from_dir(project_dir, name='test', version='1.2.3')

        with Options(project=project):
            config = JavaConfiguration()
            task_config = PackageConfiguration()

        task_config.doc = False

        jar_file = config.library_dist_dir(ensure=True) / 'test-1.2.3.jar'
        sources_jar_file = config.library_dist_dir() / 'test-1.2.3-sources.jar'
        directory = config.classes_dir()
        code_dir = config.code_dir(ensure=True)
        expected_jar = [
            'jar', '--create', '--file', str(jar_file), '--manifest', Regex('.*'), '-C', str(directory), '.'
        ]
        expected_sources = [
            'jar', '--create', '--file', str(sources_jar_file), '-C', str(code_dir), '.'
        ]

        with FakeProcessContext([FakeProcess(expected_jar), FakeProcess(expected_sources)]):
            with Options(project=project):
                with patch('builder.java.package.sign_path') as mock_signer:
                    mock_signer.return_value = {}

                    java_package(config, task_config, [])

        assert mock_signer.mock_calls == [call(jar_file), call(sources_jar_file)]

    def test_javadoc_no_dir(self, tmpdir):
        project_dir = Path(str(tmpdir))
        project = Project.from_dir(project_dir, name='test', version='1.2.3')

        with Options(project=project):
            config = JavaConfiguration()
            task_config = PackageConfiguration()

        task_config.sources = False

        jar_file = config.library_dist_dir() / 'test-1.2.3.jar'
        directory = config.classes_dir()
        doc_dir = config.doc_dir()
        expected = [
            'jar', '--create', '--file', str(jar_file), '--manifest', Regex('.*'), '-C', str(directory), '.'
        ]

        with FakeProcessContext(FakeProcess(expected)):
            with pytest.raises(ValueError) as info:
                with Options(project):
                    with patch('builder.java.package.sign_path') as mock_signer:
                        mock_signer.return_value = {}

                        java_package(config, task_config, [])

            assert info.value.args[0] == f'Cannot build a JavaDoc archive since {doc_dir} does not exist.'

    def test_javadoc_with_dir(self, tmpdir):
        project_dir = Path(str(tmpdir))
        project = Project.from_dir(project_dir, name='test', version='1.2.3')

        with Options(project=project):
            config = JavaConfiguration()
            task_config = PackageConfiguration()

        task_config.sources = False

        jar_file = config.library_dist_dir(ensure=True) / 'test-1.2.3.jar'
        doc_jar_file = config.library_dist_dir() / 'test-1.2.3-javadoc.jar'
        directory = config.classes_dir()
        doc_dir = config.doc_dir(ensure=True)
        expected_jar = [
            'jar', '--create', '--file', str(jar_file), '--manifest', Regex('.*'), '-C', str(directory), '.'
        ]
        expected_doc = [
            'jar', '--create', '--file', str(doc_jar_file), '-C', str(doc_dir), '.'
        ]

        with FakeProcessContext([FakeProcess(expected_jar), FakeProcess(expected_doc)]):
            with Options(project=project):
                with patch('builder.java.package.sign_path') as mock_signer:
                    mock_signer.return_value = {}

                    java_package(config, task_config, [])
