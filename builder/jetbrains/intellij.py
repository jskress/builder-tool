"""
This file provides all the support we need for working with IntelliJ files.
"""
from collections import OrderedDict
from pathlib import Path

import xml.etree.ElementTree as Xml
from typing import Callable, Optional, Any, List

from builder.java.modules import SOURCE_ELEMENTS, JAVADOC_ELEMENTS
from builder.models import DependencyPathSet, Dependency
from builder.utils import global_options

DocumentCreator = Callable[[Any], Xml.Element]
_idea_path = Path('.idea')
_libraries_path = _idea_path / 'libraries'


class IJFile(object):
    """
    This class represents a particular IntelliJ file under a project.
    """
    def __init__(self, project: 'IJProject', path: Path, xml_declaration: bool, document_creator: DocumentCreator,
                 force_create: bool = False, **inputs):
        self._project = project
        self._path = project.directory / path
        self._xml_declaration = xml_declaration
        self.dirty = False

        if self._path.is_file() and not force_create:
            self._root = Xml.parse(self._path).getroot()
        else:
            self._root = document_creator(**inputs)
            self.dirty = True

    @property
    def project(self) -> 'IJProject':
        return self._project

    def write(self):
        if self.dirty:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._indent(self._root)

            tree = Xml.ElementTree(self._root)

            tree.write(self._path, encoding='utf-8', xml_declaration=self._xml_declaration)

            self.dirty = False

    def _indent(self, element, level=0):
        """
        A simple routine for formatting our XML output.
        """
        i = "\n" + level * "  "
        if len(element):
            if not element.text or not element.text.strip():
                element.text = i + "  "
            if not element.tail or not element.tail.strip():
                element.tail = i
            for element in element:
                self._indent(element, level + 1)
            if not element.tail or not element.tail.strip():
                element.tail = i
        else:
            if level and (not element.tail or not element.tail.strip()):
                element.tail = i


class IJImlFile(IJFile):
    def __init__(self, project: 'IJProject', **inputs):
        super().__init__(project, Path(f'{project.directory.name}.iml'), True, self._create_default_document, **inputs)

    def clear_libraries(self):
        """
        A function that removes any existing library references.
        """
        component = self._root.find('component')

        for entry in component.findall('orderEntry'):
            if entry.attrib['type'] == 'library':
                component.remove(entry)

        self.dirty = True

    def add_library(self, dependency: Dependency):
        """
        A function for adding a dependency as a library to this project.  If the dependency
        already exists, then no changes are made.

        :param dependency: the dependency to add as a library to the project.
        """
        component = self._root.find('component')
        text = repr(dependency)

        for entry in component.findall('orderEntry'):
            if entry.attrib['type'] == 'library' and entry.attrib['name'] == text:
                # The dependency is already listed.
                return

        # If we're here, the dependency actually needs to be added.
        Xml.SubElement(component, 'orderEntry', OrderedDict(
            type='library',
            name=text,
            level='project'
        ))

        self.dirty = True

    @staticmethod
    def _create_default_document(**inputs) -> Xml.Element:
        """
        A function that creates an initial IntelliJ project file (.iml).
        """
        root = Xml.Element('module', OrderedDict(
            type='JAVA_MODULE',
            verseion='4'
        ))

        component_attrs = OrderedDict()
        component_attrs['name'] = 'NewModuleRootManager'
        component_attrs['inherit-compiler-output'] = 'true'

        component = Xml.SubElement(root, 'component', component_attrs)

        Xml.SubElement(component, 'exclude-output')

        content = Xml.SubElement(component, 'content', OrderedDict(
            url='file://$MODULE_DIR$',
            verseion='4'
        ))

        if 'source' in inputs:
            Xml.SubElement(content, 'sourceFolder', OrderedDict(
                url=f'file://$MODULE_DIR$/{inputs["source"]}',
                isTestSource='false'
            ))

        if 'resources' in inputs:
            Xml.SubElement(content, 'sourceFolder', OrderedDict(
                url=f'file://$MODULE_DIR$/{inputs["resources"]}',
                type='java-resource'
            ))

        if 'tests' in inputs:
            Xml.SubElement(content, 'sourceFolder', OrderedDict(
                url=f'file://$MODULE_DIR$/{inputs["tests"]}',
                isTestSource='true'
            ))

        Xml.SubElement(component, 'orderEntry', OrderedDict(
            type='inheritedJdk'
        ))
        Xml.SubElement(component, 'orderEntry', OrderedDict(
            type='sourceFolder',
            forTests='false'
        ))

        return root


class IJMiscFile(IJFile):
    def __init__(self, project: 'IJProject', **inputs):
        super().__init__(project, _idea_path / 'misc.xml', True, self._create_default_document, **inputs)

    @staticmethod
    def _create_default_document(**inputs) -> Xml.Element:
        """
        A function that creates an initial IntelliJ ``misc.xml`` file.
        """
        java_version_number = inputs['java_version_number']
        jdk = f'JDK_{java_version_number}'
        root = Xml.Element('project', OrderedDict(
            verseion='4'
        ))

        component_attrs = OrderedDict()
        component_attrs['name'] = 'ProjectRootManager'
        component_attrs['version'] = '2'
        component_attrs['languageLevel'] = jdk
        component_attrs['default'] = 'false'
        component_attrs['project-jdk-name'] = f'{java_version_number}'
        component_attrs['project-jdk-type'] = 'JavaSDK'

        component = Xml.SubElement(root, 'component', component_attrs)

        Xml.SubElement(component, 'output', OrderedDict(
            url='file://$PROJECT_DIR$/build/ij'
        ))

        return root


class IJModulesFile(IJFile):
    def __init__(self, project: 'IJProject', **inputs):
        super().__init__(project, _idea_path / 'modules.xml', True, self._create_default_document, **inputs)

    @staticmethod
    def _create_default_document(**inputs) -> Xml.Element:
        """
        A function that creates an initial IntelliJ ``modules.xml`` file.
        """
        project_name = inputs['project_name']
        root = Xml.Element('project', OrderedDict(
            verseion='4'
        ))

        component = Xml.SubElement(root, 'component', OrderedDict(
            name='ProjectModuleManager'
        ))
        modules = Xml.SubElement(component, 'modules')

        Xml.SubElement(modules, 'module', OrderedDict(
            fileurl=f'file://$PROJECT_DIR$/{project_name}.iml',
            filepath=f'$PROJECT_DIR$/{project_name}.iml'
        ))

        return root


class IJLibraryFile(IJFile):
    def __init__(self, project: 'IJProject', path_sets: List[DependencyPathSet]):
        main_dependency = path_sets[0].dependency
        name = repr(main_dependency)

        for ch in '.:-/':
            name = name.replace(ch, '_')

        super().__init__(
            project, _libraries_path / f'{name}.xml', True, self._create_default_document, True,
            path_sets=path_sets
        )

    @staticmethod
    def _create_default_document(**inputs) -> Xml.Element:
        """
        A function that creates an initial IntelliJ ``modules.xml`` file.
        """
        path_sets: List[DependencyPathSet] = inputs['path_sets']
        project = global_options.project()
        main_dependency = path_sets[0].dependency
        root = Xml.Element('component', OrderedDict(
            name='libraryTable'
        ))

        library = Xml.SubElement(root, 'library', OrderedDict(
            name=repr(main_dependency),
            type='repository'
        ))

        Xml.SubElement(library, 'properties', {
            'maven-id': repr(main_dependency)
        })

        classes = Xml.SubElement(library, 'CLASSES')
        javadoc = Xml.SubElement(library, 'JAVADOC')
        sources = Xml.SubElement(library, 'SOURCES')

        for path_set in path_sets:
            Xml.SubElement(classes, 'root', {
                'url': _to_relative_path_url(path_set.primary_path, project.directory)
            })

            if path_set.has_secondary_path(SOURCE_ELEMENTS):
                Xml.SubElement(sources, 'root', {
                    'url': _to_relative_path_url(path_set.sourcesElements, project.directory)
                })

            if path_set.has_secondary_path(JAVADOC_ELEMENTS):
                Xml.SubElement(javadoc, 'root', {
                    'url': _to_relative_path_url(path_set.javadocElements, project.directory)
                })

        return root


def _to_relative_path_url(path: Path, project_path: Path) -> str:
    first = str(_to_relative_path(path, Path.home()))
    second = str(_to_relative_path(path, project_path))
    var, text = ('$USER_HOME$', first) if len(first) < len(second) else ('$PROJECT_DIR$', second)

    return f'jar://{var}/{text}!/'


def _to_relative_path(path: Path, referent: Path) -> Path:
    try:
        return path.relative_to(referent)
    except ValueError:
        return path


class IJProject(object):
    """
    This class represents an IntelliJ project.  It is the source for all other instances
    of all other project-related classes.
    """
    def __init__(self, directory: Path):
        self._directory = directory
        self._iml_file: Optional[IJImlFile] = None
        self._misc_file: Optional[IJMiscFile] = None
        self._modules_file: Optional[IJModulesFile] = None
        self._library_files: List[IJLibraryFile] = []

    @property
    def directory(self):
        """
        This is a read-only property that provides the root directory for the project.
        """
        return self._directory

    def iml_file(self, **inputs) -> IJImlFile:
        if not self._iml_file:
            self._iml_file = IJImlFile(self, **inputs)
        return self._iml_file

    def misc_file(self, **inputs) -> IJMiscFile:
        if not self._misc_file:
            self._misc_file = IJMiscFile(self, **inputs)
        return self._misc_file

    def modules_file(self, **inputs) -> IJModulesFile:
        if not self._modules_file:
            self._modules_file = IJModulesFile(self, **inputs)
        return self._modules_file

    def add_library(self, path_sets: List[DependencyPathSet]):
        """
        A function that adds a dependency, and its transient dependencies, as libraries to
        this project.

        :param path_sets: the collection of resolved path sets that represent the locally
        resolved dependency information.
        """
        self._library_files.append(IJLibraryFile(self, path_sets))
        self.iml_file().add_library(path_sets[0].dependency)

    def save(self):
        """
        A helper function that will save any files that have changed.
        """
        if self._iml_file:
            self._iml_file.write()
        if self._misc_file:
            self._misc_file.write()
        if self._modules_file:
            self._modules_file.write()

        for library in self._library_files:
            library.write()
