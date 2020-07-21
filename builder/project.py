"""
This library provides an object that represents a project.
"""
from pathlib import Path
from typing import Sequence, Optional, Dict, Union, Any, MutableMapping, Mapping, List

import yaml

from builder.dependencies import DependencySet
from builder.schema import ArraySchema, ObjectSchema, OneOfSchema, StringSchema
from builder.schema_validator import SchemaValidator
from builder.task_module import get_task_module, ModuleSet
from builder.utils import global_options

_schema = ObjectSchema() \
    .properties(
        info=ObjectSchema()
            .properties(
                name=StringSchema().pattern('[a-zA-Z0-9-_]+'),
                title=StringSchema().min_length(1),
                version=StringSchema().format('semver'),
                languages=OneOfSchema(
                    StringSchema().min_length(1),
                    ArraySchema().items(StringSchema().min_length(1))
                )
            )
            .additional_properties(False),
        dependencies=ObjectSchema()
            .additional_properties(ObjectSchema()
                .properties(
                    repo=StringSchema().min_length(1),
                    group=StringSchema().min_length(1),
                    name=StringSchema().min_length(1),
                    version=StringSchema().format("semver"),
                    scope=OneOfSchema(
                        StringSchema().min_length(1),
                        ArraySchema().items(StringSchema().min_length(1))
                    )
                )
                .required('repo', 'version', 'scope')
                .additional_properties(False)
            ),
        vars=ObjectSchema().additional_properties(StringSchema().min_length(1))
    )\
    .required('info')
_project_file_schema = SchemaValidator(schema=_schema)


class Project(object):
    """
    Instances of this class represent a project.
    """
    @classmethod
    def from_file(cls, path: Path) -> 'Project':
        """
        This class function creates a project object by reading and validating a ``project.yaml``
        file.  Validation is limited to the basics; top-level sections that specify task
        configuration information are validates later when the related tasks are requested.

        :param path: the path to the ``project.yaml`` file to read.
        :return: the resulting project object.
        :raises ValueError: if the project file cannot be validated.
        """
        directory = path.parent
        with path.open() as fd:
            content = yaml.full_load(fd)
        if not _project_file_schema.validate(content):
            raise ValueError(f'Bad project file format: {_project_file_schema.error}')
        return cls(directory, content)

    @classmethod
    def from_dir(cls, path: Path, name: Optional[str] = None, version: Optional[str] = None,
                 language: Optional[str] = None) -> 'Project':
        """
        This class function creates a minimal project object from a directory.  The name
        of the project, if not specified, will be set to the simple name of the directory.
        The version, if not specified, will be set to ``0.0.1``.

        :param path: the path to the ``project.yaml`` file to read.
        :param name: the name for the project.
        :param version: the version of the project.
        :param language: the language of the project.
        :return: the resulting project object.
        """
        info = {}
        if name is not None:
            info['name'] = name
        if version is not None:
            info['version'] = version
        if language is not None:
            info['languages'] = language
        return cls(path, {
            'info': info
        })

    def __init__(self, directory: Path, content: Dict[str, Any]):
        """
        A function to create an instance of the ``Project`` class.  Use either the
        ``Project.from_file()`` or ``Project.from_dir()`` functions to create instances;
        do not use this function directly.
        """
        self._directory = directory
        self._module_set = None
        self._unknown_languages = None
        self._content = content
        self._info = self._content['info']
        if 'name' not in self._info:
            self._info['name'] = directory.name
        if 'version' not in self._info:
            self._info['version'] = '0.0.1'
        _fix_up_language_list(self._info)
        self._prefetch_module_set()
        self._dependencies = DependencySet(content['dependencies'] if 'dependencies' in content else {})
        self._config_cache = {}

        if 'vars' not in self._content:
            self._content['vars'] = {}

        # Finally, resolve any variable references.
        _resolve_vars_in_dict(self._content)

    def _prefetch_module_set(self):
        """
        This function tries to load the modules associated with all the specified
        languages.  If any module cannot be loaded, then none are and a notation
        of the specific languages that could not be loaded is made.
        """
        languages = self._info['languages']
        modules = {language: get_task_module(language) for language in languages}
        unknowns = [key for key, value in modules.items() if value is None]
        self._module_set = ModuleSet(modules) if len(unknowns) == 0 else None
        self._unknown_languages = None if len(unknowns) == 0 else unknowns

    @property
    def name(self) -> str:
        """
        A read-only property that returns the name of the project.

        :return: the name of the project.
        """
        return self._info['name']

    @property
    def version(self) -> str:
        """
        A read-only property that returns the version of the project.

        :return: the version of the project.
        """
        return self._info['version']

    @property
    def description(self) -> str:
        """
        A read-only property that returns the description of the project.  It is
        generated from the project's name and, if available, title.

        :return: the description of the project.
        """
        name = self._info['name']
        title = self._info['title'] if 'title' in self._info else None
        return name if title is None else f'{name} -- {title}'

    def has_no_languages(self) -> bool:
        """
        A function that returns whether any languages were specified in either the
        project's file or via the ``--language`` CLI option.

        **Note:** This does not test whether the specified languages are valid; only
        that a non-zero number of languages were indicated.

        :return: the name of the project.
        """
        return len(self._info['languages']) == 0

    def get_module_set(self) -> Optional[ModuleSet]:
        """
        A function the returns the set of modules that correspond to the requested
        languages.  If any requested language is unknown this function will return
        ``None``.

        :return: the project's set of modules.
        """
        return self._module_set

    def has_unknown_languages(self) -> bool:
        """
        A function that returns whether or not any of the requested languages in the project
        or via the ``--language`` CLI option are unknown.

        :return: ``True`` if at least one requested language is unknown or ``False`` if they
        are all known.
        """
        return self._unknown_languages is not None

    def get_unknown_languages(self) -> Optional[Sequence[str]]:
        """
        A function that returns the list of unknown languages.  If all languages are known,
        then this function will return ``None`` (as opposed to an empty sequence).

        :return: the list of unknown languages or ``None``.
        """
        return self._unknown_languages

    def get_dependencies(self) -> DependencySet:
        """
        A function that returns the dependency set for the project.

        :return: the project's set of dependencies.
        """
        return self._dependencies

    def get_config(self, name: str, schema: SchemaValidator = None, config_class: Optional[object] = None) -> Any:
        """
        A function that looks up a named configuration in the project.  If the given name
        is not a top-level field in the project, an empty dictionary is assumed.  If the
        given name has not been requested before,

        -   if a schema is provided, it is used to validate the named configuration.

        -   if a configuration class is provided, an instance of that class is created and
            top-level field values are copied into it from the raw configuration data.  If
            not, the raw value is used.

        -   the value is cached to more quickly satisfy lookups for the same configuration
            value.

        :param name: the name of the desired configuration.
        :param schema: an optional schema to validate the configuration value against.
        :param config_class: an optional class to return a populated instance of.
        :raises ValueError: if the configuration value does not satisfy the specified schema.
        """
        if name not in self._config_cache:
            config = self._content[name] if name in self._content else {}
            if schema is not None:
                if not schema.validate(config, name):
                    raise ValueError(f'Configuration for "{name}" is not valid: {schema.error}')
            if config_class is not None:
                config = Project._create_config_object(config_class, config)
            self._config_cache[name] = config
        return self._config_cache[name]

    def project_dir(self, path: Path, required: bool = False, ensure: bool = False) -> Path:
        """
        A function for acquiring a path that is under the project.  The path provided must
        be relative and is resolved against the root path of hte directory.

        Optionally, the function can test for the existence of the resulting directory.  If
        it is required and doesn't exist, an exception is raised.  If it should be ensured
        but doesn't exist, it, along with any necessary parent directories, will be created.

        The request to ensure the directory is processed first so that if ``ensured`` and
        ``required`` are both ``True``, the function will succeed in an expected way.

        :param path: the relative path to resolve.
        :param required: indicates whether the directory must already exist.  If it does not,
        an exception is raised.
        :param ensure: indicates that the directory should be created if it does not already
        exist.
        :raises ValueError: if the directory does not exist is required but not ensured.
        """
        directory = self._directory.joinpath(path).resolve()
        if ensure and not directory.is_dir():
            directory.mkdir(parents=True, exist_ok=True)
        if required and not directory.is_dir():
            raise ValueError(f'Required directory, {directory}, does not exist or is not a directory.')
        return directory

    def get_var_value(self, name: str) -> Optional[str]:
        """
        A function to look up the value of a configured variable; i.e., specified in the
        ``vars`` section of the project file.  It will not return values of variables set
        via the ``--set`` command line option.  If the requested variable does not exist,
        then ``None`` will be returned.

        :param name: the name of the desired variable.
        :return: the variable's value or ``None``.
        """
        return self._content['vars'].get(name, None)

    @staticmethod
    def _create_config_object(config_class, config_data):
        """
        A function to help create the instance of an object and populate it with configuration
        data.  Only the top-level fields from the config data are copied to the object.

        :param config_class: the class to create an instance of.
        :param config_data: the configuration data to copy into the new instance.
        """
        config = config_class()
        if isinstance(config_data, Mapping):
            for key, value in config_data.items():
                setattr(config, key, value)
        return config


def _fix_up_language_list(info: Dict[str, Union[str, Sequence[str]]]):
    """
    A function to normalize the list of languages in the given info dictionary.  It
    is guaranteed that, after a call to this function, the ``info`` dictionary will
    have an entry named, ``languages`` and that it maps to a sequence.

    The sequence will be empty if ``info`` did not contain a ``languages`` entry or
    it is present but already mapped to an empty sequence and no extra languages were
    specified with the ``--language`` command line option.

    If the ``languages`` maps to a single string, the string is wrapped in a sequence.

    If any extra languages were specified with the ``--language`` command line option,
    they are appended to the sequence in a way that prevents duplication.

    :param info: the ``info`` dictionary to work with.  It is modified in place.
    """
    languages = info['languages'] if 'languages' in info else []
    if isinstance(languages, str):
        languages = [languages]
    extras = global_options.languages()
    if extras:
        for extra in extras:
            if extra not in languages:
                languages.append(extra)
    info['languages'] = languages


def _resolve_vars_in_dict(data: Dict[str, Any]):
    """
    A function that traverses the specified dictionary, finding all string values and
    resolves any variable references that are found.  Nested dictionaries and sequences
    are processed as well.

    :param data: the dictionary to traverse.
    """
    for key, value in data.items():
        _resolve_vars_in_container(data, key, value)


def _resolve_vars_in_list(data: List):
    """
    A function that traverses the specified list, finding all string values and resolves
    any variable references that are found.  Nested dictionaries and sequences are
    processed as well.

    :param data: the list to traverse.
    """
    for index, value in enumerate(data):
        _resolve_vars_in_container(data, index, value)


def _resolve_vars_in_container(data: Union[MutableMapping, List], index: Any, value: Any):
    """
    A function that processes the given value.  If it is a tuple, it is converted to a
    list.  If it is a list or dictionary, then it is processed as a container.  If it
    is a string, then any variable references are resolved.

    :param data: the container (dictionary or list) the value belongs to.
    :param index: the list index or dictionary key of the value within its container.
    :param value: the value to process.
    """
    if isinstance(value, tuple):
        data[index] = value = list(value)
    if isinstance(value, str):
        data[index] = global_options.substitute(value)
    elif isinstance(value, Dict):
        _resolve_vars_in_dict(value)
    elif isinstance(value, List):
        _resolve_vars_in_list(value)


def get_project(directory: Path) -> Project:
    """
    A function to create a ``Project`` object from a directory.  If the directory
    contains a ``project.yaml`` file, it is read as the source of the project definition.
    Otherwise, a default project based on just the directory is created.

    :param directory: the directory to create the project object for.
    :return: the appropriately initialized project object.
    """
    project_file_path = directory / 'project.yaml'

    return Project.from_file(project_file_path)\
        if project_file_path.exists()\
        else Project.from_dir(project_file_path.parent)
