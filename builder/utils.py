"""
This library provides a number of low-level utilities.
"""
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence, Union, Optional, TypeVar, Dict, Match

import click

PathSequence = Union[Sequence[Path], Sequence[str]]
T = TypeVar("T")
_var_pattern = re.compile(r'[$]{(.*?)[}]')

# Types for function references.
SubprocessRunner = Callable[[Sequence[str], bool, Path], subprocess.CompletedProcess]
Echo = Callable[[str, Any], None]

# These are function references to facilitate unit testing.
_run_subprocess = subprocess.run
_echo = click.secho


class GlobalOptions(object):
    """
    A class that holds all our global information.  This consists primarily of the
    command line options specified by the user, the current project and a global
    variable pool.

    It also provides the means to perform value retrieval and text substitution from
    the variable pool.
    """
    def __init__(self):
        self._quiet = False
        self._verbose = 0
        self._independent_tasks = False
        self._force_remote_fetch = False
        self._languages = ()
        self._vars = {}
        self._tasks = ()
        self._project = None

    def set_quiet(self, value: bool) -> 'GlobalOptions':
        """
        This function sets whether or not the user has requested quiet operation.
        If this is ``True``, normal output will be suppressed.

        :param value: whether or not quiet mode is in force.
        :return: this object, for fluency.
        """
        self._quiet = value
        return self

    def set_verbose(self, value: int) -> 'GlobalOptions':
        """
        This function sets the count of how many times the user specified the verbose
        option.  The higher the number, the more verbose the output.

        :param value: the number indicating verbosity.  Zero means no verbosity.
        :return: this object, for fluency.
        """
        self._verbose = value
        return self

    def set_independent_tasks(self, value: bool) -> 'GlobalOptions':
        """
        This function sets whether or not the user is requesting that task prerequisite
        processing be bypassed.  If this is ``True``, each task will be executed without
        regard to any prerequisite tasks.  Prerequisite tasks will not be executed unless
        explicitly specified by the user.

        :param value: whether or not prerequisite tasks should be processed.
        :return: this object, for fluency.
        """
        self._independent_tasks = value
        return self

    def set_force_remote_fetch(self, value: bool) -> 'GlobalOptions':
        """
        This function sets whether or not the user is requesting that dependencies be
        fetched form their remote location, even if they are already in the local file
        cache.  If this is ``True``, dependencies will always be fetched, ignoring the
        local file cache.  The file cache will still be updated.

        :param value: whether or not dependencies should always be fetched.
        :return: this object, for fluency.
        """
        self._force_remote_fetch = value
        return self

    def set_languages(self, value: Sequence[str]) -> 'GlobalOptions':
        """
        This function sets any extra languages specified by the user to include in the
        current project.

        :param value: the sequence of any extra languages that should, for this run, be
        included in task processing.
        :return: this object, for fluency.
        """
        self._languages = value
        return self

    def set_vars(self, set_vars: Sequence[str]) -> 'GlobalOptions':
        """
        This function sets variables in the global options variable pool.  Each
        string passed in the ``set_vars`` sequence is taken as a comma delimited list
        of assignment statements of the form ``name=value``.  Passing a sequence of
        ``('n1=v1', 'n2=v2')`` is effectively identical as a sequence with a single
        ``n1=v1,n2=v2`` string.

        :param set_vars: the sequence of variable assignment statements.
        :return: this object, for fluency.
        """
        if set_vars:
            for set_var in set_vars:
                for clause in set_var.split(','):
                    parts = clause.split('=', 1)
                    name = parts[0]
                    value = parts[1] if len(parts) > 1 else ''
                    self._vars[name.strip()] = value.strip()
        return self

    def set_tasks(self, value: Sequence[str]) -> 'GlobalOptions':
        """
        This function sets the list of tasks to execute that were specified by the user.
        Other tasks may be executed that are not listed if they are prerequisite to ones
        that are specified.  This is controlled by the "independent tasks" option.

        :param value: the sequence of tasks that should be executed..
        :return: this object, for fluency.
        """
        self._tasks = value
        return self

    def set_project(self, project) -> 'GlobalOptions':
        """
        This function sets the current project in use for this run.

        :param project: the project to set as the current one.
        :return: this object, for fluency.
        """
        self._project = project
        return self

    def quiet(self) -> bool:
        """
        This function returns whether or not the user has requested quiet operation.
        If this is ``True``, normal output will be suppressed.

        :return: whether or not quiet mode is in force.
        """
        return self._quiet

    def verbose(self) -> int:
        """
        This function returns a count of how many times the user specified the verbose
        option.  The higher the number, the more verbose the output.

        :return: a number indicating verbosity.  Zero means no verbosity.
        """
        return self._verbose

    def independent_tasks(self) -> bool:
        """
        This function returns whether or not the user has requested that task prerequisite
        processing be bypassed.  If this is ``True``, each task will be executed without
        regard to any prerequisite tasks.  Prerequisite tasks will not be executed unless
        explicitly specified by the user.

        :return: whether or not prerequisite tasks should be processed.
        """
        return self._independent_tasks

    def force_remote_fetch(self) -> bool:
        """
        This function returns whether or not the user has requested that dependencies be
        fetched form their remote location, even if they are already in the local file
        cache.  If this is ``True``, dependencies will always be fetched, ignoring the
        local file cache.  The file cache will still be updated.

        :return: whether or not dependencies should always be fetched.
        """
        return self._force_remote_fetch

    def languages(self) -> Sequence[str]:
        """
        This function returns any extra languages specified by the user to include in
        the current project.

        :return: the sequence of any extra languages that should, for this run, be
        included in task processing.
        """
        return self._languages

    def var(self, name: str) -> Optional[str]:
        """
        This function returns the current value associated with the given variable name,
        if any.  When a value is requested, it will come from the variable pool.  If no
        such name is found there, the current project's variables will be checked.  If
        If there is no value there (or there's no current project), then environment
        variables are checked.  If no value is found, then ``None`` is returned.

        :param name: the name of the variable to get the value of.
        :return: the current value of the given name or `None`.
        """
        if name in self._vars:
            return self._vars[name]
        value = self._project.get_var_value(name) if self._project else None
        return value or os.environ.get(name)

    def substitute(self, text: str, extras: Optional[Dict[str, str]] = None, ignore_global_vars: bool = False) -> str:
        """
        A function to perform variable substitution in a string.  Variables must be in the
        form, ``${var-name}``.  The value of ``var-name`` is determined by the `var()` function.
        In addition, a dictionary of name/value pairs may be provided.  These will take
        precedence over the ``var()`` function result.  If the named variable has no value,
        it is replaced with the empty string.

        :param text: the text within which variables should be found and replaced.
        :param extras: an optional dictionary of name/value pairs.
        :param ignore_global_vars: if ``True``, the global variable resolution will be skipped.
        In this case, ``extras`` will be the sole source of name/value resolution.
        :return: The value of `text`, but with all variable references replaced by their
        values.
        """
        def do_substitution(match: Match[str]) -> str:
            name = match.group(1).strip()
            if extras and name in extras:
                return extras[name]
            value = None
            if not ignore_global_vars:
                value = self.var(name)
            return value or ''

        return _var_pattern.sub(do_substitution, text)

    def tasks(self) -> Sequence[str]:
        """
        This function returns the list of tasks to execute that were specified by the user.
        Other tasks may be executed that are not listed if they are prerequisite to ones
        that are specified.  This is controlled by the "independent tasks" option.

        :return: the sequence of tasks that should be executed..
        """
        return self._tasks

    # Note: text class reference to avoid a circular import problem.
    # noinspection PyUnresolvedReferences
    def project(self) -> Optional['Project']:
        """
        This function returns the current project in use for this run.

        :return: the current project project or ``None``, if there isn't one.
        """
        return self._project


class TempTextFile(object):
    # noinspection SpellCheckingInspection
    """
    This class represents a temporary text file.  The ``tempfile.mkstemp()`` function is used
    to obtain a temporary file name.  This is less safe in a concurrent sense but allows
    better control of when and what happens to the file.  The appropriate usage would be
    similar to the following:

        with TempTextFile() as file:
            file.write_lines(...)

    This style guarantees that the temporary file will be properly removed once it's no
    longer needed; i.e., upon leaving the ``with`` context.  Once the file is written, any
    reading of the file must be done within the ``with`` context.
    """
    def __init__(self):
        fd, file_name = tempfile.mkstemp(suffix='.txt', text=True)
        os.close(fd)
        self.file_name = Path(file_name)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._remove()

    def write_lines(self, lines: Iterable[str]):
        """
        A function that wries a collection of strings to the temporary file.  New lines
        are automatically added to the end of each line.

        :param lines: an iterable collection of lines to write to the temporary file.
        """
        with self.file_name.open("w", encoding='utf-8') as fd:
            fd.write('\n'.join(lines))
            fd.write('\n')

    def _remove(self):
        if self.file_name.exists():
            self.file_name.unlink()


def find(sequence: Iterable[T], predicate: Callable[[T], bool]) -> Optional[T]:
    """
    This is a helper function for efficiently applying the given predicate on the specified
    sequence.  The first item for which the predicate returns ``True`` will be returned.  If the
    predicate never returns ``True``, then ``None`` is returned.

    :param sequence: the sequence to traverse
    :param predicate: the predicate to apply to each item
    :return: the first item for which the predicate returns True or None.
    """
    for item in sequence:
        if predicate(item):
            return item
    return None


def get_matching_files(directory: Path, pattern: str, to_str: bool = False) -> PathSequence:
    """
    This is a helper function that returns a list of file paths underneath the given
    directory that match the specified glob pattern.  The paths returned are relative
    to the given directory.  Optionally, they may be returned as a list of strings.

    :param directory: the root of the file tree to search.
    :param pattern: the glob pattern to match.
    :param to_str: if ``True``, will convert the resulting file paths to strings.
    :return: the list of matching files.
    """
    file_names = []

    for path in directory.glob(pattern):
        file_name = path.relative_to(directory)
        if to_str:
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


def out(text: str = '', respect_quiet: bool = True, **kwargs):
    """
    This function is a thin wrapper around ``click.secho`` and will only output the given
    information if the user says it's ok.

    :param text: the text to print out.
    :param respect_quiet: a flag noting whether the ``quiet`` attribute of global options
    should be respected.  If this is ``False``, text will always be output.
    """
    if not (global_options.quiet() and respect_quiet):
        _echo(text, **kwargs)


def verbose_out(text, **kwargs):
    """
    This function is a thin wrapper around ``click.secho`` and will only output the given
    information if the user says it's ok via the verbose attribute of the global options.

    :param text: the text to print out.
    """
    if global_options.verbose() > 0:
        if 'fg' not in kwargs:
            kwargs['fg'] = 'green'
        _echo(text, **kwargs)


def labeled_out(text, label: Optional[str] = None, respect_quiet: bool = True, **kwargs):
    """
    This function is a thin wrapper around ``out`` and will only output the given
    information if the user says it's ok.  If a label is provided, it is prepended to
    the given text.

    :param text: the text to print out.
    :param label: the label, if any, to prepend to the text.
    :param respect_quiet: a flag noting whether the ``quiet`` attribute of global options
    should be respected.  If this is ``False``, text will always be output.
    """
    if label:
        text = f'{label}: {text}'
    out(text, respect_quiet, **kwargs)


def warn(text, label: Optional[str] = 'Warning'):
    """
    This function is a thin wrapper around ``labeled_out`` and will only output the given
    information if the user says it's ok.  If a label is not provided, it defaults to
    `Warning'.  The label is prepended to the text given.  Output will occur regardless
    of the ``quiet`` attribute of the global options.

    :param text: the text to print out.
    :param label: the label, if any, to prepend to the text.
    """
    labeled_out(text, label, respect_quiet=False, fg='yellow')


def end(*args, label: str = 'ERROR', rc=1):
    """
    A function to print messages to the end user as errors and exit.  Each line of
    output will be prepended with the given label, which defaults to ``ERROR`` if it
    is not specified.

    :param args: the list of lines to print out.
    :param label: the label, if any, to prepend to the text.
    :param rc: the return code to exit with.  This will default to ``1`` if not specified.
    """
    for line in args:
        labeled_out(line, label, respect_quiet=False, fg='bright_red')
    sys.exit(rc)


def checked_run(args: Sequence[str], action: str, capture: bool = False, cwd: Path = None,
                allowed_rcs: Optional[Sequence[int]] = None) -> subprocess.CompletedProcess:
    """
    This function invokes the specified command line as a subprocess.  If the
    subprocess fails (i.e., returns with a non-zero return code), execution is
    stopped after printing an appropriate message unless the return code value
    is present in ``allowed_rcs``.

    :param args: the sequence of words representing the command line to invoke.
    :param action: the action text to print in the event of an error.
    :param capture: whether the command's output should be captured or not.
    :param cwd: the directory to run the command from.
    :param allowed_rcs: a sequence of allowed return codes.  If it is None (the
    default), the only allowed return code is 0.  Provide an empty sequence to
    allow any return code.  A return code of 0 is always acceptable.
    :return: the CompletedProcess instance from running the command.
    """
    if allowed_rcs is None:
        allowed_rcs = []

    verbose_out(f'Running: {" ".join(args)}')
    completed_process = _run_subprocess(args, capture_output=capture, cwd=cwd)
    rc = completed_process.returncode

    if rc != 0 and rc not in allowed_rcs:
        end(f'{action} failed with return code {rc}.', f'Command line: {" ".join(args)}', rc=rc)

    return completed_process


def set_subprocess_runner(runner: Optional[SubprocessRunner] = None):
    global _run_subprocess
    _run_subprocess = runner or subprocess.run


def set_echo(echo: Optional[Echo] = None):
    global _echo
    _echo = echo or click.secho


global_options = GlobalOptions()
