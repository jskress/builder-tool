"""
This file contains all the unit tests for our Java module metadata support.
"""
import json
from collections import OrderedDict
from pathlib import Path

import pytest

from builder import VERSION
from builder.java.modules import Component, VariantFile, Variant, API_ELEMENTS, ModuleData
from builder.models import Dependency
from tests.test_support import get_test_path


class TestComponent(object):
    def test_construction(self):
        component = Component('group', 'module', '1.2.3')

        assert component.to_dict() == {
            'group': 'group',
            'module': 'module',
            'version': '1.2.3',
            'attributes': {
                'org.gradle.status': 'release'
            }
        }

    def test_from_dict(self):
        component = Component.from_dict({
            'group': 'my_group',
            'module': 'name',
            'version': '1.2.3'
        })

        assert component.to_dict() == {
            'group': 'my_group',
            'module': 'name',
            'version': '1.2.3',
            'attributes': {
                'org.gradle.status': 'release'
            }
        }

        component = Component.from_dict({
            'group': 'my_group',
            'module': 'name',
            'version': '1.2.3',
            'attributes': {
                'my.attribute': 'value'
            }
        })

        assert component.to_dict() == {
            'group': 'my_group',
            'module': 'name',
            'version': '1.2.3',
            'attributes': {
                'my.attribute': 'value'
            }
        }

    def test_from_dependency(self):
        dep = Dependency('key', {
            'location': 'remote',
            'version': '7.2.1',
            'scope': 'scope'
        })
        component = Component.from_dependency(dep)

        assert component.to_dict() == {
            'group': 'key',
            'module': 'key',
            'version': '7.2.1',
            'attributes': {
                'org.gradle.status': 'release'
            }
        }

    def test_as_dependency(self):
        component = Component('group', 'module', '7.2.1')
        parent = Dependency('parent', {
            'location': 'remote',
            'version': '7.2.1',
            'scope': 'scope'
        })
        dep = Dependency('module', {
            'location': 'remote',
            'group': 'group',
            'version': '7.2.1',
            'scope': 'scope'
        })

        assert component.as_dependency(parent) == dep


class TestVariantFile(object):
    def test_construction(self):
        file = VariantFile('name', 'url', 12)

        assert file.name == 'name'
        assert isinstance(file.signatures, OrderedDict)
        assert len(file.signatures) == 0
        assert file.to_dict() == {
            'name': 'name',
            'url': 'url',
            'size': 12
        }

    def test_signatures(self):
        file = VariantFile('name', 'url', 12)
        signatures = {'sha512': '<big-digital-signature', 'md5': '<small-digital-signature'}
        file.signatures = signatures

        assert isinstance(file.signatures, OrderedDict)
        assert file.signatures is not signatures
        assert len(file.signatures) == 2

        assert file.to_dict() == {
            'name': 'name',
            'url': 'url',
            'size': 12,
            'sha512': '<big-digital-signature',
            'md5': '<small-digital-signature'
        }

        signatures = OrderedDict(
            sha512='<big-digital-signature',
            md5='<small-digital-signature'
        )
        file.signatures = signatures

        assert isinstance(file.signatures, OrderedDict)
        assert file.signatures is signatures

        assert file.to_dict() == {
            'name': 'name',
            'url': 'url',
            'size': 12,
            'sha512': '<big-digital-signature',
            'md5': '<small-digital-signature'
        }

    def test_from_dict(self):
        content = {
            'name': 'name',
            'url': 'url',
            'size': 12
        }

        assert VariantFile.from_dict(content).to_dict() == {
            'name': 'name',
            'url': 'url',
            'size': 12
        }

        content = {
            'name': 'name',
            'url': 'url',
            'size': 12,
            'sha512': '<big-digital-signature',
            'md5': '<small-digital-signature'
        }

        assert VariantFile.from_dict(content).to_dict() == {
            'name': 'name',
            'url': 'url',
            'size': 12,
            'sha512': '<big-digital-signature',
            'md5': '<small-digital-signature'
        }

        content = {
            'name': 'name',
            'url': 'url',
            'size': 12,
            'sha512': '<big-digital-signature',
            'md5': '<small-digital-signature',
            'unknown-signature': 'garbage'
        }

        assert VariantFile.from_dict(content).to_dict() == {
            'name': 'name',
            'url': 'url',
            'size': 12,
            'sha512': '<big-digital-signature',
            'md5': '<small-digital-signature'
        }

    def test_from_path(self, tmpdir):
        path = Path(str(tmpdir)) / 'file.txt'

        assert VariantFile.from_path(path).to_dict() == {
            'name': 'file.txt',
            'url': 'file.txt',
            'size': 0
        }

        path.write_text('test', encoding='utf-8')

        assert VariantFile.from_path(path).to_dict() == {
            'name': 'file.txt',
            'url': 'file.txt',
            'size': 4
        }


class TestVariant(object):
    def test_construction(self):
        variant = Variant(API_ELEMENTS)

        assert variant.name is API_ELEMENTS
        assert len(variant.dependencies) == 0
        assert len(variant.files) == 0
        assert variant.to_dict() == {
            'name': API_ELEMENTS
        }

    def test_attributes(self):
        variant = Variant(API_ELEMENTS)

        assert variant._attributes is None

        variant.set_attr('test', 'value')

        assert variant._attributes is not None
        assert variant.to_dict() == {
            'name': API_ELEMENTS,
            'attributes': {
                'org.gradle.test': 'value'
            }
        }

        variant.set_attr('other', 7)

        assert variant.to_dict() == {
            'name': API_ELEMENTS,
            'attributes': {
                'org.gradle.test': 'value',
                'org.gradle.other': 7
            }
        }

    def test_dependencies(self):
        dependency = Dependency('dep', {
            'location': 'local',
            'version': '3.2.7',
            'scope': 'scope'
        })
        variant = Variant(API_ELEMENTS)

        assert len(variant.dependencies) == 0

        variant.add_dependency(dependency)

        assert len(variant.dependencies) == 1
        assert variant.to_dict() == {
            'name': API_ELEMENTS,
            'dependencies': [{
                'group': 'dep',
                'module': 'dep',
                'version': '3.2.7',
                'attributes': {
                    'org.gradle.status': 'release'
                }
            }]
        }

    def test_files(self):
        variant = Variant(API_ELEMENTS)

        assert len(variant.files) == 0

        variant.add_path(Path('/path/to/test.jar'))

        assert len(variant.files) == 1
        assert variant.to_dict() == {
            'name': API_ELEMENTS,
            'files': [{
                'name': 'test.jar',
                'url': 'test.jar',
                'size': 0
            }]
        }

        variant.add_path(Path('/path/to/other.jar'), {'sig': 'digest'})

        assert len(variant.files) == 2
        assert variant.to_dict() == {
            'name': API_ELEMENTS,
            'files': [{
                'name': 'test.jar',
                'url': 'test.jar',
                'size': 0
            }, {
                'name': 'other.jar',
                'url': 'other.jar',
                'size': 0,
                'sig': 'digest'
            }]
        }

    def test_from_dict(self):
        variant_data = {
            'name': API_ELEMENTS,
            'attributes': {
                'org.gradle.test': 'value',
                'org.gradle.other': 7
            },
            'dependencies': [{
                'group': 'dep',
                'module': 'dep',
                'version': '3.2.7',
                'attributes': {
                    'org.gradle.status': 'release'
                }
            }],
            'files': [{
                'name': 'test.jar',
                'url': 'test.jar',
                'size': 0
            }, {
                'name': 'other.jar',
                'url': 'other.jar',
                'size': 0,
                'sha512': '<sha512-digest>'
            }]
        }

        variant = Variant.from_dict(variant_data)

        assert variant.to_dict() == variant_data


class TestModuleData(object):
    def test_construction(self):
        md = ModuleData()

        assert md.to_dict() == {
            "formatVersion": "1.1",
            "component": {},
            "createdBy": {
                "builder": {
                    "version": VERSION
                }
            },
            "variants": []
        }

    def test_from_path(self):
        path = get_test_path('java/package/basic_module.json')
        md = ModuleData.from_path(path)

        assert md.to_dict() == {
            "formatVersion": "1.1",
            "component": {
                "group": "project",
                "module": "project",
                "version": "1.3.4",
                "attributes": {
                    "org.gradle.status": "release"
                }
            },
            "createdBy": {
                "builder": {
                    "version": VERSION
                }
            },
            "variants": []
        }

    def test_for_component(self):
        component = Component.from_dict({
            'group': 'area',
            'module': 'cool-api',
            'version': '5.2.0'
        })
        md = ModuleData.for_component(component)

        assert md.to_dict() == {
            "formatVersion": "1.1",
            "component": {
                'group': 'area',
                'module': 'cool-api',
                'version': '5.2.0',
                'attributes': {
                    'org.gradle.status': 'release'
                }
            },
            "createdBy": {
                "builder": {
                    "version": VERSION
                }
            },
            "variants": []
        }

    def test_add_variant(self):
        md = ModuleData()

        # Make sure a good add works.
        assert md._variants == []

        variant = md.add_variant(API_ELEMENTS)

        assert variant is not None
        assert md._variants == [variant]

        # Make sure an add for an already existing name errors.
        with pytest.raises(ValueError) as info:
            md.add_variant(API_ELEMENTS)

        assert info.value.args[0] == f'There is already a variant known by the name {API_ELEMENTS}.'

    def test_get_variant(self):
        md = ModuleData()

        # Non-existent names return None
        assert md.get_variant(API_ELEMENTS) is None

        # Existing gets work
        variant = md.add_variant(API_ELEMENTS)

        assert md.get_variant(API_ELEMENTS) is variant

    def test_write(self, tmpdir):
        md = ModuleData()
        path = Path(str(tmpdir)) / 'test.json'

        md.write(path)

        with path.open("r") as fd:
            actual = json.load(fd)

        assert actual == {
            "formatVersion": "1.1",
            "component": {},
            "createdBy": {
                "builder": {
                    "version": VERSION
                }
            },
            "variants": []
        }
