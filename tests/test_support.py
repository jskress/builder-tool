"""
This file provides some common helper functions to support our unit testing.
"""
import re
from subprocess import CompletedProcess
from pathlib import Path
from typing import Sequence, Union, Optional, Callable, List, Dict, Any

from builder.project import Project
from builder.schema_validator import set_schema_reader
from builder.utils import global_options, SubprocessRunner, set_subprocess_runner, set_echo


class Regex(object):
    """
    Provides a simple object wrapper around a regex that allows `==` to do the
    match.
    """
    def __init__(self, pattern: str):
        self._pattern = re.compile(pattern)

    def __eq__(self, actual):
        return bool(self._pattern.match(actual))

    def __repr__(self):
        return self._pattern.pattern


class Options(object):
    def __init__(self, project: Optional[Project] = None, quiet: Optional[bool] = None, verbose: Optional[int] = None,
                 languages: Optional[Sequence[str]] = None, variables: Optional[Dict[str, str]] = None,
                 reset: bool = False):
        self._options = {}
        self._save = {}
        self._reset = reset

        if reset is False:
            if project is not None:
                self._options['_project'] = project
            if quiet is not None:
                self._options['_quiet'] = quiet
            if verbose is not None:
                self._options['_verbose'] = verbose
            if languages is not None:
                self._options['_languages'] = languages
            if variables is not None:
                self._options['_vars'] = variables

    def __enter__(self):
        if self._reset:
            self._save = global_options.__dict__.copy()
        else:
            for attr, value in self._options.items():
                self._save[attr] = getattr(global_options, attr)
                setattr(global_options, attr, value)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        for attr, value in self._save.items():
            setattr(global_options, attr, self._save[attr])


class FakeProcess(object):
    def __init__(self, args: Optional[Sequence[str]], stdout: Optional[Union[str, Path, None]] = None,
                 stderr: Optional[Union[str, Path, None]] = None, rc: int = 0, check_args: bool = True,
                 cwd: Optional[Path] = None):
        self._args = args
        self._stdout = stdout
        self._stderr = stderr
        self._rc = rc
        self._cwd = cwd
        self._check_args = check_args

    @staticmethod
    def _get_content(source: Union[str, Path, None], capture: bool):
        result = None
        if capture:
            if isinstance(source, str):
                result = source.encode('UTF-8')
            elif isinstance(source, Path):
                result = source.read_bytes()
        return result

    def runner(self, args: Sequence[str], capture: bool, cwd: Path) -> CompletedProcess:
        if self._check_args:
            assert self._args == args
        if self._cwd:
            assert self._cwd == cwd
        return CompletedProcess(
            args, self._rc, self._get_content(self._stdout, capture), self._get_content(self._stderr, capture)
        )


class FakeProcessContext(object):
    def __init__(self, processes: Union[FakeProcess, SubprocessRunner, Sequence[Union[FakeProcess, SubprocessRunner]]],
                 check_all_consumed: bool = True):
        if isinstance(processes, FakeProcess) or isinstance(processes, Callable):
            processes = [processes]
        self._processes = processes
        self._check_all_consumed = check_all_consumed
        self._cp = 0

    def _context_runner(self, args: Sequence[str], capture_output: bool, cwd: Path) -> CompletedProcess:
        process = self._processes[self._cp]
        self._cp = self._cp + 1
        function = process.runner if isinstance(process, FakeProcess) else process

        return function(args, capture_output, cwd)

    def __enter__(self):
        self._cp = 0
        set_subprocess_runner(self._context_runner)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        set_subprocess_runner()
        if self._check_all_consumed:
            assert self._cp == len(self._processes)


class ExpectedEcho(object):
    def __init__(self, text_to_match: Optional[str], **kwargs):
        self._text_to_match = text_to_match
        self._kwargs = kwargs

    def matches(self, text, **kwargs):
        if len(self._text_to_match) == 0:
            assert len(text) == 0
        else:
            pattern = re.compile(self._text_to_match)
            assert pattern.match(text)
        assert self._kwargs == kwargs


class FakeEcho(object):
    @classmethod
    def simple(cls, text, **kwargs):
        return FakeEcho(ExpectedEcho(text, **kwargs))

    def __init__(self, expected: Optional[Union[ExpectedEcho, List[ExpectedEcho]]] = None):
        if isinstance(expected, ExpectedEcho):
            expected = [expected]
        self._expected = expected
        self._called = False

    def was_called(self):
        return self._called

    def _test_echo(self, text, **kwargs):
        self._called = True

        if self._expected is not None:
            assert self._expected
            self._expected.pop(0).matches(text, **kwargs)

    def __enter__(self):
        self._called = False
        set_echo(self._test_echo)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        set_echo()


class FakeSchemaReader(object):
    def __init__(self, resolver: Dict[str, Union[None, str, bool, int, float, dict, list]]):
        self._resolver = resolver
        self._call_count = 0

    def _fake_reader(self, url: str) -> Union[None, str, bool, int, float, dict, list]:
        return self._resolver[url]

    def __enter__(self):
        self._call_count = self._call_count + 1
        set_schema_reader(self._fake_reader)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        set_schema_reader()

    @property
    def call_count(self):
        return self._call_count


def validate_attributes(thing: Any, reference: Dict[str, Any]):
    assert thing.__dict__ == reference


def get_test_path(sub_path: str) -> Path:
    return Path(__file__).resolve().parent / 'test_data' / sub_path
