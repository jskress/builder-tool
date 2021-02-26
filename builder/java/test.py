"""
This file provides all the support we need around testing.
"""
from pathlib import Path
from typing import List, Optional, Callable, Dict

from builder.java import JavaConfiguration
from builder.java.compile import run_compiler
from builder.java.java import TestingConfiguration, add_class_path
from builder.models import DependencyPathSet
from builder.utils import checked_run, global_options


def _conditionally_add(path: Optional[Path], paths: List[Path]):
    """
    A helper function for conditionally adding a path to a list.

    :param path: the path to add, if present.
    :param paths: the list to add it to.
    """
    if path:
        paths.append(path)


def compile_tests(language_config: JavaConfiguration, dependencies: List[DependencyPathSet]):
    """
    A function that will compile and execute the project's set of tests.

    :param language_config: the current Java language configuration information.
    :param dependencies: any configured dependencies on the ``test`` task.
    """
    project_classes_dir = language_config.classes_dir(required=True)
    tests_dir = language_config.tests_dir(required=True)
    test_classes_dir = language_config.tests_classes_dir(ensure=True)
    extras: List[Path] = [project_classes_dir]

    _conditionally_add(language_config.resources_dir(), extras)

    run_compiler(tests_dir, test_classes_dir, dependencies, extras, False)


def _find_primary_jar(name: str, dependencies: List[DependencyPathSet], required: bool = True) -> Optional[Path]:
    """
    A function that will search the given list of dependencies for the given name
    and, if found, return its primary jar file.

    :param name: the name of the dependency that carries the test executor jar.
    :param dependencies: any configured dependencies on the ``test`` task.
    :param required: a flag noting whether or not the named dependency is required.
    """
    path_set = next((path_set for path_set in dependencies if path_set.dependency.key == name), None)

    if not path_set and required:
        raise ValueError(f'Cannot find the test dependency, {name}.')

    return path_set.primary_path if path_set else None


def _determine_details_level() -> str:
    """
    A helper function that translates the current verbose level to a JUnit5 details word.

    :return: the appropriate details level that matches the current verbosity.
    """
    verbose = global_options.verbose()
    details = 'none'

    if verbose == 1:
        details = 'summary'
    elif verbose > 1:
        details = 'tree'

    return details


_OptionBuilder = Callable[[JavaConfiguration, TestingConfiguration, List[DependencyPathSet]], List[str]]


def _build_junit5_options(language_config: JavaConfiguration, task_config: TestingConfiguration,
                          dependencies: List[DependencyPathSet]) -> List[str]:
    """
    A function that knows how to build the command line options for running the JUnit5 CLI
    to run tests.

    :param language_config: the current Java language configuration information.
    :param task_config: the configuration for this task.
    :param dependencies: any configured dependencies that were given..
    :return: the list of options to pass to the JUnit5 CLI executable jar.
    """
    project_classes_dir = language_config.classes_dir(required=True)
    test_classes_dir = language_config.tests_classes_dir(ensure=True)
    test_reports_dir = task_config.test_reports_dir(language_config, ensure=True)
    extras: List[Path] = [test_classes_dir, project_classes_dir]
    details = _determine_details_level()
    options: List[str] = ['--disable-banner', f'--details={details}']

    _conditionally_add(language_config.resources_dir(), extras)
    _conditionally_add(language_config.test_resources_dir(), extras)

    add_class_path(options, dependencies, extras)

    options.append('--scan-classpath')
    options.append(str(test_classes_dir))

    if test_reports_dir:
        options.append('--reports-dir')
        options.append(str(test_reports_dir))

    return options


def _build_jacoco_agent_options(language_config: JavaConfiguration, task_config: TestingConfiguration,
                                dependencies: List[DependencyPathSet]) -> List[str]:
    """
    A function that knows how to build the command line options for configuring the JaCoCo runtime
    as an agent.

    :param language_config: the current Java language configuration information.
    :param task_config: the configuration for this task.
    :param dependencies: any configured dependencies that were given..
    :return: the list of options for the JaCoCo agent.
    """
    project_name = global_options.project().name
    coverage_report_dir = task_config.coverage_reports_dir(language_config)
    data_file = coverage_report_dir / f'{project_name}.exec'
    agent_jar = _find_primary_jar(task_config.coverage_agent, dependencies)

    # noinspection SpellCheckingInspection
    return [f'-javaagent:{str(agent_jar)}=destfile={str(data_file)}']


# noinspection PyUnusedLocal
def _build_jacoco_cli_options(language_config: JavaConfiguration, task_config: TestingConfiguration,
                              dependencies: List[DependencyPathSet]) -> List[str]:
    """
    A function that knows how to build the command line options for the JaCoCo CLI for report
    formatter..

    :param language_config: the current Java language configuration information.
    :param task_config: the configuration for this task.
    :param dependencies: any configured dependencies that were given..
    :return: the list of options for the JaCoCo CLI.
    """
    project_name = global_options.project().name
    coverage_report_dir = task_config.coverage_reports_dir(language_config)
    data_file = coverage_report_dir / f'{project_name}.exec'

    # noinspection SpellCheckingInspection
    options = [
        'report', str(data_file), '--classfiles', str(language_config.classes_dir(required=True)),
        '--html', str(task_config.coverage_reports_dir(language_config, ensure=True)), '--name', project_name,
    ]

    if global_options.verbose() == 0:
        options.append('--quiet')

    # noinspection SpellCheckingInspection
    options.extend(['--sourcefiles', str(language_config.code_dir())])

    return options


def run_tests(language_config: JavaConfiguration, task_config: TestingConfiguration,
              dependencies: List[DependencyPathSet]):
    """
    A function that will execute any previously compiled unit tests in the project.

    :param language_config: the current Java language configuration information.
    :param task_config: the configuration for this task.
    :param dependencies: any configured dependencies on the ``test`` task.
    """
    executor_name = task_config.test_executor
    coverage_agent_name = task_config.coverage_agent
    executor = _find_primary_jar(task_config.test_executor, dependencies)
    options_builder = _supported_tools[executor_name]
    cmd_line = ['java']

    if coverage_agent_name and task_config.coverage_reports:
        agent_options_builder = _supported_tools[coverage_agent_name]

        cmd_line.extend(agent_options_builder(language_config, task_config, dependencies))

    cmd_line.extend(['-jar', str(executor)])
    cmd_line.extend(options_builder(language_config, task_config, dependencies))

    checked_run(cmd_line, task_config.test_executor)

    if task_config.coverage_reporter and task_config.coverage_reports:
        executor = _find_primary_jar(task_config.coverage_reporter, dependencies)
        options_builder = _supported_tools[task_config.coverage_reporter]
        cmd_line = ['java', '-jar', str(executor)]

        cmd_line.extend(options_builder(language_config, task_config, dependencies))

        checked_run(cmd_line, task_config.coverage_reporter)


_supported_tools: Dict[str, _OptionBuilder] = {
    'junit5': _build_junit5_options,
    'jacoco': _build_jacoco_agent_options,
    'jacoco-cli': _build_jacoco_cli_options
}
