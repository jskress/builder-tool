"""
This library contains all the build tasks and support code for Java.
"""
from pathlib import Path
from typing import Optional, List

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
        self.test_resources = 'test_resources'
        self.tests_target = 'tests/classes'
        self.dist = 'dist'
        self.app_target = 'app'
        self.lib_target = 'lib'

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
        """
        A function that returns the path to where Java source files should be found.
        The path returned is absolute, the root of which comes from the current project.

        :param required: a flag indicating whether we should fail if the directory
        does not exist.
        :param ensure: a flag indicating whether the directory should be created if
        it doesn't exist.
        :return: the path to the Java source files of the project.
        """
        if not self._code_dir:
            self._code_dir = self._project.project_dir(
                Path(self.source) / Path(self.code_source), required, ensure
            )
        return self._code_dir

    def resources_dir(self, required: bool = False, ensure: bool = False) -> Path:
        """
        A function that returns the path to where resources files for the code should
        be found.  The path returned is absolute, the root of which comes from the
        current project.

        :param required: a flag indicating whether we should fail if the directory
        does not exist.
        :param ensure: a flag indicating whether the directory should be created if
        it doesn't exist.
        :return: the path to the code resource files of the project.
        """
        if not self._resources_dir:
            self._resources_dir = self._project.project_dir(
                Path(self.source) / Path(self.code_resources), required, ensure
            )
        return self._resources_dir

    def tests_dir(self, required: bool = False, ensure: bool = False) -> Path:
        """
        A function that returns the path to where test source files should be found.
        The path returned is absolute, the root of which comes from the current project.

        :param required: a flag indicating whether we should fail if the directory
        does not exist.
        :param ensure: a flag indicating whether the directory should be created if
        it doesn't exist.
        :return: the path to the test source files of the project.
        """
        if not self._tests_dir:
            self._tests_dir = self._project.project_dir(
                Path(self.source) / Path(self.tests_source), required, ensure
            )
        return self._tests_dir

    def test_resources_dir(self, required: bool = False, ensure: bool = False) -> Path:
        """
        A function that returns the path to where resources files for tests should
        be found.  The path returned is absolute, the root of which comes from the
        current project.

        :param required: a flag indicating whether we should fail if the directory
        does not exist.
        :param ensure: a flag indicating whether the directory should be created if
        it doesn't exist.
        :return: the path to the test resource files of the project.
        """
        if not self._test_resources_dir:
            self._test_resources_dir = self._project.project_dir(
                Path(self.source) / Path(self.test_resources), required, ensure
            )
        return self._test_resources_dir

    def build_dir(self, required: bool = False, ensure: bool = False) -> Path:
        """
        A function that returns the path to where build artifacts will be written.
        These include compilation, documentation and testing artifacts.  The path
        returned is absolute, the root of which comes from the current project.

        :param required: a flag indicating whether we should fail if the directory
        does not exist.
        :param ensure: a flag indicating whether the directory should be created if
        it doesn't exist.
        :return: the path to where build artifacts will be written.
        """
        if not self._build_dir:
            self._build_dir = self._project.project_dir(Path(self.build), required, ensure)
        return self._build_dir

    def classes_dir(self, required: bool = False, ensure: bool = False) -> Path:
        """
        A function that returns the path to where compiled files for the code should
        be written or found.  The path returned is absolute, the root of which comes
        from the current project.

        :param required: a flag indicating whether we should fail if the directory
        does not exist.
        :param ensure: a flag indicating whether the directory should be created if
        it doesn't exist.
        :return: the path to where compiled code files will be written..
        """
        if not self._classes_dir:
            self._classes_dir = self._project.project_dir(
                Path(self.build) / Path(self.code_target), required, ensure
            )
        return self._classes_dir

    def dist_dir(self, required: bool = False, ensure: bool = False) -> Path:
        """
        A function that returns the path to where distribution artifacts will be
        written.  These include packaging artifacts.  The path returned is
        absolute, the root of which comes from the current project.

        :param required: a flag indicating whether we should fail if the directory
        does not exist.
        :param ensure: a flag indicating whether the directory should be created if
        it doesn't exist.
        :return: the path to where distribution artifacts will be written.
        """
        if not self._dist_dir:
            self._dist_dir = self._project.project_dir(Path(self.dist), required, ensure)
        return self._dist_dir

    def library_dist_dir(self, required: bool = False, ensure: bool = False) -> Path:
        """
        A function that returns the path to where library artifacts will be
        written.  These include packaging artifacts.  The path returned is
        absolute, the root of which comes from the current project.

        :param required: a flag indicating whether we should fail if the directory
        does not exist.
        :param ensure: a flag indicating whether the directory should be created if
        it doesn't exist.
        :return: the path to where library artifacts will be written.
        """
        if not self._lib_dir:
            self._lib_dir = self._project.project_dir(
                Path(self.dist) / Path(self.lib_target), required, ensure
            )
        return self._lib_dir

    def application_dist_dir(self, required: bool = False, ensure: bool = False) -> Path:
        """
        A function that returns the path to where application artifacts will be
        written.  These include packaging artifacts.  The path returned is
        absolute, the root of which comes from the current project.

        :param required: a flag indicating whether we should fail if the directory
        does not exist.
        :param ensure: a flag indicating whether the directory should be created if
        it doesn't exist.
        :return: the path to where application artifacts will be written.
        """
        if not self._app_dir:
            self._app_dir = self._project.project_dir(
                Path(self.dist) / Path(self.app_target), required, ensure
            )
        return self._app_dir


class PackageConfiguration(object):
    def __init__(self):
        self.entry_point = None
        self.sources = None
        self.sign_with = None

    def get_entry_point(self) -> Optional[str]:
        """
        A function that returns the entry point (class name) from the project
        file, if one was specified.

        :return: the entry point class name for the project or None, if one was
        not configured.
        """
        return self.entry_point

    def package_sources(self, language_config: JavaConfiguration) -> bool:
        """
        A function that returns whether the packaging task should package up the
        project source as well as the compiled code.  If this is not configured
        in the project file, this will return ``True`` for library projects and
        ``False`` for application projects.

        :return: whether project sources should be packaged in their own jar along
        side the compiled code jar during the packaging task.
        """
        return language_config.type == 'library' if self.sources is None else self.sources

    def sign_packages_with(self) -> Optional[str]:
        """
        A function that returns the name of a digital signature to apply to jar
        files created by the packaging task.  If this returns ``None``, no signature
        file will be created.  Otherwise it must be the name of a known (to Python
        signature algorithm like ``sha256``.

        :return: the name of a digital signature algorithm to use in signing any
        jar files the packaging task generates or ``None``.
        """
        return self.sign_with


def get_javac_version() -> Optional[str]:
    """
    A function that shells out to the ``javac`` tool to determine the installed
    version.  We use ``javac`` as we want to make sure that the JDK is installed
    and not just the JRE.

    :return: the version of the JDK that's installed or ``None`` if it could not
    be found.
    """
    try:
        process = checked_run(['javac', '-version'], 'Javac version check', capture=True)
        version = process.stdout.decode().split(' ')[1].strip()
        return version
    except FileNotFoundError:
        return None


def java_clean(language_config: JavaConfiguration):
    """
    A function that provides the implementation of the ``clean`` task for the Java
    language.  It deletes the configured build and distribution directory trees,
    if they exist.  It is not an error if either of the directories do not exist.

    :param language_config: the configured Java language information.
    """
    remove_directory(language_config.build_dir())
    remove_directory(language_config.dist_dir())


def _add_verbose_options(options: List[str], *extras):
    """
    A function for adding verbose options to the specified array of (ostensibly)
    command line options.  Verbosity must be at a 2 or higher for the extras to
    be included and 3 or higher for the general Java ``-verbose`` to be included.

    :param options: the options list to add verbose options to.
    :param extras: any extra verbose-style options one of the Java command line
    tools will respond to.
    """
    if global_options.verbose() > 1:
        for extra in reversed(extras):
            options.insert(0, extra)
        if global_options.verbose() > 2:
            options.insert(0, '-verbose')


# noinspection PyUnusedLocal
def java_test(language_config: JavaConfiguration):
    """
    A function that provides the implementation of the ``test`` task for the Java
    language.  It will build and execute any tests found in the location specified
    by the Java language configuration.

    **Note:** This is not currently implemented.

    :param language_config: the configured Java language information.
    """
    pass


# noinspection PyUnusedLocal
def java_doc(language_config: JavaConfiguration):
    """
    A function that provides the implementation of the ``doc`` task for the Java
    language.  It will build Java documentation for all the source found in the
    location specified by the Java language configuration.

    **Note:** This is not currently implemented.

    :param language_config: the configured Java language information.
    """
    pass


java_version = get_javac_version()
