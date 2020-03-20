"""
This library gives us the means to navigate a dictionary/list object graph using
a simple string or tuple.
"""
import numbers

from collections import OrderedDict


def find_value(root, path):
    """
    This function is used to follow the specified path through the object graph at root
    and return the item in the graph, if any, that the path refers to.

    :param root: the root of the object graph to traverse.
    :param path: the path through the graph to take.
    :return: the resulting value or None.
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


def _parse_path(path):
    """
    This function is used to parse a path string into a sequence.  Any empty strings
    are discarded.

    :param path: the string to parse.
    :return: the resulting sequence
    """
    result = []

    if path.startswith('#/'):
        path = path[2:]

    for item in path.split('/'):
        if len(item) > 0:
            if item[:1] == '[' and item[-1:] == ']':
                result.append(int(item[1:-1]))
            else:
                result.append(item)

    return result


def is_object(thing):
    return isinstance(thing, dict) or isinstance(thing, OrderedDict)


def is_array(thing):
    return isinstance(thing, list)


def is_string(thing):
    return isinstance(thing, (str, u"".__class__))


def is_integer(thing):
    return isinstance(thing, int)


def is_number(thing):
    return isinstance(thing, numbers.Number)


def is_boolean(thing):
    return isinstance(thing, bool)


def without_keys(dictionary, keys):
    """Returns a copy of the dictionary minus the given keys"""
    return {x: dictionary[x] for x in dictionary if x not in keys}
