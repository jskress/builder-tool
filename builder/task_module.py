"""
This library provides support around using a language module.
"""
import importlib
import re
from typing import Tuple, Optional, Dict, Sequence, Callable, Any, List

import click
from builder.models import Task, Language

from builder.utils import warn, out

_task_name_pattern = re.compile(r'^(?:(\w+?)?::)?(\w+(?:-\w+)*)$')
_import_module = importlib.import_module
ModuleImporter = Callable[[str], Any]


class ModuleSet(object):
    def __init__(self, modules: Dict[str, Language]):
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

    def get_language(self, language: str) -> Optional[Language]:
        """
        A function that returns the named language definition.

        :param language: the desired language definition.
        :return: the named language or ``None``.
        """
        return self._modules[language] if language in self._modules else None

    def get_task(self, task_ref: str) -> Tuple[Language, Task]:
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


def get_language_module(language: str) -> Optional[Language]:
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
        return Language(_import_module(f'builder.{language}'), language)
    except ModuleNotFoundError as exception:
        warn(f'Exception loading module for {language}: {str(exception)}')
        return None


def _get_name_mappings(modules: Dict[str, Language]) -> Tuple[Dict[str, str], Dict[str, Sequence[str]]]:
    """
    A function to build maps keyed by task name.  The first map is of task names which are
    unique across all known languages.  Each task name maps to the name of the language that
    defined it.  The second map is of task names found in more than one language.  Each task
    name maps to the list of languages that defined it.  This allows task names to only be
    qualified by language when absolutely necessary.

    :param modules: a dictionary of task modules, keyed by language.
    :return: the unique tasks map and the duplicate tasks map.
    """
    task_names: Dict[str, List[str]] = {}
    for language_name, language in modules.items():
        for task in language.tasks:
            if task.name not in task_names:
                task_names[task.name] = []
            task_names[task.name].append(language_name)
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
