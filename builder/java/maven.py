"""
This file provides all our Maven repository support.
"""
from typing import Union

from builder.dependencies import Dependency, RemoteFile, LocalFile
from builder.java.pom import pom_to_dependencies

_signatures = ['sha1', 'md5']


# noinspection PyUnusedLocal
def maven_resolver(dependency: Dependency, config) -> Union[RemoteFile, LocalFile]:
    group = dependency.group()
    name = dependency.name()
    version = dependency.version()
    jar_url = f'https://repo1.maven.org/maven2/{group}/{name}/{version}/{name}-{version}.jar'
    pom_url = f'https://repo1.maven.org/maven2/{group}/{name}/{version}/{name}-{version}.pom'
    return RemoteFile(dependency, jar_url, _signatures, name) \
        .add_meta_file(RemoteFile(dependency, pom_url, _signatures, name), pom_to_dependencies)
