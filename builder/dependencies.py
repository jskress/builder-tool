"""
This library provides support for handling dependencies.
"""
from pathlib import Path
from typing import Sequence, Optional, Callable, Union, Tuple, List, Any

from builder.file_cache import file_cache
from builder.schema_validator import SchemaValidator
from builder.signing import sign_path
from builder.utils import verbose_out, global_options


class Dependency(object):
    @classmethod
    def given(cls, repo, group, name, version, scope):
        content = {
            'repo': repo,
            'name': name,
            'version': version
        }
        if group and group != name:
            content['groupId'] = group
        if scope:
            content['scope'] = scope
        return Dependency(name, content)

    def __init__(self, key: str, content: dict):
        self._key = key
        self._repo = content['repo']
        self._group_id = content['groupId'] if 'groupId' in content else None
        self._name = content['name'] if 'name' in content else key
        self._version = content['version']
        self._scope = content['scope']

        if isinstance(self._scope, str):
            self._scope = [self._scope]

    def repo(self) -> str:
        return self._repo

    def group(self) -> str:
        return self._group_id or self._name

    def name(self) -> str:
        return self._name

    def version(self) -> str:
        return self._version

    def scope(self) -> Sequence[str]:
        return self._scope

    def applies_to(self, task: str) -> bool:
        return task in self._scope

    def __repr__(self):
        return '%s:%s:%s' % (self.group(), self._name, self._version)

    def __eq__(self, other):
        if not isinstance(other, Dependency):
            return NotImplemented
        return repr(self) == repr(other)

    def __ne__(self, other):
        return not self == other


class DependencySet(object):
    def __init__(self, dependencies: dict):
        self._dependencies = {key: Dependency(key, value) for key, value in dependencies.items()}

    def get_dependencies_for(self, task: str) -> Sequence[Dependency]:
        return [dependency for dependency in self._dependencies.values() if dependency.applies_to(task)]


MetaFileParser = Callable[[Path, Dependency], Optional[Sequence[Dependency]]]


class RemoteFile(object):
    def __init__(self, parent: Dependency, file_url: str, signature_extensions: Optional[Sequence[str]] = None,
                 cache_file_parent: Optional[str] = None):
        self._parent = parent
        self._file_url = file_url
        self._local_name = Path(file_url.split('/')[-1])
        self._signatures = signature_extensions or []
        self._meta_file = None
        self._meta_file_parser = None

        if cache_file_parent:
            parent = Path(cache_file_parent)
            self._local_name = parent / self._local_name

    def add_meta_file(self, meta_file: 'RemoteFile', meta_file_parser: MetaFileParser):
        self._meta_file = meta_file
        self._meta_file_parser = meta_file_parser
        return self

    def file_url(self) -> str:
        return self._file_url

    def local_name(self) -> Path:
        return self._local_name

    def get_signature_files(self) -> Sequence[Tuple[str, str, Path]]:
        result = []
        for ext in self._signatures:
            url = f'{self._file_url}.{ext}'
            name = f'{self._local_name.name}.{ext}'
            result.append((ext, url, self._local_name.parent / name))
        return result

    def get_meta_file_info(self) -> Tuple['RemoteFile', MetaFileParser]:
        return self._meta_file, self._meta_file_parser


class LocalFile(object):
    def __init__(self, dependency: Dependency, path: Path):
        self._dependency = dependency
        self._path = path
        self._meta_file = None
        self._meta_file_parser = None

    def add_meta_file(self, meta_file: 'LocalFile', meta_file_parser: MetaFileParser):
        self._meta_file = meta_file
        self._meta_file_parser = meta_file_parser
        return self

    def get_dependency(self):
        return self._dependency

    def get_path(self):
        return self._path

    def get_meta_file_info(self) -> Tuple['LocalFile', MetaFileParser]:
        return self._meta_file, self._meta_file_parser


DependencyResolverFunction = Callable[[Dependency, Optional[Any]], Union[RemoteFile, LocalFile]]


class DependencyResolver(object):
    def __init__(self):
        self._resolvers = {}

    def register_resolver(self, name: str, resolver: DependencyResolverFunction,
                          schema: Optional[SchemaValidator] = None, config_class: Optional[str] = None):
        self._resolvers[name] = (resolver, schema, config_class)

    def resolve(self, dependencies: Sequence[Dependency]) -> Sequence[Path]:
        paths = []
        self._resolve(dependencies, paths)
        return paths

    def _resolve(self, dependencies: Sequence[Dependency], paths: List[Path]):
        self._verify_repos_are_supported(dependencies)
        files = self._to_files(dependencies)
        while len(files) > 0:
            file, dependency = files.pop(0)
            self._resolve_file_to_paths(file, dependency, paths)

    def _verify_repos_are_supported(self, dependencies: Sequence[Dependency]):
        errors = []
        for dependency in dependencies:
            repo = dependency.repo()
            if repo not in self._resolvers:
                errors.append(f'The repository named {repo} is not known so cannot be used.')
        if len(errors) > 0:
            raise ValueError(errors)

    def _to_files(self, dependencies: Sequence[Dependency]) ->\
            List[Tuple[Union[RemoteFile, LocalFile], Dependency]]:
        project = global_options.project()
        files = []
        for dependency in dependencies:
            resolver = self._resolvers[dependency.repo()]
            config = project.get_config(dependency.repo(), resolver[1], resolver[2])
            files.append((resolver[0](dependency, config), dependency))
        return files

    def _resolve_file_to_paths(self, file: Union[RemoteFile, LocalFile], dependency: Dependency, paths: List[Path]):
        if isinstance(file, RemoteFile):
            file = _resolve_remote_file(file, dependency)

        meta_file, parser = file.get_meta_file_info()

        if meta_file:
            transients = parser(meta_file.get_path(), meta_file.get_dependency())
            if transients:
                self._resolve(transients, paths)

        _add_file_to_path(file, paths)


def _add_file_to_path(file: LocalFile, paths: List[Path]):
    path = file.get_path()

    if path not in paths:
        paths.append(path)


def _resolve_remote_file(file: RemoteFile, dependency: Dependency, optional: bool = False) -> Optional[LocalFile]:
    path = file_cache.resolve_file(file.file_url(), file.local_name(), optional=optional)

    if not path:
        return None

    if not _signature_match_found(path, file.get_signature_files()):
        raise ValueError(f'Could not verify the downloaded file {file.file_url()}')

    local_file = LocalFile(dependency, path)
    meta_file, parser = file.get_meta_file_info()

    if meta_file:
        meta_path = _resolve_remote_file(meta_file, dependency, optional=True)

        if meta_path:
            local_file.add_meta_file(meta_path, parser)

    return local_file


def _signature_match_found(path: Path, signatures: Sequence[Tuple[str, str, Path]]) -> bool:
    # If there are no reference signatures to match, we'll assume life is ok.
    if not signatures:
        return True

    matched = False

    for signature_name, signature_url, local_name in signatures:
        signature_file = file_cache.resolve_file(signature_url, local_name, optional=True)
        if signature_file:
            reference_signature = signature_file.read_text()
            hashed_signature = sign_path(signature_name, path)
            matched = reference_signature == hashed_signature
            if not matched:
                verbose_out(f'{signature_name}: {reference_signature} != {hashed_signature}')

        if matched:
            return True

    return False


dependency_resolver = DependencyResolver()
