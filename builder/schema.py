"""
This library provides a schema class to make it easier to build schemas.
"""
import inspect
import json

import stringcase

from enum import Enum, auto
from typing import Sequence, Optional


class SchemaType(Enum):
    OBJECT = auto()
    ARRAY = auto()
    STRING = auto()
    INTEGER = auto()
    NUMBER = auto()
    BOOLEAN = auto()
    NULL = auto()
    NONE = auto()


class Schema(object):
    def __init__(self, of_type: SchemaType, default_value=None):
        self._spec = {}
        if of_type is not SchemaType.NONE:
            self._spec['type'] = of_type.name.lower()
        if default_value is not None:
            self.default(default_value)

    def enum(self, *values):
        return self._set(values)

    def default(self, value):
        return self._set(value)

    def spec(self):
        return self._spec

    def _set(self, value, name=None):
        if name is None:
            name = stringcase.camelcase(inspect.stack()[1].function)
        if isinstance(value, (list, tuple)):
            value = [Schema._to_spec(value) for value in value]
        elif isinstance(value, dict):
            value = {key: Schema._to_spec(value) for key, value in value.items()}
        self._spec[name] = Schema._to_spec(value)
        return self

    def as_json_text(self):
        return json.dumps(self._spec, indent=2)

    @staticmethod
    def _to_spec(value):
        if isinstance(value, Schema):
            value = value.spec()
        return value


class StringSchema(Schema):
    def __init__(self, min_length: Optional[int] = None, max_length: Optional[int] = None,
                 pattern: Optional[str] = None, str_format: Optional[str] = None, default_value: str = None):
        super().__init__(of_type=SchemaType.STRING, default_value=default_value)
        if min_length is not None:
            self.min_length(min_length)
        if max_length is not None:
            self.max_length(max_length)
        if pattern is not None:
            self.pattern(pattern)
        if str_format is not None:
            self.format(str_format)

    def min_length(self, value: int):
        return self._set(value)

    def max_length(self, value: int):
        return self._set(value)

    def pattern(self, value: str):
        return self._set(value)

    def format(self, value: str):
        return self._set(value)


class BooleanSchema(Schema):
    def __init__(self, default_value: bool = None):
        super().__init__(of_type=SchemaType.BOOLEAN, default_value=default_value)


class ObjectSchema(Schema):
    def __init__(self, properties: Optional[dict] = None, min_properties: Optional[int] = None,
                 max_properties: Optional[int] = None,
                 additional_properties=None, default_value=None):
        super().__init__(of_type=SchemaType.OBJECT, default_value=default_value)
        if properties is not None:
            self._set(properties)
        if min_properties is not None:
            self.min_properties(min_properties)
        if max_properties is not None:
            self.max_properties(max_properties)
        if additional_properties is not None:
            self.additional_properties(additional_properties)

    def properties(self, **kwargs):
        properties = {}
        for key, value in kwargs.items():
            properties[key] = value
        return self._set(properties)

    def required(self, *names: str):
        return self._set(names)

    def min_properties(self, value: int):
        return self._set(value)

    def max_properties(self, value: int):
        return self._set(value)

    def additional_properties(self, value):
        return self._set(value)


class ArraySchema(Schema):
    def __init__(self, items: Optional[Sequence] = None, min_items: Optional[int] = None,
                 max_items: Optional[int] = None, additional_items=None,
                 unique_items: Optional[bool] = None, default_value=None):
        super().__init__(of_type=SchemaType.ARRAY, default_value=default_value)
        if items is not None:
            self.items(items)
        if min_items is not None:
            self.min_items(min_items)
        if max_items is not None:
            self.max_items(max_items)
        if additional_items is not None:
            self.additional_items(additional_items)
        if unique_items is not None:
            self.unique_items(unique_items)

    def items(self, value: Sequence):
        return self._set(value)

    def min_items(self, value: int):
        return self._set(value)

    def max_items(self, value: int):
        return self._set(value)

    def additional_items(self, value):
        return self._set(value)

    def unique_items(self, value: bool):
        return self._set(value)


class OneOfSchema(Schema):
    def __init__(self, *schemas: dict):
        super().__init__(of_type=SchemaType.NONE)
        self._set(schemas, name='oneOf')

    def add_schema(self, schema: Schema):
        schemas = self._spec['oneOf']
        # noinspection PyUnresolvedReferences
        schemas.append(Schema._to_spec(schema))

    def __add__(self, other):
        if not isinstance(other, Schema):
            return NotImplemented
        self.add_schema(other)
