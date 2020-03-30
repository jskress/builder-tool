"""
This file contains all the unit tests for our XML support.
"""
from builder.java.xml_support import parse_xml_file, XmlElement
from tests.test_utils import get_test_path


class TestXMLParsing(object):
    def test_parse_xml_file_no_namespace(self):
        """Make sure POMs with no namespaces parse correctly."""
        path = get_test_path('java/junit-no-ns.pom.xml')
        root = parse_xml_file(path)

        assert root is not None
        assert root.tag() == 'project'
        assert root.namespace() == ''

    def test_parse_pom_file_with_namespace(self):
        """Make sure POMs with namespaces parse correctly."""
        pom_path = get_test_path('java/junit.pom.xml')
        root = parse_xml_file(pom_path)

        assert root is not None
        assert root.tag() == 'project'
        assert root.namespace() == '{http://maven.apache.org/POM/4.0.0}'


class TestXMLSubscripting(object):
    def test_element_subscripting(self):
        """Make sure we can subscript an element with children and that they are properly wrapped."""
        pom_path = get_test_path('java/junit.pom.xml')
        root = parse_xml_file(pom_path)
        dependencies = root.find('dependencies')

        assert isinstance(dependencies, XmlElement)
        assert len(dependencies.children()) == 2
        assert isinstance(dependencies[0], XmlElement)
        assert isinstance(dependencies[1], XmlElement)


class TestXMLSearching(object):
    def test_findall_no_namespace(self):
        """Make sure we can find all children and that they are properly wrapped."""
        pom_path = get_test_path('java/junit-no-ns.pom.xml')
        root = parse_xml_file(pom_path)
        properties = root.findall('properties')

        assert len(properties) == 1
        assert isinstance(properties[0], XmlElement)
        assert properties[0].tag() == 'properties'

    def test_findall_with_namespace(self):
        """Make sure we can find all children and that they are properly wrapped."""
        pom_path = get_test_path('java/junit.pom.xml')
        root = parse_xml_file(pom_path)
        properties = root.findall('properties')

        assert len(properties) == 1
        assert isinstance(properties[0], XmlElement)
        assert properties[0].tag() == 'properties'

    def test_find_existing_no_namespace(self):
        """Make sure we can find the first child with a particular tag and that they are properly wrapped."""
        pom_path = get_test_path('java/junit-no-ns.pom.xml')
        root = parse_xml_file(pom_path)
        version = root.find('modelVersion')

        assert version is not None
        assert isinstance(version, XmlElement)
        assert version.tag() == 'modelVersion'

    def test_find_existing_with_namespace(self):
        """Make sure we can find the first child with a particular tag and that they are properly wrapped."""
        pom_path = get_test_path('java/junit.pom.xml')
        root = parse_xml_file(pom_path)
        version = root.find('modelVersion')

        assert version is not None
        assert isinstance(version, XmlElement)
        assert version.tag() == 'modelVersion'

    def test_find_missing_no_namespace(self):
        """Make sure we get None looking for a tag no child has, no namespace."""
        pom_path = get_test_path('java/junit-no-ns.pom.xml')
        root = parse_xml_file(pom_path)

        assert root.find('no-such-tag') is None

    def test_find_missing_with_namespace(self):
        """Make sure we get None looking for a tag no child has, with namespace."""
        pom_path = get_test_path('java/junit.pom.xml')
        root = parse_xml_file(pom_path)

        assert root.find('no-such-tag') is None
