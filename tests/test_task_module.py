"""
This file contains all the unit tests for our framework's task module support.
"""
import re
from typing import Sequence, Optional, Any

import click
# noinspection PyPackageRequirements
import pytest

# noinspection PyProtectedMember
from builder.task_module import _parse_task_ref, TaskModule, Task, _get_name_mappings, set_module_import, \
    get_task_module, ModuleSet
from tests.test_support import FakeEcho, ExpectedEcho


def _create_task_module(language: str, tasks: Optional[Sequence[Task]] = None) -> TaskModule:
    class FakeModule(object):
        tasks = []
    module = FakeModule()
    if tasks is not None:
        module.tasks = tasks
    return TaskModule(module, language)


def _create_module_with_tasks(language: str, task_names: Sequence[str]) -> TaskModule:
    tasks = [Task(name, None) for name in task_names]
    return _create_task_module(language, tasks)


class FakeImporter(object):
    def __init__(self, language: str = None, fail: bool = False):
        self._language = language
        self._fail = fail

    # noinspection PyUnusedLocal
    def _test_import(self, name: str) -> Any:
        if self._fail:
            raise ModuleNotFoundError('boom!')

        return _create_task_module(self._language)

    def __enter__(self):
        set_module_import(self._test_import)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        set_module_import()


def _unambiguous():
    return {
        'm1': _create_module_with_tasks('l1', ['t1', 't2']),
        'm2': _create_module_with_tasks('l2', ['t3', 't4']),
    }


def _ambiguity():
    return {
        'm1': _create_module_with_tasks('l1', ['t1', 't2', 't3']),
        'm2': _create_module_with_tasks('l2', ['t3', 't4', 't5']),
    }


def _ambiguity_removed():
    return {
        'm1': _create_module_with_tasks('l1', ['t1', 't2', 'm1::t3']),
        'm2': _create_module_with_tasks('l2', ['m2::t3', 't4', 't5']),
    }


def _encode(text, **kwargs):
    return re.escape(click.style(text, **kwargs))


class TestTaskModule(object):
    def test_get_task(self):
        module = _create_module_with_tasks('lang', ['task1', 'task2'])
        good_task = module.get_task('task1')

        assert good_task is not None
        assert good_task.name == 'task1'

        assert module.get_task('bad_task') is None


class TestModuleSet(object):
    @staticmethod
    def _verify_module_dicts_match(actual, expected):
        assert len(actual) == len(expected)

        for key in actual.keys():
            assert key in expected.keys()

            actual_module = actual[key]
            expected_module = expected[key]

            assert actual_module.language == expected_module.language
            assert len(actual_module.tasks) == len(expected_module.tasks)

            for index in range(len(actual_module.tasks)):
                assert actual_module.tasks[index].name == expected_module.tasks[index].name

    # noinspection PyProtectedMember
    def test_create_with_unique_task_names(self):
        module_set = ModuleSet(_unambiguous())

        self._verify_module_dicts_match(module_set._modules, _unambiguous())

        assert module_set._task_to_module == {'t1': 'm1', 't2': 'm1', 't3': 'm2', 't4': 'm2'}
        assert module_set._ambiguous == []
        assert module_set._modules['m1'].tasks[0].name == 't1'
        assert module_set._modules['m1'].tasks[1].name == 't2'
        assert module_set._modules['m2'].tasks[0].name == 't3'
        assert module_set._modules['m2'].tasks[1].name == 't4'

    # noinspection PyProtectedMember
    def test_create_with_ambiguous_task_names(self):
        module_set = ModuleSet(_ambiguity())

        self._verify_module_dicts_match(module_set._modules, _ambiguity_removed())

        assert module_set._task_to_module == {'t1': 'm1', 't2': 'm1', 't4': 'm2', 't5': 'm2'}
        assert module_set._ambiguous == ['t3']
        assert module_set._modules['m1'].tasks[0].name == 't1'
        assert module_set._modules['m1'].tasks[1].name == 't2'
        assert module_set._modules['m1'].tasks[2].name == 'm1::t3'
        assert module_set._modules['m2'].tasks[0].name == 'm2::t3'
        assert module_set._modules['m2'].tasks[1].name == 't4'
        assert module_set._modules['m2'].tasks[2].name == 't5'

    @staticmethod
    def _verify_get_task(module_set: ModuleSet, task_ref: str, language: Optional[str] = None,
                         task_name: Optional[str] = None, exception_message: Optional[str] = None):
        if exception_message:
            with pytest.raises(ValueError) as info:
                module_set.get_task(task_ref)
            assert info.value.args[0] == exception_message
        else:
            module, task = module_set.get_task(task_ref)
            assert module.language == language
            assert task.name == task_name

    def test_get_task(self):
        module_set = ModuleSet(_ambiguity())

        self._verify_get_task(module_set, 't1', language='l1', task_name='t1')
        self._verify_get_task(module_set, 'm1::t1', language='l1', task_name='t1')

        self._verify_get_task(module_set, 'ta', exception_message='The task name, "ta", is not defined.')
        self._verify_get_task(module_set, 't3', exception_message='The task name, "t3", is ambiguous.')
        self._verify_get_task(module_set, 'bad::task', exception_message='There is no language named, "bad".')
        self._verify_get_task(module_set, 'm1::bad',
                              exception_message='There is no task named, "bad" for the "m1" language.')

    def test_print_available_tasks(self):
        module_set = ModuleSet(_unambiguous())
        expected = [
            ExpectedEcho(r'    m1', fg="white"),
            ExpectedEcho(r'        %s -- %s' % (_encode('t1', fg='bright_green'), _encode('None', fg='green'))),
            ExpectedEcho(r'        %s -- %s' % (_encode('t2', fg='bright_green'), _encode('None', fg='green'))),
            ExpectedEcho(r''),
            ExpectedEcho(r'    m2', fg="white"),
            ExpectedEcho(r'        %s -- %s' % (_encode('t3', fg='bright_green'), _encode('None', fg='green'))),
            ExpectedEcho(r'        %s -- %s' % (_encode('t4', fg='bright_green'), _encode('None', fg='green'))),
            ExpectedEcho(r'')
        ]

        with FakeEcho(expected):
            module_set.print_available_tasks()


class TestTaskModuleImport(object):
    def test_good_module_import(self):
        with FakeImporter('good'):
            assert get_task_module('test') is not None

    def test_bad_module_import(self):
        with FakeImporter(fail=True):
            with FakeEcho.simple('Warning: Exception loading module for test: boom!', fg='yellow'):
                assert get_task_module('test') is None


class TestNameMappings(object):
    def test_get_name_mappings_no_clash(self):
        modules = {
            'm1': _create_module_with_tasks('l1', ['t1', 't2']),
            'm2': _create_module_with_tasks('l2', ['t3', 't4']),
        }
        u, d = _get_name_mappings(modules)
        assert u == {'t1': 'm1', 't2': 'm1', 't3': 'm2', 't4': 'm2'}
        assert d == {}

    def test_get_name_mappings_with_clash(self):
        modules = {
            'm1': _create_module_with_tasks('l1', ['t1', 't2', 't3']),
            'm2': _create_module_with_tasks('l2', ['t3', 't4', 't5']),
        }
        u, d = _get_name_mappings(modules)
        assert u == {'t1': 'm1', 't2': 'm1', 't4': 'm2', 't5': 'm2'}
        assert d == {'t3': ['m1', 'm2']}


class TestParseTaskRef(object):
    def test_parse_task_ref(self):
        assert _parse_task_ref('task') == (None, 'task')
        assert _parse_task_ref('::task') == (None, 'task')
        assert _parse_task_ref('module::task') == ('module', 'task')

        with pytest.raises(ValueError) as info:
            _parse_task_ref('module::')
        assert info.value.args[0] == 'The text, "module::", is not a valid task name.'

        with pytest.raises(ValueError) as info:
            _parse_task_ref('::')
        assert info.value.args[0] == 'The text, "::", is not a valid task name.'

        with pytest.raises(ValueError) as info:
            _parse_task_ref('/')
        assert info.value.args[0] == 'The text, "/", is not a valid task name.'
