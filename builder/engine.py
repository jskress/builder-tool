"""
This library provides the core of the builder engine as a class.
"""
import inspect
import sys
from typing import Sequence, Tuple

import click

from builder.dependencies import dependency_resolver
from builder.project import Project
from builder.task_module import Task, TaskModule
from builder.utils import global_options, end, out, warn


class Engine(object):
    def __init__(self, project: Project):
        self._project = project
        self._module_set = project.get_module_set()
        self._rc = 0

    def run(self):
        if len(global_options.tasks()) is 0:
            self._show_existing_tasks()
        else:
            tasks = self._get_tasks_in_execution_order()
            self._execute_tasks(tasks)
        sys.exit(self._rc)

    def _show_existing_tasks(self):
        warn('No tasks specified.  Available tasks are:', None)
        click.echo()
        self._module_set.print_available_tasks()
        self._rc = 1

    def _get_tasks_in_execution_order(self):
        tasks = [self._module_set.get_task(name) for name in global_options.tasks()]
        if global_options.independent_tasks():
            return tasks

        def add_task(containing_module: TaskModule, new_task: Task):
            if new_task.name not in task_names:
                for required_task_name in new_task.require:
                    add_task(containing_module, containing_module.get_task(required_task_name))

                task_names.append(new_task.name)
                full_task_list.append((containing_module, new_task))

        task_names = []
        full_task_list = []
        for module, task in tasks:
            add_task(module, task)

        return full_task_list

    def _execute_tasks(self, tasks: Sequence[Tuple[TaskModule, Task]]):
        for module, task in tasks:
            out(f'--> {task.name}', fg='bright_green')
            if task.function is not None:
                self._execute_task(module, task)

    def _execute_task(self, module: TaskModule, task: Task):
        args, kwargs = self._format_args(module, task)

        task.function(*args, **kwargs)

    def _format_args(self, module: TaskModule, task: Task):
        dependencies = self._project.get_dependencies().get_dependencies_for(task.name)
        dependencies_not_accepted = True
        signature = inspect.signature(task.function)
        args = []
        kwargs = {}

        def store(kind, value):
            if kind == inspect.Parameter.POSITIONAL_ONLY or \
               kind == inspect.Parameter.POSITIONAL_OR_KEYWORD:
                args.append(value)
            else:
                kwargs[parameter.name] = value

        for parameter in signature.parameters.values():
            if parameter.name == 'project':
                store(parameter.kind, self._project)
            elif parameter.name == 'language_config':
                store(parameter.kind, self._get_language_config(module))
            elif parameter.name == 'task_config':
                store(parameter.kind, self._get_task_config(task))
            elif parameter.name == 'dependencies':
                store(parameter.kind, dependency_resolver.resolve(dependencies))
                dependencies_not_accepted = False

        if len(dependencies) > 0 and dependencies_not_accepted:
            end(f'Dependencies were specified for task {task.name} but it does not accept dependencies.')

        return args, kwargs

    def _get_language_config(self, module: TaskModule):
        return self._project.get_config(module.language, module.configuration_schema, module.configuration_class)

    def _get_task_config(self, task: Task):
        return self._project.get_config(task.name, task.configuration_schema, task.configuration_class)
