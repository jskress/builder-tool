"""
This file provides all the support we need around the `javap` tool for describing
compiled Java classes.
"""
import re
from pathlib import Path
from typing import Sequence, List

from builder.java.java import _add_verbose_options
from builder.utils import checked_run, get_matching_files

_name_pattern = re.compile(r'^(?:public |protected |private )?(?:final )?(class|interface) ([.$\w]+) ')
_entry_point_signature = 'public static void main(java.lang.String[]);'


class JavaClass(object):
    """
    This class provides a representation of the information we gather about a class
    by running the ``javap`` CLI tool.
    """
    def __init__(self, lines: Sequence[str]):
        print(lines[0])
        match = _name_pattern.match(lines[0])
        self._type = match.group(1)
        self._name = match.group(2)
        self._lines = [line.strip() for line in lines[1:-1]]

    def type(self):
        """
        The type of the class, either `class` or `interface`.

        :return: the type of compiled thing we found.
        """
        return self._type

    def name(self):
        """
        The name of the class.

        :return: the name of the class or interface.
        """
        return self._name

    def is_entry_point(self) -> bool:
        """
        Tells whether the class we represent is an application entry point.
        The type must be ``class`` and the content must include a static ``main``
        method for this to return ``True``.

        :return: whether what we represent is a Java application entry point or
        not.
        """
        return 'class' == self._type and _entry_point_signature in self._lines


def _group_class_file_names(paths: Sequence[Path], max_length: int = 3900) -> Sequence[Sequence[Path]]:
    """
    Take the given sequence of paths and split them into sequences such that
    their cumulative length is no more than requested.  This is used to build
    command lines for the ``javap`` tool that are not overly long, regardless of
    the lengths of individual class file names while still minimizing the number
    of times the ``javap`` tool must be invoked.

    :param paths: the list of paths to group.
    :param max_length: the maximum cumulative length to allow.  The default is
    3900.
    :return: a sequence of sequences.  Each sub-sequence contains an appropriate
    number of paths.
    """
    sets = []
    start = 0
    length = 0

    for index, path in enumerate(paths):
        path_length = len(str(path)) + 1
        if length + path_length > max_length:
            sets.append(paths[start:index])
            start = index
            length = 0
        else:
            length = length + path_length

    sets.append(paths[start:])

    return sets


def _parse_class_info_output(lines: Sequence[str], classes: List[JavaClass]):
    """
    A function that parses the lines printed by the ``javap`` tool into a list
    of representative ``JavaClass`` objects.

    :param lines: the output lines from the ``javap`` tool to parse.
    :return: the resulting list of Java object representations.
    """
    start = 1

    for index, line in enumerate(lines):
        if line.startswith('Compiled from '):
            if start < index:
                classes.append(JavaClass(lines[start:index]))
            start = index + 1

    classes.append(JavaClass(lines[start:]))


def _run_describer(classes_dir: Path, paths: Sequence[Path], public_only: bool) -> Sequence[str]:
    """
    A function that wraps the execution of the ``javap`` tool.

    :param classes_dir: the root directory for all the classes we are passing to the
    ``javap`` tool.
    :param paths: the sequence of class files to pass to the ``javap`` tool.  Each must
    be relative to ``classes_dir``.
    :param public_only: controls whether the ``-public`` switch is given to ``javap``.
    :return: the output of the ``javap`` tool, as a sequence of lines.
    """
    # noinspection SpellCheckingInspection
    options = []

    if public_only:
        options.append('-public')

    _add_verbose_options(options)

    for path in paths:
        options.append(str(path))

    # Needs to happen last because of how verbose works.
    options.insert(0, 'javap')

    process = checked_run(options, 'Class description', capture=True, cwd=classes_dir)
    lines = process.stdout.decode().split('\n')

    return lines


def describe_classes(classes_dir: Path, public_only: bool = True) -> Sequence[JavaClass]:
    """
    This function locates all the class files in the directory sub-tree rooted
    at the specified classes directory and generates a ``JavaClass`` instance for
    each one found by using the ``javap`` CLI tool to describe it.

    :param classes_dir: the directory to scan for class files.
    :param public_only: a flag that controls whether we ask for public information
    only about each class.  The default is ``True``.
    :return: a sequence of ``JavaClass`` objects that describe each of the class files
    we found under the requested directory..
    """
    class_files = get_matching_files(classes_dir, '**/*.class')
    classes = []

    if len(class_files) > 0:
        class_file_sets = _group_class_file_names(class_files)

        for class_file_set in class_file_sets:
            output = _run_describer(classes_dir, class_file_set, public_only)
            _parse_class_info_output(output, classes)

    return classes
