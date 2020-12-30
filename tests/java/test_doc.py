"""
This file contains all the unit tests for our javadoc support.
"""
from pathlib import Path

from builder.java import JavaConfiguration
# noinspection PyProtectedMember
from builder.java.doc import _find_packages, java_doc
from builder.project import Project
from tests.test_support import FakeProcessContext, FakeProcess, Options


class TestJavaDocSupport(object):
    @staticmethod
    def _create_fake_source_structure(root: Path):
        com = root / 'com'
        test = com / 'test'
        package = test / 'pkg'
        sub = package / 'sub'
        java_file = package / 'Test.java'
        sub_java_file = sub / 'SubClass.java'

        sub.mkdir(parents=True, exist_ok=True)
        java_file.touch()
        sub_java_file.touch()

    def test_find_packages(self, tmpdir):
        root = Path(str(tmpdir))
        packages = []

        self._create_fake_source_structure(root)

        _find_packages(root, root, packages)

        assert packages == ['com.test.pkg', 'com.test.pkg.sub']

    def _test_java_doc(self, tmpdir, verbose: int):
        project_dir = Path(str(tmpdir))
        project = Project.from_dir(project_dir)

        with Options(project=project):
            config = JavaConfiguration()

        # These need to exist for the test to work.
        code_dir = config.code_dir(ensure=True)
        doc_dir = config.doc_dir(ensure=True)

        self._create_fake_source_structure(code_dir)

        expected = [
            'javadoc', '-d', str(doc_dir), '--source-path', str(code_dir), 'com.test.pkg', 'com.test.pkg.sub'
        ]

        if verbose == 0:
            expected.insert(1, '-quiet')

        with FakeProcessContext(FakeProcess(expected)):
            with Options(verbose=verbose):
                java_doc(config, [])

    def test_java_doc_quiet(self, tmpdir):
        self._test_java_doc(tmpdir, verbose=0)

    def test_java_doc_not_quiet(self, tmpdir):
        self._test_java_doc(tmpdir, verbose=1)
