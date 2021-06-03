"""
This library provides our core data model.
"""
import re
from collections import OrderedDict
from pathlib import Path
from typing import Dict, Sequence, Optional, Callable, List, Any, Type, Tuple, Generator

from builder.config import version_validator, Configuration
from builder.file_cache import file_cache
from builder.schema_validator import SchemaValidator
from builder.signing import verify_signature
from builder.utils import find, warn, verbose_out

_version_pattern = re.compile(r'^(\d+)(\.(\d+)(\.(\d+))?)?([-_.]\w+)?$')
_tag_pattern = re.compile(r'.(\D*)(\d*)')
_tree_leader = '└── '
_tree_spacer = ' ' * len(_tree_leader)


def _compare_tags(tag1: Optional[str], tag2: Optional[str]) -> int:
    """
    A function that attempts proper ordering of the tag portion of a version.

    :param tag1: the first tag to look at.
    :param tag2: the second tag to look at.
    :return: the usual result of comparing.
    """
    # Simple equivalence
    if (tag1 is None and tag2 is None) or tag1 == tag2:
        return 0

    # Normalize and drop the separator.
    t1_match = _tag_pattern.match(tag1 if tag1 else '-0')
    t1_group_1 = t1_match.group(1)
    t2_match = _tag_pattern.match(tag2 if tag2 else '-0')
    t2_group_1 = t2_match.group(1)

    if t1_group_1 and not t2_group_1:
        return -1
    if not t1_group_1 and t2_group_1:
        return 1
    # We have letter tags.
    if t1_group_1 and t1_group_1 != t2_group_1:
        return -1 if t1_group_1 < t2_group_1 else 1

    t1_number = int(t1_match.group(2)) if t1_match.group(2) else 0
    t2_number = int(t2_match.group(2)) if t2_match.group(2) else 0

    return t1_number - t2_number


class Version(object):
    def __init__(self, text: str):
        match = _version_pattern.match(text)
        if not match:
            raise ValueError(f'The text, "{text}", cannot be parsed as a version identifier.')

        self._major = int(match.group(1))
        self._minor = int(match.group(3)) if match.group(3) else 0
        self._micro = int(match.group(5)) if match.group(5) else 0
        self._tag = match.group(6) if match.group(6) else ''

    def same_major_minor(self, other: 'Version') -> bool:
        return self._major == other._major and self._minor == other._minor

    def _compare(self, other: 'Version'):
        diff = self._major - other._major

        if diff == 0:
            diff = self._minor - other._minor

        if diff == 0:
            diff = self._micro - other._micro

        if diff == 0 and self._tag != other._tag:
            diff = _compare_tags(self._tag, other._tag)

        return diff

    def __eq__(self, other):
        if not isinstance(other, Version):
            return NotImplemented

        return self._compare(other) == 0

    def __ne__(self, other):
        return not self == other

    def __lt__(self, other):
        if not isinstance(other, Version):
            return NotImplemented

        return self._compare(other) < 0

    def __le__(self, other):
        if not isinstance(other, Version):
            return NotImplemented

        return self._compare(other) <= 0

    def __gt__(self, other):
        if not isinstance(other, Version):
            return NotImplemented

        return self._compare(other) > 0

    def __ge__(self, other):
        if not isinstance(other, Version):
            return NotImplemented

        return self._compare(other) >= 0

    def __str__(self) -> str:
        return f'{self._major}.{self._minor}.{self._micro}{self._tag}'


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
            if not version_validator.validate(version):
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
    def id(self) -> str:
        """
        A read-only property that returns the ID of the dependency.  This is a string
        made up of the group and name with a colon character, ``:``, in between.

        :return: the ID of the dependency.
        """
        return f'{self.group}:{self.name}'

    @property
    def classifier(self) -> Optional[str]:
        """
        A read-only property that returns the classifier, if any, of the dependency.

        :return: the classifier of the dependency.
        """
        return self._classifier

    @property
    def ignore_transients(self) -> bool:
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
        return self.id == other.id and self._version != other._version

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
    Instances of this class represent a set of paths that a dependency represents.
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


class RemoteResolver(object):
    """
    Instances of this class represent a URL and local directory pair used for resolving
    a remote file reference into a local one.
    """
    def __init__(self, directory_url: str, directory_path: Path):
        """
        A function to create an instance of the ``RemoteResolver`` class.

        :param directory_url: the parent URL where file assets may be found.
        :param directory_path: the local path, relative to the file cache, where remote files
        should be downloaded.
        """
        if directory_url.endswith('/'):
            directory_url = directory_url[:-1]

        self._directory_url = directory_url
        self._directory_path = directory_path
        self._resolve_remotely = file_cache.resolve_file

    def resolve(self, file_name: str) -> Optional[Path]:
        """
        A function that will resolve the given file name from a remote reference into
        a local one, downloading it if needed.

        :param file_name: the name of the desired file.
        :return: the absolute path to the local file or ``None`` if it doesn't exist.
        """
        url = f'{self._directory_url}/{file_name}'
        directory = self._directory_path / file_name

        return self._resolve_remotely(url, directory)


class Resolution(object):
    """
    Instances of this class represent the resolution of a dependency.  It carries a
    dependency, the path set it resolved to and the number of dependencies it causes
    (including itself).
    """
    def __init__(self, dependency: Dependency, path_set: DependencyPathSet):
        """
        A function to create an instance of the ``Resolution`` class.

        :param dependency: the dependency we are the resolution for.
        :param path_set: the path set the dependency resolved to.
        dependency itself and its immediate transient dependencies.
        """
        self._dependency = dependency
        self._path_set = path_set

    @property
    def dependency(self):
        """
        A read-only property returning the dependency we resolve.
        """
        return self._dependency

    @property
    def path_set(self):
        """
        A property returning the path set our dependency resolved to.
        """
        return self._path_set


class DependencyNode(object):
    """
    Instances of this class represent a node in a dependency tree.
    """
    def __init__(self, dependency: Optional[Dependency] = None, parent: Optional['DependencyNode'] = None):
        """
        A function to create instances of the ``DependencyNode`` class.

        :param dependency: the dependency this node represents.
        :param parent: the parent node of this node.
        """
        self._parent = parent
        self._dependency = dependency
        self._children: Dict[str, DependencyNode] = {}

        if parent is not None:
            parent._children[dependency.id] = self

    @property
    def dependency(self) -> Dependency:
        """
        A read-only property that returns the dependency this node wraps.
        """
        return self._dependency

    @property
    def parent(self) -> 'DependencyNode':
        """
        A read-only property that returns the parent node of this node.
        """
        return self._parent

    def get_child(self, dependency: Dependency) -> 'DependencyNode':
        """
        A function that returns the child node for the given dependency.

        :param dependency: the dependency to get the child node for.
        :return: the child node for the dependency.
        """
        return self._children[dependency.id]

    def remove_child(self, dependency: Dependency) -> 'DependencyNode':
        """
        A function that removes and returns the child node for the given dependency.

        :param dependency: the dependency to remove the child node for.
        :return: the child node for the dependency.
        """
        return self._children.pop(dependency.id)

    def copy(self, parent: 'DependencyNode') -> 'DependencyNode':
        """
        A function to create a copy of the tree rooted at this node.

        :param parent: the parent for the copy.
        :return: the copy of this node.
        """
        new_node = DependencyNode(self._dependency, parent)

        for child_node in self._children.values():
            child_node.copy(new_node)

        return new_node

    def traceback(self) -> str:
        """
        A function that produces a dump of the dependency parentage of the current node.

        :return: a multi-line string showing the dependency parentage to this node.
        """
        node = self
        lines = []

        while node.parent is not None:
            lines.append(repr(node.dependency))
            node = node.parent

        lines.reverse()

        for index in range(1, len(lines)):
            lines[index] = _tree_spacer * (index - 1) + _tree_leader + lines[index]

        return '\n'.join(lines)

    def depth_first(self) -> Generator['DependencyNode', None, None]:
        """
        A function to iterate over the node tree rooted at this node in a depth-first
        manner.

        :return: the next node.
        """
        for child in self._children.values():
            for node in child.depth_first():
                yield node

        yield self


class ResolutionSet(object):
    """
    Instances of this class represent a full set of resolved dependencies.
    """
    def __init__(self):
        """
        A function to create instances of the ``ResolutionSet`` class.
        """
        self._resolutions: Dict[str, Resolution] = OrderedDict()
        self._deleted: Dict[str, Tuple[Resolution, DependencyNode]] = {}
        self._references: Dict[str, List[DependencyNode]] = {}
        self._root = DependencyNode()
        self._current_node = self._root

    def start(self, dependency: Dependency):
        """
        A function that starts the resolution of a dependency.

        :param dependency: the dependency that is about to be resolved.
        """
        node = DependencyNode(dependency, parent=self._current_node)

        self._add_reference(node)
        self._current_node = node

    def _add_reference(self, node: DependencyNode):
        """
        A function to note the use of a dependency node subtree.
        """
        dep_id = node.dependency.id
        refs = self._references[dep_id] if dep_id in self._references else []

        refs.append(node.parent)

        self._references[dep_id] = refs

    def end_dependency(self):
        """
        A function to note that, whatever the outcome of trying to resolve a dependency,
        the processing is done and we need to pop up one level of the tree.
        """
        self._current_node = self._current_node.parent

    def find(self, dependency: Dependency) -> Tuple[bool, Optional[Dependency]]:
        """
        A function to see if a dependency has already been resolved.  The tuple returned
        will consist of a boolean and an optional dependency.  The boolean is a flag
        indicating whether an exact match was found.  If the dependency is ``None``, then
        no completed dependency was found that comes close to the given one.  Otherwise,
        it will be the completed dependency that was either an exact or a near match.

        :param dependency: the dependency to search for.
        :return: a tuple carrying the search results.
        """
        # If we've completed the exact dependency, we're good.  If there's an exact
        # match from what's been deleted, that's good too.
        if repr(dependency) in self._resolutions or repr(dependency) in self._deleted:
            return True, dependency

        # Otherwise, we need to search for a near match.
        for resolution in self._resolutions.values():
            if dependency.same_but_for_version(resolution.dependency):
                return False, resolution.dependency

        # Not even a near match...
        return False, None

    def note_usage_of(self, dependency: Dependency):
        """
        A function that notes the usage of the previously resolved dependency
        given.

        :param dependency: the previously resolved dependency to note as used
        in the current place in the dependency tree.
        """
        if repr(dependency) in self._resolutions:
            # If the dependency is already active, use that.
            parent = self._references[dependency.id][0]
            source_node = parent.get_child(dependency)
        else:
            # Otherwise, it has been deleted so reinstate it.
            _, source_node = self._deleted[repr(dependency)]

            for node in source_node.depth_first():
                if repr(node.dependency) not in self._resolutions and repr(node.dependency) in self._deleted:
                    resolution, _ = self._deleted.pop(repr(node.dependency))
                    self._resolutions[repr(node.dependency)] = resolution

        dependency_node = source_node.copy(self._current_node)

        for node in dependency_node.depth_first():
            self._add_reference(node)

    def completed(self, dependency: Dependency, path_set: DependencyPathSet):
        """
        A function that adds a newly resolved dependency to this set.

        :param dependency: the dependency that was just resolved.
        :param path_set: the path set that represents the resolution.
        dependency itself plus the number of immediate child dependencies.
        """
        self._resolutions[repr(dependency)] = Resolution(dependency, path_set)

    def abandon(self, completed: Dependency):
        """
        A function used to remove a completed dependency and its resolution from
        this resolution set.

        :param completed: the completed dependency to remove.
        """
        references = self._references[completed.id]
        child = references[-1].get_child(completed)
        all_nested_dependencies = [node.dependency for node in child.depth_first()]

        for dependency in all_nested_dependencies:
            self._remove_dependency(dependency)

    def _remove_dependency(self, dependency: Dependency):
        """
        A function that will remove the given dependency from our dependency tree.

        :param dependency: the dependency to remove.
        """
        full_id = repr(dependency)
        abandoned_id = dependency.id
        references = self._references[abandoned_id]
        parent = references.pop()
        child = parent.remove_child(dependency)

        # If we're removing the last one, move the resolution and node tree to a
        # saved place in case we can use it later.
        if len(references) == 0:
            self._deleted[full_id] = (self._resolutions.pop(full_id), child)
            self._references.pop(abandoned_id)

    @property
    def path_sets(self) -> List[DependencyPathSet]:
        """
        A read-only property that returns a list of the resolved dependencies as path
        sets.
        """
        sets = [resolution.path_set for resolution in self._resolutions.values()]
        if len(sets) > 1:
            sets.insert(0, sets.pop())
        return sets

    def traceback(self) -> str:
        """
        A function that produces a dump of the dependency parentage of the current node.

        :return: a multi-line string showing the dependency parentage to this node.
        """
        return self._current_node.traceback()


_path_set_cache: Dict[str, List[DependencyPathSet]] = {}


class DependencyContext(object):
    """
    Instances of this class represent a dependency context for a task.  This includes
    the collection of dependencies that apply to a particular task and getting them
    resolved to an appropriate set of files.
    """
    def __init__(self, dependencies: List[Dependency], language: Language, configuration: Configuration):
        """
        A function to create an instance of the ``TaskDependencies`` class.

        :param dependencies: the list of dependencies that are directly required for a task.
        :param language: the language definition that the related task belongs to.
        :param configuration: the overall project configuration..se,
        """
        self._dependencies = dependencies.copy()
        self._language = language
        self._remote_resolver: Optional[RemoteResolver] = None
        self._configuration = configuration
        self._resolutions = ResolutionSet()

    def split(self) -> List['DependencyContext']:
        """
        A function that creates copies of this context, one copy for each dependency.  In
        other words, each resulting context will have one, and only one, dependency in it.
        This allows for easily capturing all the transient dependency information for a
        dependency.

        :return: a list of contexts, one for each of our own dependencies.
        """
        return [
            DependencyContext([dependency], self._language, self._configuration)
            for dependency in self._dependencies
        ]

    @property
    def dependencies(self) -> List[Dependency]:
        """
        A read-only property containing the list of our dependencies.

        :return: the dependencies from this context.
        """
        return self._dependencies.copy()

    def set_remote_resolver(self, resolver: RemoteResolver):
        """
        A function used to set the remote resolver to use for this context.

        :param resolver: the resolver to use for remote dependencies.
        """
        self._remote_resolver = resolver

    def resolve(self) -> List[DependencyPathSet]:
        """
        A function that resolves our list of dependencies into a list of dependency path sets.

        :return: the resulting list of dependency path sets.
        """
        if not self._language.resolver:
            raise ValueError(
                f'The language, {self._language.language}, does not provide a means of resolving dependencies.'
            )

        key = self._dependencies_as_key()

        if key in _path_set_cache:
            return _path_set_cache[key]

        # Make sure we start off with a clean set of resolutions.
        self._resolutions = ResolutionSet()

        for dependency in self._dependencies:
            self._resolve(dependency)

        path_sets = self._resolutions.path_sets

        _path_set_cache[key] = path_sets

        return path_sets

    def _dependencies_as_key(self) -> str:
        """
        A function that creates a single key string from our set of dependencies.

        :return: the key that represents our complete collection of dependencies.
        """
        strings = [repr(dependency) for dependency in self._dependencies]

        strings.sort()

        return '|'.join(strings)

    def _resolve(self, dependency: Dependency):
        """
        A function that resolves a specific dependency.

        :param dependency: the dependency to resolve.
        """
        verbose_out(f'Resolving dependency {dependency}...')

        exact_match, completed = self._resolutions.find(dependency)

        # Already done it?  Move along.
        if exact_match:
            self._resolutions.note_usage_of(completed)
            return

        # If completed is not None, then we have a near match.
        if completed and self._handle_version_conflict(dependency, completed):
            self._resolutions.note_usage_of(completed)
            return

        self._resolutions.start(dependency)

        try:
            # All good, so resolve it.
            path_set = self._language.resolver(self, dependency)

            if not path_set:
                raise ValueError(f'Dependency path:\n{self._resolutions.traceback()}\n'
                                 f'The dependency, {dependency}, could not be resolved.')

            self._resolutions.completed(dependency, path_set)
        finally:
            self._resolutions.end_dependency()

    def _handle_version_conflict(self, pending: Dependency, completed: Dependency) -> bool:
        """
        A function that appropriately handles a version conflict for a dependency.

        :param pending: the current dependency.
        :param completed: the dependency the current one is a near match to.
        :return: ``True`` if the pending dependency should just be skipped or ``False``
        if it should be processed normally.
        """
        pending_version = Version(pending.version)
        completed_version = Version(completed.version)
        conflict = self._configuration.get_conflict(pending.id, not pending_version.same_major_minor(completed_version))

        if conflict.error_out:
            raise ValueError(f'The same library, {pending.id}, is required at two different versions,'
                             f' {completed.version} vs. {pending.version}.')

        # If the completed one is the one we want, then we're all good.
        if (conflict.use_newer and completed_version > pending_version) or \
                (conflict.use_older and completed_version < pending_version):
            if conflict.warn:
                warn(f'Favoring {conflict.action} version {completed.version} over {pending.version} of'
                     f' {completed.id}.')
            return True

        if conflict.warn:
            warn(f'Favoring {conflict.action} version {pending.version} over {completed.version} of'
                 f' {pending.id}.')

        # We need to throw away the completed dependency and allow the pending one to process.
        self._resolutions.abandon(completed)

        return False

    def add_dependency(self, dependency: Dependency):
        """
        A function that will add the given dependency to our required set.  It is assumed
        that the dependency is a transient, as opposed to a primary, one.  It is immediately
        resolved as necessary.

        :param dependency: the dependency to include into the context.
        """
        dependency.transient = True
        hold = self._remote_resolver

        try:
            self._resolve(dependency)
        finally:
            self._remote_resolver = hold

    def to_local_path(self, dependency: Dependency, name: str, signatures: Optional[Dict[str, str]] = None,
                      override_resolver: Optional[RemoteResolver] = None) -> Optional[Path]:
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
        :param override_resolver: an optional resolver to override the current remote
        resolver.
        :return: the absolute path to the local file or ``None`` if it doesn't exist.
        """
        set_aside = self._remote_resolver

        if override_resolver:
            self._remote_resolver = override_resolver

        try:
            path = self._fetch_file(dependency, name)
            condition = self._configuration.get_file_condition(name)

            # Handle signature verification, if we need to.
            if not condition.ignore_signature and path and (signatures or signatures is None):
                if not verify_signature(path, signatures, lambda sn: self._fetch_file(dependency, sn)):
                    if condition.warn_on_bad_signature:
                        warn(f'Could not verify the signature of the file {path.name}.')
                    else:
                        raise ValueError(f'Dependency path:\n{self._resolutions.traceback()}\n'
                                         f'Could not verify the signature of the file {path.name}.')
        finally:
            self._remote_resolver = set_aside

        return path

    def get_publishing_directory(self, project_name: str) -> Optional[Path]:
        """
        A helper function to resolve a project name to its project and then to a publishing
        directory.

        :param project_name: the name of the project to resolve to a publishing directory.
        :return: the project's publishing directory or ``None``.
        """
        project = self._configuration.project_cache.get_project(project_name)

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
        return self._remote_resolver.resolve(name)

    def _handle_local_resolution(self, name: str) -> Optional[Path]:
        """
        A function that handles resolving a local file into its exact location.

        :param name: the name of the desired file.
        :return: the absolute path to the local file or ``None`` if it doesn't exist.
        """
        for directory in self._configuration.local_paths:
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

    def create_full_dependency_context(self, language: Language, configuration: Configuration) -> DependencyContext:
        """
        A function that returns a context for resolving all dependencies in a project.

        :param language: the language definition that should be assumed.
        :param configuration: the framework-level project configuration.
        :return: an appropriate dependency resolution context for the specified task.
        """
        return DependencyContext([
            dependency for dependency in self._dependencies.values()
        ], language, configuration)

    def create_dependency_context_for(self, task: str, language: Language, configuration: Configuration)\
            -> DependencyContext:
        """
        A function that returns a context for resolving the dependencies that apply to
        the specified task.  The context may carry no dependencies.

        :param task: the task whose applicable dependencies should be returned.
        :param language: the language definition that defines the task.
        :param configuration: the framework-level project configuration.
        :return: an appropriate dependency resolution context for the specified task.
        """
        return DependencyContext([
            dependency for dependency in self._dependencies.values() if dependency.applies_to(task)
        ], language, configuration)
