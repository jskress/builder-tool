"""
This library contains all the build tasks and support code for Java.
"""
from pathlib import Path
from typing import Sequence, Optional, List

from builder.utils import checked_run, global_options, remove_directory


class JavaConfiguration(object):
    def __init__(self):
        self.type = 'library'
        self.source = 'src'
        self.build = 'build'
        self.code_source = 'code'
        self.code_resources = 'resources'
        self.code_target = 'code/classes'
        self.tests_source = 'tests'
        self.tests_resources = 'test_resources'
        self.tests_target = 'tests/classes'
        self.dist = 'dist'
        self.app_target = 'app'
        self.lib_target = 'lib'
        self.packaging = {}

        self._project = global_options.project()
        self._code_dir = None
        self._resources_dir = None
        self._tests_dir = None
        self._test_resources_dir = None
        self._build_dir = None
        self._classes_dir = None
        self._dist_dir = None
        self._lib_dir = None
        self._app_dir = None

    def code_dir(self, required: bool = False, ensure: bool = False) -> Path:
        if not self._code_dir:
            self._code_dir = self._project.project_dir(
                Path(self.source) / Path(self.code_source), required, ensure
            )
        return self._code_dir

    def resources_dir(self, required: bool = False, ensure: bool = False) -> Path:
        if not self._resources_dir:
            self._resources_dir = self._project.project_dir(
                Path(self.source) / Path(self.code_resources), required, ensure
            )
        return self._resources_dir

    def tests_dir(self, required: bool = False, ensure: bool = False) -> Path:
        if not self._tests_dir:
            self._tests_dir = self._project.project_dir(
                Path(self.source) / Path(self.tests_source), required, ensure
            )
        return self._tests_dir

    def test_resources_dir(self, required: bool = False, ensure: bool = False) -> Path:
        if not self._test_resources_dir:
            self._resources_dir = self._project.project_dir(
                Path(self.source) / Path(self.tests_resources), required, ensure
            )
        return self._test_resources_dir

    def build_dir(self, required: bool = False, ensure: bool = False) -> Path:
        if not self._build_dir:
            self._build_dir = self._project.project_dir(Path(self.build), required, ensure)
        return self._build_dir

    def classes_dir(self, required: bool = False, ensure: bool = False) -> Path:
        if not self._classes_dir:
            self._classes_dir = self._project.project_dir(
                Path(self.build) / Path(self.code_target), required, ensure
            )
        return self._classes_dir

    def dist_dir(self, required: bool = False, ensure: bool = False) -> Path:
        if not self._dist_dir:
            self._dist_dir = self._project.project_dir(Path(self.dist), required, ensure)
        return self._dist_dir

    def library_dist_dir(self, required: bool = False, ensure: bool = False) -> Path:
        if not self._lib_dir:
            self._lib_dir = self._project.project_dir(
                Path(self.dist) / Path(self.lib_target), required, ensure
            )
        return self._lib_dir

    def application_dist_dir(self, required: bool = False, ensure: bool = False) -> Path:
        if not self._app_dir:
            self._app_dir = self._project.project_dir(
                Path(self.dist) / Path(self.app_target), required, ensure
            )
        return self._app_dir

    def entry_point(self) -> Optional[str]:
        return self.packaging['entry_point'] if 'entry_point' in self.packaging else None

    def package_sources(self) -> bool:
        if 'sources' in self.packaging:
            return self.packaging['sources']
        return self.type == 'library'

    def sign_packages_with(self) -> Optional[str]:
        return self.packaging['sign_with'] if 'sign_with' in self.packaging else None


def get_javac_version() -> Optional[str]:
    try:
        process = checked_run(['javac', '-version'], 'Javac version check', capture=True)
        version = process.stdout.decode().split(' ')[1].strip()
        return version
    except FileNotFoundError:
        return None


def java_clean(language_config: JavaConfiguration):
    remove_directory(language_config.build_dir())
    remove_directory(language_config.dist_dir())


def _add_verbose_options(options: List[str], *extras):
    if global_options.verbose() > 1:
        for extra in extras:
            options.insert(0, extra)
        if global_options.verbose() > 2:
            options.insert(0, '-verbose')


def _describe_classes(classes_dir: Path, *paths: Path) -> Sequence[str]:
    # noinspection SpellCheckingInspection
    options = ['javap', '-public']

    _add_verbose_options(options)

    for path in paths:
        options.append(str(path))

    process = checked_run(options, 'Class description', capture=True, cwd=classes_dir)
    lines = process.stdout.decode().split('\n')

    return lines


# noinspection PyUnusedLocal
def java_test(project, language_config: JavaConfiguration, task_config):
    pass


# noinspection PyUnusedLocal
def java_doc(language_config: JavaConfiguration, task_config):
    pass


java_version = get_javac_version()
