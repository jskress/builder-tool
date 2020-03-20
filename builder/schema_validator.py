"""
This library provides a schema validator class.
"""
import datetime
import json
import re
import socket
from typing import Union, Optional

import stringcase

from email.utils import parseaddr
from urllib.request import urlopen

from builder.data_helper import find_value, is_array, is_boolean, is_number, is_object, is_string
from builder.schema import Schema

hostname_pattern = re.compile(r"(?!-)[A-Z\d-]{1,63}(?<!-)$", re.IGNORECASE)
semver_pattern = re.compile(r"\d+\.\d+(\.\d+)?")


def none_count(sequence):
    return sum(1 for _ in filter(None.__ne__, sequence))


def _validate_as_date(text: str) -> bool:
    try:
        datetime.datetime.strptime(text, '%Y-%m-%d')

        return True
    except ValueError:
        return False


def _validate_as_date_time(text: str) -> bool:
    try:
        datetime.datetime.strptime(text, '%Y-%m-%dT%H:%M:%S.%f')
        return True
    except ValueError:
        return False


def _validate_as_email(text: str) -> bool:
    name, address = parseaddr(text)

    return len(address) > 0 and '@' in address


def _validate_as_hostname(text: str) -> bool:
    if len(text) > 255:
        return False

    if text[-1] == ".":
        text = text[:-1]  # strip exactly one dot from the right, if present

    return all(hostname_pattern.match(x) for x in text.split("."))


def _validate_as_semver(text: str) -> bool:
    return semver_pattern.match(text) is not None


def _validate_as_ipv4(text: str) -> bool:
    try:
        socket.inet_pton(socket.AF_INET, text)
        return True
    except socket.error:
        return False


def _validate_as_ipv6(text: str) -> bool:
    try:
        socket.inet_pton(socket.AF_INET6, text)
        return True
    except socket.error:
        return False


# noinspection PyUnusedLocal
def _validate_as_uri(text: str) -> bool:
    # There's really not a good way to do this...
    return True


empty_schema = {}
default_format_cache = {
    'date': _validate_as_date,
    'date-time': _validate_as_date_time,
    'email': _validate_as_email,
    'semver': _validate_as_semver,
    'hostname': _validate_as_hostname,
    'ipv4': _validate_as_ipv4,
    'ipv6': _validate_as_ipv6,
    'uri': _validate_as_uri
}


def read_schema(url: str) -> Union[None, str, int, float, dict, list]:
    with urlopen(url) as response:
        return json.loads(response.read())


class SchemaValidator(object):
    def __init__(self, schema: Union[Schema, dict, None] = None, json_text: Optional[str] = None,
                 url: Optional[str] = None):
        count = none_count((schema, json_text, url))
        if count == 0:
            raise ValueError("A schema must be specified.")
        if count > 1:
            raise ValueError("Only one form of schema may be specified.")
        if isinstance(schema, Schema):
            schema = schema.spec()
        if json_text is not None:
            schema = json.loads(json_text)
        elif url is not None:
            schema = read_schema(url)

        self.format_cache = default_format_cache.copy()
        self.extension_cache = {}
        self.ref_cache = {}
        self.error = None
        self.schema = schema

    def add_extension(self, name: str, validator=None, schema=None, json_text=None, url=None):
        count = none_count((validator, schema, json_text, url))
        if count == 0:
            raise ValueError("A validator (or schema) must be specified.")
        if count > 1:
            raise ValueError("Only one form of validator may be specified.")
        if validator is None:
            validator = SchemaValidator(schema=schema, json_text=json_text, url=url)

        self.extension_cache[name] = validator

    def validate(self, value, path: str = ''):
        if path == '':
            path = '#'
        else:
            path = '#/%s' % path
        self.error = self._validate(value, schema=self.schema, path=path)

        return self.error is None

    def _validate(self, value, schema, path):
        for key in schema.keys():
            call = getattr(self, '_validate_%s' % stringcase.snakecase(key).replace('$', '_'))
            error = call(value, schema, schema[key], path)

            if error is not None:
                if ' constraint: ' not in error:
                    error = '%s violates the \'%s\' constraint: %s' % ('#/' if path == '#' else path, key, error)

                return error

    # ------------------- #
    # General validations #
    # ------------------- #
    def _validate_type(self, value, schema, constraint, path):
        if isinstance(constraint, list):
            for possible_type in constraint:
                if self._validate_type(value, schema, possible_type, path) is None:
                    return None

            return 'it is not one of %s' % str(constraint).replace('None', 'null')
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
            if not is_number(value):
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
        if value is None:
            value = 'null'

        if value not in constraint:
            return 'it is not one of [%s].' % ', '.join(map(str, constraint))

    # ------------------ #
    # String validations #
    # ------------------ #
    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def _validate_min_length(self, value, schema, constraint, path):
        if is_string(value) and is_number(constraint):
            if len(value) < constraint:
                return 'the string is shorter than %s.' % constraint

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def _validate_max_length(self, value, schema, constraint, path):
        if is_string(value) and is_number(constraint):
            if len(value) > constraint:
                return 'the string is longer than %s.' % constraint

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def _validate_pattern(self, value, schema, constraint, path):
        if is_string(value) and is_string(constraint):
            if not re.match(constraint, value):
                return 'it does not match the \'%s\' pattern.' % constraint

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def _validate_format(self, value, schema, constraint, path):
        if is_string(constraint) and constraint in self.format_cache:
            if not self.format_cache[constraint](value):
                return 'it does not follow the %s format.' % constraint

    # ------------------ #
    # Number validations #
    # ------------------ #
    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def _validate_multiple_of(self, value, schema, constraint, path):
        if is_number(value) and is_number(constraint):
            if value % constraint != 0:
                return '%s is not a multiple of %s' % (value, constraint)

    @staticmethod
    def _get_exclusive(name, schema):
        exclusive = schema[name] if name in schema else False

        return exclusive if is_boolean(exclusive) else False

    # noinspection PyUnusedLocal
    def _validate_minimum(self, value, schema, constraint, path):
        if is_number(value) and is_number(constraint):
            if self._get_exclusive('exclusiveMinimum', schema):
                if len(value) < constraint:
                    return '%s is less than %s.' % (value, constraint)
            else:
                if len(value) <= constraint:
                    return '%s is less than or equal to %s.' % (value, constraint)

    def _validate_exclusive_minimum(self, value, schema, constraint, path):
        # The validation will be handled by the minimum constraint.
        pass

    # noinspection PyUnusedLocal
    def _validate_maximum(self, value, schema, constraint, path):
        if is_number(value) and is_number(constraint):
            if self._get_exclusive('exclusiveMaximum', schema):
                if len(value) > constraint:
                    return '%s is greater than %s.' % (value, constraint)
            else:
                if len(value) >= constraint:
                    return '%s is greater than or equal to %s.' % (value, constraint)

    def _validate_exclusive_maximum(self, value, schema, constraint, path):
        # The validation will be handled by the maximum constraint.
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
            child_path = '%s/%s' % (path, name)
            schema = None

            if name in specific_props:
                schema = specific_props[name]
            else:
                for pattern in pattern_props.keys():
                    if re.match(pattern, str(name)):
                        schema = pattern_props[pattern]

                        break

            if schema is None:
                schema = additional_props

            if schema is None:
                return 'the %s property is not allowed here.' % name

            error = self._validate(child, schema, child_path)

            if error is None and str(name) in self.extension_cache:
                error = self._validate(child, self.extension_cache[str(name)].schema, child_path)

            if error is not None:
                break

        return error

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def _validate_required(self, value, schema, constraint, path):
        if is_object(value) and is_array(constraint):
            for required in constraint:
                if required not in value:
                    return 'it is missing the %s property.' % required

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def _validate_min_properties(self, value, schema, constraint, path):
        if is_object(value) and is_number(constraint):
            if len(value) < constraint:
                return 'the object needs at least %s properties.' % constraint

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def _validate_max_properties(self, value, schema, constraint, path):
        if is_object(value) and is_number(constraint):
            if len(value) > constraint:
                return 'the object can have no more than %s properties.' % constraint

    # noinspection PyUnusedLocal
    def _validate_dependencies(self, value, schema, constraint, path):
        if is_object(value) and is_object(constraint):
            for name, child_constraint in constraint.items():
                if name in value:
                    if is_array(child_constraint):
                        for required in child_constraint:
                            if required not in value:
                                return 'the \'%s\' property requires the \'%s\' property but it is missing.' %\
                                       (name, required)

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

            for index in range(0, len(value)):
                if is_object(constraint):
                    schema = constraint
                elif index < len(constraint):
                    schema = constraint[index]
                else:
                    schema = additional

                if schema is None:
                    return 'entry %s in the array is not allowed here.' % index

                error = self._validate(value[index], schema, '%s[%s]' % (path, index))

                if error is not None:
                    return error

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def _validate_min_items(self, value, schema, constraint, path):
        if is_object(value) and is_number(constraint):
            if len(value) < constraint:
                return 'the array needs at least %s items.' % constraint

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def _validate_max_items(self, value, schema, constraint, path):
        if is_object(value) and is_number(constraint):
            if len(value) > constraint:
                return 'the array can have no more than %s items.' % constraint

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def _validate_unique_items(self, value, schema, constraint, path):
        if is_boolean(constraint) and constraint and is_array(value):
            count = len(value)

            for outer in range(0, count - 1):
                for inner in range(outer + 1, count):
                    if value[outer] == value[inner]:
                        return 'entry %s is the same as entry %s' % (outer, inner)

    # --------------------- #
    # Combining validations #
    # --------------------- #
    # noinspection PyUnusedLocal
    def _validate_all_of(self, value, schema, constraint, path):
        if is_array(constraint):
            for index in range(0, len(constraint)):
                error = self._validate(value, constraint[index], path)

                if error is not None:
                    error = '%s violates schema #%s in the \'allOf\' constraint: %s' %\
                            ('#/' if path == '#' else path, index + 1, error)

    # noinspection PyUnusedLocal
    def _validate_any_of(self, value, schema, constraint, path):
        if is_array(constraint):
            text = ''

            for index in range(0, len(constraint)):
                error = self._validate(value, constraint[index], path)

                if error is None:
                    return None

                text = '%s\n%s' % (text, error)

            return 'the value was not accepted by any of the child schemas:' + text

    # noinspection PyUnusedLocal
    def _validate_one_of(self, value, schema, constraint, path):
        if is_array(constraint):
            once = False
            text = ''

            for index in range(0, len(constraint)):
                error = self._validate(value, constraint[index], path)

                if error is None:
                    if once:
                        return 'the value was accepted by at least 2 of the child schemas.'

                    once = True
                else:
                    text = '%s\n%s' % (text, error)

            return None if once else 'the value was not accepted by any of the child schemas:' + text

    # noinspection PyUnusedLocal
    def _validate_not(self, value, schema, constraint, path):
        if is_object(constraint):
            error = self._validate(value, constraint, path)

            return 'the value was accepted by the child schema' if error is None else None

    # --------------- #
    # $ref is SPECIAL #
    # --------------- #
    # noinspection PyUnusedLocal
    def _validate_ref(self, value, schema, constraint, path):
        document = self.schema
        ref_path = constraint
        index = constraint.index('#')

        # Pull external resource
        if index > 0:
            url = constraint[:index]
            ref_path = constraint[index:]

            if url not in self.ref_cache:
                document = read_schema(url)

                self._fully_qualify_refs(document, url)
                self.ref_cache[url] = document
            else:
                document = self.ref_cache[url]

        schema = find_value(document, ref_path)

        if schema is None:
            return 'the reference, \'%s\', does not refer to anything.' % constraint

        if not is_object(schema):
            return 'the reference, \'%s\', does not refer to a schema.' % constraint

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

    def _validate_id(self, value, schema, constraint, path):
        # IDs are info-only
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

    def _validate_definitions(self, value, schema, constraint, path):
        # definitions are info-only
        pass
