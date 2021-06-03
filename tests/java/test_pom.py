"""
This file contains all the unit tests for our POM support.
"""
from unittest import mock
from unittest.mock import Mock

from builder.config import Configuration
from builder.java import resolve
from builder.models import Dependency, DependencyContext, Language, DependencyPathSet
# noinspection PyProtectedMember
from builder.java.pom import _get_pom_properties, read_pom_for_dependencies
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
        context = DependencyContext([], Language({}, 'lang'), Configuration({}, [], None))

        read_pom_for_dependencies(pom_path, context, self._parent_dependency())

        assert context.is_empty()
