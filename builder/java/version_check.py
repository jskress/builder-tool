"""
This file provides the support we need around dependency version checking.
"""
import re
from pathlib import Path
from typing import Tuple, List, Optional
from xml.etree import ElementTree

from builder.java.java import build_names
from builder.models import Dependency, DependencyContext
from builder.utils import global_options, out, verbose_out

_version_pattern = re.compile(r'^(\d+)\.(\d+)\.(\d+)([-_.]\w+)?$')
_tag_pattern = re.compile(r'.(\D*)(\d*)')


def _compare_tags(tag1: Optional[str], tag2: Optional[str]) -> int:
    """
    A function that attempts proper ordering of the tag portion of a version.

    :param tag1: the first tag to look at.
    :param tag2: the second tag to look at.
    :return: the usual result of comparing.
    """
    # Simple equivalence
    if (tag1 is None and tag2 is None) or tag1 == tag2:
        return 0

    # Normalize and drop the separator.
    t1_match = _tag_pattern.match(tag1 if tag1 else '-0')
    t1_group_1 = t1_match.group(1)
    t2_match = _tag_pattern.match(tag2 if tag2 else '-0')
    t2_group_1 = t2_match.group(1)

    if t1_group_1 and not t2_group_1:
        return -1
    if not t1_group_1 and t2_group_1:
        return 1
    # We have letter tags.
    if t1_group_1 and t1_group_1 != t2_group_1:
        return -1 if t1_group_1 < t2_group_1 else 1

    t1_number = int(t1_match.group(2)) if t1_match.group(2) else 0
    t2_number = int(t2_match.group(2)) if t2_match.group(2) else 0

    return t1_number - t2_number


class Version(object):
    def __init__(self, text: str):
        match = _version_pattern.match(text)
        if not match:
            raise ValueError(f'The text, "{text}", cannot be parsed as a version identifier.')
        self._major = int(match.group(1))
        self._minor = int(match.group(2))
        self._micro = int(match.group(3))
        self._tag = match.group(4) if match.group(4) else ''

    def _compare(self, other: 'Version'):
        diff = self._major - other._major

        if diff == 0:
            diff = self._minor - other._minor

        if diff == 0:
            diff = self._micro - other._micro

        if diff == 0 and self._tag != other._tag:
            diff = _compare_tags(self._tag, other._tag)

        return diff

    def __eq__(self, other):
        if not isinstance(other, Version):
            return NotImplemented

        return self._compare(other) == 0

    def __ne__(self, other):
        return not self == other

    def __lt__(self, other):
        if not isinstance(other, Version):
            return NotImplemented

        return self._compare(other) < 0

    def __le__(self, other):
        if not isinstance(other, Version):
            return NotImplemented

        return self._compare(other) <= 0

    def __gt__(self, other):
        if not isinstance(other, Version):
            return NotImplemented

        return self._compare(other) > 0

    def __ge__(self, other):
        if not isinstance(other, Version):
            return NotImplemented

        return self._compare(other) >= 0

    def __str__(self) -> str:
        return f'{self._major}.{self._minor}.{self._micro}{self._tag}'


def _get_remote_version_info(context: DependencyContext, dependency: Dependency) -> \
        Optional[Tuple[Version, List[Version]]]:
    """
    A function that determines the available and latest version numbers for the given
    remote dependency.  This is achieved by retrieving the ``maven-metadata.xml`` file
    for the dependency from Maven.

    :param context: the current context to use in pulling down remote files.
    :param dependency: the dependency to get the version information for.
    :return: Either ``None``, if version information could not be determined or a tuple
    containing the latest version in the 1st position and the list of available versions
    in the 2nd.
    """
    metadata_path = context.to_local_path(dependency, 'maven-metadata.xml')

    if metadata_path:
        data = ElementTree.parse(metadata_path).getroot()
        versioning = data.find('versioning')
        latest = versioning.find('latest')
        versions = versioning.find('versions')
        versions = [Version(version.text) for version in versions.iter('version')]

        return Version(latest.text), versions

    return None


def _get_local_version_info(paths: List[Path], name: str) -> Optional[Tuple[Version, List[Version]]]:
    """
    A function that determines the available and latest version numbers for the given
    local or project dependency name.  This is achieved by scanning the provided list of
    directories for appropriately named jar files.

    :param paths: the list of directory paths to scan.
    :param name: the name of the dependency to find versions for.
    :return: Either ``None``, if version information could not be determined or a tuple
    containing the latest version in the 1st position and the list of available versions
    in the 2nd.
    """
    latest: Optional[Version] = None
    available: List[Version] = []
    prefix = f'{name}-'
    suffix = '.jar'

    for path in paths:
        for file in path.iterdir():
            if file.name.startswith(prefix) and file.suffix == suffix:
                text = file.name[len(prefix):-len(suffix)]
                for trim in ['-javadoc', '-sources', '-source']:
                    if text.endswith(trim):
                        text = text[:-len(trim)]
                try:
                    version = Version(text)
                    if version not in available:
                        available.append(version)
                        latest = version if not latest else max(latest, version)
                except ValueError:
                    # Couldn't parse a version, just skip.
                    verbose_out(f'Could not parse a version from "{text}" the file {file}.')

    return None if not (latest or available) else latest, available


def check_dependency_versions():
    """
    A function that provides the implementation of the ``check-versions`` task for the
    Java language.  It will attempt to verify the version of all dependencies noted in
    the current project and report when a dependency is not using the current one or
    it's version cannot be found.
    """
    context = global_options.project().get_full_dependency_context('java')

    for dependency in context.dependencies:
        directory_url, directory_path, _, _ = build_names(dependency, version_in_url=False)
        version_info = None

        context.set_remote_info(directory_url, directory_path)

        if dependency.is_remote:
            version_info = _get_remote_version_info(context, dependency)
        elif dependency.is_project:
            publishing_directory = context.get_publishing_directory(dependency.key)

            if publishing_directory:
                version_info = _get_local_version_info([publishing_directory], dependency.name)

        else:  # dependency.is_local
            version_info = _get_local_version_info(context.local_paths, dependency.name)

        if version_info:
            dependency_version = Version(dependency.version)
            latest, available = version_info

            if latest == dependency_version:
                out(f'  - {dependency.name}: {dependency_version} (current).')
            elif dependency_version not in available:
                out(f'  - Version {dependency.version} of {dependency.name} is not available.')
            else:
                out(f'  - {dependency.name}: {dependency_version} (not latest; latest is {latest}).')
        else:
            out(f'  - Could not obtain version information for the {dependency.name} dependency.')
