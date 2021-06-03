"""
This file provides the support we need around dependency version checking.
"""
from pathlib import Path
from typing import Tuple, List, Optional
from xml.etree import ElementTree

from builder.java.java import build_names
from builder.models import Dependency, DependencyContext, Version
from builder.utils import global_options, out, verbose_out


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
    local_paths = global_options.project().configuration.local_paths

    for dependency in context.dependencies:
        resolver, _, _ = build_names(dependency, version_in_url=False)
        version_info = None

        context.set_remote_resolver(resolver)

        if dependency.is_remote:
            version_info = _get_remote_version_info(context, dependency)
        elif dependency.is_project:
            publishing_directory = context.get_publishing_directory(dependency.key)

            if publishing_directory:
                version_info = _get_local_version_info([publishing_directory], dependency.name)

        else:  # dependency.is_local
            version_info = _get_local_version_info(local_paths, dependency.name)

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
