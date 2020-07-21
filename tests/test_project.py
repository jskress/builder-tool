"""
This file contains all the unit tests for our framework's project data support.
"""
from pathlib import Path

# noinspection PyPackageRequirements
import pytest

from builder.dependencies import DependencySet
# noinspection PyProtectedMember
from builder.project import _schema, Project, _fix_up_language_list, _resolve_vars_in_dict, _resolve_vars_in_list, \
    get_project
from builder.schema_validator import SchemaValidator
from builder.task_module import ModuleSet
from tests.test_support import get_test_path, Options


class TestProjectSchema(object):
    def test_project_schema(self):
        assert _schema.spec() == {
            'type': 'object',
            'properties': {
                'info': {
                    'type': 'object',
                    'properties': {
                        'name': {'type': 'string', 'pattern': '[a-zA-Z0-9-_]+'},
                        'title': {'type': 'string', 'minLength': 1},
                        'version': {'type': 'string', 'format': 'semver'},
                        'languages': {
                            'oneOf': [
                                {'type': 'string', 'minLength': 1},
                                {'type': 'array', 'items': {'type': 'string', 'minLength': 1}}
                            ]
                        }
                    },
                    'additionalProperties': False
                },
                'dependencies': {
                    'type': 'object',
                    'additionalProperties': {
                        'type': 'object',
                        'properties': {
                            'repo': {'type': 'string', 'minLength': 1},
                            'group': {'type': 'string', 'minLength': 1},
                            'name': {'type': 'string', 'minLength': 1},
                            'version': {'type': 'string', 'format': 'semver'},
                            'scope': {
                                'oneOf': [
                                    {'type': 'string', 'minLength': 1},
                                    {'type': 'array', 'items': {'type': 'string', 'minLength': 1}}
                                ]
                            }
                        },
                        'required': ['repo', 'version', 'scope'],
                        'additionalProperties': False
                    }
                },
                'vars': {
                    'type': 'object',
                    'additionalProperties': {
                        'type': 'string',
                        'minLength': 1
                    }
                }
            },
            'required': ['info']
        }


class TestProjectCreation(object):
    def test_create_project_from_bad_file(self):
        file = get_test_path('project') / 'bad_project.yaml'

        with pytest.raises(ValueError) as info:
            Project.from_file(file)

        assert info.value.args[0] == "Bad project file format: #/info/name violates the \"pattern\" constraint: it " \
                                     "does not match the '[a-zA-Z0-9-_]+' pattern."

    def test_create_project_from_good_file(self):
        file = get_test_path('project') / 'good_project.yaml'
        project = Project.from_file(file)
        # noinspection PyProtectedMember
        assert project._content == {
            'info': {
                'name': 'test-project',
                'title': 'A Glorious Implementation',
                'version': '1.0.1',
                'languages': ['java']
            },
            'vars': {'n1': 'v1'}
        }

    def test_create_project_from_directory(self):
        path = Path('/path/to/dir')
        project = Project.from_dir(path)
        # noinspection PyProtectedMember
        assert project._content == {
            'info': {
                'name': 'dir',
                'version': '0.0.1',
                'languages': []
            },
            'vars': {}
        }
        project = Project.from_dir(path, name='test')
        # noinspection PyProtectedMember
        assert project._content == {
            'info': {
                'name': 'test',
                'version': '0.0.1',
                'languages': []
            },
            'vars': {}
        }
        project = Project.from_dir(path, version='1.2.3')
        # noinspection PyProtectedMember
        assert project._content == {
            'info': {
                'name': 'dir',
                'version': '1.2.3',
                'languages': []
            },
            'vars': {}
        }
        project = Project.from_dir(path, language='java')
        # noinspection PyProtectedMember
        assert project._content == {
            'info': {
                'name': 'dir',
                'version': '0.0.1',
                'languages': ['java']
            },
            'vars': {}
        }


class Bob(object):
    def __init__(self, name: str = '', age: int = 0):
        self.name = name
        self.age = age

    def __eq__(self, other):
        if not isinstance(other, Bob):
            return NotImplemented
        return self.name == other.name and self.age == other.age


class TestProjectData(object):
    # noinspection PyProtectedMember
    def test_prefetch_module_set(self):
        project = Project.from_file(Path(get_test_path('project') / 'good_project_unknown_language.yaml'))

        assert project._info['languages'] == ['java', 'python']
        assert project._module_set is None
        assert project._unknown_languages == ['python']

        project = Project.from_file(Path(get_test_path('project') / 'good_project.yaml'))

        assert project._info['languages'] == ['java']
        assert isinstance(project._module_set, ModuleSet)
        assert project._unknown_languages is None

    def test_project_name(self):
        project = Project.from_dir(Path('/path/to/dir'), name='project-name')

        assert project.name == 'project-name'

    def test_project_version(self):
        project = Project.from_dir(Path('/path/to/dir'), version='1.4.1')

        assert project.version == '1.4.1'

    def test_project_description(self):
        project = Project.from_dir(Path('/path/to/dir'))

        assert project.description == 'dir'

        # noinspection PyProtectedMember
        project._info['title'] = 'The Title'

        assert project.description == 'dir -- The Title'

    def test_has_no_languages(self):
        project = Project.from_dir(Path('/path/to/dir'))

        assert project.has_no_languages() is True

        project = Project.from_file(Path(get_test_path('project') / 'good_project.yaml'))

        assert project.has_no_languages() is False

        project = Project.from_file(Path(get_test_path('project') / 'good_project_unknown_language.yaml'))

        assert project.has_no_languages() is False

    def test_get_module_set(self):
        project = Project.from_file(Path(get_test_path('project') / 'good_project.yaml'))

        assert isinstance(project.get_module_set(), ModuleSet)

        project = Project.from_file(Path(get_test_path('project') / 'good_project_unknown_language.yaml'))

        assert project.get_module_set() is None

    def test_has_unknown_languages(self):
        project = Project.from_file(Path(get_test_path('project') / 'good_project.yaml'))

        assert project.has_unknown_languages() is False

        project = Project.from_file(Path(get_test_path('project') / 'good_project_unknown_language.yaml'))

        assert project.has_unknown_languages() is True

    def test_get_unknown_languages(self):
        project = Project.from_file(Path(get_test_path('project') / 'good_project.yaml'))

        assert project.get_unknown_languages() is None

        project = Project.from_file(Path(get_test_path('project') / 'good_project_unknown_language.yaml'))

        assert project.get_unknown_languages() == ['python']

    def test_get_dependencies(self):
        project = Project.from_file(Path(get_test_path('project') / 'good_project.yaml'))

        assert isinstance(project.get_dependencies(), DependencySet)

    def test_get_nonexistent_config(self):
        project = Project.from_dir(Path('/path/to/dir'))

        config = project.get_config('testing')

        assert config == {}
        # Make sure caching works.
        assert project.get_config('testing') is config

    def test_get_config_with_schema(self):
        project = Project.from_dir(Path('/path/to/dir'))
        int_validator = SchemaValidator({'type': 'integer'})
        str_validator = SchemaValidator({'type': 'string'})
        # noinspection PyProtectedMember
        project._content['name'] = 'Bob'

        with pytest.raises(ValueError) as info:
            project.get_config('name', schema=int_validator)

        assert info.value.args[0] == 'Configuration for "name" is not valid: #/name violates the "type" constraint: ' \
                                     'it is not an integer.'
        assert project.get_config('name', str_validator) == 'Bob'

    def test_get_config_with_class(self):
        project = Project.from_dir(Path('/path/to/dir'))
        # noinspection PyProtectedMember
        project._content['bob'] = {
            'name': 'Bob',
            'age': 12
        }

        thing = project.get_config('bob', config_class=Bob)

        assert isinstance(thing, Bob) is True
        assert thing.name == 'Bob'
        assert thing.age == 12
        assert project.get_config('bob') is thing

    def test_plain_project_dir(self, tmpdir):
        root = Path(tmpdir)
        expected = root / 'dir'
        project = Project.from_dir(root)

        directory = project.project_dir(Path('dir'))

        assert directory == expected

    def test_required_project_dir(self, tmpdir):
        root = Path(tmpdir)
        expected = root / 'dir'
        project = Project.from_dir(root)

        with pytest.raises(ValueError) as error:
            project.project_dir(Path('dir'), required=True)

        assert error.value.args[0] == f'Required directory, {expected}, does not exist or is not a directory.'

        expected.mkdir()

        directory = project.project_dir(Path('dir'), required=True)

        assert directory == expected

    def test_expected_project_dir(self, tmpdir):
        root = Path(tmpdir)
        expected = root / 'dir'
        project = Project.from_dir(root)

        assert expected.is_dir() is False

        directory = project.project_dir(Path('dir'), ensure=True)

        assert directory == expected
        assert directory.is_dir() is True

        directory = project.project_dir(Path('dir'), ensure=True)

        assert directory == expected

        directory = project.project_dir(Path('dir'), required=True)

        assert directory == expected

    def test_get_var_value(self):
        project = Project.from_dir(Path('/path/to/dir'))

        assert project.get_var_value('variable') is None

        # noinspection PyProtectedMember
        project._content['vars'] = {'variable': 'the value'}

        assert project.get_var_value('variable') == 'the value'

    # noinspection PyProtectedMember
    def test_create_config_object(self):
        project = Project.from_dir(Path('/path/to/dir'))

        thing = project._create_config_object(Bob, None)

        assert thing == Bob()

        thing = project._create_config_object(Bob, 'bogus')

        assert thing == Bob()

        thing = project._create_config_object(Bob, {})

        assert thing == Bob()

        thing = project._create_config_object(Bob, {'name': 'Larry', 'extra': True})

        assert thing == Bob('Larry')
        assert hasattr(thing, 'extra') is True
        assert thing.extra is True

        thing = project._create_config_object(Bob, {'age': 12})

        assert thing == Bob(age=12)

        thing = project._create_config_object(Bob, {'name': 'Larry', 'age': 12})

        assert thing == Bob('Larry', 12)


class TestLanguageFixup(object):
    def test_fix_up_empty_language_list(self):
        info = {}

        _fix_up_language_list(info)

        assert info == {'languages': []}

    def test_fix_up_single_language_list(self):
        info = {'languages': 'java'}

        _fix_up_language_list(info)

        assert info == {'languages': ['java']}

    def test_fix_up_arrayed_language_list(self):
        info = {'languages': ['java']}

        _fix_up_language_list(info)

        assert info == {'languages': ['java']}

        info = {'languages': ['java', 'python']}

        _fix_up_language_list(info)

        assert info == {'languages': ['java', 'python']}

    def test_fix_up_option_language_list(self):
        info = {'languages': 'java'}

        with Options(languages=['python']):
            _fix_up_language_list(info)

        assert info == {'languages': ['java', 'python']}

        info = {'languages': ['java', 'python']}

        with Options(languages=['python']):
            _fix_up_language_list(info)

        assert info == {'languages': ['java', 'python']}


class TestVariableSubstitution(object):
    def test_basic_dict_substitutions(self):
        data = {'name': '${value}'}
        variables = {
            'value': '1'
        }

        with Options(variables=variables):
            _resolve_vars_in_dict(data)

        assert data == {'name': '1'}

    def test_basic_list_substitutions(self):
        data = ['name', '${value}']
        variables = {
            'value': '1'
        }

        with Options(variables=variables):
            _resolve_vars_in_list(data)

        assert data == ['name', '1']

    def test_compound_substitutions(self):
        data = {
            'name': '${value}',
            'list': ['${value}', '2'],
            'tuple': ('${value}', '2'),
            'dict': {
                'nested': '${value}'
            }
        }
        variables = {
            'value': '1'
        }

        with Options(variables=variables):
            _resolve_vars_in_dict(data)

        assert data == {
            'name': '1',
            'list': ['1', '2'],
            'tuple': ['1', '2'],
            'dict': {'nested': '1'}
        }


class TestGetProject(object):
    def test_get_project_from_file(self):
        directory = get_test_path('project')

        project = get_project(directory)

        assert project.name == 'test-project'
        assert project.version == '1.0.1'

    def test_get_project_from_dir(self):
        directory = get_test_path('java')

        project = get_project(directory)

        assert project.name == 'java'
        assert project.version == '0.0.1'
