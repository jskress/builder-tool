"""
This file provides all the support we need around compiling and javac.
"""
import os
from pathlib import Path
from typing import Iterable, Sequence, Union

from builder.java.java import _add_verbose_options, JavaConfiguration
from builder.utils import get_matching_files, TempTextFile, checked_run


def _build_compiler_options(classes_dir: Path, class_path: Iterable[Union[Path, str]] = None):
    options = [
        '-d', str(classes_dir)
    ]

    # noinspection SpellCheckingInspection
    _add_verbose_options(options, '-Xdiags:verbose')

    if class_path is not None:
        class_path = [str(path) for path in class_path]
        options.append('--class-path')
        options.append(os.pathsep.join(class_path))

    return options


def _run_compiler(java_dir: Path, classes_dir: Path, class_path: Iterable[Union[Path, str]] = None):
    options = _build_compiler_options(classes_dir, class_path)
    lines = get_matching_files(java_dir, '**/*.java')
    temp_file = TempTextFile()
    try:
        temp_file.write_lines(lines)
        name = f'@{temp_file.file_name}'
        options.insert(0, 'javac')
        options.append(name)
        process = checked_run(options, 'Compilation', cwd=java_dir, allowed_rcs=(1,))
        if process.returncode == 1:
            raise ValueError('Java source could not be compiled.')
    finally:
        temp_file.remove()


def java_compile(language_config: JavaConfiguration, dependencies: Sequence[Path]):
    java_dir = language_config.code_dir(required=True)
    classes_dir = language_config.classes_dir(ensure=True)

    _run_compiler(java_dir, classes_dir, class_path=dependencies)
