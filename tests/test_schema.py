"""
This file contains all the unit tests for our framework's schema creation support.
"""
from builder.schema import EmptySchema, BooleanSchema, IntegerSchema, NumberSchema, StringSchema, Schema, \
    ObjectSchema, ArraySchema, AllOfSchema, AnyOfSchema, OneOfSchema, NotSchema, RefSchema

_creation_test_cases = [
    # Basic schema stuff.
    (EmptySchema(), {}),
    (EmptySchema().enum(1, 2, 3), {'enum': [1, 2, 3]}),
    (EmptySchema().const('word'), {'const': 'word'}),
    (EmptySchema().if_then_else(BooleanSchema(), then_schema=IntegerSchema(), else_schema=StringSchema()),
     {
         'if': {"type": "boolean"},
         'then': {"type": "integer"},
         'else': {"type": "string"},
     }),
    (EmptySchema().ref('#/path/to/thing'), {'$ref': '#/path/to/thing'}),
    (EmptySchema().add_definition('port', IntegerSchema(minimum=1, maximum=65535)),
     {
         'definitions': {
             'port': {
                 'type': 'integer',
                 'minimum': 1,
                 'maximum': 65535
             }
         }
     }),
    (EmptySchema().default(3), {'default': 3}),
    (EmptySchema().schema('spec-url'), {'$schema': 'spec-url'}),
    (EmptySchema().comment('my comment'), {'$comment': 'my comment'}),
    (EmptySchema().id('my-id'), {'$id': 'my-id'}),
    (EmptySchema().title('The Title'), {'title': 'The Title'}),
    (EmptySchema().description('The description.'), {'description': 'The description.'}),

    # String schema stuff.
    (StringSchema(), {'type': 'string'}),
    (StringSchema(min_length=3), {'type': 'string', 'minLength': 3}),
    (StringSchema().min_length(3), {'type': 'string', 'minLength': 3}),
    (StringSchema(max_length=3), {'type': 'string', 'maxLength': 3}),
    (StringSchema().max_length(3), {'type': 'string', 'maxLength': 3}),
    (StringSchema(pattern='^hi$'), {'type': 'string', 'pattern': '^hi$'}),
    (StringSchema().pattern('^hi$'), {'type': 'string', 'pattern': '^hi$'}),
    (StringSchema(str_format='ipv4'), {'type': 'string', 'format': 'ipv4'}),
    (StringSchema().format('ipv4'), {'type': 'string', 'format': 'ipv4'}),
    (StringSchema(default_value='bob'), {'type': 'string', 'default': 'bob'}),

    # Integer schema stuff.
    (IntegerSchema(), {'type': 'integer'}),
    (IntegerSchema(minimum=2), {'type': 'integer', 'minimum': 2}),
    (IntegerSchema().minimum(2), {'type': 'integer', 'minimum': 2}),
    (IntegerSchema(exclusive_minimum=True), {'type': 'integer', 'exclusiveMinimum': True}),
    (IntegerSchema(exclusive_minimum=5), {'type': 'integer', 'exclusiveMinimum': 5}),
    (IntegerSchema().exclusive_minimum(True), {'type': 'integer', 'exclusiveMinimum': True}),
    (IntegerSchema().exclusive_minimum(5), {'type': 'integer', 'exclusiveMinimum': 5}),
    (IntegerSchema(maximum=2), {'type': 'integer', 'maximum': 2}),
    (IntegerSchema().maximum(2), {'type': 'integer', 'maximum': 2}),
    (IntegerSchema(exclusive_maximum=True), {'type': 'integer', 'exclusiveMaximum': True}),
    (IntegerSchema(exclusive_maximum=5), {'type': 'integer', 'exclusiveMaximum': 5}),
    (IntegerSchema().exclusive_maximum(True), {'type': 'integer', 'exclusiveMaximum': True}),
    (IntegerSchema().exclusive_maximum(5), {'type': 'integer', 'exclusiveMaximum': 5}),
    (IntegerSchema(multiple_of=8), {'type': 'integer', 'multipleOf': 8}),
    (IntegerSchema().multiple_of(8), {'type': 'integer', 'multipleOf': 8}),
    (IntegerSchema(default_value=7), {'type': 'integer', 'default': 7}),

    # Number schema stuff.
    (NumberSchema(), {'type': 'number'}),
    (NumberSchema(minimum=2), {'type': 'number', 'minimum': 2}),
    (NumberSchema().minimum(2), {'type': 'number', 'minimum': 2}),
    (NumberSchema(exclusive_minimum=True), {'type': 'number', 'exclusiveMinimum': True}),
    (NumberSchema(exclusive_minimum=5), {'type': 'number', 'exclusiveMinimum': 5}),
    (NumberSchema().exclusive_minimum(True), {'type': 'number', 'exclusiveMinimum': True}),
    (NumberSchema().exclusive_minimum(5), {'type': 'number', 'exclusiveMinimum': 5}),
    (NumberSchema(maximum=2), {'type': 'number', 'maximum': 2}),
    (NumberSchema().maximum(2), {'type': 'number', 'maximum': 2}),
    (NumberSchema(exclusive_maximum=True), {'type': 'number', 'exclusiveMaximum': True}),
    (NumberSchema(exclusive_maximum=5), {'type': 'number', 'exclusiveMaximum': 5}),
    (NumberSchema().exclusive_maximum(True), {'type': 'number', 'exclusiveMaximum': True}),
    (NumberSchema().exclusive_maximum(5), {'type': 'number', 'exclusiveMaximum': 5}),
    (NumberSchema(multiple_of=8), {'type': 'number', 'multipleOf': 8}),
    (NumberSchema().multiple_of(8), {'type': 'number', 'multipleOf': 8}),
    (NumberSchema(default_value=7), {'type': 'number', 'default': 7}),

    # Boolean schema stuff.
    (BooleanSchema(), {'type': 'boolean'}),
    (BooleanSchema(default_value=True), {'type': 'boolean', 'default': True}),

    # Object schema stuff,
    (ObjectSchema(), {'type': 'object'}),
    (ObjectSchema(properties={'i': IntegerSchema()}), {
        'type': 'object',
        'properties': {
            'i': {'type': 'integer'}
        }
    }),
    (ObjectSchema().properties(i=IntegerSchema()), {
        'type': 'object',
        'properties': {
            'i': {'type': 'integer'}
        }
    }),
    (ObjectSchema(pattern_properties={'^fi': IntegerSchema()}), {
        'type': 'object',
        'patternProperties': {
            '^fi': {'type': 'integer'}
        }
    }),
    (ObjectSchema().add_pattern_property('^fi', IntegerSchema()), {
        'type': 'object',
        'patternProperties': {
            '^fi': {'type': 'integer'}
        }
    }),
    (ObjectSchema().add_pattern_property('^fi', {'type': 'integer'}), {
        'type': 'object',
        'patternProperties': {
            '^fi': {'type': 'integer'}
        }
    }),
    (ObjectSchema().required(), {'type': 'object', 'required': []}),
    (ObjectSchema().required('a'), {'type': 'object', 'required': ['a']}),
    (ObjectSchema().required('a', 'b'), {'type': 'object', 'required': ['a', 'b']}),
    (ObjectSchema(property_names={'pattern': '^hi'}), {
        'type': 'object',
        'propertyNames': {
            'pattern': '^hi'
        }
    }),
    (ObjectSchema(property_names=StringSchema(pattern='^hi')), {
        'type': 'object',
        'propertyNames': {
            'type': 'string',
            'pattern': '^hi'
        }
    }),
    (ObjectSchema().property_names({'pattern': '^hi'}), {
        'type': 'object',
        'propertyNames': {
            'pattern': '^hi'
        }
    }),
    (ObjectSchema().property_names(StringSchema(pattern='^hi')), {
        'type': 'object',
        'propertyNames': {
            'type': 'string',
            'pattern': '^hi'
        }
    }),
    (ObjectSchema(min_properties=2), {'type': 'object', 'minProperties': 2}),
    (ObjectSchema().min_properties(2), {'type': 'object', 'minProperties': 2}),
    (ObjectSchema(max_properties=2), {'type': 'object', 'maxProperties': 2}),
    (ObjectSchema().max_properties(2), {'type': 'object', 'maxProperties': 2}),
    (ObjectSchema().dependencies({
        'one': {'type': 'number'},
        'two': ['one', 'three'],
        'three': IntegerSchema()
    }), {
        'type': 'object',
        'dependencies': {
            'one': {'type': 'number'},
            'two': ['one', 'three'],
            'three': {'type': 'integer'}
        }
    }),
    (ObjectSchema(additional_properties=False), {'type': 'object', 'additionalProperties': False}),
    (ObjectSchema().additional_properties(False), {'type': 'object', 'additionalProperties': False}),
    (ObjectSchema(additional_properties={'type': 'integer'}), {
        'type': 'object',
        'additionalProperties': {'type': 'integer'}
    }),
    (ObjectSchema().additional_properties({'type': 'integer'}), {
        'type': 'object',
        'additionalProperties': {'type': 'integer'}
    }),
    (ObjectSchema(additional_properties=BooleanSchema()), {
        'type': 'object',
        'additionalProperties': {'type': 'boolean'}
    }),
    (ObjectSchema().additional_properties(BooleanSchema()), {
        'type': 'object',
        'additionalProperties': {'type': 'boolean'}
    }),
    (ObjectSchema(default_value={'1': 2}), {'type': 'object', 'default': {'1': 2}}),

    # Array schema stuff.
    (ArraySchema(), {'type': 'array'}),
    (ArraySchema(items=[{'type': 'boolean'}, IntegerSchema()]), {
        'type': 'array', 'items': [
            {'type': 'boolean'},
            {'type': 'integer'}
        ]
    }),
    (ArraySchema().items([{'type': 'boolean'}, IntegerSchema()]), {
        'type': 'array', 'items': [
            {'type': 'boolean'},
            {'type': 'integer'}
        ]
    }),
    (ArraySchema(items={'type': 'boolean'}), {
        'type': 'array', 'items': {'type': 'boolean'}
    }),
    (ArraySchema().items({'type': 'boolean'}), {
        'type': 'array', 'items': {'type': 'boolean'}
    }),
    (ArraySchema(items=IntegerSchema()), {
        'type': 'array', 'items': {'type': 'integer'}
    }),
    (ArraySchema().items(IntegerSchema()), {
        'type': 'array', 'items': {'type': 'integer'}
    }),
    (ArraySchema(contains={'type': 'boolean'}), {
        'type': 'array', 'contains': {'type': 'boolean'}
    }),
    (ArraySchema().contains({'type': 'boolean'}), {
        'type': 'array', 'contains': {'type': 'boolean'}
    }),
    (ArraySchema(contains=IntegerSchema()), {
        'type': 'array', 'contains': {'type': 'integer'}
    }),
    (ArraySchema().contains(IntegerSchema()), {
        'type': 'array', 'contains': {'type': 'integer'}
    }),
    (ArraySchema(min_items=2), {'type': 'array', 'minItems': 2}),
    (ArraySchema().min_items(2), {'type': 'array', 'minItems': 2}),
    (ArraySchema(max_items=2), {'type': 'array', 'maxItems': 2}),
    (ArraySchema().max_items(2), {'type': 'array', 'maxItems': 2}),
    (ArraySchema(unique_items=True), {'type': 'array', 'uniqueItems': True}),
    (ArraySchema().unique_items(True), {'type': 'array', 'uniqueItems': True}),
    (ArraySchema(additional_items=False), {'type': 'array', 'additionalItems': False}),
    (ArraySchema().additional_items(False), {'type': 'array', 'additionalItems': False}),
    (ArraySchema(additional_items={'type': 'integer'}), {
        'type': 'array',
        'additionalItems': {'type': 'integer'}
    }),
    (ArraySchema().additional_items({'type': 'integer'}), {
        'type': 'array',
        'additionalItems': {'type': 'integer'}
    }),
    (ArraySchema(additional_items=BooleanSchema()), {
        'type': 'array',
        'additionalItems': {'type': 'boolean'}
    }),
    (ArraySchema().additional_items(BooleanSchema()), {
        'type': 'array',
        'additionalItems': {'type': 'boolean'}
    }),
    (ArraySchema(default_value=['1', 2]), {'type': 'array', 'default': ['1', 2]}),

    # AllOf schema stuff.
    (AllOfSchema(), {'allOf': []}),
    (AllOfSchema({'type': 'integer'}), {'allOf': [{'type': 'integer'}]}),
    (AllOfSchema(IntegerSchema()), {'allOf': [{'type': 'integer'}]}),
    (AllOfSchema() + IntegerSchema(), {'allOf': [{'type': 'integer'}]}),
    (AllOfSchema() + {'type': 'integer'}, {'allOf': [{'type': 'integer'}]}),
    (AllOfSchema().add_schema(IntegerSchema()), {'allOf': [{'type': 'integer'}]}),
    (AllOfSchema(IntegerSchema(), BooleanSchema()), {'allOf': [{'type': 'integer'}, {'type': 'boolean'}]}),
    (AllOfSchema() + IntegerSchema() + BooleanSchema(), {'allOf': [{'type': 'integer'}, {'type': 'boolean'}]}),
    (AllOfSchema().add_schema(IntegerSchema()).add_schema(BooleanSchema()),
     {'allOf': [{'type': 'integer'}, {'type': 'boolean'}]}),

    # AnyOf schema stuff.
    (AnyOfSchema(), {'anyOf': []}),
    (AnyOfSchema({'type': 'integer'}), {'anyOf': [{'type': 'integer'}]}),
    (AnyOfSchema(IntegerSchema()), {'anyOf': [{'type': 'integer'}]}),
    (AnyOfSchema() + IntegerSchema(), {'anyOf': [{'type': 'integer'}]}),
    (AnyOfSchema() + {'type': 'integer'}, {'anyOf': [{'type': 'integer'}]}),
    (AnyOfSchema().add_schema(IntegerSchema()), {'anyOf': [{'type': 'integer'}]}),
    (AnyOfSchema(IntegerSchema(), BooleanSchema()), {'anyOf': [{'type': 'integer'}, {'type': 'boolean'}]}),
    (AnyOfSchema() + IntegerSchema() + BooleanSchema(), {'anyOf': [{'type': 'integer'}, {'type': 'boolean'}]}),
    (AnyOfSchema().add_schema(IntegerSchema()).add_schema(BooleanSchema()),
     {'anyOf': [{'type': 'integer'}, {'type': 'boolean'}]}),

    # OneOf schema stuff.
    (OneOfSchema(), {'oneOf': []}),
    (OneOfSchema(IntegerSchema()), {'oneOf': [{'type': 'integer'}]}),
    (OneOfSchema({'type': 'integer'}), {'oneOf': [{'type': 'integer'}]}),
    (OneOfSchema() + IntegerSchema(), {'oneOf': [{'type': 'integer'}]}),
    (OneOfSchema() + {'type': 'integer'}, {'oneOf': [{'type': 'integer'}]}),
    (OneOfSchema().add_schema(IntegerSchema()), {'oneOf': [{'type': 'integer'}]}),
    (OneOfSchema(IntegerSchema(), BooleanSchema()), {'oneOf': [{'type': 'integer'}, {'type': 'boolean'}]}),
    (OneOfSchema() + IntegerSchema() + BooleanSchema(), {'oneOf': [{'type': 'integer'}, {'type': 'boolean'}]}),
    (OneOfSchema().add_schema(IntegerSchema()).add_schema(BooleanSchema()),
     {'oneOf': [{'type': 'integer'}, {'type': 'boolean'}]}),

    # Not schema stuff.
    (NotSchema({'type': 'integer'}), {'not': {'type': 'integer'}}),
    (NotSchema(IntegerSchema()), {'not': {'type': 'integer'}}),

    # $ref schema stuff.
    (RefSchema('#/path/to/thing'), {'$ref': '#/path/to/thing'}),
]


class TestSchemaCreation(object):
    def test_schema_creations(self):
        test = 1
        for schema, expected in _creation_test_cases:
            assert schema.spec() == expected, f'Test #{test}'
            test = test + 1

        import atexit

        def _report():
            print(f'Executed {test - 1} schema creation tests.')

        atexit.register(_report)

    def test_ensure_dict(self):
        schema = EmptySchema()

        assert schema.spec() == {}
        # noinspection PyProtectedMember
        assert schema._ensure_dict('name') == {}
        assert schema.spec() == {'name': {}}

    def test_field_set_no_name(self):
        schema = EmptySchema()

        def tag():
            # noinspection PyProtectedMember
            schema._set('value')

        tag()

        assert schema.spec() == {'tag': 'value'}

    def test_field_set_with_name(self):
        schema = EmptySchema()
        # noinspection PyProtectedMember
        schema._set('value', name='name')

        assert schema.spec() == {'name': 'value'}

    def test_as_json_text(self):
        schema = EmptySchema()

        assert schema.as_json_text() == "{}"

    # noinspection PyProtectedMember
    def test_to_spec(self):
        assert Schema._to_spec(3) == 3
        assert Schema._to_spec([1, 2, 3]) == [1, 2, 3]
        assert Schema._to_spec((1, 2, 3)) == [1, 2, 3]
        assert Schema._to_spec({'key': 'value'}) == {'key': 'value'}
        assert Schema._to_spec(EmptySchema()) == {}
        assert Schema._to_spec(
            [IntegerSchema(), BooleanSchema()]
        ) == [
            {'type': 'integer'},
            {'type': 'boolean'}
        ]
        assert Schema._to_spec(
            (IntegerSchema(), BooleanSchema())
        ) == [
            {'type': 'integer'},
            {'type': 'boolean'}
        ]
        assert Schema._to_spec({
            'one': IntegerSchema(),
            'two': BooleanSchema()
        }) == {
            'one': {'type': 'integer'},
            'two': {'type': 'boolean'}
        }
