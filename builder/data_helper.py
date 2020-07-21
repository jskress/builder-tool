"""
This library gives us the means to navigate a dictionary/list object graph using
a simple string or tuple.
"""
import numbers

from typing import Any, Dict, List, Optional, Sequence, Union


def find_value(root: Any, path: Union[str, Sequence[Union[str, int]]]) -> Optional[Any]:
    """
    This function is used to follow the specified path through the object graph at root
    and return the item in the graph, if any, that the path refers to.  The path may be
    either a simple string, which is then parsed, or a sequence of keys down the data
    hierarchy.  If the path is a sequence, then each item must correspond to what the
    data is.  If a path piece is a string, then the data must be a dictionary.  If it is
    an integer, then it must be a list.

    :param root: the root of the object graph to traverse.
    :param path: the path through the graph to take.
    :return: the resulting value or ``None``.
    """
    if is_string(path):
        path = _parse_path(path)

    parent = root

    for part in path:
        if is_integer(part):
            if not is_array(parent) or part >= len(parent) or part < 0:
                return None
        elif not is_object(parent) or part not in parent:
            return None

        parent = parent[part]

    return parent


def _parse_path(path: str) -> Sequence[Union[str, int]]:
    """
    This function is used to parse a path string into a sequence.  Any empty strings
    are discarded.

    :param path: the string to parse.
    :return: the resulting sequence
    """
    result = []

    for item in path.split('/'):
        if len(item) > 0:
            if item[:1] == '[' and item[-1:] == ']':
                result.append(int(item[1:-1].strip()))
            else:
                result.append(item)

    return result


def is_object(thing: Any) -> bool:
    """
    A function that returns whether the given value is an object.  This is in terms of
    a data structure and not Python; i.e., it will return ``True`` for any value which
    is dictionary-like.

    :param thing: the value to check.
    :return: ``True`` if the value is (or is like) a dictionary.
    """
    return isinstance(thing, Dict)


def is_array(thing: Any) -> bool:
    """
    A function that returns whether the given value is an array.  This is in terms of
    a data structure and equates to checking that the value is a list.

    :param thing: the value to check.
    :return: ``True`` if the value is a list.
    """
    return isinstance(thing, List)


def is_string(thing: Any) -> bool:
    """
    A function that returns whether the given value is a string.

    :param thing: the value to check.
    :return: ``True`` if the value is a string.
    """
    return isinstance(thing, str)


def is_integer(thing: Any) -> bool:
    """
    A function that returns whether the given value is an integer.  Note that this will return
    ``False`` for the value, ``True``, which is different from normal Python.

    :param thing: the value to check.
    :return: ``True`` if the value is an integer.
    """
    return isinstance(thing, int) and not isinstance(thing, bool)


def is_number(thing: Any) -> bool:
    """
    A function that returns whether the given value is a number, either integer or floating
    point.  Note that this will return ``False`` for the value, ``True``, which is different
    from normal Python.

    :param thing: the value to check.
    :return: ``True`` if the value is a number.
    """
    return isinstance(thing, numbers.Number) and not isinstance(thing, bool)


def is_boolean(thing: Any) -> bool:
    """
    A function that returns whether the given value is a boolean.

    :param thing: the value to check.
    :return: ``True`` if the value is a boolean.
    """
    return isinstance(thing, bool)
