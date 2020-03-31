"""
This library provides an object that represents a project.
"""
from pathlib import Path
from typing import Sequence, Optional, Dict, Union, Any, List, MutableMapping

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
project_file_schema = SchemaValidator(schema=_schema)


class Project(object):
    @classmethod
    def from_file(cls, path: Path):
        directory = path.parent
        with path.open() as fd:
            content = yaml.full_load(fd)
        if not project_file_schema.validate(content):
            raise ValueError(f'Bad project file format: {project_file_schema.error}')
        return cls(directory, content)

    @classmethod
    def from_dir(cls, path: Path):
        return cls(path, {
            'info': {}
        })

    def __init__(self, directory, content: Dict[str, Any]):
        self._directory = directory
        self._module_set = None
        self._unknown_languages = None
        self._content = content
        self.info = self._content['info']
        if 'name' not in self.info:
            self.info['name'] = directory.name
        if 'version' not in self.info:
            self.info['version'] = '0.0.1'
        _fix_up_language_list(self.info)
        self._prefetch_module_set()
        self._dependencies = DependencySet(content['dependencies'] if 'dependencies' in content else {})
        self._config_cache = {}

        if 'vars' not in self._content:
            self._content['vars'] = {}

        # Make us globally known.
        global_options.set_project(self)

        # Finally, resolve any variable references.
        self._resolve_vars_in_dict(self._content)

    @staticmethod
    def _resolve_vars_in_dict(data: Dict[str, Any]):
        for key, value in data.items():
            Project._resolve_vars_in_container(data, key, value)

    @staticmethod
    def _resolve_vars_in_list(data: MutableMapping):
        for index, value in enumerate(data):
            Project._resolve_vars_in_container(data, index, value)

    @staticmethod
    def _resolve_vars_in_container(data: MutableMapping, index: Any, value: Any):
        if isinstance(value, tuple) and not isinstance(value, list):
            data[index] = value = list(value)
        if isinstance(value, str):
            data[index] = global_options.substitute(value)
        elif isinstance(value, Dict):
            Project._resolve_vars_in_dict(value)
        elif isinstance(value, List):
            # noinspection PyTypeChecker
            Project._resolve_vars_in_list(value)

    def _prefetch_module_set(self):
        languages = self.info['languages']
        modules = {language: get_task_module(language) for language in languages}
        unknowns = [key for key, value in modules.items() if value is None]
        self._module_set = ModuleSet(modules) if len(unknowns) == 0 else None
        self._unknown_languages = None if len(unknowns) == 0 else unknowns

    def description(self) -> str:
        name = self.info['name']
        title = self.info['title'] if 'title' in self.info else None
        return name if title is None else f'{name} -- {title}'

    def has_no_languages(self) -> bool:
        if 'languages' not in self.info:
            return True
        languages = self.info['languages']
        if isinstance(languages, Sequence):
            return len(languages) == 0
        return False

    def get_module_set(self) -> Optional[ModuleSet]:
        return self._module_set

    def has_unknown_languages(self) -> bool:
        return self._unknown_languages is not None

    def get_unknown_languages(self) -> Optional[Sequence[str]]:
        return self._unknown_languages

    def get_dependencies(self) -> DependencySet:
        return self._dependencies

    def get_config(self, name, schema: SchemaValidator = None, config_class: Optional[str] = None) -> Any:
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
        directory = self._directory.joinpath(path).resolve()
        if required and not directory.is_dir():
            raise ValueError(f'Required directory, {directory}, does not exist.')
        if ensure and not directory.is_dir():
            directory.mkdir(parents=True, exist_ok=True)
        return directory

    def get_var_value(self, name: str) -> Optional[str]:
        return self._content['vars'].get(name, None)

    @staticmethod
    def _create_config_object(config_class, config_data):
        config = config_class()
        if config_data is not None:
            for key, value in config_data.items():
                setattr(config, key, value)
        return config


def _fix_up_language_list(info: Dict[str, Union[str, Sequence[str]]]):
    languages = info['languages'] if 'languages' in info else []
    if isinstance(languages, str):
        languages = [languages]
    extras = global_options.languages()
    if extras:
        for extra in extras:
            if extra not in languages:
                languages.append(extra)
    info['languages'] = languages


def get_project() -> Project:
    project_file_path = Path.cwd() / 'project.yaml'

    return Project.from_file(project_file_path) if project_file_path.exists() else Project.from_dir(project_file_path)
