"""
This file contains all the unit tests for our framework's dependencies support.
"""
from pathlib import Path
from typing import Any, Optional, Sequence, Union
from unittest.mock import call, patch, MagicMock

# noinspection PyPackageRequirements
import pytest

# noinspection PyProtectedMember
from builder.dependencies import Dependency, DependencySet, RemoteFile, LocalFile, ResolverData, DependencyResolver, \
    _add_file_to_path, _resolve_remote_file, _signature_match_found
from builder.project import Project
from builder.schema import EmptySchema
from builder.schema_validator import SchemaValidator
from tests.test_support import get_test_path, Options


class TestDependencyObject(object):
    def test_given(self):
        dep = Dependency.given('repo', 'group', 'name', '1.2.3', 'scope')

        compare(dep, 'repo', 'group', 'name', '1.2.3', ['scope'])

        dep = Dependency.given('repo', 'name', 'name', '1.2.3', 'scope')

        compare(dep, 'repo', 'name', 'name', '1.2.3', ['scope'])

        dep = Dependency.given('repo', None, 'name', '1.2.3', 'scope')

        compare(dep, 'repo', 'name', 'name', '1.2.3', ['scope'])

        dep = Dependency.given('repo', None, 'name', '1.2.3', ['scope'])

        compare(dep, 'repo', 'name', 'name', '1.2.3', ['scope'])

        dep = Dependency.given('repo', None, 'name', '1.2.3', None)

        compare(dep, 'repo', 'name', 'name', '1.2.3', [])

    def test_applies_to(self):
        dep = Dependency.given('repo', None, 'name', '1.2.3', 'scope')

        assert dep.applies_to('scope') is True
        assert dep.applies_to('bad_scope') is False

    def test_format(self):
        dep = Dependency.given('repo', None, 'name', '1.2.3', 'scope')

        assert dep.format('{name}.jar') == 'name.jar'
        assert dep.format('{name}-{version}.jar') == 'name-1.2.3.jar'
        assert dep.format('{group}-{name}-{version}.jar') == 'name-name-1.2.3.jar'

    def test_repr(self):
        dep = Dependency.given('repo', None, 'name', '1.2.3', ['scope'])

        assert repr(dep) == 'name:name:1.2.3'

        dep = Dependency.given('repo', 'group', 'name', '1.2.3', ['scope'])

        assert repr(dep) == 'group:name:1.2.3'

    def test_equality(self):
        dep1 = Dependency.given('repo', None, 'name', '1.2.3', ['scope'])
        dep2 = Dependency.given('repo', 'group', 'name', '1.2.3', ['scope'])
        dep3 = Dependency.given('repo', None, 'name', '1.2.3', ['scope'])

        assert dep1 == dep1
        assert dep1 == dep3
        assert dep1 != dep2


def compare(dep, repo, group, name, version, scope):
    assert dep.repo == repo
    assert dep.group == group
    assert dep.name == name
    assert dep.version == version
    assert dep.scope == scope


_set_test_data = {
    'dep1': {
        'repo': 'repo1',
        'version': '1.2.3',
        'scope': 'task'
    },
    'dep2': {
        'repo': 'repo2',
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

        compare(dep_set._dependencies['dep1'], 'repo1', 'dep1', 'dep1', '1.2.3', ['task'])
        compare(dep_set._dependencies['dep2'], 'repo2', 'dep2', 'dep2', '4.5.6', ['task'])

    def test_get_dependencies_for(self):
        dep_set = DependencySet(_set_test_data)

        assert len(dep_set.get_dependencies_for("bogus")) == 0

        deps = dep_set.get_dependencies_for('task')

        assert len(deps) == 2

        dep1 = deps[0]
        dep2 = deps[1]

        # Make sure order is correct for consistent testing.
        if dep1.name == 'dep2':
            dep1, dep2 = dep2, dep1

        compare(dep1, 'repo1', 'dep1', 'dep1', '1.2.3', ['task'])
        compare(dep2, 'repo2', 'dep2', 'dep2', '4.5.6', ['task'])


class TestRemoteFile(object):
    # noinspection PyProtectedMember
    def test_remote_file_creation_no_signatures(self):
        dep = Dependency.given('repo', None, 'name', '1.2.3', 'task')
        url = 'http://example.com/path/to/file.jar'
        rf = RemoteFile(dep, url)

        assert rf._parent is dep
        assert rf._file_url == url
        assert rf._local_name == Path('file.jar')
        assert rf._signatures == []
        assert rf._meta_file is None
        assert rf._meta_file_parser is None

    # noinspection PyProtectedMember
    def test_remote_file_creation_with_signatures(self):
        dep = Dependency.given('repo', None, 'name', '1.2.3', 'task')
        url = 'http://example.com/path/to/file.jar'
        rf = RemoteFile(dep, url, signature_names=['sha1'])

        assert rf._parent is dep
        assert rf._file_url == url
        assert rf._local_name == Path('file.jar')
        assert rf._signatures == ['sha1']
        assert rf._meta_file is None
        assert rf._meta_file_parser is None

    # noinspection PyProtectedMember
    def test_remote_file_creation_with_cache_parent(self):
        dep = Dependency.given('repo', None, 'name', '1.2.3', 'task')
        url = 'http://example.com/path/to/file.jar'
        rf = RemoteFile(dep, url, cache_file_parent='path/to')

        assert rf._parent is dep
        assert rf._file_url == url
        assert rf._local_name == Path('path/to/file.jar')
        assert rf._signatures == []
        assert rf._meta_file is None
        assert rf._meta_file_parser is None

    def test_remote_file_properties(self):
        dep = Dependency.given('repo', None, 'name', '1.2.3', 'task')
        url = 'http://example.com/path/to/file.jar'
        rf = RemoteFile(dep, url)

        assert rf.file_url == url
        assert rf.local_name == Path('file.jar')

    def test_get_signature_files(self):
        dep = Dependency.given('repo', None, 'name', '1.2.3', 'task')
        rf = RemoteFile(dep, 'http://example.com/path/to/file.jar', signature_names=['sha1'])
        info = rf.get_signature_file_info()

        assert len(info) == 1
        assert len(info[0]) == 3

        signature, name, path = info[0]

        assert signature == 'sha1'
        assert name == 'http://example.com/path/to/file.jar.sha1'
        assert path == Path('file.jar.sha1')

        dep = Dependency.given('repo', None, 'name', '1.2.3', 'task')
        rf = RemoteFile(dep, 'http://example.com/path/to/file.jar', signature_names=['sha1'],
                        cache_file_parent='path/to')
        info = rf.get_signature_file_info()

        assert len(info) == 1
        assert len(info[0]) == 3

        signature, name, path = info[0]

        assert signature == 'sha1'
        assert name == 'http://example.com/path/to/file.jar.sha1'
        assert path == Path('path/to/file.jar.sha1')

    def test_get_meta_file_info(self):
        dep = Dependency.given('repo', None, 'name', '1.2.3', 'task')
        rf = RemoteFile(dep, 'http://example.com/path/to/file.jar')
        mrf = RemoteFile(dep, 'http://other.com/path/to/dep.jar')

        rf.set_meta_file(mrf, _bogus_parser)

        f, p = rf.get_meta_file_info()

        assert f is mrf
        assert p is _bogus_parser


class TestLocalFile(object):
    # noinspection PyProtectedMember
    def test_local_file_creation(self):
        dep = Dependency.given('repo', None, 'name', '1.2.3', 'task')
        path = Path('path/to/file.ext')
        lf = LocalFile(dep, path)

        assert lf._dependency is dep
        assert lf._path == path
        assert lf._meta_file is None
        assert lf._meta_file_parser is None

    def test_local_file_properties(self):
        dep = Dependency.given('repo', None, 'name', '1.2.3', 'task')
        path = Path('path/to/file.ext')
        lf = LocalFile(dep, path)

        assert lf.dependency == dep
        assert lf.path == path

    def test_get_meta_file_info(self):
        dep = Dependency.given('repo', None, 'name', '1.2.3', 'task')
        path = Path('path/to/file.ext')
        meta_path = Path('path/to/file.ext2')
        lf = LocalFile(dep, path)
        mlf = LocalFile(dep, meta_path)

        lf.set_meta_file(mlf, _bogus_parser)

        f, p = lf.get_meta_file_info()

        assert f is mlf
        assert p is _bogus_parser


class TestResolverData(object):
    def test_resolver_data(self):
        schema = SchemaValidator(EmptySchema())
        data = ResolverData(_bogus_resolver, schema, TestResolverData)

        assert data.function == _bogus_resolver
        assert data.schema == schema
        assert data.config_class == TestResolverData


# noinspection PyProtectedMember,DuplicatedCode
class TestDependencyResolver(object):
    def test_dependency_resolver_creation(self):
        dr = DependencyResolver()

        assert dr._resolvers == {}
        assert dr._name_patterns == {}

    def test_register_functions(self):
        dr = DependencyResolver()
        rd = ResolverData(_bogus_resolver)

        dr.register_resolver('repo', rd)
        dr.register_name_format('java', 'the-format')

        assert dr._resolvers == {'repo': rd}
        assert dr._name_patterns == {'java': 'the-format'}

    def test_resolve(self):
        dr = DependencyResolver()
        dep = Dependency.given('repo', None, 'name', '1.2.3', 'task')
        lf = LocalFile(dep, Path('file.ext'))
        files = [(lf, dep)]

        mock_verify = MagicMock()
        mock_to_files = MagicMock()
        mock_resolve = MagicMock()

        mock_to_files.return_value = files

        dr._verify_repos_are_supported = mock_verify
        dr._to_files = mock_to_files
        dr._resolve_file_to_paths = mock_resolve

        paths = dr.resolve('java', [dep])

        # Since calls are mocked...
        assert len(paths) == 0

        assert mock_verify.mock_calls == [call([dep])]
        assert mock_to_files.mock_calls == [call('java', [dep])]
        assert mock_resolve.mock_calls == [call('java', lf, dep, [])]

    def test_verify_repos_are_supported(self):
        dr = DependencyResolver()
        dep = Dependency.given('repo', None, 'name', '1.2.3', 'task')
        dep2 = Dependency.given('repo2', None, 'name', '1.2.3', 'task')

        with pytest.raises(ValueError) as error:
            dr._verify_repos_are_supported([dep])

        assert error.value.args[0] == ['The repository named repo is not known so cannot be used.']

        with pytest.raises(ValueError) as error:
            dr._verify_repos_are_supported([dep, dep2])

        assert error.value.args[0] == [
            'The repository named repo is not known so cannot be used.',
            'The repository named repo2 is not known so cannot be used.'
        ]

        dr.register_resolver('repo', ResolverData(_bogus_resolver))

        # This should not error.
        dr._verify_repos_are_supported([dep])

    def test_to_files_no_language(self):
        project = Project.from_dir(Path('path/to/project'))
        dr = DependencyResolver()
        dep = Dependency.given('repo', None, 'name', '1.2.3', 'task')
        lf = LocalFile(dep, Path('file.ext'))
        mock = MagicMock()

        mock.return_value = lf
        dr.register_resolver('repo', ResolverData(mock))

        with Options(project=project):
            files = dr._to_files('java', [dep])

        assert mock.mock_calls == [call(dep, None, {})]
        assert len(files) == 1
        assert len(files[0]) == 2

        f, d = files[0]

        assert f is lf
        assert d == dep

    def test_to_files_with_language(self):
        project = Project.from_dir(Path('path/to/project'))
        dr = DependencyResolver()
        dep = Dependency.given('repo', None, 'name', '1.2.3', 'task')
        lf = LocalFile(dep, Path('file.ext'))
        mock = MagicMock()

        mock.return_value = lf
        dr.register_resolver('repo', ResolverData(mock))
        dr.register_name_format('java', '{group}-{name}-{version}.jar')

        with Options(project=project):
            files = dr._to_files('java', [dep])

        assert mock.mock_calls == [call(dep, 'name-name-1.2.3.jar', {})]
        assert len(files) == 1
        assert len(files[0]) == 2

        f, d = files[0]

        assert f is lf
        assert d == dep

    def test_resolve_file_to_paths_local(self):
        dr = DependencyResolver()
        dep = Dependency.given('repo', None, 'name', '1.2.3', 'task')
        path = Path('file.ext')
        lf = LocalFile(dep, path)
        paths = []

        dr._resolve_file_to_paths('java', lf, dep, paths)

        assert paths == [path]

    def test_resolve_file_to_paths_remote(self):
        dr = DependencyResolver()
        dep = Dependency.given('repo', None, 'name', '1.2.3', 'task')
        path = Path('file.ext')
        rf = RemoteFile(dep, 'http://example.com/path/to/file.ext')
        lf = LocalFile(dep, path)
        paths = []

        with patch('builder.dependencies._resolve_remote_file') as mock:
            mock.return_value = lf

            dr._resolve_file_to_paths('java', rf, dep, paths)

        assert paths == [path]

    def test_resolve_file_to_paths_meta_no_transients(self):
        dr = DependencyResolver()
        dep = Dependency.given('repo', None, 'name', '1.2.3', 'task')
        path = Path('file.ext')
        lf = LocalFile(dep, path)
        lf_meta = LocalFile(dep, Path('file.meta'))
        paths = []

        mock_parser = MagicMock()
        mock_parser.return_value = None

        lf.set_meta_file(lf_meta, mock_parser)

        dr._resolve_file_to_paths('java', lf, dep, paths)

        assert paths == [path]

    def test_resolve_file_to_paths_meta_with_transients(self):
        dr = DependencyResolver()
        dep = Dependency.given('repo', None, 'name', '1.2.3', 'task')
        dep2 = Dependency.given('repo', None, 'name2', '1.2.7', 'task')
        path = Path('file.ext')
        lf = LocalFile(dep, path)
        meta = Path('file.meta')
        lf_meta = LocalFile(dep, meta)
        paths = []

        mock_resolve = MagicMock()
        mock_parser = MagicMock()
        mock_parser.return_value = [dep2]

        lf.set_meta_file(lf_meta, mock_parser)

        dr._resolve = mock_resolve

        dr._resolve_file_to_paths('java', lf, dep, paths)

        assert mock_resolve.mock_calls == [call('java', [dep2], [path])]
        assert paths == [path]


# noinspection DuplicatedCode
class TestDRSupportFunctions(object):
    def test_add_file_to_path(self):
        dep = Dependency.given('repo', None, 'name', '1.2.3', 'task')
        path1 = Path('file1.ext')
        path2 = Path('file2.ext')
        file1 = LocalFile(dep, path1)
        file2 = LocalFile(dep, path2)
        paths = []

        _add_file_to_path(file1, paths)

        assert paths == [path1]

        _add_file_to_path(file1, paths)

        assert paths == [path1]

        _add_file_to_path(file2, paths)

        assert paths == [path1, path2]

        _add_file_to_path(file2, paths)

        assert paths == [path1, path2]

    def test_resolve_remote_file_resolve_fail(self):
        dep = Dependency.given('repo', None, 'name', '1.2.3', 'task')
        url = 'http://example.com/fake/file.ext'
        path = Path('file.ext')
        rf = RemoteFile(dep, url)
        expected = [call(url, path, optional=False)]

        with patch('builder.dependencies.file_cache') as mock:
            mock.resolve_file.return_value = None

            assert _resolve_remote_file(rf, dep) is None
            assert mock.resolve_file.mock_calls == expected

    def test_resolve_remote_file_resolve_no_signatures(self):
        dep = Dependency.given('repo', None, 'name', '1.2.3', 'task')
        url = 'http://example.com/fake/file.ext'
        path = Path('file.ext')
        rf = RemoteFile(dep, url)
        expected = [call(url, path, optional=False)]

        with patch('builder.dependencies.file_cache') as mock:
            mock.resolve_file.return_value = path

            result = _resolve_remote_file(rf, dep)

            assert isinstance(result, LocalFile)
            assert result.dependency == dep
            assert result.path == path
            assert mock.resolve_file.mock_calls == expected

    def test_resolve_remote_file_resolve_with_meta(self):
        dep = Dependency.given('repo', None, 'name', '1.2.3', 'task')
        file_url = 'http://example.com/fake/file.ext'
        meta_url = 'http://example.com/fake/file.meta'
        file_path = Path('file.ext')
        meta_path = Path('file.meta')
        rf = RemoteFile(dep, file_url)
        expected = [call(file_url, file_path, optional=False), call(meta_url, meta_path, optional=True)]

        rf.set_meta_file(RemoteFile(dep, meta_url), _bogus_parser)

        with patch('builder.dependencies.file_cache') as mock:
            mock.resolve_file.side_effect = [file_path, meta_path]

            result = _resolve_remote_file(rf, dep)

            assert mock.resolve_file.mock_calls == expected

            assert isinstance(result, LocalFile)
            assert result.dependency == dep
            assert result.path == file_path

            lf, parser = result.get_meta_file_info()

            assert isinstance(lf, LocalFile)
            assert lf.dependency == dep
            assert lf.path == meta_path
            assert parser is _bogus_parser

    def test_resolve_remote_file_resolve_missing_meta(self):
        dep = Dependency.given('repo', None, 'name', '1.2.3', 'task')
        file_url = 'http://example.com/fake/file.ext'
        meta_url = 'http://example.com/fake/file.meta'
        file_path = Path('file.ext')
        meta_path = Path('file.meta')
        rf = RemoteFile(dep, file_url)
        expected = [call(file_url, file_path, optional=False), call(meta_url, meta_path, optional=True)]

        rf.set_meta_file(RemoteFile(dep, meta_url), _bogus_parser)

        with patch('builder.dependencies.file_cache') as mock:
            mock.resolve_file.side_effect = [file_path, None]

            result = _resolve_remote_file(rf, dep)

            assert mock.resolve_file.mock_calls == expected

            assert isinstance(result, LocalFile)
            assert result.dependency == dep
            assert result.path == file_path

            lf, parser = result.get_meta_file_info()

            assert lf is None
            assert parser is None

    def test_resolve_remote_file_resolve_bad_signatures(self):
        dep = Dependency.given('repo', None, 'name', '1.2.3', 'task')
        url = 'http://example.com/fake/file.ext'
        file_path = Path('file.ext')
        rf = RemoteFile(dep, url, ['sha9'])

        with patch('builder.dependencies.file_cache') as mock:
            mock.resolve_file.side_effect = [file_path, None]

            with pytest.raises(ValueError) as error:
                _ = _resolve_remote_file(rf, dep)

            assert error.value.args[0] == f'Could not verify the downloaded file {url}.'

    def test_signature_match_found_no_signatures(self):
        path = Path('file.ext')

        assert _signature_match_found(path, []) is True

    def test_signature_match_missing_signature_file(self):
        path = Path('file.ext.sha9')

        with patch('builder.dependencies.file_cache') as mock:
            mock.resolve_file.return_value = None

            assert _signature_match_found(path, [('sha9', '', path)]) is False

    def test_signature_match_unmatched_signature_file(self):
        local_path = Path('file.ext')
        signature_path = get_test_path('dependencies/test.sha1')

        with patch('builder.dependencies.file_cache') as mock:
            mock.resolve_file.return_value = signature_path

            with patch('builder.dependencies.sign_path') as signer:
                signer.return_value = 'Bogus SHA value'

                with patch('builder.dependencies.verbose_out') as vo:
                    assert _signature_match_found(
                        local_path, [('sha1', 'http://example.com/path/to/file.sha1', local_path)]
                    ) is False

                # noinspection SpellCheckingInspection
                assert vo.mock_calls == [
                    call('sha1: 3c1bb0cd5d67dddc02fae50bf56d3a3a4cbc7204 != Bogus SHA value for file.ext.')
                ]

    def test_signature_match_matched_signature_file(self):
        local_path = Path('file.ext')
        signature_path = get_test_path('dependencies/test.sha1')

        with patch('builder.dependencies.file_cache') as mock:
            mock.resolve_file.return_value = signature_path

            with patch('builder.dependencies.sign_path') as signer:
                signer.return_value = '3c1bb0cd5d67dddc02fae50bf56d3a3a4cbc7204'

                with patch('builder.dependencies.verbose_out') as vo:
                    assert _signature_match_found(
                        local_path, [('sha1', 'http://example.com/path/to/file.sha1', local_path)]
                    ) is True

                # noinspection SpellCheckingInspection
                assert vo.mock_calls == []


# noinspection PyUnusedLocal
def _bogus_parser(path: Path, dependency: Dependency) -> Optional[Sequence[Dependency]]:
    return None


# noinspection PyUnusedLocal
def _bogus_resolver(dependency: Dependency, name: str, config: Any) -> Union[RemoteFile, LocalFile]:
    return LocalFile(dependency, Path('path/to/file.ext'))


# noinspection PyUnusedLocal
def _bogus_resolve_remote_file(file: RemoteFile, path: Path, optional: bool = False) -> Optional[LocalFile]:
    dep = Dependency.given('repo', None, 'name', '1.2.3', 'task')
    return LocalFile(dep, Path('path/to/file.ext'))
