"""
This file contains all the unit tests for our framework's task processing engine.
"""
from pathlib import Path
from unittest.mock import patch, MagicMock, call

from builder.dependencies import Dependency
from builder.engine import Engine
from builder.project import Project
from builder.task_module import TaskModule, Task
from tests.test_support import validate_attributes


# noinspection DuplicatedCode
class TestEngine(object):
    def test_engine_construction(self):
        project = Project.from_dir(Path('/path/to/project'))
        engine = Engine(project)

        validate_attributes(engine, {
            '_project': project,
            '_module_set': project.get_module_set(),
            '_rc': 0
        })

    def test_show_existing_tasks(self):
        project = Project.from_dir(Path('/path/to/project'))
        engine = Engine(project)
        mock_print = MagicMock()
        project.get_module_set().print_available_tasks = mock_print

        with patch('builder.engine.warn') as mock_warn:
            with patch('builder.engine.out') as mock_out:
                assert engine.run() == 1

        assert mock_warn.mock_calls == [call('No tasks specified.  Available tasks are:', None)]
        assert mock_out.mock_calls == [call()]
        assert mock_print.mock_calls == [call()]

    def test_get_tasks_in_execution_order(self):
        project = Project.from_dir(Path('/path/to/project'), language='java')
        ms = project.get_module_set()
        engine = Engine(project)

        with patch('builder.engine.global_options') as go:
            go.tasks.return_value = ['package', 'compile']
            go.independent_tasks.return_value = False

            # noinspection PyProtectedMember
            tasks = engine._get_tasks_in_execution_order()

        assert tasks == [ms.get_task('compile'), ms.get_task('test'), ms.get_task('package')]

    def test_get_tasks_in_execution_order_independent(self):
        project = Project.from_dir(Path('/path/to/project'), language='java')
        ms = project.get_module_set()
        engine = Engine(project)

        with patch('builder.engine.global_options') as go:
            go.tasks.return_value = ['test', 'compile']
            go.independent_tasks.return_value = True

            # noinspection PyProtectedMember
            tasks = engine._get_tasks_in_execution_order()

        assert tasks == [ms.get_task('test'), ms.get_task('compile')]

    def test_execute_tasks(self):
        project = Project.from_dir(Path('/path/to/project'))
        engine = Engine(project)
        module = TaskModule(None, 'java')
        et = MagicMock()
        task1 = Task('task1', MagicMock())
        task2 = Task('task2', None)
        task3 = Task('task3', MagicMock())
        tasks = [(module, task1), (module, task2), (module, task3)]

        engine._execute_task = et

        with patch('builder.engine.out') as mock_out:
            # noinspection PyProtectedMember
            engine._execute_tasks(tasks)

        assert et.mock_calls == [call(module, task1), call(module, task3)]
        assert mock_out.mock_calls == [
            call('--> task1', fg='bright_green'),
            call('--> task2', fg='bright_green'),
            call('--> task3', fg='bright_green')
        ]

    def test_get_language_config(self):
        config = {'lib_target': 'library'}
        project = Project.from_dir(Path('/path/to/project'))
        engine = Engine(project)
        module = TaskModule(None, 'java')
        mock_get_config = MagicMock()

        mock_get_config.return_value = config

        project.get_config = mock_get_config

        # noinspection PyProtectedMember
        assert engine._get_language_config(module) == config
        assert mock_get_config.mock_calls == [call('java', None, None)]

    def test_get_task_config(self):
        config = {'field': 'value'}
        project = Project.from_dir(Path('/path/to/project'))
        engine = Engine(project)
        task = Task('myTask', None)
        mock_get_config = MagicMock()

        mock_get_config.return_value = config

        project.get_config = mock_get_config

        # noinspection PyProtectedMember
        assert engine._get_task_config(task) == config
        assert mock_get_config.mock_calls == [call('myTask', None, None)]

    def test_format_args_no_args(self):
        project = Project.from_dir(Path('/path/to/project'))
        engine = Engine(project)
        module = TaskModule(None, 'java')
        task = Task('myTask', func_no_args)

        # noinspection PyProtectedMember
        args, kwargs = engine._format_args(module, task)

        assert args == []
        assert kwargs == {}

    def test_format_args_default_args(self):
        project = Project.from_dir(Path('/path/to/project'))
        engine = Engine(project)
        module = TaskModule(None, 'java')
        task = Task('myTask', func_default_args)

        # noinspection PyProtectedMember
        args, kwargs = engine._format_args(module, task)

        assert args == [1]
        assert kwargs == {}

        task.function = func_named_default_args

        # noinspection PyProtectedMember
        args, kwargs = engine._format_args(module, task)

        assert args == []
        assert kwargs == {'mine': 1}

    def test_format_args_language_config(self):
        config = {'lib_target': 'library'}
        project = Project.from_dir(Path('/path/to/project'))
        engine = Engine(project)
        module = TaskModule(None, 'java')
        task = Task('myTask', func_language_config)
        mock_get_config = MagicMock()

        mock_get_config.return_value = config

        project.get_config = mock_get_config

        # noinspection PyProtectedMember
        args, kwargs = engine._format_args(module, task)

        assert args == [config]
        assert kwargs == {}

        task.function = func_named_language_config

        # noinspection PyProtectedMember
        args, kwargs = engine._format_args(module, task)

        assert args == []
        assert kwargs == {'language_config': config}

    def test_format_args_task_config(self):
        config = {'lib_target': 'library'}
        project = Project.from_dir(Path('/path/to/project'))
        engine = Engine(project)
        module = TaskModule(None, 'java')
        task = Task('myTask', func_task_config)
        mock_get_config = MagicMock()

        mock_get_config.return_value = config

        project.get_config = mock_get_config

        # noinspection PyProtectedMember
        args, kwargs = engine._format_args(module, task)

        assert args == [config]
        assert kwargs == {}

        task.function = func_named_task_config

        # noinspection PyProtectedMember
        args, kwargs = engine._format_args(module, task)

        assert args == []
        assert kwargs == {'task_config': config}

    def test_format_args_dependencies(self):
        paths = [Path('/path/to/dep')]
        project = Project.from_dir(Path('/path/to/project'))
        engine = Engine(project)
        module = TaskModule(None, 'java')
        task = Task('myTask', func_dependencies)

        with patch('builder.engine.dependency_resolver') as mock_resolver:
            mock_resolver.resolve.return_value = paths

            # noinspection PyProtectedMember
            args, kwargs = engine._format_args(module, task)

        assert args == [paths]
        assert kwargs == {}

        task.function = func_named_dependencies

        with patch('builder.engine.dependency_resolver') as mock_resolver:
            mock_resolver.resolve.return_value = paths

            # noinspection PyProtectedMember
            args, kwargs = engine._format_args(module, task)

        assert args == []
        assert kwargs == {'dependencies': paths}

    def test_format_args_dependencies_not_accepted(self):
        dependency = Dependency.given('repo', None, 'name', '1.2.3', None)
        project = Project.from_dir(Path('/path/to/project'))
        engine = Engine(project)
        module = TaskModule(None, 'java')
        task = Task('myTask', func_no_args)
        mock_get_dependencies = MagicMock()

        mock_get_dependencies.return_value = [dependency]

        project.get_dependencies().get_dependencies_for = mock_get_dependencies

        with patch('builder.engine.end') as mock_end:
            # noinspection PyProtectedMember
            _, _ = engine._format_args(module, task)

        assert mock_get_dependencies.mock_calls == [call('myTask')]
        assert mock_end.mock_calls == [
            call('Dependencies were specified for task myTask but it does not accept dependencies.')
        ]


def func_no_args():
    pass


# noinspection PyUnusedLocal
def func_default_args(mine: int = 1):
    pass


# noinspection PyUnusedLocal
def func_named_default_args(*, mine: int = 1):
    pass


# noinspection PyUnusedLocal
def func_language_config(language_config):
    pass


# noinspection PyUnusedLocal
def func_named_language_config(*, language_config):
    pass


# noinspection PyUnusedLocal
def func_task_config(task_config):
    pass


# noinspection PyUnusedLocal
def func_named_task_config(*, task_config):
    pass


# noinspection PyUnusedLocal
def func_dependencies(dependencies):
    pass


# noinspection PyUnusedLocal
def func_named_dependencies(*, dependencies):
    pass
