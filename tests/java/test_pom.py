"""
This file contains all the unit tests for our POM support.
"""
from builder.models import Dependency, DependencyContext, Language
# noinspection PyProtectedMember
from builder.java.pom import _get_pom_properties, _resolve_property, read_pom_for_dependencies
from builder.java.xml_support import parse_xml_file, parse_xml_string
from tests.test_support import get_test_path

_substitute_test_doc = """<?xml version="1.0" encoding="UTF-8"?>
<root>
    <child></child>
    <child>testing</child>
    <child>{field}</child>
    <child>${var1}</child>
    <child>${var2}</child>
    <child>${v} on ${v}</child>
</root>
"""


class TestPOMPropertyDiscovery(object):
    @staticmethod
    def _validate_properties(properties):
        # noinspection SpellCheckingInspection
        assert properties == {
            'jdkVersion': '1.5',
            'surefireVersion': '2.19.1',
            'hamcrestVersion': '1.3',
            'project.build.sourceEncoding': 'ISO-8859-1',
            'gpg.keyname': '67893CC4',
            'arguments': None
        }

    def test_property_discovery_no_namespace(self):
        """Make sure we find properties in a POM with no namespace."""
        pom_path = get_test_path('java/junit-no-ns.pom.xml')
        root = parse_xml_file(pom_path)

        self._validate_properties(_get_pom_properties(root))

    def test_property_discovery_with_namespace(self):
        """Make sure we find properties in a POM with a namespace."""
        pom_path = get_test_path('java/junit.pom.xml')
        root = parse_xml_file(pom_path)

        self._validate_properties(_get_pom_properties(root))

    def test_property_discovery_no_properties(self):
        """Make sure we deal with no properties correctly."""
        pom_path = get_test_path('java/junit-2.pom.xml')
        root = parse_xml_file(pom_path)
        properties = _get_pom_properties(root)

        assert len(properties) == 0


class TestPOMPropertyResolve(object):
    def test_basic_property_substitution(self):
        """Make sure we handle variable substitution properly."""
        properties = {'var1': 'value1', 'v': 'one'}
        root = parse_xml_string(_substitute_test_doc)
        expected_values = (None, 'testing', '{field}', 'value1', '', 'one on one')

        assert _resolve_property(None, properties) is None

        for index, expected in enumerate(expected_values):
            assert _resolve_property(root[index], properties) == expected


class TestPOMToDependencies(object):
    @staticmethod
    def _parent_dependency():
        return Dependency('name', {
            'location': 'remote',
            'version': '1.0.1',
            'scope': 'compile'
        })

    def test_read_pom_for_dependencies_no_dependencies(self):
        """Make sure we generate no dependencies when none exist."""
        pom_path = get_test_path('java/junit-2.pom.xml')
        context = DependencyContext([], Language({}, 'lang'), [], None)

        read_pom_for_dependencies(pom_path, context, self._parent_dependency())

        assert context.is_empty()

    def test_read_pom_for_dependencies_with_dependencies(self):
        """Make sure we generate proper dependency objects when dependencies exist."""
        pom_path = get_test_path('java/junit.pom.xml')
        context = DependencyContext([], Language({}, 'lang'), [], None)

        read_pom_for_dependencies(pom_path, context, self._parent_dependency())

        assert len(context._dependencies) == 2

        # Make sure parent dependency info is properly propagated.
        for dependency in context._dependencies:
            assert dependency.location == 'remote'
            assert dependency.scope == ['compile']
            assert dependency.transient is True

        dependencies = [repr(dependency) for dependency in context._dependencies]

        # And that we found the right stuff.
        assert dependencies == [
            'org.hamcrest:hamcrest-core:1.3',
            'org.hamcrest:hamcrest-library:1.3'
        ]
