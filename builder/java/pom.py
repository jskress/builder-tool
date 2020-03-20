"""
This file provides all our POM file handling.
"""
import re
from pathlib import Path
from typing import Dict, Optional, Sequence
from xml.etree import ElementTree as Xml
from xml.etree.ElementTree import Element

from builder.dependencies import Dependency

_var_pattern = re.compile(r'[$]{(.*?)[}]')


def _get_pom_properties(root: Element) -> Dict[str, str]:
    result = {}
    for props in root.findall('properties'):
        for prop in props:
            result[prop.tag] = prop.text
    return result


def _resolve_property(element: Element, props: Dict[str, str]) -> str:
    def substitute(match):
        name = match.group(1)
        return props[name] if name in props else ''

    text = element.text if element else None
    if text:
        text = _var_pattern.sub(substitute, text)
    return text


def pom_to_dependencies(pom_path: Path, parent_dependency: Dependency) -> Optional[Sequence[Dependency]]:
    root = Xml.parse(pom_path).getroot()
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
