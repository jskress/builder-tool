"""
This file contains all the unit tests for our Maven support.
"""
from pathlib import Path

from builder.dependencies import Dependency, RemoteFile
# noinspection PyProtectedMember
from builder.java.maven import maven_resolver
from builder.java.pom import pom_to_dependencies


class TestMaven(object):
    # noinspection PyProtectedMember
    def test_maven_resolver(self):
        dependency = Dependency.given('maven', None, 'test', '1.4.7', 'compile')
        result = maven_resolver(dependency, None)

        assert isinstance(result, RemoteFile)
        assert result._parent is dependency
        assert result.file_url() == 'https://repo1.maven.org/maven2/test/test/1.4.7/test-1.4.7.jar'
        assert result.local_name() == Path('test/test-1.4.7.jar')

        signature_files = result.get_signature_files()

        assert signature_files == [
            ('sha1', 'https://repo1.maven.org/maven2/test/test/1.4.7/test-1.4.7.jar.sha1',
             Path('test/test-1.4.7.jar.sha1')),
            ('md5', 'https://repo1.maven.org/maven2/test/test/1.4.7/test-1.4.7.jar.md5',
             Path('test/test-1.4.7.jar.md5'))
        ]

        meta_file, parser = result.get_meta_file_info()

        assert isinstance(meta_file, RemoteFile)
        assert meta_file._parent is dependency
        assert meta_file.file_url() == 'https://repo1.maven.org/maven2/test/test/1.4.7/test-1.4.7.pom'
        assert meta_file.local_name() == Path('test/test-1.4.7.pom')

        signature_files = meta_file.get_signature_files()

        assert signature_files == [
            ('sha1', 'https://repo1.maven.org/maven2/test/test/1.4.7/test-1.4.7.pom.sha1',
             Path('test/test-1.4.7.pom.sha1')),
            ('md5', 'https://repo1.maven.org/maven2/test/test/1.4.7/test-1.4.7.pom.md5',
             Path('test/test-1.4.7.pom.md5'))
        ]

        assert parser is pom_to_dependencies

        meta_file, parser = meta_file.get_meta_file_info()

        assert meta_file is None
        assert parser is None
