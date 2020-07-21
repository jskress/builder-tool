"""
This file contains all the unit tests for our framework's schema validation support.
"""
from typing import Union

# noinspection PyPackageRequirements
import pytest

from builder.schema import StringSchema, BooleanSchema, IntegerSchema, NumberSchema, ObjectSchema, ArraySchema, \
    AllOfSchema, AnyOfSchema, OneOfSchema, NotSchema, RefSchema, EmptySchema
# noinspection PyProtectedMember
from builder.schema_validator import _not_none_count, _validate_as_date, _validate_as_date_time, _validate_as_email, \
    _validate_as_hostname, _validate_as_semver, SchemaValidator, _validate_as_time, _validate_as_regex
from tests.test_support import FakeSchemaReader


class TestSVHelperFunctions(object):
    def test_none_count(self):
        assert _not_none_count([]) == 0
        assert _not_none_count([1, 2, 3]) == 3
        assert _not_none_count([1, None, 3]) == 2
        assert _not_none_count([1, None, None]) == 1
        assert _not_none_count([None, None, None]) == 0

    def test_validate_as_date(self):
        assert _validate_as_date('2020-04-27') is True
        assert _validate_as_date('Bob') is False

    def test_validate_as_time(self):
        assert _validate_as_time('10:38:27.122') is True
        assert _validate_as_time('Bob') is False

    def test_validate_as_date_time(self):
        assert _validate_as_date_time('2020-04-27T10:38:27.122') is True
        assert _validate_as_date_time('Bob') is False

    def test_validate_as_email(self):
        assert _validate_as_email('a@b') is True
        assert _validate_as_email('Bob') is False

    def test_validate_as_hostname(self):
        assert _validate_as_hostname('host') is True
        assert _validate_as_hostname('host!') is False
        assert _validate_as_hostname('h' * 63) is True
        assert _validate_as_hostname('h' * 64) is False
        assert _validate_as_hostname('0123456.' * 32) is False
        assert _validate_as_hostname(('0123456.' * 32)[:-1]) is True

    def test_validate_as_semver(self):
        assert _validate_as_semver('1.2') is True
        assert _validate_as_semver('1.2.3') is True
        assert _validate_as_semver('1') is False
        assert _validate_as_semver('1.') is False
        assert _validate_as_semver('1.2.') is False
        assert _validate_as_semver('1.2.3.') is False
        assert _validate_as_semver('1.2.3.4') is False

    def test_validate_as_regex(self):
        assert _validate_as_regex('^Goodness$') is True
        assert _validate_as_regex(')badness(') is False


# noinspection PyProtectedMember
class TestValidatorConstruction(object):
    def test_validator_construction_errors(self):
        with pytest.raises(ValueError) as info:
            SchemaValidator()
        assert info.value.args[0] == 'A schema must be specified.'

        with pytest.raises(ValueError) as info:
            SchemaValidator(schema={}, url='a-url')
        assert info.value.args[0] == 'Only one form of schema may be specified.'

    def test_validator_construction_from_dict(self):
        validator = SchemaValidator(schema={"type": "string"})
        assert isinstance(validator._schema, dict)
        assert validator._schema == {"type": "string"}

    def test_validator_construction_from_schema(self):
        validator = SchemaValidator(schema=StringSchema())
        assert isinstance(validator._schema, dict)
        assert validator._schema == {"type": "string"}

    def test_validator_construction_from_json(self):
        validator = SchemaValidator(schema='{"type":"string"}')
        assert isinstance(validator._schema, dict)
        assert validator._schema == {"type": "string"}

    def test_validator_construction_from_url(self):
        resolver = {
            'http://example.com': {"type": "string"}
        }
        with FakeSchemaReader(resolver):
            validator = SchemaValidator(url='http://example.com')
            assert isinstance(validator._schema, dict)
            assert validator._schema == {"type": "string"}


# noinspection PyProtectedMember
class TestValidatorAddExtension(object):
    def test_validator_add_extension_errors(self):
        validator = SchemaValidator(schema=StringSchema())
        sub_validator = SchemaValidator(schema=BooleanSchema())
        with pytest.raises(ValueError) as info:
            validator.add_extension('name')
        assert info.value.args[0] == 'A validator or schema must be specified.'

        with pytest.raises(ValueError) as info:
            validator.add_extension('name', validator=sub_validator, schema=BooleanSchema(), url='a-url')
        assert info.value.args[0] == 'Only one form of validator may be specified.'

        with pytest.raises(ValueError) as info:
            validator.add_extension('name', validator=sub_validator, schema=BooleanSchema())
        assert info.value.args[0] == 'Only one form of validator may be specified.'

        with pytest.raises(ValueError) as info:
            validator.add_extension('name', schema=BooleanSchema(), url='a-url')
        assert info.value.args[0] == 'Only one form of validator may be specified.'

        with pytest.raises(ValueError) as info:
            validator.add_extension('name', validator=sub_validator, url='a-url')
        assert info.value.args[0] == 'Only one form of validator may be specified.'

    def test_validator_add_extension(self):
        validator = SchemaValidator(schema=StringSchema())
        sub_validator = SchemaValidator(schema=BooleanSchema())
        validator.add_extension('name', sub_validator)
        assert validator._extension_cache == {'name': sub_validator}

        validator = SchemaValidator(schema=StringSchema())
        validator.add_extension('name', schema=BooleanSchema())
        assert 'name' in validator._extension_cache
        assert isinstance(validator._extension_cache['name'], SchemaValidator)


def _em(constraint: str, message: str, path: Union[str, int] = '') -> str:
    if isinstance(path, int):
        path = f'[{path}]'
    elif not path.startswith('/'):
        path = f'/{path}'
    return f'#{path} violates the "{constraint}" constraint: {message}'


_dependency_sub_schema = ObjectSchema().properties(
    f2=IntegerSchema()
)
_port_schema = IntegerSchema(minimum=1, maximum=65535)
_port_ref_schema = RefSchema('#/definitions/port') \
    .add_definition('port', _port_schema)

_validation_test_cases = [
    # Type constraints tests.
    ({}, dict(type='object'), None),
    ('string', dict(type='object'), _em('type', 'it is not an object.')),
    ([], dict(type='array'), None),
    ('string', dict(type='array'), _em('type', 'it is not an array.')),
    ('string', dict(type='string'), None),
    (12, dict(type='string'), _em('type', 'it is not a string.')),
    (7, dict(type='integer'), None),
    ('string', dict(type='integer'), _em('type', 'it is not an integer.')),
    (7, dict(type='number'), None),
    (7.5, dict(type='number'), None),
    ('string', dict(type='number'), _em('type', 'it is not a number.')),
    (True, dict(type='boolean'), None),
    (False, dict(type='boolean'), None),
    ('string', dict(type='boolean'), _em('type', 'it is not a boolean.')),
    (None, dict(type='null'), None),
    (None, dict(type=None), None),
    (12, dict(type='null'), _em('type', 'it is not null.')),
    (12, dict(type=None), _em('type', 'it is not null.')),
    ('string', dict(type=['string', 'object']), None),
    ({}, dict(type=['string', 'object']), None),
    (7, dict(type=['string', 'object']), _em('type', "it is not one of ['string', 'object']")),

    # Enum constraint tests.
    (1, dict(enum=[1, 2, 3]), None),
    (2, dict(enum=[1, 2, 3]), None),
    (3, dict(enum=[1, 2, 3]), None),
    (None, dict(enum=[1, None, 3]), None),
    (None, dict(enum=[1, 'null', 3]), None),
    ('null', dict(enum=[1, None, 3]), None),
    ('null', dict(enum=[1, 'null', 3]), None),
    (0, dict(enum=[1, 2, 3]), _em('enum', 'it is not one of [1, 2, 3].')),
    (None, dict(enum=[1, 2, 3]), _em('enum', 'it is not one of [1, 2, 3].')),
    ('null', dict(enum=[1, 2, 3]), _em('enum', 'it is not one of [1, 2, 3].')),

    # const constraint tests.
    (7, EmptySchema().const(7), None),
    (8, EmptySchema().const(7), _em('const', 'the value 8 is not 7.')),

    # String constraints tests.
    ('string', StringSchema(min_length=6), None),
    ('bobby', StringSchema(min_length=6), _em('minLength', 'the string is shorter than 6.')),
    ('string', StringSchema(max_length=6), None),
    ('string2', StringSchema(max_length=6), _em('maxLength', 'the string is longer than 6.')),
    ('good', StringSchema(pattern=r'^go'), None),
    ('bad', StringSchema(pattern=r'^go'), _em('pattern', "it does not match the '^go' pattern.")),
    ('1.2.3.4', StringSchema(str_format='ipv4'), None),
    ('1.2.3', StringSchema(str_format='ipv4'), _em('format', 'it does not follow the ipv4 format.')),

    # Number constraints tests.
    (7, IntegerSchema(minimum=5), None),
    (5, IntegerSchema(minimum=5, exclusive_minimum=True), None),
    (5, IntegerSchema(minimum=5), _em('minimum', '5 is less than or equal to 5.')),
    (4, IntegerSchema(minimum=5, exclusive_minimum=True), _em('minimum', '4 is less than 5.')),
    (4, IntegerSchema(exclusive_minimum=5), _em('exclusiveMinimum', '4 is less than 5.')),
    (3, IntegerSchema(maximum=5), None),
    (5, IntegerSchema(maximum=5, exclusive_maximum=True), None),
    (5, IntegerSchema(maximum=5), _em('maximum', '5 is greater than or equal to 5.')),
    (6, IntegerSchema(maximum=5, exclusive_maximum=True), _em('maximum', '6 is greater than 5.')),
    (6, IntegerSchema(exclusive_maximum=5), _em('exclusiveMaximum', '6 is greater than 5.')),
    (8, IntegerSchema(multiple_of=4), None),
    (8, IntegerSchema(multiple_of=5), _em('multipleOf', '8 is not a multiple of 5.')),

    (7.0, NumberSchema(minimum=5), None),
    (5.0, NumberSchema(minimum=5, exclusive_minimum=True), None),
    (5.0, NumberSchema(minimum=5), _em('minimum', '5.0 is less than or equal to 5.')),
    (4.0, NumberSchema(minimum=5, exclusive_minimum=True), _em('minimum', '4.0 is less than 5.')),
    (4.0, NumberSchema(exclusive_minimum=5), _em('exclusiveMinimum', '4.0 is less than 5.')),
    (3.0, NumberSchema(maximum=5), None),
    (5.0, NumberSchema(maximum=5, exclusive_maximum=True), None),
    (5.0, NumberSchema(maximum=5), _em('maximum', '5.0 is greater than or equal to 5.')),
    (6.0, NumberSchema(maximum=5, exclusive_maximum=True), _em('maximum', '6.0 is greater than 5.')),
    (6.0, NumberSchema(exclusive_maximum=5), _em('exclusiveMaximum', '6.0 is greater than 5.')),
    (8.0, NumberSchema(multiple_of=4), None),
    (8.0, NumberSchema(multiple_of=5.0), _em('multipleOf', '8.0 is not a multiple of 5.0.')),

    # Object constraints tests.
    (dict(field='value'), ObjectSchema(), None),
    (dict(field='value'), ObjectSchema(additional_properties=False),
     _em('additionalProperties', 'the field property is not allowed here.')),
    (dict(field='value'), ObjectSchema(additional_properties=IntegerSchema()),
     _em('type', 'it is not an integer.', path='field')),
    (dict(field=7), ObjectSchema().properties(field=IntegerSchema()), None),
    (dict(field=7), ObjectSchema().properties(field=StringSchema()),
     _em('type', 'it is not a string.', path='field')),
    (dict(field=7, field2=3), ObjectSchema().properties(field=IntegerSchema()), None),
    (dict(field=7, field2=3), ObjectSchema().properties(field=IntegerSchema()).additional_properties(False),
     _em('properties', 'the field2 property is not allowed here.')),
    (dict(field=12), ObjectSchema(pattern_properties={r'^fi': IntegerSchema()}, additional_properties=False), None),
    (dict(field=12), ObjectSchema(pattern_properties={r'^no': IntegerSchema()}, additional_properties=False),
     _em('patternProperties', 'the field property is not allowed here.')),
    (dict(field='value'), ObjectSchema().required('field'), None),
    (dict(field='value'), ObjectSchema().required('field2'), _em('required', 'it is missing the field2 property.')),
    (dict(f1=1), ObjectSchema().property_names(StringSchema(pattern=r'^f\d$')), None),
    (dict(a1=1), ObjectSchema().property_names(StringSchema(pattern=r'^f\d$')),
     _em("pattern", r"it does not match the '^f\d$' pattern.", path='a1')),
    (dict(field='value'), ObjectSchema(min_properties=1), None),
    (dict(), ObjectSchema(min_properties=1),
     _em('minProperties', 'the object needs at least 1 property.')),
    (dict(field='value'), ObjectSchema(min_properties=2),
     _em('minProperties', 'the object needs at least 2 properties.')),
    (dict(field='value'), ObjectSchema(max_properties=1), None),
    (dict(f1=1, f2=2), ObjectSchema(max_properties=1),
     _em('maxProperties', 'the object can have no more than 1 property.')),
    (dict(f1=1, f2=2, f3=3), ObjectSchema(max_properties=2),
     _em('maxProperties', 'the object can have no more than 2 properties.')),
    (dict(f1=1, f2=2), ObjectSchema().dependencies(dict(f1=['f2'])), None),
    (dict(f1=1), ObjectSchema().dependencies(dict(f1=['f2'])),
     _em('dependencies', 'the f1 property requires the f2 property but it is missing.')),
    (dict(f1=1, f2=2), ObjectSchema().dependencies(dict(f1=_dependency_sub_schema)), None),
    (dict(f1=1, f2='a'), ObjectSchema().dependencies(dict(f1=_dependency_sub_schema)),
     _em('type', 'it is not an integer.', path='f2')),

    # Array constraints tests.
    (['value'], ArraySchema(), None),
    (['value'], ArraySchema().items(StringSchema()), None),
    (['v1', 'v2', 'v3'], ArraySchema().items(StringSchema()), None),
    (['v1', 'v2', 3], ArraySchema().items(StringSchema()), _em('type', 'it is not a string.', path=2)),
    ([1], ArraySchema().items(StringSchema()), _em('type', 'it is not a string.', path=0)),
    (['value'], ArraySchema(additional_items=False),
     _em('additionalItems', 'entry 0 in the array is not allowed here.')),
    ([12], ArraySchema(additional_items=IntegerSchema()), None),
    (['value'], ArraySchema(additional_items=IntegerSchema()), _em('type', 'it is not an integer.', path=0)),
    ([1, 2, 3], ArraySchema().contains(IntegerSchema()), None),
    (['1', '2', 3], ArraySchema().contains(IntegerSchema()), None),
    (['1', '2', '3'], ArraySchema().contains(IntegerSchema()),
     _em('contains', 'the array does not contain any item that satisfies the contains schema.')),
    (['value'], ArraySchema(min_items=1), None),
    ([], ArraySchema(min_items=1), _em('minItems', 'the array needs at least 1 item.')),
    (['value'], ArraySchema(min_items=2), _em('minItems', 'the array needs at least 2 items.')),
    (['value'], ArraySchema(max_items=1), None),
    ([1, 2], ArraySchema(max_items=1), _em('maxItems', 'the array can have no more than 1 item.')),
    ([1, 2, 3], ArraySchema(max_items=2), _em('maxItems', 'the array can have no more than 2 items.')),
    ([1, 2, 3], ArraySchema(unique_items=False), None),
    ([1, 2, 2], ArraySchema(unique_items=False), None),
    ([1, 2, 3], ArraySchema(unique_items=True), None),
    ([1, 2, 2], ArraySchema(unique_items=True), _em('uniqueItems', 'entry 1 is the same as entry 2.')),

    # allOf constraint tests.
    (7, AllOfSchema(), None),
    (7, AllOfSchema(IntegerSchema()), None),
    (7, AllOfSchema() + IntegerSchema(), None),
    (7, AllOfSchema() + IntegerSchema(minimum=3) + IntegerSchema(maximum=10), None),
    (7, AllOfSchema() + IntegerSchema(minimum=8) + IntegerSchema(maximum=10),
     '#/ violates the "minimum" constraint of schema #1 in the \'allOf\' constraint: 7 is less than or equal to 8.'),

    # anyOf constraint tests.
    (7, AnyOfSchema(), None),
    (7, AnyOfSchema(IntegerSchema()), None),
    (7, AnyOfSchema() + IntegerSchema(), None),
    (7, AnyOfSchema() + IntegerSchema() + StringSchema(), None),
    ('7', AnyOfSchema() + IntegerSchema() + StringSchema(), None),
    ({}, AnyOfSchema() + IntegerSchema() + StringSchema(),
     """#/ violates the "anyOf" constraint: the value was not accepted by any of the child schemas:
    #/ violates the "type" constraint: it is not an integer.
    #/ violates the "type" constraint: it is not a string."""),

    # oneOf constraint tests.
    (7, OneOfSchema(), None),
    (7, OneOfSchema(IntegerSchema()), None),
    (7, OneOfSchema() + IntegerSchema(), None),
    (7, OneOfSchema() + IntegerSchema() + StringSchema(), None),
    ('7', OneOfSchema() + IntegerSchema() + StringSchema(), None),
    (7, OneOfSchema() + IntegerSchema(minimum=1) + IntegerSchema(maximum=10),
     _em('oneOf', 'the value was accepted by schemas 0 and 1.')),
    (7, OneOfSchema() + IntegerSchema(minimum=10) + IntegerSchema(maximum=1),
     """#/ violates the "oneOf" constraint: the value was not accepted by any of the child schemas:
    #/ violates the "minimum" constraint: 7 is less than or equal to 10.
    #/ violates the "maximum" constraint: 7 is greater than or equal to 1."""),

    # not constraint tests.
    (7, NotSchema(StringSchema()), None),
    ('7', NotSchema(StringSchema()), _em('not', 'the value was accepted by the child schema.')),

    # Conditional constraints tests.
    (7, EmptySchema().if_then_else(IntegerSchema()), None),
    (7, EmptySchema().if_then_else(StringSchema()), None),
    (7, EmptySchema().if_then_else(IntegerSchema(), else_schema=StringSchema()), None),
    (7, EmptySchema().if_then_else(StringSchema(), then_schema=IntegerSchema(minimum=10)), None),
    (7, EmptySchema().if_then_else(IntegerSchema(), then_schema=IntegerSchema(minimum=10)),
     _em('minimum', '7 is less than or equal to 10.')),
    (7, EmptySchema().if_then_else(
        IntegerSchema(), then_schema=IntegerSchema(minimum=10), else_schema=StringSchema()
    ), _em('minimum', '7 is less than or equal to 10.')),
    (7, EmptySchema().if_then_else(BooleanSchema(), else_schema=StringSchema()),
     _em('type', 'it is not a string.')),
    (7, EmptySchema().if_then_else(BooleanSchema(), then_schema=IntegerSchema(minimum=10), else_schema=StringSchema()),
     _em('type', 'it is not a string.')),

    # $ref constraint tests.
    (7, _port_ref_schema, None),
    (0, _port_ref_schema, _em('minimum', '0 is less than or equal to 1.')),
]


class TestValidations(object):
    def test_validations(self):
        test = 1
        for value, schema, error in _validation_test_cases:
            validator = SchemaValidator(schema=schema)
            validator.validate(value)
            assert validator.error == error, f'Test #{test}: [{value}, {schema}, {error}]'
            test = test + 1

        import atexit

        def _report():
            print(f'Executed {test - 1} schema validation tests.')

        atexit.register(_report)

    def test_ref_resolution(self):
        resolver = {
            'http://example.com': EmptySchema().add_definition('port', _port_schema).spec()
        }
        validator = SchemaValidator(RefSchema('http://example.com#/definitions/port'))
        with FakeSchemaReader(resolver) as fsr:
            assert validator.validate(7) is True
            assert validator.validate(0) is False
            assert validator.error == _em('minimum', '0 is less than or equal to 1.')
        assert fsr.call_count == 1
