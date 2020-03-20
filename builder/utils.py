"""
This library provides a number of low-level utilities.
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable, Iterable, Sequence, Union, Optional, TypeVar, Tuple

import click

PathSequence = Union[Sequence[Path], Sequence[str]]
T = TypeVar("T")


class GlobalOptions(object):
    def __init__(self):
        self._quiet = False
        self._verbose = False
        self._independent_tasks = False
        self._force_remote_fetch = False
        self._languages = ()
        self._vars = {}
        self._tasks = ()
        self._project = None

    def set_quiet(self, value: bool):
        self._quiet = value
        return self

    def set_verbose(self, value: int):
        self._verbose = value
        return self

    def set_independent_tasks(self, value: bool):
        self._independent_tasks = value
        return self

    def set_force_remote_fetch(self, value: bool):
        self._force_remote_fetch = value
        return self

    def set_languages(self, value: Sequence):
        self._languages = value
        return self

    def set_vars(self, set_vars: Tuple[str]):
        if set_vars:
            for set_var in set_vars:
                for clause in set_var.split(','):
                    name, value = clause.split('=', 1)
                    self._vars[name.strip()] = value.strip()
        return self

    def set_tasks(self, value: Sequence):
        self._tasks = value
        return self

    def set_project(self, project):
        self._project = project

    def quiet(self):
        return self._quiet

    def verbose(self):
        return self._verbose

    def independent_tasks(self):
        return self._independent_tasks

    def force_remote_fetch(self):
        return self._force_remote_fetch

    def languages(self):
        return self._languages

    def var(self, name: str) -> Optional[str]:
        return self._vars[name] if name in self._vars else None

    def tasks(self):
        return self._tasks

    def project(self):
        return self._project


class TempTextFile(object):
    # noinspection SpellCheckingInspection
    """
    This class represents a temporary text file.  The `tempfile.mkstemp()` function is used
    to obtain a temporary file name.  This is less safe in a concurrent sense but allows
    better control of when and what happens to the file.  The appropriate usage would be
    similar to the following:

    ```
    tf = TempTextFile()
    try:
        tf.write_lines(...)
    finally:
        tf.remove()
    ```

    This style guarantees that the temporary file will be properly removed once it's no
    longer needed.
    """
    def __init__(self):
        fd, file_name = tempfile.mkstemp(suffix='.txt', text=True)
        os.close(fd)
        self.file_name = file_name

    def write_lines(self, lines: Iterable[str]):
        with open(self.file_name, "w", encoding='utf-8') as fd:
            fd.write('\n'.join(lines))
            fd.write('\n')

    def remove(self):
        os.remove(self.file_name)


def find(sequence: Iterable[T], predicate: Callable) -> Optional[T]:
    """
    This is a helper function for efficiently applying the given predicate on the specified
    sequence.  The first item for which the predicate returns True will be returned.  If the
    predicate never returns True, then None is returned.

    :param sequence: The sequence to traverse
    :param predicate: The predicate to apply to each item
    :return: The first item for which the predicate returns True or None.
    """
    for item in sequence:
        if predicate(item):
            return item
    return None


def get_matching_files(directory: Path, pattern: str, path_like: bool = False) -> PathSequence:
    """
    This is a helper function that returns a list of file names underneath the given
    directory that match the specified glob pattern.  The names returned are relative
    to the given directory.  The file names are returned as strings.

    :param directory: the root of the file tree to search.
    :param pattern: the glob pattern to match.
    :param path_like: if True, will not convert the resulting file names to strings.
    :return: the list of matching files.
    """
    file_names = []

    for path in directory.glob(pattern):
        file_name = path.relative_to(directory)
        if not path_like:
            file_name = str(file_name)
        file_names.append(file_name)

    return file_names


def remove_directory(directory: Path):
    """
    This function may be used to remove a directory.  If the directory is not currently empty,
    it will iterate over the contents, removing each item.  If the item is a directory, the
    function will recurse on it to remove the entire tree.  If the directory already does not
    exist, we quietly do nothing.

    :param directory: the directory to remove.
    """
    if directory.is_dir():
        for path in directory.iterdir():
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                remove_directory(path)
        directory.rmdir()


def out(text, respect_quiet: bool = True, **kwargs):
    """
    This function is a thin wrapper around `click.secho` and will only output the given information
    if the user says it's ok.
    """
    if not (global_options.quiet() and respect_quiet):
        click.secho(text, **kwargs)


def verbose_out(text, **kwargs):
    """
    This function is a thin wrapper around `click.secho` and will only output the given information
    if the user says it's ok.
    """
    if global_options.verbose() > 0:
        if 'fg' not in kwargs:
            kwargs['fg'] = 'green'
        click.secho(text, **kwargs)


def labeled_out(text, label: Optional[str] = None, respect_quiet: bool = True, **kwargs):
    if label:
        text = f'{label}: {text}'
    out(text, respect_quiet, **kwargs)


def warn(text, label: Optional[str] = 'Warning'):
    labeled_out(text, label, respect_quiet=False, fg='yellow')


def end(*args, label: str = 'ERROR', rc=1):
    for line in args:
        labeled_out(line, label, respect_quiet=False, fg='bright_red')
    sys.exit(rc)


def checked_run(args, action: str, capture=False, cwd=None, allowed_rcs=None) -> subprocess.CompletedProcess:
    """
    This function invokes the specified command line as a subprocess.  If the
    subprocess fails (i.e., returns with a non-zero return code), execution is
    stopped after printing an appropriate message.

    :param args: the sequence of words representing the command line to invoke.
    :param action: the action text to print in the event of an error.
    :param capture: whether the command's output should be captured or not.
    :param cwd: the directory to run the command from.
    :param allowed_rcs: a sequence of allowed return codes.  If it is None (the
           default), the only allowed return code is 0.  Provide an empty sequence
           to allow any return code.  A return code of 0 is always acceptable.
    :return the CompletedProcess instance from running the command.
    """
    if allowed_rcs is None:
        allowed_rcs = []

    verbose_out(f'Running: {" ".join(args)}')
    completed_process = subprocess.run(args, capture_output=capture, cwd=cwd)
    rc = completed_process.returncode

    if len(allowed_rcs) > 0 and rc != 0 and rc not in allowed_rcs:
        end(f'{action} failed with return code {rc}.', f'Command: {" ".join(args)}', rc=rc)

    return completed_process


global_options = GlobalOptions()
