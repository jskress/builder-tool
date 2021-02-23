"""
This file contains all the unit tests for our framework's dependencies support.
"""
from pathlib import Path
from typing import Dict, List, Optional

from unittest.mock import MagicMock, call

# noinspection PyPackageRequirements
import pytest

from builder.models import Dependency, DependencySet, DependencyPathSet, Language, Task, DependencyContext
from builder.signing import sign_path, supported_signatures, sign_path_to_files


def _make_dep(location: Optional[str] = 'remote', version: Optional[str] = '1.2.3',
              scope: Optional[List[str]] = None) -> Dependency:
    content = {
        'location': location,
        'name': 'name',
        'version': version
    }

    if scope:
        content['scope'] = scope

    return Dependency('dep', content)


def _assert_dep(dep: Dependency, location: str, group: str, name: str, version: str, transient: bool, scope: List[str]):
    assert dep.location == location
    assert dep.group == group
    assert dep.name == name
    assert dep.version == version
    assert dep.transient is transient
    assert dep.scope == scope


class TestTaskObject(object):
    def test_construction(self):
        task = Task('task', None)

        assert task.name == 'task'
        assert task.function is None
        assert task.require == []

        task = Task('task', None, require=['pre-task'])

        assert task.name == 'task'
        assert task.function is None
        assert task.require == ['pre-task']


class TestDependencyObject(object):
    @classmethod
    def _verify_dependency(cls, content: Dict[str, str], location: str, group: str, name: str, version: str,
                           transient: bool, scope: List[str]):
        dep = Dependency('dep', content)

        _assert_dep(dep, location, group, name, version, transient, scope)

    def test_construction(self):
        content = {
            'location': 'remote',
            'name': 'name',
            'version': '1.2.3'
        }

        self._verify_dependency(content, 'remote', 'name', 'name', '1.2.3', False, [])

        content['group'] = 'group'

        self._verify_dependency(content, 'remote', 'group', 'name', '1.2.3', False, [])

        del content['name']
        assert 'name' not in content

        self._verify_dependency(content, 'remote', 'group', 'dep', '1.2.3', False, [])

        content['scope'] = 'compile'

        self._verify_dependency(content, 'remote', 'group', 'dep', '1.2.3', False, ['compile'])

        content['scope'] = ['a', 'b']

        self._verify_dependency(content, 'remote', 'group', 'dep', '1.2.3', False, ['a', 'b'])

    def test_transient(self):
        dep = _make_dep()

        assert dep.transient is False

        dep.transient = True

        assert dep.transient is True

    def test_derive_from(self):
        source = _make_dep()
        dep = source.derive_from('group', 'name', '1.2.3')

        _assert_dep(dep, 'remote', 'group', 'name', '1.2.3', False, [])

        dep = source.derive_from('name', 'name', '1.2.3')

        _assert_dep(dep, 'remote', 'name', 'name', '1.2.3', False, [])

    def test_applies_to(self):
        dep = _make_dep(scope=['scope'])

        assert dep.applies_to('scope') is True
        assert dep.applies_to('bad_scope') is False

    def test_format(self):
        dep = _make_dep()

        assert dep.format('{name}.jar') == 'name.jar'
        assert dep.format('{name}-{version}.jar') == 'name-1.2.3.jar'
        assert dep.format('{group}-{name}-{version}.jar') == 'name-name-1.2.3.jar'

    def test_same_but_for_version(self):
        dep1 = _make_dep()
        dep2 = dep1.derive_from('group', 'name', '1.2.3')
        dep3 = dep1.derive_from('group', 'name', '4.5.6')

        assert dep1.same_but_for_version(dep1) is False
        assert dep1.same_but_for_version(dep2) is False
        assert dep2.same_but_for_version(dep1) is False
        assert dep2.same_but_for_version(dep3) is True
        assert dep3.same_but_for_version(dep2) is True

    def test_repr(self):
        dep = _make_dep()

        assert repr(dep) == 'name:name:1.2.3'

        dep = dep.derive_from('group', 'name', '4.5.6')

        assert repr(dep) == 'group:name:4.5.6'

    def test_equality(self):
        dep1 = _make_dep()
        dep2 = dep1.derive_from('group', 'name', '1.2.3')
        dep3 = _make_dep()

        assert dep1 == dep1
        assert dep1 == dep3
        assert dep1 != dep2


class TestDependencyPathSet(object):
    def test_dependency_file_construction(self):
        path = Path('path/to/file.txt')
        dep = _make_dep()
        file_set = DependencyPathSet(dep, path)

        assert file_set.dependency == dep
        assert file_set.primary_path is path

    def test_secondary_files(self):
        dep = _make_dep()
        primary_path = Path('path/to/file.txt')
        secondary_path = Path('path/to/file_2.txt')
        file_set = DependencyPathSet(dep, primary_path)

        with pytest.raises(AttributeError) as info:
            print(file_set.source_path)

        assert info.value.args[0] == "'DependencyPathSet' object has no attribute 'source_path'"

        file_set.add_secondary_path('source_path', secondary_path)

        assert file_set.source_path is secondary_path


class TestLanguageObject(object):
    def test_no_function(self):
        module = {}
        language = Language(module, 'lang')

        assert language.language == 'lang'
        assert len(language.tasks) == 0

    def test_with_function(self):
        class FakeModule(object):
            @staticmethod
            def define_language(lang: Language):
                lang.tasks = [Task('task', None)]

        module = FakeModule()
        language = Language(module, 'lang')

        assert language.language == 'lang'
        assert len(language.tasks) == 1
        assert language.tasks[0].name == 'task'


# noinspection DuplicatedCode
class TestDependencyContext(object):
    def test_construction(self):
        deps = []
        language = Language({}, 'lang')
        context = DependencyContext(deps, language, [], None)

        assert context._dependencies == deps
        assert context._dependencies is not deps
        assert context._language is language

    def test_remote_info(self):
        path = Path('.')
        context = DependencyContext([], Language({}, 'lang'), [], None)

        assert context._directory_url is None
        assert context._directory_path is None

        context.set_remote_info('the url', path)

        assert context._directory_url == 'the url'
        assert context._directory_path is path

        context.set_remote_info('http://server/path/', path)

        assert context._directory_url == 'http://server/path'
        assert context._directory_path is path

    def test_resolve_no_resolver(self):
        context = DependencyContext([], Language({}, 'lang'), [], None)

        with pytest.raises(ValueError) as info:
            context.resolve()

        assert info.value.args[0] == 'The language, lang, does not provide a means of resolving dependencies.'

    def test_resolve_no_dependencies(self):
        language = Language({}, 'lang')
        context = DependencyContext([], language, [], None)

        language.resolver = MagicMock()

        assert context.resolve() == []

    def test_resolve_basics(self):
        dep = _make_dep()
        path = Path('/path/to/file.txt')
        language = Language({}, 'lang')
        path_set = DependencyPathSet(dep, path)
        context = DependencyContext([dep], language, [], None)

        language.resolver = MagicMock(return_value=path_set)

        assert context.resolve() == [path_set]

        language.resolver.assert_called_once_with(context, dep)

    def test_resolve_duplicates(self):
        dep = _make_dep()
        path = Path('/path/to/file.txt')
        language = Language({}, 'lang')
        path_set = DependencyPathSet(dep, path)
        context = DependencyContext([dep, dep], language, [], None)

        language.resolver = MagicMock(return_value=path_set)

        assert context.resolve() == [path_set]

        language.resolver.assert_called_once_with(context, dep)

    def test_resolve_to_nothing(self):
        dep = _make_dep()
        language = Language({}, 'lang')
        context = DependencyContext([dep], language, [], None)

        language.resolver = MagicMock(return_value=None)

        with pytest.raises(ValueError) as info:
            context.resolve()

        assert info.value.args[0] == 'The dependency, name:name:1.2.3, could not be resolved.'

        language.resolver.assert_called_once_with(context, dep)

    def test_resolve_version_mismatch(self):
        dep1 = _make_dep(version='1.2.3')
        dep2 = _make_dep(version='4.5.6')
        path = Path('/path/to/file.txt')
        language = Language({}, 'lang')
        path_set = DependencyPathSet(dep1, path)
        context = DependencyContext([dep1, dep2], language, [], None)

        language.resolver = MagicMock(return_value=path_set)

        with pytest.raises(ValueError) as info:
            context.resolve()

        assert info.value.args[0] == 'The same library, name:name, is required at two different versions, 1.2.3 vs. ' \
                                     '4.5.6.'

        language.resolver.assert_called_once_with(context, dep1)

    def test_add_dependency(self):
        dep = _make_dep()
        context = DependencyContext([], Language({}, 'lang'), [], None)

        assert dep.transient is False
        assert len(context._dependencies) == 0

        context.add_dependency(dep)

        assert dep.transient is True
        assert len(context._dependencies) == 1
        assert context._dependencies[0] is dep

    def test_to_local_file_no_path(self):
        mock_fetch = MagicMock(return_value=None)
        dep = _make_dep()
        context = DependencyContext([], Language({}, 'lang'), [], None)

        context._fetch_file = mock_fetch

        assert context.to_local_path(dep, 'file.txt') is None

        mock_fetch.assert_called_once_with(dep, 'file.txt')

    def test_to_local_file_empty_signatures(self):
        path = 'file.txt'
        mock_fetch = MagicMock(return_value=path)
        dep = _make_dep()
        context = DependencyContext([], Language({}, 'lang'), [], None)

        context._fetch_file = mock_fetch

        assert context.to_local_path(dep, 'file.txt', {}) is path

        mock_fetch.assert_called_once_with(dep, 'file.txt')

    def test_to_local_file_bad_passed_signatures(self, tmpdir):
        directory = Path(str(tmpdir))
        path = directory / 'file.txt'
        mock_fetch = MagicMock(return_value=path)
        dep = _make_dep()
        context = DependencyContext([], Language({}, 'lang'), [], None)
        context._fetch_file = mock_fetch

        path.write_text("file content.\n")

        with pytest.raises(ValueError) as info:
            context.to_local_path(dep, 'file.txt', {'sha512': 'bad-signature'})

        assert info.value.args[0] == 'Could not verify the signature of the file file.txt.'
        assert mock_fetch.mock_calls == [call(dep, 'file.txt')]

    def test_to_local_file_good_passed_signatures(self, tmpdir):
        directory = Path(str(tmpdir))
        path = directory / 'file.txt'
        mock_fetch = MagicMock(return_value=path)
        dep = _make_dep()
        context = DependencyContext([], Language({}, 'lang'), [], None)
        context._fetch_file = mock_fetch

        path.write_text("file content.\n")

        signatures = sign_path(path)

        assert context.to_local_path(dep, 'file.txt', signatures) is path
        assert mock_fetch.mock_calls == [call(dep, 'file.txt')]

    def test_to_local_file_bad_file_signatures(self, tmpdir):
        directory = Path(str(tmpdir))
        path = directory / 'file.txt'
        mock_fetch = MagicMock(return_value=path)
        dep = _make_dep()
        context = DependencyContext([], Language({}, 'lang'), [], None)
        context._fetch_file = mock_fetch
        file_names = ['file.txt']
        file_names.extend([f'file.txt.{sn}' for sn in supported_signatures])

        path.write_text("file content.\n")

        with pytest.raises(ValueError) as info:
            context.to_local_path(dep, 'file.txt')

        assert info.value.args[0] == 'Could not verify the signature of the file file.txt.'
        assert mock_fetch.mock_calls == [call(dep, file_name) for file_name in file_names]

    def test_to_local_file_good_file_signatures(self, tmpdir):
        directory = Path(str(tmpdir))
        path = directory / 'file.txt'
        file_names = ['file.txt']
        file_names.extend([f'file.txt.{sn}' for sn in supported_signatures])
        mock_fetch = MagicMock(side_effect=[directory / name for name in file_names])
        dep = _make_dep()
        context = DependencyContext([], Language({}, 'lang'), [], None)
        context._fetch_file = mock_fetch
        file_names = ['file.txt']
        file_names.extend([f'file.txt.{sn}' for sn in supported_signatures])

        path.write_text("file content.\n")

        sign_path_to_files(path)

        assert context.to_local_path(dep, 'file.txt') == path
        assert mock_fetch.mock_calls == [call(dep, 'file.txt'), call(dep, f'file.txt.{supported_signatures[0]}')]

    def test_fetch_file(self):
        remote_dep = _make_dep(location='remote')
        local_dep = _make_dep(location='local')
        project_dep = _make_dep(location='project')
        p1 = Path('path1')
        p2 = Path('path2')
        p3 = Path('path3')
        context = DependencyContext([], Language({}, 'lang'), [], None)

        context._handle_remote_resolution = MagicMock(return_value=p1)
        context._handle_local_resolution = MagicMock(return_value=p2)
        context._handle_project_resolution = MagicMock(return_value=p3)

        r1 = context._fetch_file(remote_dep, 'remote.name')
        r2 = context._fetch_file(local_dep, 'local.name')
        r3 = context._fetch_file(project_dep, 'project.name')

        context._handle_remote_resolution.assert_called_once_with('remote.name')
        context._handle_local_resolution.assert_called_once_with('local.name')
        context._handle_project_resolution.assert_called_once_with('project.name')

        assert r1 is p1
        assert r2 is p2
        assert r3 is p3

    def test_handle_remote_resolution(self):
        name = 'file.txt'
        parent_url = 'http://server/path/to'
        url = parent_url + '/' + name
        parent_path = Path('path/to')
        file = parent_path / name
        return_value = Path('/resolved/path/to/' + name)
        context = DependencyContext([], Language({}, 'lang'), [], None)

        context._resolve_remotely = MagicMock(return_value=return_value)
        context.set_remote_info(parent_url, parent_path)

        rv = context._handle_remote_resolution(name)

        context._resolve_remotely.assert_called_once_with(url, file)

        assert rv is return_value

    def test_handle_local_resolution(self, tmpdir):
        directory = Path(str(tmpdir))
        good_name = 'file.txt'
        bad_name = 'no-such-file.txt'

        existing_file = directory / good_name
        existing_file.write_text("")

        context = DependencyContext([], Language({}, 'lang'), [directory], None)

        assert context._handle_local_resolution(bad_name) is None
        assert context._handle_local_resolution(good_name) == existing_file

    def test_handle_project_resolution_missing_function(self):
        context = DependencyContext([], Language({}, 'lang'), [], None)

        with pytest.raises(ValueError) as info:
            context._handle_project_resolution('name.txt')

        assert info.value.args[0] == 'The language, lang, does not provide a means of resolving project-based ' \
                                     'dependencies.'

    def test_handle_project_resolution(self, tmpdir):
        directory = Path(str(tmpdir))
        name = 'name.txt'
        path = directory / name
        mock_project = MagicMock()
        mock_project.get_config.return_value = None
        mock_cache = MagicMock()
        mock_cache.names = ['a name']
        mock_cache.get_project.return_value = mock_project
        language = Language({}, 'lang')

        language.project_as_dist_path = MagicMock(return_value=None)

        context = DependencyContext([], language, [], mock_cache)

        assert context._handle_project_resolution(name) is None

        language.project_as_dist_path = MagicMock(return_value=directory)

        assert context._handle_project_resolution(name) is None

        path.write_text("")

        assert context._handle_project_resolution(name) == path

    def test_is_empty(self):
        dep = _make_dep()
        context = DependencyContext([], Language({}, 'lang'), [], None)

        assert context.is_empty() is True

        context.add_dependency(dep)

        assert context.is_empty() is False


_set_test_data = {
    'dep1': {
        'location': 'remote',
        'version': '1.2.3',
        'scope': 'task'
    },
    'dep2': {
        'location': 'local',
        'version': '4.5.6',
        'scope': 'task'
    }
}


class TestDependencySet(object):
    # noinspection PyProtectedMember
    def test_dependency_set_creation(self):
        dep_set = DependencySet(_set_test_data)

        assert len(dep_set._dependencies) == 2
        assert 'dep1' in dep_set._dependencies
        assert 'dep2' in dep_set._dependencies

        _assert_dep(dep_set._dependencies['dep1'], 'remote', 'dep1', 'dep1', '1.2.3', False, ['task'])
        _assert_dep(dep_set._dependencies['dep2'], 'local', 'dep2', 'dep2', '4.5.6', False, ['task'])

    def test_create_dependency_context_for(self):
        dep_set = DependencySet(_set_test_data)
        context = dep_set.create_dependency_context_for('bogus', Language(None, 'fake'), [], None)

        assert context.is_empty() is True

        context = dep_set.create_dependency_context_for('task', Language(None, 'fake'), [], None)

        assert context.is_empty() is False
        assert len(context._dependencies) == 2

        dep1 = context._dependencies[0]
        dep2 = context._dependencies[1]

        # Make sure order is correct for consistent testing.
        if dep1.name == 'dep2':
            dep1, dep2 = dep2, dep1

        _assert_dep(dep1, 'remote', 'dep1', 'dep1', '1.2.3', False, ['task'])
        _assert_dep(dep2, 'local', 'dep2', 'dep2', '4.5.6', False, ['task'])
