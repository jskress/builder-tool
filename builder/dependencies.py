"""
This library provides support for handling dependencies.
"""
from pathlib import Path
from typing import Dict, Sequence, Optional, Callable, Union, Tuple, List, Any
from urllib.parse import urlparse

from builder.file_cache import file_cache
from builder.schema_validator import SchemaValidator
from builder.signing import sign_path
from builder.utils import verbose_out, global_options


class Dependency(object):
    """
    Instances of this class represent a dependency specified in a project file.
    """
    @classmethod
    def given(cls, repo: str, group: Optional[str], name: str, version: str, scope: Union[str, Sequence[str], None]):
        """
        A function that creates a dependency object.  If a group name is not specified,
        it is assumed to be the same as the name.  The name, or names, provided as the
        scope of the dependency represent the tasks to which the dependency applies.

        :param repo: the name of the repository that contains the dependent artifacts.
        :param group: the name of the group the dependency belongs to.
        :param name: the name of the dependency.
        :param version: the version (in semver form) of the dependency.
        :param scope: the scope of the dependency.
        """
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

    def __init__(self, key: str, content: Dict[str, Any]):
        """
        A function to create an instance of the ``Dependency`` class.  Since schema
        validation is done on project file load, we don't bother with any validation
        of the contents of the ``content`` dictionary here.

        :param key: the key by which this dependency is known. This must be the same
        as the ``content['name']`` field.
        :param content: a dictionary of the data that specifies the dependency.
        """
        self._key = key
        self._repo = content['repo']
        self._group_id = content['groupId'] if 'groupId' in content else None
        self._name = content['name'] if 'name' in content else key
        self._version = content['version']

        if 'scope' in content:
            self._scope = content['scope']

            if isinstance(self._scope, str):
                self._scope = [self._scope]
        else:
            self._scope = []

    @property
    def repo(self) -> str:
        """
        A read-only property that returns the name of the repository that hosts the
        dependency.

        :return: the name of the dependency's repository.
        """
        return self._repo

    @property
    def group(self) -> str:
        """
        A read-only property that returns the name of the group that the dependency
        belongs to.

        :return: the name of the dependency's group.
        """
        return self._group_id or self._name

    @property
    def name(self) -> str:
        """
        A read-only property that returns the name of the dependency.

        :return: the name of the dependency.
        """
        return self._name

    @property
    def version(self) -> str:
        """
        A read-only property that returns the version of the dependency.

        :return: the version of the dependency.
        """
        return self._version

    @property
    def scope(self) -> Sequence[str]:
        """
        A read-only property that returns a list containing the names of the tasks
        to which this dependency applies.

        :return: the tasks that the dependency applies to.
        """
        return self._scope

    def applies_to(self, task: str) -> bool:
        """
        A function that returns whether or not this dependency applies to a specific
        task.

        :param task: the name of the task to test.
        :return: ``True`` if the dependency applies to the specified task or ``False``
        if not.
        """
        return task in self._scope

    def format(self, format_pattern: str):
        """
        A function to format a string based on details from this dependency.  We support
        three variables; ``group``, ``name`` and ``version``.  Surround them with braces
        in the format pattern for proper substitution.

        :param format_pattern: the format pattern to fill in.
        """
        return format_pattern.format(group=self.group, name=self._name, version=self._version)

    def __repr__(self):
        return f'{self.group}:{self._name}:{self._version}'

    def __eq__(self, other):
        if not isinstance(other, Dependency):
            return NotImplemented
        return repr(self) == repr(other)

    def __ne__(self, other):
        return not self == other


class DependencySet(object):
    """
    Instances of this class represent a set of dependencies.  The primary responsibility
    here is to produce a list of dependencies that apply to a particular task.
    """
    def __init__(self, dependencies: Dict[str, Any]):
        """
        A function to create an instance of the ``DependencySet`` class.  Since schema
        validation is done on project file load, we don't bother with any validation
        of the contents of the ``dependencies`` dictionary here.

        :param dependencies: a dictionary of the data that specifies the set of dependencies.
        """
        self._dependencies = {key: Dependency(key, value) for key, value in dependencies.items()}

    def get_dependencies_for(self, task: str) -> Sequence[Dependency]:
        """
        A function that returns the list of dependencies that apply to the specified task.
        The list returned may be empty.

        :param task: the task whose applicable dependencies should be returned.
        :return: the list of dependencies that apply to the given task, which may be an
        empty list.
        """
        return [dependency for dependency in self._dependencies.values() if dependency.applies_to(task)]


MetaFileParser = Callable[[Path, Dependency], Optional[Sequence[Dependency]]]


class RemoteFile(object):
    """
    Instances of this class represent a remote file.  A remote file may carry a list
    of possible signatures which may be used to verify the file once it has been
    downloaded.  It may also carry a meta file which may be used to enumerate any
    dependencies on which the remote file itself may depend.

    When signatures are provided, each is tried in turn to validate the downloaded
    file.  Once one signature is found to match, it is considered good.
    """
    def __init__(self, parent: Dependency, file_url: str, signature_names: Optional[Sequence[str]] = None,
                 cache_file_parent: Optional[str] = None):
        """
        A function to create an instance of the ``RemoteFile`` class.

        :param parent: the dependency to which this remote file belongs.
        :param file_url: the URL from which the file we are to represent will be
        downloaded.
        :param signature_names: the list of signature names (such as ``sha1``) to
        try to validate the integrity of the main file when it is downloaded.
        """
        parsed = urlparse(file_url)
        self._parent = parent
        self._file_url = file_url
        self._local_name = Path(parsed.path.split('/')[-1])
        self._signatures = signature_names or []
        self._meta_file = None
        self._meta_file_parser = None

        if cache_file_parent:
            parent_path = Path(cache_file_parent)
            self._local_name = parent_path / self._local_name

    def set_meta_file(self, meta_file: 'RemoteFile', meta_file_parser: MetaFileParser):
        """
        A function that is used to set meta file information for this remote file.  Meta
        files are used to note any dependencies required by the one this file represents.

        :param meta_file: the remote file representing the meta information for this one.
        :param meta_file_parser: a function that may be used to parse the meta file once
        it is downloaded.
        """
        self._meta_file = meta_file
        self._meta_file_parser = meta_file_parser
        return self

    @property
    def file_url(self) -> str:
        """
        A read-only property that returns the URL from which this file may be retrieved..

        :return: the URL for this file.
        """
        return self._file_url

    @property
    def local_name(self) -> Path:
        """
        A read-only property that returns the path to the local file where this file
        should be downloaded.  It will always be a relative path.

        :return: the path to where this file should be stored locally, relative to an
        arbitrary root path.
        """
        return self._local_name

    def get_signature_file_info(self) -> Sequence[Tuple[str, str, Path]]:
        """
        A function that returns information about any signature files that should be
        used to validate the download of the file we represent.

        For each signature we carry, a tuple will be returned where the first entry
        contains the signature name, the second entry contains the URL for the signature
        file and the third entry, the relative path for the local signature file.

        If this remote file was created with no signatures, then the result will be an
        empty list.

        :return: the (possibly empty) list of signature file information.
        """
        result = []
        for ext in self._signatures:
            url = f'{self._file_url}.{ext}'
            name = f'{self._local_name.name}.{ext}'
            result.append((ext, url, self._local_name.parent / name))
        return result

    def get_meta_file_info(self) -> Tuple['RemoteFile', MetaFileParser]:
        """
        A function that returns any meta file information for this remote file.  Meta
        files are used to note any dependencies required by the one this file represents.

        :return: a tuple of the remote meta file and a function to parse it.
        """
        return self._meta_file, self._meta_file_parser


class LocalFile(object):
    """
    Instances of this class represent a local file.
    """
    def __init__(self, dependency: Dependency, path: Path):
        """
        A function to create an instance of the ``LocalFile`` class.

        :param dependency: the dependency to which this local file belongs.
        :param path: the path that represents the file in the file system.
        """
        self._dependency = dependency
        self._path = path
        self._meta_file = None
        self._meta_file_parser = None

    def set_meta_file(self, meta_file: 'LocalFile', meta_file_parser: MetaFileParser):
        """
        A function that is used to set meta file information for this local file.  Meta
        files are used to note any dependencies required by the one this file represents.

        :param meta_file: the local file representing the meta information for this one.
        :param meta_file_parser: a function that may be used to parse the meta file.
        """
        self._meta_file = meta_file
        self._meta_file_parser = meta_file_parser
        return self

    @property
    def dependency(self):
        """
        A read-only property that returns the dependency to which this local file belongs.

        :return: the dependency this file supports.
        """
        return self._dependency

    @property
    def path(self):
        """
        A read-only property that returns the path to the local file this file represents.
        It is always an absolute file.

        :return: the path to the file we represent.
        """
        return self._path

    def get_meta_file_info(self) -> Tuple['LocalFile', MetaFileParser]:
        """
        A function that returns any meta file information for this local file.  Meta
        files are used to note any dependencies required by the one this file represents.

        :return: a tuple of the local meta file and a function to parse it.
        """
        return self._meta_file, self._meta_file_parser


DependencyResolverFunction = Callable[[Dependency, str, Optional[Any]], Union[RemoteFile, LocalFile]]


class ResolverData(object):
    """
    Instances of this class represent the data for a repository needed to convert
    dependency information into either remote or local file information..
    """
    def __init__(self, function: DependencyResolverFunction, schema: Optional[SchemaValidator] = None,
                 config_class: Optional[object] = None):
        """
        A function to create an instance of the ``ResolverData`` class.

        :param function: the actual resolution function that should be used.
        :param schema: an optional schema for validating the related repository's configuration
        information.
        :param schema: an optional class for holding the related repository's configuration
        information.
        """
        self._function = function
        self._schema = schema
        self._config_class = config_class

    @property
    def function(self) -> DependencyResolverFunction:
        """
        A read-only property that returns the function that may be used to resolve dependencies
        into files, either remote or local.

        :return: the function to use for dependency resolution.
        """
        return self._function

    @property
    def schema(self) -> Optional[SchemaValidator]:
        """
        A read-only property that returns the schema, if any, that should be used to
        validate any configuration information for the repository this resolver supports.

        :return: the validation schema for the related repository's configuration
        information.
        """
        return self._schema

    @property
    def config_class(self):
        """
        A read-only property that returns the configuration class, if any, that should be
        used to pass configuration information to the resolver function.

        :return: the class for the related repository's configuration information.
        """
        return self._config_class


class DependencyResolver(object):
    """
    Instances of this class represent the means for resolving dependencies into local files.
    A resolver may result in remote files which are then cached and used locally.
    """
    def __init__(self):
        """
        A function to create an instance of the ``DependencyResolver`` class.  This class is
        designed to be a singleton so this function should never be used.  Use the
        ``dependency_resolver`` attribute from this module for all resolver work.
        """
        self._resolvers: Dict[str, ResolverData] = {}
        self._name_patterns: Dict[str, str] = {}

    def register_resolver(self, name: str, resolver: ResolverData):
        """
        A function for registering a repository resolver.

        :param name: the name of the repository that the resolver supports.
        :param resolver: the data about the resolver for the named repository.
        """
        self._resolvers[name] = resolver

    def register_name_format(self, language: str, name_format: str):
        """
        A function for registering a file name pattern for a language.  It is assumed that
        each language has a primary name format for a dependent file (like a library or a
        jar file).  This format describes how fields from a dependency are injected into
        the file name.

        :param language: the language to which the format should apply.
        :param name_format the file name pattern for the language's dependent file.
        """
        self._name_patterns[language] = name_format

    def resolve(self, language: str, dependencies: Sequence[Dependency]) -> Sequence[Path]:
        """
        A function that is used to resolve dependencies to local file system paths.
        Secondary dependencies are accounted for and will be included in the returned
        list.  No local path will appear in the resulting list more than once.

        :param language: the current language in play.
        :param dependencies: the list of dependencies to resolve to local file system
        paths.
        """
        paths = []
        self._resolve(language, dependencies, paths)
        return paths

    def _resolve(self, language: str, dependencies: Sequence[Dependency], paths: List[Path]):
        """
        A function that is used to resolve dependencies to paths and add them to a
        list.  Secondary dependencies are accounted for and will be included.  No
        local path will be in the ``paths`` list more than once.

        :param language: the current language in play.
        :param dependencies: the list of dependencies to resolve to local file system
        paths.
        :param paths: the list to add resolved paths to.
        """
        self._verify_repos_are_supported(dependencies)
        files = self._to_files(language, dependencies)
        while len(files) > 0:
            file, dependency = files.pop(0)
            self._resolve_file_to_paths(language, file, dependency, paths)

    def _verify_repos_are_supported(self, dependencies: Sequence[Dependency]):
        """
        A function that takes a list of dependencies and verifies that a resolver for the
        repository in each dependency has been registered.  If not, an error is raised.
        All dependencies are checked.  The resulting ``ValueError`` will have messages for
        each one that carries a repository name for which there is no resolver.

        :param dependencies: the list of dependencies to check.
        :raises ValueError: when a named repository does not have a registered resolver.
        """
        errors = []
        for dependency in dependencies:
            repo = dependency.repo
            if repo not in self._resolvers:
                errors.append(f'The repository named {repo} is not known so cannot be used.')
        if len(errors) > 0:
            raise ValueError(errors)

    def _to_files(self, language, dependencies: Sequence[Dependency]) ->\
            List[Tuple[Union[RemoteFile, LocalFile], Dependency]]:
        """
        A function that converts a list of dependencies into a list of tuples, each of
        which contains a remote or local file and the associated dependency.

        :param language: the language currently in play.
        :param dependencies: the list of dependencies to resolve to files.
        :return: a list of tuples, each containing a remote or local file and the
        associated dependency.
        """
        project = global_options.project()
        name_format = self._name_patterns[language] if language in self._name_patterns else None
        files = []
        for dependency in dependencies:
            name = None if name_format is None else dependency.format(name_format)
            resolver = self._resolvers[dependency.repo]
            config = project.get_config(dependency.repo, resolver.schema, resolver.config_class)
            files.append((resolver.function(dependency, name, config), dependency))
        return files

    def _resolve_file_to_paths(self, language, file: Union[RemoteFile, LocalFile], dependency: Dependency,
                               paths: List[Path]):
        """
        A function that resolves a  remote or local file into a list of paths.  As
        remote and local files are resolved to file system paths, they are added to the
        give path list so long as they are not already present.  If a file has a meta
        file, it is parsed for secondary dependencies.  If such dependencies are found,
        then they too are resolved through remote/local files to and added to the path
        list.

        :param language: the current language in play.
        :param file: the remote or local file to resolve.
        :param dependency: the dependency the specified file belongs to.
        :param paths: the list to add new paths to.
        """
        if isinstance(file, RemoteFile):
            file = _resolve_remote_file(file, dependency)

        meta_file, parser = file.get_meta_file_info()

        if meta_file:
            transients = parser(meta_file.path, meta_file.dependency)
            if transients:
                self._resolve(language, transients, paths)

        _add_file_to_path(file, paths)


def _add_file_to_path(file: LocalFile, paths: List[Path]):
    """
    A function to add the path from a local file to a list of paths.  Each path is
    guaranteed to appear in the list only once.

    :param file: the local file whose path should be included in the list.
    :param paths: the list of paths to add the local file's path to.
    """
    path = file.path

    if path not in paths:
        paths.append(path)


def _resolve_remote_file(file: RemoteFile, dependency: Dependency, optional: bool = False) -> Optional[LocalFile]:
    """
    A function to resolve a remote file into a local one.  If the remote file contains
    meta file information, that too is resolved to a local file.

    :param file: the remote file to resolve to a local one.
    :param dependency: the dependency that owns the remote file.
    :param optional: a flag that notes whether the file is optional.  This is only used
    on the recursive call to resolve the remote file's meta file.  It should be ``False``
    (the default) for all other calls.
    :return the remote file as a local file.
    """
    path = file_cache.resolve_file(file.file_url, file.local_name, optional=optional)

    if not path:
        return None

    if not _signature_match_found(path, file.get_signature_file_info()):
        raise ValueError(f'Could not verify the downloaded file {file.file_url}.')

    local_file = LocalFile(dependency, path)
    meta_file, parser = file.get_meta_file_info()

    if meta_file:
        meta_path = _resolve_remote_file(meta_file, dependency, optional=True)

        if meta_path:
            local_file.set_meta_file(meta_path, parser)

    return local_file


def _signature_match_found(path: Path, signatures: Sequence[Tuple[str, str, Path]]) -> bool:
    """
    A function that determines whether one of a list of signature information can be matched
    with the signature of a file.  If the list of signatures is empty, we assume all is well
    as that implies signatures are not important.

    For each signature tuple provided, the content of the given path is signed with the
    signature algorithm.  The URL and local file is then resolved through the file cache
    and (assuming that succeeds) is compared against the generated signature.  If the two
    signatures match, we return ``True``.  If all signature algorithms fail to produce a
    match, we return ``False``.

    :param path: the path to the file to validate.
    :param signatures: a list of tuples where the first entry is the name of a signature
    algorithm (such as ``sha1``), the second entry is the URL to the remote signature
    reference file and the third entry is the local name for the signature reference file.
    """
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
                verbose_out(f'{signature_name}: {reference_signature} != {hashed_signature} for {path}.')

        if matched:
            return True

    return False


dependency_resolver = DependencyResolver()
