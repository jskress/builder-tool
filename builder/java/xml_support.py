"""
This file provides some thin wrapper stuff to make XML easier to play with, especially
regarding namespaces.
"""
from pathlib import Path
from typing import Optional, Sequence
from xml.etree import ElementTree as Xml
from xml.etree.ElementTree import Element


class XmlElement(object):
    """
    A thin wrapper around XML element objects to make namespace stuff transparent.

    Note: the various XML functions are not optimized for large XML documents;
    they are intended for use on configuration XML-sized documents.
    """
    def __init__(self, element: Element, namespace: str):
        self.element = element
        self._namespace = namespace

    def tag(self) -> str:
        """
        Gets the tag of the element.  The value returned is always the simple
        tag name; no namespace information is included.

        :return: the simple tag of the element.
        """
        return self.element.tag[len(self._namespace):]

    def text(self) -> str:
        """
        Gets the text value for the element.  The value returned is only the text
        found after the tag in the source document and does not contain any child
        or tail text.  It is intended for use on simple value elements.

        :return: the element's text value.
        """
        return self.element.text

    def namespace(self) -> str:
        """
        Gets the namespace for this element.  The value may be the empty string
        but will never be `None`.

        :return: the element's namespace, if any.
        """
        return self._namespace

    def children(self) -> Sequence['XmlElement']:
        """
        Gets a sequence containing all the child elements of this element.

        :return: the child elements of this element.
        """
        return [XmlElement(element, self._namespace) for element in self.element]

    def find(self, tag_name: str) -> Optional['XmlElement']:
        """
        Finds the first child of this element that carries the specified tag.  If
        no such children exist, then ``None`` is returned.

        :param tag_name: the tag name to search for.
        :return: the first child with the given tag name or ``None``.
        """
        result = self.element.find(f'{self._namespace}{tag_name}')
        return None if result is None else XmlElement(result, self._namespace)

    def findall(self, tag_name: str) -> Sequence['XmlElement']:
        """
        Finds all the children of this element that carry the specified tag.  If
        no such children exist, then an empty sequence is returned.

        :param tag_name: the tag name to search for.
        :return: all the children of this element with the given tag name.
        """
        result = self.element.findall(f'{self._namespace}{tag_name}')
        return [XmlElement(element, self._namespace) for element in result]

    def __iter__(self):
        return iter(self.children())

    def __getitem__(self, item):
        return XmlElement(self.element[item], self._namespace)


def _get_root_element(root: Element) -> XmlElement:
    """
    This function is used to derive a wrapped root element from the given XML
    document root.  The root returned is a thin wrapper around the normal
    element so we can provide namespace awareness in a more transparent manner.

    :param root: the root of the XML DOM tree.
    :return the root element of the XML document.
    """
    namespace = ''
    if root.tag.startswith('{'):
        p = root.tag.find('}')
        if p > 0:
            namespace = root.tag[:p + 1]
    return XmlElement(root, namespace)


def parse_xml_file(path: Path) -> XmlElement:
    """
    This function is used to parse the given XML file into a  document represented
    by its root element.  The root returned is a thin wrapper around the normal
    element so we can provide namespace awareness in a more transparent manner.

    :param path: the path to the POM file to read.
    :return the root element of the XML document.
    """
    # noinspection PyTypeChecker
    return _get_root_element(Xml.parse(path).getroot())


def parse_xml_string(text: str) -> XmlElement:
    """
    This function is used to parse the given XML file into a  document represented
    by its root element.  The root returned is a thin wrapper around the normal
    element so we can provide namespace awareness in a more transparent manner.

    :param text: the path to the POM file to read.
    :return the root element of the XML document.
    """
    return _get_root_element(Xml.fromstring(text))
