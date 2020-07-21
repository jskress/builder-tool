"""
This library provides the core of the builder engine as a class.
"""
import inspect
from typing import Sequence, Tuple, Any

from builder.dependencies import dependency_resolver
from builder.project import Project
from builder.task_module import Task, TaskModule
from builder.utils import global_options, end, out, warn


class Engine(object):
    """
    Instances of this class represent the core engine for executing tasks requested
    by the end user.
    """
    def __init__(self, project: Project):
        """
        A function to create an instance of the ``Engine`` class.  This class is
        designed to be created once during the execution of the command line.

        :param project: the project that provides our execution definitions and
        context.
        """
        self._project = project
        self._module_set = project.get_module_set()
        self._rc = 0

    def run(self):
        if len(global_options.tasks()) is 0:
            self._show_existing_tasks()
        else:
            tasks = self._get_tasks_in_execution_order()
            self._execute_tasks(tasks)
        return self._rc

    def _show_existing_tasks(self):
        """
        A function to display existing tasks.
        """
        warn('No tasks specified.  Available tasks are:', None)
        out()
        self._module_set.print_available_tasks()
        self._rc = 1

    def _get_tasks_in_execution_order(self) -> Sequence[Tuple[TaskModule, Task]]:
        """
        A function to return a sequence of tuples, each containing a task to execute
        and the module to which it belongs.  If the ``--no-requires`` command line
        options was specified, then we return the tasks in the order they were
        specified by the end user.  Otherwise, any tasks required by the ones
        specified by the end user will also be included and the order of the tasks
        is guaranteed to be in the proper order.

        :return: a sequence of tuples, each of which contains the task module a
        tasks belongs to as the first entry and the task itself as the second.
        """
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
        """
        A function that executes the given list of tasks.  We note each task is "visited"
        but (obviously) only execute those for which a function exists.

        :param tasks: a sequence of module/task pairs to execute.
        """
        for module, task in tasks:
            out(f'--> {task.name}', fg='bright_green')
            if task.function is not None:
                self._execute_task(module, task)

    def _execute_task(self, module: TaskModule, task: Task):
        """
        A function for executing a task.  This is nothing more than determining the
        proper arguments and then passing them to the task's function.

        :param module: the module that the task belongs to.
        :param task: the task to execute.
        """
        args, kwargs = self._format_args(module, task)

        task.function(*args, **kwargs)

    def _format_args(self, module: TaskModule, task: Task):
        """
        A function that determines the arguments, in their proper order, that are to be
        passed to a task's function.  Based on the function signature, they are classified
        as either positional or keyword arguments.  Once all parameters are filled in, a
        tuple is returned where the first entry is a list of the positional arguments and
        the second is a dictionary of the keyword arguments.  It is an error for a task to
        have dependencies but it's function does not have a ``dependencies`` parameter.

        We recognize parameters by name and support ``language_config``, ``task_config``
        and ``dependencies``.  Any parameters found that are not named thus are set to their
        default values.

        :param module: the module that the task belongs to.
        :param task: the task for whose function we are to derive arguments.
        :return: a tuple containing the function's positional and keyword arguments.
        """
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
            if parameter.name == 'language_config':
                store(parameter.kind, self._get_language_config(module))
            elif parameter.name == 'task_config':
                store(parameter.kind, self._get_task_config(task))
            elif parameter.name == 'dependencies':
                store(parameter.kind, dependency_resolver.resolve(module.language, dependencies))
                dependencies_not_accepted = False
            else:
                store(parameter.kind, parameter.default)

        if len(dependencies) > 0 and dependencies_not_accepted:
            end(f'Dependencies were specified for task {task.name} but it does not accept dependencies.')

        return args, kwargs

    def _get_language_config(self, module: TaskModule):
        """
        A function that looks up the configuration information, if any, for the given module
        from the current project.

        :param module: the module whose configuration in the project is to be returned.
        :return: the module's configuration data or ``None``.
        """
        return self._project.get_config(module.language, module.configuration_schema, module.configuration_class)

    def _get_task_config(self, task: Task) -> Any:
        """
        A function that looks up the configuration information, if any, for the given task
        from the current project.

        :param task: the task whose configuration in the project is to be returned.
        :return: the module's configuration data or ``None``.
        """
        return self._project.get_config(task.name, task.configuration_schema, task.configuration_class)
