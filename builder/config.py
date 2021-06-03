"""
This file provides all our needed config support.
"""
from pathlib import Path
from typing import Dict, Any, List

from builder.schema import StringSchema, ObjectSchema, BooleanSchema, OneOfSchema, ArraySchema
from builder.schema_validator import SchemaValidator

_version_schema = StringSchema().format("semver")
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
version_validator = SchemaValidator(_version_schema)
dependency_schema = OneOfSchema(
    _full_dependency_schema,
    _spec_dependency_schema
)
conflict_schema = ObjectSchema() \
    .properties(
        action=StringSchema().enum('error', 'newer', 'older').default('error'),
        warn=BooleanSchema().default(False)
    )
file_condition_schema = ObjectSchema() \
    .properties(
        signature=StringSchema().enum('ignore', 'warn', 'error').default('error')
    )


class Conflict(object):
    """
    Instances of this class represent a way to deal with a dependency version
    conflict.
    """
    def __init__(self, data: Dict[str, Any]):
        """
        A function that creates instances of the ``Conflict`` class.

        :param data: the data to use in defining the conflict.
        """
        self._action: str = data['action'] if 'action' in data else 'error'
        self._warn: bool = data['warn'] if 'warn' in data else True

    @property
    def action(self):
        """
        A read-only property that returns the action that should be taken.

        :return: the action for this conflict.
        """
        return self._action

    @property
    def error_out(self) -> bool:
        """
        A function that says this conflict should cause an error.
        """
        return self._action == 'error'

    @property
    def use_newer(self) -> bool:
        """
        A function that says this conflict should use the newer version of the dependency.
        """
        return self._action == 'newer'

    @property
    def use_older(self) -> bool:
        """
        A function that says this conflict should use the older version of the dependency.
        """
        return self._action == 'older'

    @property
    def warn(self) -> bool:
        """
        A function that returns whether a warning message should be displayed.  This is
        valid only for ``newer`` and ``older`` actions.
        """
        return self._warn

    def __str__(self) -> str:
        return f'Conflict[action={self._action}, warn={self._warn}]'


class ConflictSet(object):
    """
    Instances of this class represent a collection of conflict handling rules.
    """
    def __init__(self, data: Dict[str, Any]):
        """
        A function that creates instances of the ``ConflictSet`` class.

        :param data: the data to use in defining the conflict.
        """
        self._conflicts = {key: Conflict(value) for key, value in data.items()}
        self._newer_with_warning_conflict = Conflict({'action': 'newer'})
        self._error_conflict = Conflict({})

    def get_conflict(self, dependency_id: str, error_default: bool) -> Conflict:
        """
        A function that returns the appropriate conflict information for the given
        dependency.

        :param dependency_id: the ID of the dependency to get the conflict information
        for.
        :param error_default: a flag noting whether an error (``True``) or warning
        (``False``) conflict should be returned if a specific conflict doesn't exist.
        :return: the appropriate conflict handling information.
        """
        return self._conflicts[dependency_id] if dependency_id in self._conflicts else \
            self._error_conflict if error_default else self._newer_with_warning_conflict


class FileCondition(object):
    """
    Instances of this object specify how to handle conditions related to a file.
    """
    def __init__(self, source: Dict[str, Any]):
        """
        A function that creates instances of the ``FileCondition`` class.

        :param source: the source data to pull from.
        """
        self._signature: str = source['signature'] if 'signature' in source else 'error'

    @property
    def ignore_signature(self) -> bool:
        """
        A read-only property that says signature verification should be ignored for
        the related file.

        :return: ``True`` if signature validation should be ignored or ``False``
        otherwise.
        """
        return self._signature == 'ignore'

    @property
    def warn_on_bad_signature(self) -> bool:
        """
        A read-only property that says only a warning should be issued of signature
        verification for the related file fails.

        :return: ``True`` if a failed signature validation should produce a warning
         only ``False`` otherwise.
        """
        return self._signature == 'warn'


class Configuration(object):
    """
    Instances of this class represent information from the project configuration
    file.
    """
    def __init__(self, source: Dict[str, Any], local_paths: List[Path], project_cache):
        """
        A function that creates instances of a project configuration.

        :param source: the source dictionary containing all the source information
        we provide.
        :param local_paths: the list of any local paths defined in the project.
        :param project_cache: the cache used for accessing dependent projects.
        """
        self._conflict_set = ConflictSet(source['conflicts'] if 'conflicts' in source else {})
        self._file_conditions: Dict[str, FileCondition] = {}
        self._default_file_condition = FileCondition({})
        self._local_paths = local_paths
        self._project_cache = project_cache

        if 'conditions' in source:
            if 'files' in source['conditions']:
                self._file_conditions = {
                    key: FileCondition(value) for key, value in source['conditions']['files'].items()
                }

    def get_conflict(self, dependency_id: str, error_default: bool) -> Conflict:
        """
        A function that returns the appropriate conflict information for the given
        dependency.

        :param dependency_id: the ID of the dependency to get the conflict information
        for.
        :param error_default: a flag noting whether an error (``True``) or warning
        (``False``) conflict should be returned if a specific conflict doesn't exist.
        :return: the appropriate conflict handling information.
        """
        return self._conflict_set.get_conflict(dependency_id, error_default)

    def get_file_condition(self, name: str) -> FileCondition:
        """
        A function that returns a file condition for the named file.

        :param name: the (simple) name of the file to get a condition for.
        :return: an appropriate condition for the named file.
        """
        return self._file_conditions[name] if name in self._file_conditions else self._default_file_condition

    @property
    def local_paths(self) -> List[Path]:
        """
        A read-only property that returns the list of local location paths configured
        for this project.  The list returned may be empty but will never be ``None``.

        :return: the list of local location paths for the current project.
        """
        return self._local_paths

    @property
    def project_cache(self):
        """
        A read-only property that returns a cache of projects defined as locations
        within this project.

        :return: this project's project location cache.
        """
        return self._project_cache
