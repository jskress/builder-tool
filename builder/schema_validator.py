"""
This library provides a schema validator class.
"""
import datetime
import json
import re
import socket
from typing import Union, Optional, Iterable, Callable
from urllib.parse import urldefrag

import stringcase

from email.utils import parseaddr
from urllib.request import urlopen

from builder.data_helper import find_value, is_array, is_boolean, is_number, is_object, is_string, is_integer
from builder.schema import Schema

hostname_pattern = re.compile(r"(?!-)[A-Z\d-]{1,63}(?<!-)$", re.IGNORECASE)
semver_pattern = re.compile(r"^\d+\.\d+(?:\.\d+)?$")


def _not_none_count(sequence: Iterable) -> int:
    """
    A helper function for counting the number of non-`None` entries in a sequence.

    :param sequence: the sequence to look through.
    :return: the number of values in the sequence that are not `None`.
    """
    return sum(1 for _ in filter(None.__ne__, sequence))


def _validate_as_date(text: str) -> bool:
    """
    A helper function for verifying that a string represents a date.

    :param text: the string to verify.
    :return: `True` if the string looks like a date or `False` if not.
    """
    try:
        datetime.datetime.strptime(text, '%Y-%m-%d')

        return True
    except ValueError:
        return False


def _validate_as_time(text: str) -> bool:
    """
    A helper function for verifying that a string represents a time.

    :param text: the string to verify.
    :return: `True` if the string looks like a time or `False` if not.
    """
    try:
        datetime.datetime.strptime(text, '%H:%M:%S.%f')
        return True
    except ValueError:
        return False


def _validate_as_date_time(text: str) -> bool:
    """
    A helper function for verifying that a string represents a date/time.

    :param text: the string to verify.
    :return: `True` if the string looks like a date/time or `False` if not.
    """
    try:
        datetime.datetime.strptime(text, '%Y-%m-%dT%H:%M:%S.%f')
        return True
    except ValueError:
        return False


def _validate_as_email(text: str) -> bool:
    """
    A helper function for verifying that a string represents an email address.  This is a
    very lightweight check; it only verifies that the text contains an "at" (`@`) sign and
    that it is not at the beginning or end of the string.

    :param text: the string to verify.
    :return: `True` if the string looks like an email address or `False` if not.
    """
    name, address = parseaddr(text)

    return '@' in address and not (address.startswith('@') or address.endswith('@'))


def _validate_as_hostname(text: str) -> bool:
    """
    A helper function for verifying that a string represents a host name.

    :param text: the string to verify.
    :return: `True` if the string looks like a host name or `False` if not.
    """
    if len(text) > 255:
        return False

    if text[-1] == ".":
        text = text[:-1]  # strip exactly one dot from the right, if present

    return all(hostname_pattern.match(x) for x in text.split("."))


def _validate_as_semver(text: str) -> bool:
    """
    A helper function for verifying that a string represents a semantic version string.

    :param text: the string to verify.
    :return: `True` if the string looks like a semantic version or `False` if not.
    """
    return semver_pattern.match(text) is not None


def _validate_as_ipv4(text: str) -> bool:
    """
    A helper function for verifying that a string represents an IPv4 address.

    :param text: the string to verify.
    :return: `True` if the string looks like an IPv4 address or `False` if not.
    """
    try:
        socket.inet_pton(socket.AF_INET, text)
        return True
    except socket.error:
        return False


def _validate_as_ipv6(text: str) -> bool:
    """
    A helper function for verifying that a string represents an IPv6 address.

    :param text: the string to verify.
    :return: `True` if the string looks like an IPv6 address or `False` if not.
    """
    try:
        socket.inet_pton(socket.AF_INET6, text)
        return True
    except socket.error:
        return False


def _validate_as_regex(text: str) -> bool:
    """
    A helper function for verifying that a string represents a valid regular expression.

    :param text: the string to verify.
    :return: `True` if the string looks like a regular expression or `False` if not.
    """
    try:
        re.compile(text)
        return True
    except re.error:
        return False


# noinspection PyUnusedLocal
def _validate_as_uri(text: str) -> bool:
    """
    A helper function for verifying that a string represents a URI.  We always return
    `True` as there's not a reliable way to do this.

    :param text: the string to verify.
    :return: `True` if the string looks like a URI or `False` if not.
    """
    # There's really not a good way to do this...
    return True


empty_schema = {}
default_format_cache = {
    'date': _validate_as_date,
    'time': _validate_as_time,
    'date-time': _validate_as_date_time,
    'email': _validate_as_email,
    'semver': _validate_as_semver,
    'regex': _validate_as_regex,
    'hostname': _validate_as_hostname,
    'ipv4': _validate_as_ipv4,
    'ipv6': _validate_as_ipv6,
    'uri': _validate_as_uri,
    'uri-reference': _validate_as_uri
}


def _read_schema(url: str) -> Union[None, str, int, float, dict, list]:
    """
    A helper function for reading a value from a URL that is assumed to produce a JSON
    document.

    :param url: the URL to open and read.  The document read is then parsed as a JSON value.
    :return: the parsed JSON value.
    """
    with urlopen(url) as response:
        return json.loads(response.read())


class SchemaValidator(object):
    """
    This class represents an object that wraps a schema definition and uses it to validate
    values.
    """
    def __init__(self, schema: Union[Schema, dict, str, None] = None, url: Optional[str] = None):
        """
        This function creates a new schema validator around a schema which may be specified
        as either a ``Schema`` object, a raw dictionary or the test of a JSON object that
        specifies the schema.  Alternately, a URL from which the JSON schema may be downloaded
        may be specified.  It is an error to specify both a schema and a URL.

        :param schema: the schema to wrap.
        :param url: the URL to download the schema definition from.
        """
        count = _not_none_count((schema, url))
        if count == 0:
            raise ValueError('A schema must be specified.')
        if count > 1:
            raise ValueError('Only one form of schema may be specified.')
        if isinstance(schema, Schema):
            schema = schema.spec()
        elif isinstance(schema, str):
            schema = json.loads(schema)
        elif url is not None:
            schema = _schema_reader(url)

        self._format_cache = default_format_cache.copy()
        self._extension_cache = {}
        self._ref_cache = {}
        self.error = None
        self._schema = schema

    def add_extension(self, name: str, validator: 'SchemaValidator' = None,
                      schema: Union[Schema, dict, str, None] = None, url=None):
        count = _not_none_count((validator, schema, url))
        if count == 0:
            raise ValueError("A validator or schema must be specified.")
        if count > 1:
            raise ValueError("Only one form of validator may be specified.")
        if validator is None:
            validator = SchemaValidator(schema=schema, url=url)

        self._extension_cache[name] = validator

    def validate(self, value, path: str = ''):
        if path == '':
            path = '#'
        else:
            path = f'#/{path}'
        self.error = self._validate(value, schema=self._schema, path=path)

        return self.error is None

    def _validate(self, value, schema, path):
        for key in schema.keys():
            call = getattr(self, f'_validate_{stringcase.snakecase(key).replace("$", "_")}')
            error = call(value, schema, schema[key], path)

            if error is not None:
                if ' constraint: ' not in error:
                    error = f'{"#/" if path == "#" else path} violates the "{key}" constraint: {error}'

                return error

    # ------------------- #
    # General validations #
    # ------------------- #
    def _validate_type(self, value, schema, constraint, path):
        if isinstance(constraint, list):
            for possible_type in constraint:
                if self._validate_type(value, schema, possible_type, path) is None:
                    return None

            return f'it is not one of {str(constraint).replace("None", "null")}'
        elif constraint == 'object':
            if not is_object(value):
                return 'it is not an object.'
        elif constraint == 'array':
            if not is_array(value):
                return 'it is not an array.'
        elif constraint == 'string':
            if not is_string(value):
                return 'it is not a string.'
        elif constraint == 'integer':
            if not is_integer(value):
                return 'it is not an integer.'
        elif constraint == 'number':
            if not is_number(value):
                return 'it is not a number.'
        elif constraint == 'boolean':
            if not is_boolean(value):
                return 'it is not a boolean.'
        elif constraint == 'null' or constraint is None:
            if value is not None:
                return 'it is not null.'

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def _validate_enum(self, value, schema, constraint, path):
        if value in constraint or (value is None and 'null' in constraint) or (value is 'null' and None in constraint):
            return None
        return f'it is not one of [{", ".join(map(str, constraint))}].'

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def _validate_const(self, value, schema, constraint, path):
        if value != constraint:
            return f'the value {value} is not {constraint}.'

    # ------------------ #
    # String validations #
    # ------------------ #
    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def _validate_min_length(self, value, schema, constraint, path):
        if is_string(value) and is_number(constraint):
            if len(value) < constraint:
                return f'the string is shorter than {constraint}.'

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def _validate_max_length(self, value, schema, constraint, path):
        if is_string(value) and is_number(constraint):
            if len(value) > constraint:
                return f'the string is longer than {constraint}.'

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def _validate_pattern(self, value, schema, constraint, path):
        if is_string(value) and is_string(constraint):
            if not re.match(constraint, value):
                return f'it does not match the \'{constraint}\' pattern.'

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def _validate_format(self, value, schema, constraint, path):
        if is_string(constraint) and constraint in self._format_cache:
            if not self._format_cache[constraint](value):
                return f'it does not follow the {constraint} format.'

    # ------------------ #
    # Number validations #
    # ------------------ #
    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def _validate_multiple_of(self, value, schema, constraint, path):
        if is_number(value) and is_number(constraint):
            if value % constraint != 0:
                return f'{value} is not a multiple of {constraint}.'

    @staticmethod
    def _get_exclusive(name, schema):
        exclusive = schema[name] if name in schema else False

        return exclusive if is_boolean(exclusive) else False

    # noinspection PyUnusedLocal
    def _validate_minimum(self, value, schema, constraint, path):
        if is_number(value) and is_number(constraint):
            if self._get_exclusive('exclusiveMinimum', schema):
                if value < constraint:
                    return f'{value} is less than {constraint}.'
            else:
                if value <= constraint:
                    return f'{value} is less than or equal to {constraint}.'

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def _validate_exclusive_minimum(self, value, schema, constraint, path):
        if not is_boolean(constraint):
            # Got a number so use the newer behavior.
            if value < constraint:
                return f'{value} is less than {constraint}.'
        # Otherwise, the validation will be handled by the minimum constraint.
        pass

    # noinspection PyUnusedLocal
    def _validate_maximum(self, value, schema, constraint, path):
        if is_number(value) and is_number(constraint):
            if self._get_exclusive('exclusiveMaximum', schema):
                if value > constraint:
                    return f'{value} is greater than {constraint}.'
            else:
                if value >= constraint:
                    return f'{value} is greater than or equal to {constraint}.'

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def _validate_exclusive_maximum(self, value, schema, constraint, path):
        if not is_boolean(constraint):
            # Got a number so use the newer behavior.
            if value > constraint:
                return f'{value} is greater than {constraint}.'
        # Otherwise, the validation will be handled by the maximum constraint.
        pass

    # ------------------ #
    # Object validations #
    # ------------------ #
    def _validate_properties(self, value, schema, constraint, path):
        patterns = schema['patternProperties'] if 'patternProperties' in schema else empty_schema

        return self._handle_property_validation(
            value, constraint, patterns, self._get_additional_schema('additionalProperties', schema), path
        )

    def _validate_pattern_properties(self, value, schema, constraint, path):
        # if present, the 'properties' constraints will do the real validation.
        if 'properties' in schema:
            return None

        return self._handle_property_validation(
            value, empty_schema, constraint, self._get_additional_schema('additionalProperties', schema), path
        )

    # noinspection PyUnusedLocal
    def _validate_additional_properties(self, value, schema, constraint, path):
        # if present, the other constraints will do the real validation.
        if 'properties' in schema or 'patternProperties' in schema:
            return None

        return self._handle_property_validation(
            value, empty_schema, empty_schema, self._get_additional_schema('additionalProperties', schema), path
        )

    @staticmethod
    def _get_additional_schema(name, schema):
        additional = True

        if name in schema:
            additional = schema[name]

        if is_boolean(additional):
            additional = empty_schema if additional else None

        return additional

    def _handle_property_validation(self, value, specific_props, pattern_props, additional_props, path):
        if not is_object(value):
            return None

        error = None

        for name, child in value.items():
            name = str(name)
            child_path = f'{path}/{name}'
            schema = None

            if name in specific_props:
                schema = specific_props[name]
            else:
                for pattern in pattern_props.keys():
                    if re.match(pattern, name):
                        schema = pattern_props[pattern]

                        break

            if schema is None:
                schema = additional_props

            if schema is None:
                return f'the {name} property is not allowed here.'

            error = self._validate(child, schema, child_path)

            if error is None:
                if path in self._extension_cache:
                    # noinspection PyProtectedMember
                    error = self._validate(child, self._extension_cache[path]._schema, child_path)
                elif name in self._extension_cache:
                    # noinspection PyProtectedMember
                    error = self._validate(child, self._extension_cache[name]._schema, child_path)

            if error is not None:
                break

        return error

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def _validate_required(self, value, schema, constraint, path):
        if is_object(value) and is_array(constraint):
            for required in constraint:
                if required not in value:
                    return f'it is missing the {required} property.'

    def _validate_property_names(self, value, schema, constraint, path):
        if is_object(value) and is_object(constraint):
            for name in value.keys():
                name = str(name)
                child_path = f'{path}/{name}'
                error = self._validate(name, constraint, child_path)

                if error is not None:
                    return error

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def _validate_min_properties(self, value, schema, constraint, path):
        if is_object(value) and is_number(constraint):
            if len(value) < constraint:
                # noinspection SpellCheckingInspection
                return f'the object needs at least {constraint} propert{"y" if constraint == 1 else "ies"}.'

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def _validate_max_properties(self, value, schema, constraint, path):
        if is_object(value) and is_number(constraint):
            if len(value) > constraint:
                # noinspection SpellCheckingInspection
                return f'the object can have no more than {constraint} propert{"y" if constraint == 1 else "ies"}.'

    # noinspection PyUnusedLocal
    def _validate_dependencies(self, value, schema, constraint, path):
        if is_object(value) and is_object(constraint):
            for name, child_constraint in constraint.items():
                if name in value:
                    if is_array(child_constraint):
                        for required in child_constraint:
                            if required not in value:
                                return f"the {name} property requires the {required} property but it is missing."

                    elif is_object(child_constraint):
                        error = self._validate(value, child_constraint, path)

                        if error is not None:
                            return error

    # ----------------- #
    # Array validations #
    # ----------------- #
    def _validate_items(self, value, schema, constraint, path):
        return self._handle_item_validation(
            value, schema, constraint, path
        )

    # noinspection PyUnusedLocal
    def _validate_additional_items(self, value, schema, constraint, path):
        # if present, the items constraints will do the real validation.
        if 'items' not in schema:
            return self._handle_item_validation(
                value, schema, [], path
            )

    def _handle_item_validation(self, value, schema, constraint, path):
        if (is_object(constraint) or is_array(constraint)) and is_array(value):
            additional = self._get_additional_schema('additionalItems', schema)

            for index in range(len(value)):
                if is_object(constraint):
                    schema = constraint
                elif index < len(constraint):
                    schema = constraint[index]
                else:
                    schema = additional

                if schema is None:
                    return f'entry {index} in the array is not allowed here.'

                error = self._validate(value[index], schema, f'{path}[{index}]')

                if error is not None:
                    return error

    def _validate_contains(self, value, schema, constraint, path):
        if is_array(value) and is_object(constraint):
            for index, item in enumerate(value):
                error = self._validate(item, constraint, f'{path}[{index}]')
                if error is None:
                    return None
            return 'the array does not contain any item that satisfies the contains schema.'

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def _validate_min_items(self, value, schema, constraint, path):
        if is_array(value) and is_number(constraint):
            if len(value) < constraint:
                return f'the array needs at least {constraint} item{"" if constraint == 1 else "s"}.'

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def _validate_max_items(self, value, schema, constraint, path):
        if is_array(value) and is_number(constraint):
            if len(value) > constraint:
                return f'the array can have no more than {constraint} item{"" if constraint == 1 else "s"}.'

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def _validate_unique_items(self, value, schema, constraint, path):
        if is_boolean(constraint) and constraint and is_array(value):
            count = len(value)

            for outer in range(count - 1):
                for inner in range(outer + 1, count):
                    if value[outer] == value[inner]:
                        return f'entry {outer} is the same as entry {inner}.'

    # --------------------- #
    # Combining validations #
    # --------------------- #
    # noinspection PyUnusedLocal
    def _validate_all_of(self, value, schema, constraint, path):
        if is_array(constraint):
            for index in range(len(constraint)):
                error = self._validate(value, constraint[index], path)

                if error is not None:
                    path = '#/' if path == '#' else path
                    i = error.find(' violates ')
                    j = error.find(': ')
                    if 0 <= i < j:
                        text = error[i + 10:j]
                        error = error[j + 2:]
                        return f'{path} violates {text} of schema #{index + 1} in the \'allOf\' constraint: {error}'
                    return f'{path} violates schema #{index + 1} in the \'allOf\' constraint: {error}'

    # noinspection PyUnusedLocal
    def _validate_any_of(self, value, schema, constraint, path):
        if is_array(constraint):
            errors = []

            for index in range(len(constraint)):
                error = self._validate(value, constraint[index], path)

                if error is None:
                    return None

                errors.append('\n    ' + error)

            return self._format_multiple_errors('anyOf', errors, path)

    @staticmethod
    def _format_multiple_errors(constraint, errors, path):
        if errors:
            path = '#/' if path == '#' else path
            errors = ''.join(errors)
            return f'{path} violates the "{constraint}" constraint: the value was not accepted by any of the child' \
                   f' schemas:{errors}'

    # noinspection PyUnusedLocal
    def _validate_one_of(self, value, schema, constraint, path):
        if is_array(constraint):
            first = None
            errors = []

            for index in range(len(constraint)):
                error = self._validate(value, constraint[index], path)

                if error is None:
                    if first is not None:
                        return f'the value was accepted by schemas {first} and {index}.'

                    first = index
                else:
                    errors.append('\n    ' + error)

            return None if first is not None else self._format_multiple_errors('oneOf', errors, path)

    # noinspection PyUnusedLocal
    def _validate_not(self, value, schema, constraint, path):
        if is_object(constraint):
            error = self._validate(value, constraint, path)

            return 'the value was accepted by the child schema.' if error is None else None

    # ----------------------- #
    # Conditional validations #
    # ----------------------- #
    def _validate_if(self, value, schema, constraint, path):
        if is_object(constraint):
            error = self._validate(value, constraint, path)
            key = 'then' if error is None else 'else'
            constraint = schema[key] if key in schema else None
            if is_object(constraint):
                return self._validate(value, constraint, path)

    def _validate_then(self, value, schema, constraint, path):
        # The validation will be handled by the if constraint.
        pass

    def _validate_else(self, value, schema, constraint, path):
        # The validation will be handled by the if constraint.
        pass

    # --------------- #
    # $ref is SPECIAL #
    # --------------- #
    # noinspection PyUnusedLocal
    def _validate__ref(self, value, schema, constraint, path):
        document = self._schema
        url, ref_path = urldefrag(constraint)

        # Pull external resource
        if url:
            if url not in self._ref_cache:
                document = _schema_reader(url)

                self._fully_qualify_refs(document, url)
                self._ref_cache[url] = document
            else:
                document = self._ref_cache[url]

        schema = find_value(document, ref_path)

        if schema is None:
            return f'the reference, \'{constraint}\', does not refer to anything.'

        if not is_object(schema):
            return f'the reference, \'{constraint}\', does not refer to a schema.'

        return self._validate(value, schema, path)

    def _fully_qualify_refs(self, dictionary, url):
        for key, value in dictionary.items():
            if key == '$ref':
                if value.startswith('#'):
                    dictionary[key] = url + value
            elif is_object(value):
                self._fully_qualify_refs(value, url)
            elif is_array(value):
                for item in value:
                    if is_object(item):
                        self._fully_qualify_refs(item, url)

    # ----------------------- #
    # Validations that aren't #
    # ----------------------- #
    def _validate__schema(self, value, schema, constraint, path):
        # $schemas are info-only
        pass

    def _validate__comment(self, value, schema, constraint, path):
        # $comments are info-only
        pass

    def _validate__id(self, value, schema, constraint, path):
        # $ids are info-only
        pass

    def _validate_id(self, value, schema, constraint, path):
        # ids are info-only
        pass

    def _validate_title(self, value, schema, constraint, path):
        # titles are info-only
        pass

    def _validate_description(self, value, schema, constraint, path):
        # descriptions are info-only
        pass

    def _validate_default(self, value, schema, constraint, path):
        # default values are info-only
        pass

    def _validate_examples(self, value, schema, constraint, path):
        # example values are info-only
        pass

    def _validate_content_media_type(self, value, schema, constraint, path):
        # content media types are info-only for us.
        pass

    def _validate_content_encoding(self, value, schema, constraint, path):
        # content encodings are info-only for us.
        pass

    def _validate_definitions(self, value, schema, constraint, path):
        # definitions are info-only
        pass


SchemaReader = Callable[[str], Union[None, str, int, float, dict, list]]
_schema_reader = _read_schema


def set_schema_reader(reader: Optional[SchemaReader] = None):
    global _schema_reader
    _schema_reader = reader or _read_schema
