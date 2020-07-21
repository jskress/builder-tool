"""
This library provides a schema class to make it easier to build schemas.
"""
import inspect
import json
import numbers

import stringcase

from enum import Enum, auto
from typing import Sequence, Optional, Union, Any, Dict


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

    def const(self, value: Any):
        return self._set(value)

    def if_then_else(self, if_schema: Union[dict, 'Schema'], then_schema: Union[dict, 'Schema', None] = None,
                     else_schema: Union[dict, 'Schema', None] = None):
        self._set(if_schema, name='if')
        if then_schema is not None:
            self._set(then_schema, name='then')
        if else_schema is not None:
            self._set(else_schema, name='else')
        return self

    def ref(self, reference: str):
        return self._set(reference, name='$ref')

    def add_definition(self, name: str, schema: Union[dict, 'Schema']):
        definitions = self._ensure_dict('definitions')
        definitions[name] = self._to_spec(schema)
        return self

    def default(self, value):
        return self._set(value)

    def schema(self, schema: str):
        return self._set(schema, name='$schema')

    def comment(self, comment: str):
        return self._set(comment, name='$comment')

    def id(self, id_str: str):
        return self._set(id_str, name='$id')

    def title(self, title: str):
        return self._set(title, name='title')

    def description(self, description: str):
        return self._set(description, name='description')

    def spec(self):
        return self._spec

    def _ensure_dict(self, name: str) -> dict:
        result = self._spec[name] if name in self._spec else {}
        self._spec[name] = result
        return result

    def _set(self, value, name=None):
        if name is None:
            name = stringcase.camelcase(inspect.stack()[1].function)
        self._spec[name] = Schema._to_spec(value)
        return self

    def as_json_text(self):
        return json.dumps(self._spec, indent=2)

    @staticmethod
    def _to_spec(value: Any) -> Any:
        if isinstance(value, Schema):
            value = value.spec()
        if isinstance(value, (list, tuple)):
            value = [Schema._to_spec(value) for value in value]
        if isinstance(value, dict):
            value = {key: Schema._to_spec(value) for key, value in value.items()}
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


class IntegerSchema(Schema):
    def __init__(self, minimum: Optional[int] = None, exclusive_minimum: Union[bool, int, None] = None,
                 maximum: Optional[int] = None, exclusive_maximum: Union[bool, int, None] = None,
                 multiple_of: Optional[numbers.Number] = None, default_value: int = None):
        super().__init__(of_type=SchemaType.INTEGER, default_value=default_value)
        if minimum is not None:
            self.minimum(minimum)
        if exclusive_minimum is not None:
            self.exclusive_minimum(exclusive_minimum)
        if maximum is not None:
            self.maximum(maximum)
        if exclusive_maximum is not None:
            self.exclusive_maximum(exclusive_maximum)
        if multiple_of is not None:
            self.multiple_of(multiple_of)

    def minimum(self, value: int):
        return self._set(value)

    def exclusive_minimum(self, value: Union[bool, int]):
        return self._set(value)

    def maximum(self, value: int):
        return self._set(value)

    def exclusive_maximum(self, value: Union[bool, int]):
        return self._set(value)

    def multiple_of(self, value: numbers.Number):
        return self._set(value)


class NumberSchema(Schema):
    def __init__(self, minimum: Optional[numbers.Number] = None,
                 exclusive_minimum: Union[bool, numbers.Number, None] = None,
                 maximum: Optional[numbers.Number] = None,
                 exclusive_maximum: Union[bool, numbers.Number, None] = None,
                 multiple_of: Optional[numbers.Number] = None, default_value: int = None):
        super().__init__(of_type=SchemaType.NUMBER, default_value=default_value)
        if minimum is not None:
            self.minimum(minimum)
        if exclusive_minimum is not None:
            self.exclusive_minimum(exclusive_minimum)
        if maximum is not None:
            self.maximum(maximum)
        if exclusive_maximum is not None:
            self.exclusive_maximum(exclusive_maximum)
        if multiple_of is not None:
            self.multiple_of(multiple_of)

    def minimum(self, value: numbers.Number):
        return self._set(value)

    def exclusive_minimum(self, value: Union[bool, numbers.Number]):
        return self._set(value)

    def maximum(self, value: numbers.Number):
        return self._set(value)

    def exclusive_maximum(self, value: Union[bool, numbers.Number]):
        return self._set(value)

    def multiple_of(self, value: numbers.Number):
        return self._set(value)


class BooleanSchema(Schema):
    def __init__(self, default_value: bool = None):
        super().__init__(of_type=SchemaType.BOOLEAN, default_value=default_value)


class ObjectSchema(Schema):
    def __init__(self, properties: Optional[dict] = None, pattern_properties: Optional[dict] = None,
                 property_names: Optional[Union[dict, Schema]] = None,
                 min_properties: Optional[int] = None, max_properties: Optional[int] = None,
                 additional_properties: Union[bool, dict, Schema, None] = None, default_value=None):
        super().__init__(of_type=SchemaType.OBJECT, default_value=default_value)
        if properties is not None:
            self._set(properties, name='properties')
        if pattern_properties is not None:
            self._set(pattern_properties, name='patternProperties')
        if property_names is not None:
            self.property_names(property_names)
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

    def add_pattern_property(self, pattern: str, schema: Union[dict, Schema]):
        properties = self._ensure_dict('patternProperties')
        properties[pattern] = self._to_spec(schema)
        return self

    def required(self, *names: str):
        return self._set(names)

    def property_names(self, schema: Union[dict, Schema]):
        return self._set(schema)

    def min_properties(self, value: int):
        return self._set(value)

    def max_properties(self, value: int):
        return self._set(value)

    def dependencies(self, value: Dict[str, Union[Sequence[str], dict, Schema]]):
        return self._set(value)

    def additional_properties(self, value: Union[bool, dict, Schema]):
        return self._set(value)


class ArraySchema(Schema):
    def __init__(self, items: Union[Sequence[Union[dict, Schema]], dict, Schema, None] = None,
                 contains: Optional[Union[dict, Schema]] = None,
                 min_items: Optional[int] = None, max_items: Optional[int] = None,
                 unique_items: Optional[bool] = None, additional_items: Union[bool, dict, Schema, None] = None,
                 default_value=None):
        super().__init__(of_type=SchemaType.ARRAY, default_value=default_value)
        if items is not None:
            self.items(items)
        if contains is not None:
            self.contains(contains)
        if min_items is not None:
            self.min_items(min_items)
        if max_items is not None:
            self.max_items(max_items)
        if unique_items is not None:
            self.unique_items(unique_items)
        if additional_items is not None:
            self.additional_items(additional_items)

    def items(self, value: Union[Sequence[Union[dict, Schema]], dict, Schema]):
        return self._set(value)

    def contains(self, schema: Union[dict, Schema]):
        return self._set(schema)

    def min_items(self, value: int):
        return self._set(value)

    def max_items(self, value: int):
        return self._set(value)

    def unique_items(self, value: bool):
        return self._set(value)

    def additional_items(self, value: Union[bool, dict, Schema]):
        return self._set(value)


class CombinerSchema(Schema):
    def __init__(self, *schemas: Union[dict, Schema], tag: str):
        super().__init__(of_type=SchemaType.NONE)
        self._tag = tag
        self._set(schemas, name=tag)

    def add_schema(self, schema: Union[dict, Schema]):
        schemas = self._spec[self._tag]
        # noinspection PyUnresolvedReferences
        schemas.append(Schema._to_spec(schema))
        return self

    def __add__(self, other):
        if not (isinstance(other, dict) or isinstance(other, Schema)):
            return NotImplemented
        return self.add_schema(other)


class AllOfSchema(CombinerSchema):
    def __init__(self, *schemas: Union[dict, Schema]):
        super().__init__(*schemas, tag='allOf')


class AnyOfSchema(CombinerSchema):
    def __init__(self, *schemas: Union[dict, Schema]):
        super().__init__(*schemas, tag='anyOf')


class OneOfSchema(CombinerSchema):
    def __init__(self, *schemas: Union[dict, Schema]):
        super().__init__(*schemas, tag='oneOf')


class NotSchema(Schema):
    def __init__(self, schema: Union[dict, Schema]):
        super().__init__(of_type=SchemaType.NONE)
        self._set(schema, name='not')


class RefSchema(Schema):
    def __init__(self, reference: str):
        super().__init__(of_type=SchemaType.NONE)
        self.ref(reference)


class EmptySchema(Schema):
    def __init__(self):
        super().__init__(of_type=SchemaType.NONE)
