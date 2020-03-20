"""
This library provides support around using a language module.
"""
import importlib
from typing import Tuple, Optional, Dict, Sequence

import click

from builder.utils import find, verbose_out


class Task(object):
    def __init__(self, name, function, require=None, schema=None, configuration_class=None, configuration_schema=None,
                 help_text=None):
        if require is None:
            require = []
        self.name = name
        self.function = function
        self.require = require
        self.schema = schema
        self.configuration_class = configuration_class
        self.configuration_schema = configuration_schema
        self.help_text = help_text


class TaskModule(object):
    def __init__(self, module, language):
        self.language = language
        self.configuration_class = getattr(module, 'configuration_class', None)
        self.configuration_schema = getattr(module, 'configuration_schema', None)
        self.tasks = getattr(module, 'tasks', None)

    def get_task(self, name: str):
        return find(self.tasks, lambda task: task.name == name)


class ModuleSet(object):
    def __init__(self, modules: dict):
        self._task_to_module = {}
        self._ambiguous = []
        self._modules = modules
        self._force_unique_names()

    def _force_unique_names(self):
        self._task_to_module, duplicates = _get_name_mappings(self._modules)
        for task_name, sources in duplicates:
            for module_name in sources:
                module = self._modules[module_name]
                task = module.get_task(task_name)
                task.name = f'{module_name}::{task_name}'
        self._ambiguous = duplicates.keys()

    def get_task(self, name: str) -> Tuple[TaskModule, Task]:
        module_name, task_name = _parse_task_ref(name)
        if module_name is None:
            module_name = self._task_to_module[task_name] if task_name in self._task_to_module else None
        if module_name is None:
            if task_name in self._ambiguous:
                message = f'The task name, "{task_name}", is ambiguous.'
            else:
                message = f'The task name, "{task_name}", is not defined.'
            raise ValueError(message)
        if module_name not in self._modules:
            raise ValueError(f'There is no language named, "{module_name}".')
        module = self._modules[module_name]
        task = module.get_task(task_name)
        if task is None:
            raise ValueError(f'There is no task named, "{task_name}" for the "{module_name}" language.')
        return module, task

    def print_available_tasks(self):
        for module_name, module in self._modules.items():
            click.secho(f'    {module_name}', fg='white')
            name_width = max(len(task.name) for task in module.tasks)
            for task in module.tasks:
                task_name = click.style(f'{task.name.ljust(name_width)}', fg='bright_green')
                task_help = click.style(f'{task.help_text}', fg='green')
                click.echo(f'        {task_name} -- {task_help}')
            click.echo()


def get_task_module(language: str) -> Optional[TaskModule]:
    try:
        return TaskModule(importlib.import_module(f'builder.{language}'), language)
    except ModuleNotFoundError as exception:
        verbose_out(f'Exception loading module for {language}: {str(exception)}', fg='bright_red')
        return None


def _get_name_mappings(modules: Dict[str, TaskModule]) -> Tuple[Dict[str, str], Dict[str, Sequence[str]]]:
    task_names = {}
    for module_name, module in modules.items():
        for task in module.tasks:
            if task.name not in task_names:
                task_names[task.name] = []
            task_names[task.name].append(module_name)
    duplicate_names = {name: sources for name, sources in task_names.items() if len(sources) > 1}
    unique_names = {name: sources[0] for name, sources in task_names.items() if len(sources) == 1}

    return unique_names, duplicate_names


def _parse_task_ref(reference: str) -> Tuple[Optional[str], str]:
    parts = [part.strip() for part in reference.split('::', maxsplit=1)]
    # Allow the form, "::task_name" and treat it the same as just "task_name"
    if len(parts[0]) == 0:
        parts = parts[1:]
    # Length of parts now will be either 1 (task name only) or 2 (module and task names)
    if len(parts) == 2:
        return parts[0], parts[1]
    else:
        return None, parts[0]
