"""
This file contains all the unit tests for our framework's data helpers.
"""
from collections import OrderedDict

# noinspection PyProtectedMember
from builder.data_helper import is_object, is_array, is_string, is_integer, is_number, is_boolean, _parse_path, \
    find_value

test_dict = {
    'n1': 'v1',
    'n2': 2,
    'n3': {
        't1': [1, 2, 3],
        't2': 'bob'
    },
    'n4': [7, 8, '9']
}
test_list = ['one', 'two', {'name': 'value'}]


class TestFindValue(object):
    def test_find_value(self):
        assert find_value('value', '') == 'value'
        assert find_value('value', 'name') is None
        assert find_value(test_dict, '') == test_dict
        assert find_value(test_dict, 'n1') == 'v1'
        assert find_value(test_dict, 'n2') == 2
        assert find_value(test_dict, 'n3/t1/[2]') == 3
        assert find_value(test_dict, 'n3/t1/[3]') is None
        assert find_value(test_dict, ['n3', 't1', 2]) == 3
        assert find_value(test_dict, ['n3', 't1', 3]) is None
        assert find_value(test_dict, 'n3/t2') == 'bob'
        assert find_value(test_dict, ['n3', 't2']) == 'bob'
        assert find_value(test_dict, 'n4/t2') is None
        assert find_value(test_dict, ['n4', 't2']) is None
        assert find_value(test_dict, 'n4') == [7, 8, '9']
        assert find_value(test_dict, 'n5') is None
        assert find_value(test_list, '') == test_list
        assert find_value(test_list, '[1]') == 'two'
        assert find_value(test_list, [1]) == 'two'
        assert find_value(test_list, '[2]/name') == 'value'
        assert find_value(test_list, [2, 'name']) == 'value'
        assert find_value(test_list, [3]) is None


class TestPathParsing(object):
    def test_path_parsing(self):
        assert _parse_path('') == []
        assert _parse_path('/test') == ['test']
        assert _parse_path('test') == ['test']
        assert _parse_path('test/next') == ['test', 'next']
        assert _parse_path('/test/next') == ['test', 'next']
        assert _parse_path('/test/1/next') == ['test', '1', 'next']
        assert _parse_path('/test/[1/next') == ['test', '[1', 'next']
        assert _parse_path('/test/1]/next') == ['test', '1]', 'next']
        assert _parse_path('/test/[1]/next') == ['test', 1, 'next']


class TestIsFunctions(object):
    def test_is_object(self):
        assert is_object(True) is False
        assert is_number(False) is False
        assert is_object(0) is False
        assert is_object(0.0) is False
        assert is_object('Bob') is False
        assert is_object([1]) is False
        assert is_object((1,)) is False
        assert is_object({}) is True
        assert is_object(OrderedDict()) is True

    def test_is_array(self):
        assert is_array(True) is False
        assert is_number(False) is False
        assert is_array(0) is False
        assert is_array(0.0) is False
        assert is_array('Bob') is False
        assert is_array([1]) is True
        assert is_array((1,)) is False
        assert is_array({}) is False

    def test_is_string(self):
        assert is_string(True) is False
        assert is_number(False) is False
        assert is_string(0) is False
        assert is_string(0.0) is False
        assert is_string('Bob') is True
        assert is_string([1]) is False
        assert is_string((1,)) is False
        assert is_string({}) is False

    def test_is_integer(self):
        assert is_integer(True) is False
        assert is_number(False) is False
        assert is_integer(0) is True
        assert is_integer(0.0) is False
        assert is_integer('Bob') is False
        assert is_integer([1]) is False
        assert is_integer((1,)) is False
        assert is_integer({}) is False

    def test_is_number(self):
        assert is_number(True) is False
        assert is_number(False) is False
        assert is_number(0) is True
        assert is_number(0.0) is True
        assert is_number('Bob') is False
        assert is_number([1]) is False
        assert is_number((1,)) is False
        assert is_number({}) is False

    def test_is_boolean(self):
        assert is_boolean(True) is True
        assert is_boolean(False) is True
        assert is_boolean(0) is False
        assert is_boolean(0.0) is False
        assert is_boolean('Bob') is False
        assert is_boolean([1]) is False
        assert is_boolean((1,)) is False
        assert is_boolean({}) is False
