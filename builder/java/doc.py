"""
This file provides all the support we need around the `javadoc` tool stuff.
"""
from pathlib import Path
from typing import List

from builder.java import JavaConfiguration
from builder.java.java import _add_verbose_options, add_class_path
from builder.models import DependencyPathSet
from builder.utils import checked_run, global_options


def _find_packages(root: Path, directory: Path, packages: List[str]):
    paths = [path for path in directory.iterdir()]
    dirs = [path for path in paths if path.is_dir()]
    java_files = [path for path in paths if path.is_file() and path.suffix == '.java']

    if len(java_files) > 0:
        packages.append(str(directory.relative_to(root)).replace('/', '.'))

    if len(dirs) > 0:
        for path in dirs:
            _find_packages(root, path, packages)


def java_doc(language_config: JavaConfiguration, dependencies: List[DependencyPathSet]):
    """
    A function that provides the implementation of the ``doc`` task for the Java
    language.  It will build Java documentation for all the source found in the
    location specified by the Java language configuration.

    :param language_config: the configured Java language information.
    :param dependencies: any configured dependencies on the ``doc`` task.
    """
    code_dir = language_config.code_dir()
    doc_dir = language_config.doc_dir(ensure=True)
    options = ['javadoc']
    packages = []

    if global_options.verbose() == 0:
        options.append('-quiet')
    else:
        _add_verbose_options(options)

    add_class_path(options, dependencies)

    options.extend(['-d', str(doc_dir), '--source-path', str(code_dir)])

    _find_packages(code_dir, code_dir, packages)

    options.extend(packages)

    checked_run(options, 'JavaDoc')
