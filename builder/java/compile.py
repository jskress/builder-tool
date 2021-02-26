"""
This file provides all the support we need around compiling and javac.
"""
from pathlib import Path
from typing import List

from builder.java.java import _add_verbose_options, JavaConfiguration, add_class_path
from builder.models import DependencyPathSet
from builder.utils import get_matching_files, TempTextFile, checked_run


def _build_compiler_options(classes_dir: Path, class_path: List[DependencyPathSet],
                            extra_paths: List[Path] = None) -> List[str]:
    """
    Build a list of the command line options we need to send to the ``javac`` tool.

    :param classes_dir: the path representing the directory into which compile files
    should be written.
    :param class_path: an optional collection of path sets that represent any dependencies
    to include in the class path.
    :param extra_paths: an optional list of extra paths to include in the class path.
    :return: the list of basic options for the ``javac`` command.
    """
    options = [
        '-d', str(classes_dir)
    ]

    # noinspection SpellCheckingInspection
    _add_verbose_options(options, '-Xdiags:verbose')
    add_class_path(options, class_path, extra_paths)

    return options


def run_compiler(java_dir: Path, classes_dir: Path, class_path: List[DependencyPathSet],
                 extra_paths: List[Path] = None, sources_required: bool = True):
    """
    A function that executes the ``javac`` tool with appropriate parameters.  Globbing
    is used to search for Java files whose names are written to a temporary file.  That
    file is passed to ``javac`` with the ``@`` sign.

    :param java_dir: the root directory under which Java source files are searched.
    :param classes_dir: the directory into which compiled files should be written.
    :param class_path: an optional collection of path sets that represent any dependencies
    to include in the class path.
    :param extra_paths: an optional list of extra paths to include in the class path.
    :param sources_required: a note as to whether sources are required to exist or not.
    class path.
    """
    options = _build_compiler_options(classes_dir, class_path, extra_paths)
    lines = get_matching_files(java_dir, '**/*.java', to_str=True)

    if lines or sources_required:
        with TempTextFile() as temp_file:
            temp_file.write_lines(lines)
            options.insert(0, 'javac')
            options.append(f'@{temp_file.file_name}')
            process = checked_run(options, 'Compilation', cwd=java_dir, allowed_rcs=(1,))
            if process.returncode == 1:
                raise ValueError('Java source could not be compiled.')


def java_compile(language_config: JavaConfiguration, dependencies: List[DependencyPathSet]):
    """
    A function that will compile a collection of Java source files

    :param language_config: the current Java language configuration information.
    :param dependencies: any configured dependencies on the ``compile`` task.
    """
    java_dir = language_config.code_dir(required=True)
    classes_dir = language_config.classes_dir(ensure=True)

    run_compiler(java_dir, classes_dir, class_path=dependencies)
