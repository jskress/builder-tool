"""
This library provides support around using a language module.
"""
import importlib
import re
from typing import Tuple, Optional, Dict, Sequence, Callable, Any

import click

from builder.schema_validator import SchemaValidator
from builder.utils import find, warn, out

_task_name_pattern = re.compile(r'^(?:(\w+?)?::)?(\w+)$')
_import_module = importlib.import_module
ModuleImporter = Callable[[str], Any]


class Task(object):
    def __init__(self, name: str, function: Optional[Callable], require: Optional[Sequence[str]] = None,
                 configuration_class=None, configuration_schema: Optional[SchemaValidator] = None,
                 help_text: Optional[str] = None):
        if require is None:
            require = []
        self.name = name
        self.function = function
        self.require = require
        self.configuration_class = configuration_class
        self.configuration_schema = configuration_schema
        self.help_text = help_text


class TaskModule(object):
    def __init__(self, module, language: str):
        self.language = language
        self.configuration_class = getattr(module, 'configuration_class', None)
        self.configuration_schema = getattr(module, 'configuration_schema', None)
        self.tasks = getattr(module, 'tasks', None)

    def get_task(self, name: str) -> Optional[Task]:
        """
        A function that returns the named task.  If there is no task that carries the
        requested name, then ``None`` will be returned.

        :param name: the name of the desired task.
        :return: the requested task or ``None``.
        """
        return find(self.tasks, lambda task: task.name == name)


class ModuleSet(object):
    def __init__(self, modules: Dict[str, TaskModule]):
        self._task_to_module = {}
        self._ambiguous = []
        self._modules = modules
        self._force_unique_names()

    def _force_unique_names(self):
        """
        A function that guarantees that all task names across all modules are globally unique.
        If the same task name is found in multiple modules, it's name is altered to be qualified
        by the name of the module that contains it in the form, ``<module-name>::<task-name>``.
        """
        self._task_to_module, duplicates = _get_name_mappings(self._modules)
        for task_name, sources in duplicates.items():
            for module_name in sources:
                module = self._modules[module_name]
                task = module.get_task(task_name)
                task.name = f'{module_name}::{task_name}'
        self._ambiguous = list(duplicates.keys())

    def get_task(self, task_ref: str) -> Tuple[TaskModule, Task]:
        """
        A function that uses a task reference to look up the module and task that it represents.
        If the reference cannot be resolved to a module/task pair, an exception is raised.

        :param task_ref: the task reference to use to look up the task and its owning module.
        :return: a tuple containing the module and task that the reference resolves to.
        """
        module_name, task_name = _parse_task_ref(task_ref)
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
        """
        A function that prints out the list of tasks that are defined in each of our known
        modules.
        """
        for module_name, module in self._modules.items():
            out(f'    {module_name}', respect_quiet=False, fg='white')
            name_width = max(len(task.name) for task in module.tasks)
            for task in module.tasks:
                task_name = click.style(f'{task.name.ljust(name_width)}', fg='bright_green')
                task_help = click.style(f'{task.help_text}', fg='green')
                out(f'        {task_name} -- {task_help}', respect_quiet=False)
            out('', respect_quiet=False)


def get_task_module(language: str) -> Optional[TaskModule]:
    """
    A function for loading the support module for a language.  This isn't considered
    fatal since a task error will likely occur.  This gives the end user the most
    information.  Especially since this is most likely to occur when a language is
    added via the ``--language`` command line option.  If a support module cannot
    be loaded, a warning is printed and ``None`` is returned.

    :param language: the language to load the support module for.
    :return: the loaded task module or ``None``.
    """
    try:
        return TaskModule(_import_module(f'builder.{language}'), language)
    except ModuleNotFoundError as exception:
        warn(f'Exception loading module for {language}: {str(exception)}')
        return None


def _get_name_mappings(modules: Dict[str, TaskModule]) -> Tuple[Dict[str, str], Dict[str, Sequence[str]]]:
    """
    A function to build maps keyed by task name.  The first map is of task names which are
    unique across all known languages.  Each task name maps to the name of the language that
    defined it.  The second map is of task names found in more than one language.  Each task
    name maps to the list of languages that defined it.  This allows task names to only be
    qualified by language when absolutely necessary.

    :param modules: a dictionary of task modules, keyed by language.
    :return: the unique tasks map and the duplicate tasks map.
    """
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
    """
    A function for parsing a task reference as specified by a user.  A reference must contain
    a task name, optionally prefixed with a module name.  If a module name is present, it is
    separated from the task name by a pair of colons.  The pair of colons may prefix the task
    name without the module name but is treated the same as if just the task name was specified.

    :param reference: the task reference to parse.
    :return: a two-entry tuple containing the module name, which may be ``None`` and the task
    name.
    """
    match = _task_name_pattern.match(reference)
    if not match:
        raise ValueError(f'The text, "{reference}", is not a valid task name.')
    module, task = match.groups()
    return module, task


def set_module_import(importer: Optional[ModuleImporter] = None):
    global _import_module
    _import_module = importer or importlib.import_module
