"""
This file provides all our POM file handling.
"""
import re
from pathlib import Path
from typing import Dict, Optional, Sequence, Match

from builder.dependencies import Dependency
from builder.java.xml_support import parse_xml_file, XmlElement

_var_pattern = re.compile(r'[$]{(.*?)[}]')


def _get_pom_properties(root: XmlElement) -> Dict[str, str]:
    """
    A helper function which locates property value elements in the root document of
    a parsed POM XML file.

    :param root: the root element of the parsed POM XML file.
    :return: a dictionary of property names mapped to their values.
    """
    result = {}
    for props in root.findall('properties'):
        for prop in props:
            result[prop.tag()] = prop.text()
    return result


def _resolve_property(element: Optional[XmlElement], props: Dict[str, str]) -> Optional[str]:
    """
    A helper for resolving any property references in the text for an XML element.
    If a property reference exists for which there is no value, it is replaced with
    the empty string.

    :param element: the element to pull the text value from.  This may be `None`.
    :param props: a dictionary of property values pulled from the containing POM
    file.
    :return: the text of the given element, with any property references resolved or
    `None` if no element was provided.
    """
    def substitute(match: Match[str]) -> str:
        name = match.group(1)
        return props[name] if name in props else ''

    text = None if element is None else element.text()
    if text:
        text = _var_pattern.sub(substitute, text)
    return text


def pom_to_dependencies(pom_path: Path, parent_dependency: Dependency) -> Optional[Sequence[Dependency]]:
    """
    This function satisfies the `MetaFileParser` type defined in `dependencies`.  It
    is used to parse POM files to locate transient dependencies for a dependent library.

    :param pom_path: the path to the POM file to read.
    :param parent_dependency: the dependency to which the POM file belongs.
    :return: the list of dependencies found in the POM file, if any.
    """
    root = parse_xml_file(pom_path)
    properties = _get_pom_properties(root)
    result = []
    for dependencies in root.findall('dependencies'):
        for dependency in dependencies.findall('dependency'):
            group = _resolve_property(dependency.find('groupId'), properties)
            name = _resolve_property(dependency.find('artifactId'), properties)
            version = _resolve_property(dependency.find('version'), properties)
            result.append(Dependency.given(parent_dependency.repo(), group, name, version,
                                           parent_dependency.scope()))

    return result
