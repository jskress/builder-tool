"""
This file provides all our Maven repository support.
"""
from pathlib import Path
from typing import Union

from builder.dependencies import Dependency, RemoteFile, LocalFile
from builder.java.pom import pom_to_dependencies

_signatures = ['sha1', 'md5']


# noinspection PyUnusedLocal
def maven_resolver(dependency: Dependency, jar_name: str, maven_config) -> Union[RemoteFile, LocalFile]:
    """
    A function to convert a Maven dependency into a remote file reference for the
    builder framework to resolve and cache.

    :param dependency: the dependency to convert.
    :param jar_name: the pre-formatted simple name for the dependency.
    :param maven_config: the configuration information for Maven; this is ignored
    as we have no configuration we respond to.
    :return: the given dependency as a remote file.
    """
    group = dependency.group
    name = dependency.name
    version = dependency.version
    pom_name = str(Path(jar_name).with_suffix('.pom'))
    jar_url = f'https://repo1.maven.org/maven2/{group}/{name}/{version}/{jar_name}'
    pom_url = f'https://repo1.maven.org/maven2/{group}/{name}/{version}/{pom_name}'
    return RemoteFile(dependency, jar_url, _signatures, name) \
        .set_meta_file(RemoteFile(dependency, pom_url, _signatures, name), pom_to_dependencies)
