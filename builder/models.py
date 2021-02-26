"""
This library provides our core data model..
"""
from pathlib import Path
from typing import Dict, Sequence, Optional, Callable, List, Any, Type

from builder.file_cache import file_cache
from builder.schema import ObjectSchema, StringSchema, OneOfSchema, ArraySchema, BooleanSchema
from builder.schema_validator import SchemaValidator
from builder.signing import verify_signature
from builder.utils import find


class Task(object):
    """
    Instances of this class represent a task that the builder can execute.  Instances of these
    are created by language implementations.
    """
    def __init__(self, name: str, function: Optional[Callable], require: Optional[Sequence[str]] = None,
                 configuration_class: Optional[type] = None, configuration_schema: Optional[SchemaValidator] = None,
                 needs_all_dependencies: bool = False, help_text: Optional[str] = None):
        """
        A function to create an instance of the ``Task`` class.

        :param name: the name of the task.
        :param function: the function that implements the work of the task.
        :param require: a list of task names that must be executed before this one can be.
        :param configuration_class: a class that represents the configuration for the task.
        :param configuration_schema: a validator to use in validating the configuration for
        the task.
        :param needs_all_dependencies: a flag noting whether the task is more of a housekeeping
        sort of thing and wants all project dependencies passed to it.  This allows it to receive
        all dependencies without having to be explicitly listed in the scope of each dependency.
        :param help_text: the help text to show for this task.
        """
        self.name = name
        self.function = function
        self.require = [] if require is None else require
        self.configuration_class = configuration_class
        self.configuration_schema = configuration_schema
        self.needs_all_dependencies = needs_all_dependencies
        self.help_text = help_text


_version_schema = StringSchema().format("semver")
_version_validator = SchemaValidator(_version_schema)
_full_dependency_schema = ObjectSchema()\
    .properties(
        location=StringSchema().enum('remote', 'local', 'project'),
        group=StringSchema().min_length(1),
        name=StringSchema().min_length(1),
        classifier=StringSchema().min_length(1),
        ignore_transients=BooleanSchema(),
        version=_version_schema,
        scope=OneOfSchema(
            StringSchema().min_length(1),
            ArraySchema().items(StringSchema().min_length(1))
        )
    )\
    .required('location', 'version', 'scope')\
    .additional_properties(False)
_spec_dependency_schema = ObjectSchema()\
    .properties(
        spec=StringSchema().min_length(1),
        classifier=StringSchema().min_length(1),
        ignore_transients=BooleanSchema(),
        scope=OneOfSchema(
            StringSchema().min_length(1),
            ArraySchema().items(StringSchema().min_length(1))
        )
    )\
    .required('spec', 'scope')\
    .additional_properties(False)
dependency_schema = OneOfSchema(
    _full_dependency_schema,
    _spec_dependency_schema
)


class Dependency(object):
    """
    Instances of this class represent a dependency specified in a project file.
    """
    def __init__(self, key: str, content: Dict[str, Any]):
        """
        A function to create an instance of the ``Dependency`` class.  Since schema
        validation is done on project file load, we don't bother with any validation
        of the contents of the ``content`` dictionary here.

        :param key: the key by which this dependency is known.
        :param content: a dictionary of the data that specifies the dependency.
        """
        self._resolve_spec(key, content)

        self._key = key
        self._location = content['location']
        self._group_id = content['group'] if 'group' in content else None
        self._name = content['name'] if 'name' in content else key
        self._classifier = content['classifier'] if 'classifier' in content else None
        self._ignore_transients = content['ignore_transients'] if 'ignore_transients' in content else False
        self._version = content['version']
        self._transient = False

        if 'scope' in content:
            self._scope = content['scope']

            if isinstance(self._scope, str):
                self._scope = [self._scope]
        else:
            self._scope = []

    @staticmethod
    def _resolve_spec(key: str, content: Dict[str, Any]):
        """
        A function that will parse a dependency from a spec, if one was specified.

        :param key: the key by which the dependency is known.
        :param content: a dictionary of the data that specifies the dependency.
        """
        if 'spec' in content:
            spec: str = content['spec']
            parts = spec.split(':')

            if len(parts) < 2 or len(parts) > 4:
                raise ValueError(f'Cannot make the {key} dependency from the specification, "{spec}"')

            location = parts.pop(0)
            version = parts.pop()

            if location not in ['local', 'remote', 'project']:
                raise ValueError(f'A dependency cannot have a location of {location}.')
            if not _version_validator.validate(version):
                raise ValueError(f'The version, "{version}", is not a valid version for the {key} dependency.')

            content['location'] = location
            content['version'] = version

            if len(parts) == 1:
                # Name only.
                name = parts[0].strip()

                if len(name) > 0:
                    content['name'] = name
            elif len(parts) == 2:
                # Group and name.
                group, name = (parts[0].strip(), parts[1].strip())

                if len(group) > 0:
                    content['group'] = group

                if len(name) > 0:
                    content['name'] = name

    @property
    def key(self) -> str:
        """
        A read-only property that returns the key for this dependency.
        """
        return self._key

    @property
    def location(self) -> str:
        """
        A read-only property that returns the location (remote, local or project) where
        dependency files may be found.

        :return: the location of the dependency's files.
        """
        return self._location

    @property
    def is_remote(self) -> bool:
        """
        A read-only property that returns whether or not this dependency is a remote one.

        :return: ``True``, if this dependency is remote or ``False`` otherwise.
        """
        return self._location == 'remote'

    @property
    def is_local(self) -> bool:
        """
        A read-only property that returns whether or not this dependency is a local one.

        :return: ``True``, if this dependency is local or ``False`` otherwise.
        """
        return self._location == 'local'

    @property
    def is_project(self) -> bool:
        """
        A read-only property that returns whether or not this dependency is a project one.

        :return: ``True``, if this dependency is project or ``False`` otherwise.
        """
        return self._location == 'project'

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
    def classifier(self) -> Optional[str]:
        """
        A read-only property that returns the classifier, if any, of the dependency.

        :return: the classifier of the dependency.
        """
        return self._classifier

    @property
    def ignore_transients(self) -> Optional[str]:
        """
        A read-only property that returns whether or not any transient dependencies noted
        by this dependency should be ignored.

        :return: the whether or not the transient dependencies for this dependency should
        be ignored.
        """
        return self._ignore_transients

    @property
    def version(self) -> str:
        """
        A read-only property that returns the version of the dependency.

        :return: the version of the dependency.
        """
        return self._version

    @property
    def transient(self) -> bool:
        """
        The get side of a property that indicates whether this is a transient dependency
        or not.

        :return: ``True`` if this is a transient dependency or ``False`` if not.
        """
        return self._transient

    @transient.setter
    def transient(self, value: bool):
        """
        The set side of a property that indicates whether this is a transient dependency
        or not.

        :param value: the new value for the transient property; ``True`` if this is a
        transient dependency or ``False`` if not.
        """
        self._transient = value

    def derive_from(self, group: str, name: str, version: str) -> 'Dependency':
        """
        A function that creates a dependency object off this one.  The dependency returned
        will inherit the same location and scope as this one.

        :param group: the name of the group the dependency belongs to.
        :param name: the name of the dependency.
        :param version: the version (in semver form) of the dependency.
        :return: the derived dependency.
        """
        content = {
            'location': self._location,
            'group': group,
            'name': name,
            'version': version,
            'scope': self._scope
        }
        return Dependency(name, content)

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

    def same_but_for_version(self, other: 'Dependency') -> bool:
        """
        This method tests to see if a given dependency is the same as this one except at
        a different version.

        :param other: the dependency to compare against.
        :return: ``True`` if the dependencies are the same except for version number.
        """
        return self.group == other.group and self._name == other._name and self._version != other._version

    def __repr__(self):
        return self.format('{group}:{name}:{version}')

    def __eq__(self, other):
        if not isinstance(other, Dependency):
            return NotImplemented
        return repr(self) == repr(other)

    def __ne__(self, other):
        return not self == other


class DependencyPathSet(object):
    """
    Instances of this class represent a set of path that a dependency represents.
    """
    def __init__(self, dependency: Dependency, primary_file: Path):
        """
        A function that creates instances of the ``DependencyPathSet`` class.

        :param dependency: the dependency to whom this path set belongs.
        :param primary_file: the primary file of the path set.
        """
        self._dependency = dependency
        self._primary_path = primary_file
        self._secondary_paths: Dict[str, Path] = {}

    @property
    def dependency(self) -> Dependency:
        """
        A read-only property that returns the dependency to which this set of paths belongs.

        :return: the dependency we belong to.
        """
        return self._dependency

    @property
    def primary_path(self) -> Path:
        """
        A read-only property that returns the primary path of the dependency.

        :return: the dependency's primary file.
        """
        return self._primary_path

    def add_secondary_path(self, key: str, path: Path):
        """
        This function is used to add a secondary path to the dependency file set.
        Once a secondary file has been stored in this way, it is accessible by
        the key as an attribute name.

        :param key: the key by which the secondary path should be known.
        :param path: the secondary path to remember.
        """
        self._secondary_paths[key] = path

    def has_secondary_path(self, key: str) -> bool:
        """
        A function that returns whether this path set contains a secondary file known by
        the given key.

        :param key: the key to test.
        :return: ``True`` if we have a secondary file known by the given key or ``False``
        if not.
        """
        return key in self._secondary_paths

    def __getattr__(self, key):
        if key not in self._secondary_paths:
            raise AttributeError(f"'DependencyPathSet' object has no attribute '{key}'")
        return self._secondary_paths[key]


ResolveDependencyFunction = Callable[['DependencyContext', Dependency], Optional[DependencyPathSet]]
ProjectConfigToPathFunction = Callable[[Any], Optional[Path]]


class Language(object):
    def __init__(self, module, language: str):
        self.language = language
        self.configuration_class: Optional[Type] = None
        self.configuration_schema: Optional[SchemaValidator] = None
        self.tasks: Sequence[Task] = []
        self.resolver: Optional[ResolveDependencyFunction] = None
        self.project_as_dist_path: Optional[ProjectConfigToPathFunction] = None

        function = getattr(module, 'define_language', None)

        if function:
            function(self)

    def get_task(self, name: str) -> Optional[Task]:
        """
        A function that returns the named task.  If there is no task that carries the
        requested name, then ``None`` will be returned.

        :param name: the name of the desired task.
        :return: the requested task or ``None``.
        """
        return find(self.tasks, lambda task: task.name == name)


class DependencyContext(object):
    """
    Instances of this class represent a dependency context for a task.  This includes
    the collection of dependencies that apply to a particular task and getting them
    resolved to an appropriate set of files.
    """
    def __init__(self, dependencies: List[Dependency], language: Language, local_paths: List[Path],
                 project_cache):
        """
        A function to create an instance of the ``TaskDependencies`` class.

        :param dependencies: the list of dependencies that are directly required for a task.
        :param language: the language definition that the related task belongs to.
        :param local_paths: the list of local path locations.
        :param project_cache: the current project cache.
        """
        self._dependencies = dependencies.copy()
        self._language = language
        self._resolve_remotely = file_cache.resolve_file
        self._directory_url: Optional[str] = None
        self._directory_path: Optional[Path] = None
        self._local_paths = local_paths
        self._project_cache = project_cache

    def split(self) -> List['DependencyContext']:
        """
        A function that creates copies of this context, one copy for each dependency.  In
        other words, each resulting context will have one, and only one, dependency in it.
        This allows for easily capturing all the transient dependency information for a
        dependency.

        :return: a list of contexts, one for each of our own dependencies.
        """
        return [
            DependencyContext([dependency], self._language, self._local_paths, self._project_cache)
            for dependency in self._dependencies
        ]

    @property
    def dependencies(self) -> List[Dependency]:
        """
        A read-only property containing the list of our dependencies.

        :return: the dependencies from this context.
        """
        return self._dependencies.copy()

    @property
    def local_paths(self) -> List[Path]:
        """
        A read-only property containing the list of local paths we were created to look in.
        These are used in resolving local dependencies.

        :return: the local paths for this context.
        """
        return self._local_paths

    def set_remote_info(self, directory_url: str, directory_path: Path):
        """
        A function used to set the remote URL and local directory scope for this context.

        :param directory_url: the parent URL where file assets may be found.
        :param directory_path: the local path, relative to the file cache, where remote files
        should be downloaded.
        """
        if directory_url.endswith('/'):
            directory_url = directory_url[:-1]

        self._directory_url = directory_url
        self._directory_path = directory_path

    def resolve(self) -> List[DependencyPathSet]:
        """
        A function that resolves our list of dependencies into a list of dependency path sets.

        :return: the resulting list of dependency path sets.
        """
        if not self._language.resolver:
            raise ValueError(
                f'The language, {self._language.language}, does not provide a means of resolving dependencies.'
            )

        done: List[Dependency] = []
        result: List[DependencyPathSet] = []

        while len(self._dependencies) > 0:
            dependency = self._dependencies.pop(0)

            # Already done it?  Move along.
            if dependency in done:
                continue

            # Now see if we have the same library but at a different version.
            similar = next((item for item in done if dependency.same_but_for_version(item)), None)

            if similar is not None:
                raise ValueError(
                    f'The same library, {dependency.group}:{dependency.name}, is required at two different versions, '
                    f'{similar.version} vs. {dependency.version}.'
                )

            # All good, so resolve it.
            path_set = self._language.resolver(self, dependency)

            if not path_set:
                raise ValueError(f'The dependency, {dependency}, could not be resolved.')

            result.append(path_set)
            done.append(dependency)

        return result

    def add_dependency(self, dependency):
        """
        A function that will add the given dependency to our required set.  It is assumed
        that the dependency is a transient, as opposed to a primary, one.

        :param dependency: the dependency to include into the context.
        """
        dependency.transient = True

        self._dependencies.append(dependency)

    def to_local_path(self, dependency: Dependency, name: str, signatures: Optional[Dict[str, str]] = None)\
            -> Optional[Path]:
        """
        A function that will isolate a path for the given dependency.  If the dependency
        is located remotely, it will be downloaded via the local file cache.  This
        process will include any appropriate signature validation.  If no signature map
        is provided (``signatures`` is ``None``), it is assumed that signature validation
        should use a parallel file of the same name as given but including a signature
        algorithm as the final extension.  To bypass signature processing completely,
        specify an empty map for ``signatures``.

        For remote dependencies to resolve correctly, the ``set_remote_info()`` function
        should have already been called.

        :param dependency: the dependency the file belongs to.
        :param name: the name of the desired file.
        :param signatures: an optional map of signature names to actual signatures.
        :return: the absolute path to the local file or ``None`` if it doesn't exist.
        """
        path = self._fetch_file(dependency, name)

        # Handle signature verification, if we need to.
        if path and (signatures or signatures is None):
            if not verify_signature(path, signatures, lambda sn: self._fetch_file(dependency, sn)):
                raise ValueError(f'Could not verify the signature of the file {path.name}.')

        return path

    def get_publishing_directory(self, project_name: str) -> Optional[Path]:
        """
        A helper function to resolve a project name to its project and then to a publishing
        directory.

        :param project_name: the name of the project to resolve to a publishing directory.
        :return: the project's publishing directory or ``None``.
        """
        project = self._project_cache.get_project(project_name)

        if project:
            config = project.get_config(
                self._language.language, self._language.configuration_schema, self._language.configuration_class
            )

            with project:
                return self._language.project_as_dist_path(config)

        return None

    def _fetch_file(self, dependency: Dependency, name: str) -> Optional[Path]:
        """
        A function that resolves the named file in relation to the specified dependency.

        :param dependency: the dependency the file belongs to.
        :param name: the name of the desired file.
        :return: the absolute path to the local file or ``None`` if it doesn't exist.
        """
        if dependency.is_remote:
            path = self._handle_remote_resolution(name)
        elif dependency.is_local:
            path = self._handle_local_resolution(name)
        else:  # location is project.
            path = self._handle_project_resolution(dependency.key, name)

        return path

    def _handle_remote_resolution(self, name: str) -> Optional[Path]:
        """
        A function that handles resolving a remote file into a locally cached one.

        :param name: the name of the desired file.
        :return: the absolute path to the local file or ``None`` if it doesn't exist.
        """
        url = f'{self._directory_url}/{name}'
        directory = self._directory_path / name

        return self._resolve_remotely(url, directory)

    def _handle_local_resolution(self, name: str) -> Optional[Path]:
        """
        A function that handles resolving a local file into its exact location.

        :param name: the name of the desired file.
        :return: the absolute path to the local file or ``None`` if it doesn't exist.
        """
        for directory in self._local_paths:
            path = directory / name

            if path.is_file():
                return path

        return None

    def _handle_project_resolution(self, key: str, name: str) -> Optional[Path]:
        """
        A function that handles resolving a local file into its exact location based on
        its project.

        :param key: the key to the dependency that owns the file.
        :param name: the name of the desired file.
        :return: the absolute path to the local file or ``None`` if it doesn't exist.
        """
        if not self._language.project_as_dist_path:
            raise ValueError(
                f'The language, {self._language.language}, does not provide a means of resolving project-based '
                f'dependencies.'
            )

        path = self.get_publishing_directory(key)

        if path:
            path = path / name
            if path.is_file():
                return path

        return None

    def is_empty(self) -> bool:
        """
        A function that returns whether this context carries any actual dependencies.

        :return: ``True`` if there is at least one dependency in the context or ``False``
        if not.
        """
        return len(self._dependencies) == 0


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

    def create_full_dependency_context(self, language: Language, local_paths: List[Path], project_cache) -> \
            DependencyContext:
        """
        A function that returns a context for resolving all dependencies in a project.

        :param language: the language definition that should be assumed.
        :param local_paths: the list of local path locations.
        :param project_cache: the current project cache.
        :return: an appropriate dependency resolution context for the specified task.
        """
        return DependencyContext([
            dependency for dependency in self._dependencies.values()
        ], language, local_paths, project_cache)

    def create_dependency_context_for(self, task: str, language: Language, local_paths: List[Path],
                                      project_cache) -> DependencyContext:
        """
        A function that returns a context for resolving the dependencies that apply to
        the specified task.  The context may carry no dependencies.

        :param task: the task whose applicable dependencies should be returned.
        :param language: the language definition that defines the task.
        :param local_paths: the list of local path locations.
        :param project_cache: the current project cache.
        :return: an appropriate dependency resolution context for the specified task.
        """
        return DependencyContext([
            dependency for dependency in self._dependencies.values() if dependency.applies_to(task)
        ], language, local_paths, project_cache)
