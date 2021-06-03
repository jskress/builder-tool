"""
This file provides all our POM file handling.
"""
import re
from pathlib import Path
from typing import Dict, Optional, List, Generator, Tuple

from builder.java.java import create_remote_resolver
from builder.models import Dependency, DependencyContext
from builder.java.xml_support import parse_xml_file, XmlElement
from builder.utils import global_options

_var_pattern = re.compile(r'[$]{(.*?)[}]')
_excluded_scopes = ['test', 'provided', 'system']


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


class POMFile(object):
    """
    Instances of this class represent a loaded POM file.
    """
    def __init__(self, path: Path, context: DependencyContext):
        """
        A function to create instances of the ``POMFile`` class.

        :param path: the path to the POM file.
        :param context: the dependency context to add dependencies to.
        """
        self._root = parse_xml_file(path)
        self._properties = _get_pom_properties(self._root)
        self._imported = self._get_imported_dependencies(context)
        self._parent = self._get_parent(context)
        self._group_id = self._get_element_text(self._root.find('groupId'))
        self._version = self._get_element_text(self._root.find('version'))

        resolved_group_id = self.group_id
        resolved_version = self.version

        if resolved_group_id:
            self._properties['project.groupId'] = resolved_group_id

        if resolved_version:
            self._properties['project.version'] = resolved_version

    @property
    def group_id(self) -> Optional[str]:
        """
        A read-only property that returns the group ID specified in this POM file.
        If it doesn't have one, any existing parent is queried for it.

        :return: the value of any top-level ``groupId`` element in the POM file.
        """
        return self._group_id or (self._parent.group_id if self._parent else None)

    @property
    def version(self) -> Optional[str]:
        """
        A read-only property that returns the version specified in this POM file.
        If it doesn't have one, any existing parent is queried for it.

        :return: the value of any top-level ``version`` element in the POM file.
        """
        return self._version or (self._parent.version if self._parent else None)

    def _get_parent(self, context: DependencyContext) -> Optional['POMFile']:
        """
        A function that returns a parent POM file if our XML indicates one.

        :param context: the dependency context currently in play.
        :return: the parent POM file, if one is specified.
        """
        parent_element = self._root.find('parent')
        parent: Optional[POMFile] = None

        if parent_element:
            group, name, version = self.get_dependency_info(parent_element)
            resolver = create_remote_resolver(group, name, version)
            pom_path = resolver.resolve(f'{name}-{version}.pom')

            parent = POMFile(pom_path, context)

        return parent

    def _get_imported_dependencies(self, context: DependencyContext) -> List['POMFile']:
        """
        A function that returns a list of imported POM files.

        :param context: the dependency context currently in play.
        :return: a list of imported POM files.
        """
        result: List[POMFile] = []

        for dependency in self.management_dependencies():
            dep_type = self.get_element_value(dependency, 'type')
            dep_scope = self.get_element_value(dependency, 'scope')

            if dep_type == 'pom' and dep_scope == 'import':
                group, name, version = self.get_dependency_info(dependency)
                resolver = create_remote_resolver(group, name, version)
                pom_path = resolver.resolve(f'{name}-{version}.pom')

                result.append(POMFile(pom_path, context))

        return result

    @staticmethod
    def _get_element_text(element: Optional[XmlElement]) -> str:
        """
        A helper method to return the string value of the given XML element.

        :param element: the element to pull the text value from.  This may be `None`.
        :return: the text of the element.
        """
        return None if element is None else element.text()

    def _resolve_property(self, element: Optional[XmlElement]) -> Optional[str]:
        """
        A helper for resolving any property references in the text for an XML element.
        If a property reference exists for which there is no value, it is replaced with
        the empty string.

        :param element: the element to pull the text value from.  This may be `None`.
        :return: the text of the given element, with any property references resolved or
        `None` if no element was provided.
        """
        text = self._get_element_text(element)
        if text:
            text = global_options.substitute(text, extras=self._properties, ignore_global_vars=True)
        return text

    def get_element_value(self, element: XmlElement, tag: str) -> Optional[str]:
        """
        A function that accepts a parent element, looks for an immediate child element
        carrying the given tag, and returns its text after resolving any variable
        references.

        :param element: the parent element to start with.
        :param tag: the tag of the desired child.
        :return: the text value of the child element, with any variable references
        resolved.
        """
        return self._resolve_property(element.find(tag))

    def get_dependency_info(self, dependency: XmlElement) -> Tuple[str, str, Optional[str]]:
        """
        A helper function that retrieves the group, name and version values from a
        dependency element.

        :param dependency: the dependency element to pull the information from.
        :return: a tuple containing the group, name and optional version from the
        given dependency element.
        """
        group = self.get_element_value(dependency, 'groupId')
        name = self.get_element_value(dependency, 'artifactId')
        version = self.get_element_value(dependency, 'version')

        return group, name, version

    def is_optional(self, dependency: XmlElement) -> bool:
        """
        A helper function that notes whether the dependency represented by the given
        XML element is optional.

        :param dependency: the dependency element to check.
        :return: ``True`` if the dependency is marked as optional or ``False`` if not.
        """
        return self.get_element_value(dependency, 'optional') == 'true'

    def management_dependencies(self) -> Generator[XmlElement, None, None]:
        """
        A function that returns a generator over the POM file's ``dependency`` elements
        that are listed under its ``dependencyManagement`` element.
        """
        for dependencyManagement in self._root.findall('dependencyManagement'):
            for dependency_list in dependencyManagement.findall('dependencies'):
                for dependency in dependency_list.findall('dependency'):
                    scope = self.get_element_value(dependency, 'scope')

                    if scope not in _excluded_scopes and not self.is_optional(dependency):
                        yield dependency

    def dependencies(self) -> Generator[XmlElement, None, None]:
        """
        A function that returns a generator over the POM file's listed ``dependency``
        elements.
        """
        for dependencies in self._root.findall('dependencies'):
            for dependency in dependencies.findall('dependency'):
                scope = self.get_element_value(dependency, 'scope')
                dep_type = self.get_element_value(dependency, 'type')

                if scope not in _excluded_scopes and not self.is_optional(dependency) and dep_type != 'tar.gz':
                    yield dependency

    def resolve_version(self, group: str, name: str, version: Optional[str]) -> Optional[str]:
        """
        A function that tries to resolve the version for a dependency, if it is missing.
        If we have any imported or parent POM files, these are searched for a reference
        dependency with the same group and name.  The search is performed only if
        ``version`` is ``None`` or the empty string.

        If this function still returns ``None``, it's probably because it was ultimately
        something that should be excluded.

        :param group: the group to search for.
        :param name: the name to search for.
        :param version: the version, which may be ``None``.
        """
        if not version:
            for pom_file in self._imported:
                for dependency in pom_file.management_dependencies():
                    dep_group, dep_name, dep_version = pom_file.get_dependency_info(dependency)

                    if dep_group == group and dep_name == name:
                        return dep_version

            if self._parent:
                for dependency in self._parent.dependencies():
                    dep_group, dep_name, dep_version = self._parent.get_dependency_info(dependency)

                    if dep_group == group and dep_name == name:
                        return dep_version

                return self._parent.resolve_version(group, name, version)

        return version


def read_pom_for_dependencies(pom_path: Path, context: DependencyContext, parent_dependency: Dependency):
    """
    A function that reads a POM file for transient dependencies and includes them into
    the specified context.

    :param pom_path: the path to the POM file to read.
    :param context: the dependency context to add dependencies to.
    :param parent_dependency: the dependency to which the POM file belongs.
    :return: the list of dependencies found in the POM file, if any.
    """
    pom_file = POMFile(pom_path, context)

    for dependency in pom_file.dependencies():
        group, name, version = pom_file.get_dependency_info(dependency)
        version = pom_file.resolve_version(group, name, version)

        # If the version could not be resolved, it's not a dependency we care about.
        if version:
            context.add_dependency(parent_dependency.derive_from(group, name, version))
