"""
This file provides all our module file handling.
"""
import json
from collections import OrderedDict
from pathlib import Path
from typing import Optional, Dict, Any, List

from builder import VERSION
from builder.models import Dependency
from builder.signing import supported_signatures


API_ELEMENTS = 'apiElements'
RUNTIME_ELEMENTS = 'runtimeElements'
SHADOW_RUNTIME_ELEMENTS = 'shadowRuntimeElements'
JAVADOC_ELEMENTS = 'javadocElements'
SOURCE_ELEMENTS = 'sourcesElements'
_attr_prefix = 'org.gradle.'


class Component(object):
    """
    Instances of this class represent the component information in a module file.
    """
    @classmethod
    def from_dict(cls, content: Dict[str, Any]) -> 'Component':
        """
        A function to create a component from a dictionary of data.

        :param content: the content to load from.
        """
        result = Component(content['group'], content['module'], content['version'])

        if 'attributes' in content:
            result._attributes = OrderedDict(content['attributes'])

        return result

    @classmethod
    def from_dependency(cls, dependency: Dependency) -> 'Component':
        """
        A function to create a component from a framework dependency object.

        :param dependency: the dependency to create the component from.
        """
        return Component(dependency.group, dependency.name, dependency.version)

    def __init__(self, group: str, module: str, version: str):
        """
        A function to create a module component.

        :param group: the group name of the component.
        :param module: the name of the component.
        :param version: the version of the component.
        """
        self._group = group
        self._module = module
        self._version = version
        self._attributes = OrderedDict({
            f'{_attr_prefix}status': 'release'
        })
        self._endorse_strict_versions = False

    def as_dependency(self, parent: Dependency) -> Dependency:
        """
        A function that creates a builder dependency object out of the information
        we carry.

        :param parent: the parent dependency to use.
        :return: the representative framework dependency object.
        """
        return parent.derive_from(self._group, self._module, self._version)

    def to_dict(self) -> Dict[str, Any]:
        """
        A function to build a dictionary out of our data.
        """
        result = OrderedDict(
            group=self._group,
            module=self._module,
            version=self._version
        )

        if self._attributes:
            result['attributes'] = self._attributes

        if self._endorse_strict_versions:
            result['endorseStrictVersions'] = True

        return result


class VariantFile(object):
    """
    Instances of this class represent the information about a variant file.
    """
    @classmethod
    def from_dict(cls, content: Dict[str, Any]) -> 'VariantFile':
        """
        A function to create a variant file from a dictionary of data.

        :param content: the content to load from.
        :return: the resulting variant file.
        """
        result = VariantFile(content['name'], content['url'], content['size'])

        for signature_name in supported_signatures:
            if signature_name in content:
                result._signatures[signature_name] = content[signature_name]

        return result

    @classmethod
    def from_path(cls, path: Path):
        """
        A function to create a variant file from a path.

        :param path: the path to create the variant file from.
        :return: the resulting variant file.
        """
        size = path.stat().st_size if path.is_file() else 0
        return VariantFile(path.name, path.name, size)

    def __init__(self, name: str, url: str, size: int):
        """
        A function to create a module component variant.

        :param name: the name of the variant.
        """
        self._name = name
        self._url = url
        self._size = size
        self._signatures: OrderedDict[str, str] = OrderedDict()

    @property
    def name(self):
        """
        A read-only property that provides the name of the variant file.

        :return: the name of the variant file.
        """
        return self._name

    @property
    def signatures(self) -> Dict[str, str]:
        """
        The get side of a property that returns the known signatures we currently
        carry for the file. The dictionary returned is keyed by signature name
        which is mapped to the digital signature of the file as determined by that
        signature algorithm.

        :return: the dictionary of known digital signatures for the file.
        """
        return self._signatures

    @signatures.setter
    def signatures(self, signatures: Dict[str, str]):
        """
        The set side of a property that sets the known signatures we should carry for
        the file.  The dictionary provided must be keyed by signature name which should
        be mapped to the digital signature of the file as determined by that signature
        algorithm.

        :param self: the new dictionary of known digital signatures for the file.
        """
        if not isinstance(signatures, OrderedDict):
            signatures = OrderedDict(signatures)

        self._signatures = signatures

    def to_dict(self) -> Dict[str, Any]:
        """
        A function to build a dictionary out of our data.
        """
        result = OrderedDict(
            name=self._name,
            url=self._url,
            size=self._size
        )

        for signature_name, digital_signature in self._signatures.items():
            result[signature_name] = digital_signature

        return result


class Variant(object):
    """
    Instances of this class represent variant information in a module file.
    """
    @classmethod
    def from_dict(cls, content: Dict[str, Any]) -> 'Variant':
        """
        A function to create a variant from a dictionary of data.

        :param content: the content to load from.
        """
        result = Variant(content['name'])

        if 'attributes' in content:
            result._attributes = OrderedDict(content['attributes'])

        if 'dependencies' in content:
            for dependency in content['dependencies']:
                result._dependencies.append(Component.from_dict(dependency))

        if 'files' in content:
            for file_info in content['files']:
                result._files.append(VariantFile.from_dict(file_info))

        return result

    def __init__(self, name: str):
        """
        A function to create a module component variant.

        :param name: the name of the variant.
        """
        self._name = name
        self._attributes: Optional[OrderedDict[str, Any]] = None
        self._dependencies: List[Component] = []
        self._files: List[VariantFile] = []

    @property
    def name(self):
        """
        A read-only property that provides the name of the variant.

        :return: the name of the variant.
        """
        return self._name

    def set_attr(self, name: str, value: Any):
        """
        A function for setting an attribute of the variant.  Note that the name provided
        will be prefixed with ``org.gradle.`` to form the actual name of the attribute.

        :param name: the name of the attribute to set.
        :param value: the value to set the attribute to.
        """
        if self._attributes is None:
            self._attributes = OrderedDict()
        self._attributes[f'{_attr_prefix}{name}'] = value
        return self

    def add_dependency(self, dependency: Dependency):
        """
        A function to add a dependency to this variant.

        :param dependency: the dependency to add.
        """
        self._dependencies.append(Component.from_dependency(dependency))

    @property
    def dependencies(self) -> List[Component]:
        """
        A read-only property that provides the dependencies of this variant represented
        as a list of components.

        :return: the list of dependencies for this variant.
        """
        return self._dependencies

    def add_path(self, path: Path, signatures: Optional[Dict[str, str]] = None):
        """
        A function for adding a new file to the variant by virtue of adding a path
        and its digital signatures.

        :param path: the path to add a file reference for.
        :param signatures: the digital signatures of the path.
        """
        variant_file = VariantFile.from_path(path)

        if signatures:
            variant_file.signatures = signatures

        self._files.append(variant_file)

    @property
    def files(self) -> List[VariantFile]:
        """
        A read-only property that provides the list of files that make up this
        variant.

        :return: the variant's list of files.
        """
        return self._files

    def to_dict(self) -> Dict[str, Any]:
        """
        A function to build a dictionary out of our data.
        """
        result = OrderedDict(
            name=self._name
        )

        if self._attributes:
            result['attributes'] = self._attributes

        if len(self._dependencies) > 0:
            result['dependencies'] = [dependency.to_dict() for dependency in self._dependencies]

        if len(self._files) > 0:
            result['files'] = [variant_file.to_dict() for variant_file in self._files]

        return result


class ModuleData(object):
    """
    Instances of this class represent a module file that provides metadata about a
    Java API.
    """
    @classmethod
    def from_path(cls, path: Path) -> 'ModuleData':
        """
        A function that creates an instance of the ``ModuleFile`` class by reading its
        content from the given path.

        :param path: the path to read our content from.
        """
        content = json.loads(path.read_text(encoding='utf-8'))
        module_file = ModuleData()

        if 'formatVersion' in content:
            module_file._format_version = content['formatVersion']

        module_file._component = Component.from_dict(content['component'])

        if 'variants' in content:
            for variant in content['variants']:
                module_file._variants.append(Variant.from_dict(variant))

        return module_file

    @classmethod
    def for_component(cls, component: Component) -> 'ModuleData':
        """
        A function that creates an instance of the ``ModuleFile`` class for the specified
        component..

        :param component: the path to read our content from.
        """
        module_data = ModuleData()

        module_data._component = component

        return module_data

    def __init__(self):
        """
        A function that creates an instance of the ``ModuleFile`` class.
        """
        self._format_version = "1.1"
        self._component: Optional[Component] = None
        self._variants: List[Variant] = []

    def add_variant(self, name: str) -> Variant:
        """
        A function that creates a variant based on the given name.

        :param name: the name of the new variant.
        :return: the named variant or ``None`` if no such variant exists.
        """
        if self.get_variant(name) is not None:
            raise ValueError(f'There is already a variant known by the name {name}.')

        variant = Variant(name)

        self._variants.append(variant)

        return variant

    def get_variant(self, name: str) -> Optional[Variant]:
        """
        A function that returns the named variant.

        :param name: the name of the desired variant.
        :return: the named variant or ``None`` if no such variant exists.
        """
        return next((variant for variant in self._variants if variant.name == name), None)

    def to_dict(self) -> Dict[str, Any]:
        """
        A function that returns the contents of this module data as a dictionary.

        :return: the contents of this set of module data as a dictionary.
        """
        component_data = self._component.to_dict() if self._component else {}
        return OrderedDict(
            formatVersion=self._format_version,
            component=component_data,
            createdBy=OrderedDict(
                builder={"version": VERSION}
            ),
            variants=[variant.to_dict() for variant in self._variants]
        )

    def write(self, path: Path):
        """
        A function to write the contents of this set of module data to a file. The
        resulting file will be in JSON format.

        :param path: the path to write our contents to.
        """
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding='utf-8')
