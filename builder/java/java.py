"""
This library contains all the build tasks and support code for Java.
"""
import fnmatch
import os
import re
from pathlib import Path
from typing import Optional, List, Tuple, Union, Dict
from zipfile import ZipInfo

from builder.models import DependencyPathSet, Dependency, RemoteResolver
from builder.utils import checked_run, global_options, remove_directory


class JavaConfiguration(object):
    def __init__(self):
        self.type = 'library'
        self.source = 'src'
        self.build = 'build'
        self.code_source = 'code'
        self.code_resources = 'resources'
        self.code_target = 'code/classes'
        self.code_doc = 'code/javadoc'
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
        self._test_target_dir = None
        self._doc_dir = None
        self._dist_dir = None
        self._lib_dir = None
        self._app_dir = None

    @property
    def project(self):
        """
        A read-only property that returns the project we were constructed with.

        :return: our owning project.
        """
        return self._project

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
        :return: the path to where compiled code files will be written.
        """
        if not self._classes_dir:
            self._classes_dir = self._project.project_dir(
                Path(self.build) / Path(self.code_target), required, ensure
            )
        return self._classes_dir

    def tests_classes_dir(self, required: bool = False, ensure: bool = False) -> Path:
        """
        A function that returns the path to where compiled files for tests should be
        written or found.  The path returned is absolute, the root of which comes
        from the current project.

        :param required: a flag indicating whether we should fail if the directory
        does not exist.
        :param ensure: a flag indicating whether the directory should be created if
        it doesn't exist.
        :return: the path to where compiled tests will be written.
        """
        if not self._test_target_dir:
            self._test_target_dir = self._project.project_dir(
                Path(self.build) / Path(self.tests_target), required, ensure
            )
        return self._test_target_dir

    def doc_dir(self, required: bool = False, ensure: bool = False) -> Path:
        """
        A function that returns the path to where JavaDoc files for the code should
        be written or found.  The path returned is absolute, the root of which comes
        from the current project.

        :param required: a flag indicating whether we should fail if the directory
        does not exist.
        :param ensure: a flag indicating whether the directory should be created if
        it doesn't exist.
        :return: the path to where JavaDoc files will be written.
        """
        if not self._doc_dir:
            self._doc_dir = self._project.project_dir(
                Path(self.build) / Path(self.code_doc), required, ensure
            )
        return self._doc_dir

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


class TestingConfiguration(object):
    def __init__(self):
        self.test_executor = 'junit5'
        self.coverage_agent = 'jacoco'
        self.coverage_reporter = 'jacoco-cli'
        self.test_reports = None
        self.coverage_reports = 'reports/coverage'
        self.no_tests = False

        self._test_reports_dir = None
        self._coverage_reports_dir = None

    def test_reports_dir(self, config: JavaConfiguration, required: bool = False, ensure: bool = False) -> Path:
        """
        A function that returns the path to where execution reports for running tests
        should be written.  The path returned is absolute, the root of which comes the
        current project.

        :param config: the Java language configuration to refer to.
        :param required: a flag indicating whether we should fail if the directory
        does not exist.
        :param ensure: a flag indicating whether the directory should be created if
        it doesn't exist.
        :return: the path to where test execution report files will be written.
        """
        if not self._test_reports_dir and self.test_reports:
            self._test_reports_dir = config.project.project_dir(
                Path(config.build) / Path(self.test_reports), required, ensure
            )
        return self._test_reports_dir

    def coverage_reports_dir(self, config: JavaConfiguration, required: bool = False, ensure: bool = False) -> Path:
        """
        A function that returns the path to where coverage reports from running tests
        should be written or found.  The path returned is absolute, the root of which
        comes the current project.

        :param config: the Java language configuration to refer to.
        :param required: a flag indicating whether we should fail if the directory
        does not exist.
        :param ensure: a flag indicating whether the directory should be created if
        it doesn't exist.
        :return: the path to where coverage files and reports will be written.
        """
        if not self._coverage_reports_dir and self.coverage_reports:
            self._coverage_reports_dir = config.project.project_dir(
                Path(config.build) / Path(self.coverage_reports), required, ensure
            )
        return self._coverage_reports_dir


class PackageConfiguration(object):
    def __init__(self):
        self.entry_point = None
        self.fat_jar = None
        self.include: List[Dict[str, str]] = []
        self.exclude: List[str] = []
        self.duplicates: Dict[str, str] = {}
        self.sources = None
        self.doc = None

        self._extra_content: List[Tuple[Path, Optional[Path]]] = []
        self._path_dispositions: List[Tuple[re.Pattern, str]] = []

    def get_entry_point(self) -> Optional[str]:
        """
        A function that returns the entry point (class name) from the project
        file, if one was specified.

        :return: the entry point class name for the project or None, if one was
        not configured.
        """
        return self.entry_point

    def include_dependencies(self, config: JavaConfiguration) -> bool:
        """
        A function that returns whether the packaging task should package up all
        the dependencies into the primary jar file.  If this is not configured
        in the project file, this will return ``True`` for application projects
        and ``False`` for library projects.

        :param config: the language level configuration.
        :return: whether project sources should be packaged in their own jar along
        side the compiled code jar during the packaging task.
        """
        return config.type == 'application' if self.fat_jar is None else self.fat_jar

    def get_extra_content(self, config: JavaConfiguration) -> List[Tuple[Path, Optional[Path]]]:
        """
        A function that returns any declared extra content that should be included in
        the packaged jar file.  Each tuple in the list returned will have two elements.
        The first element may be a directory or file.  If it is a directory, then that
        directory's content will be included in the jar file being built.  If it is a
        jar or zip file, it's contents will be included in the jar file being built.
        Any other file will be included as-is.  The second element is an optional
        relative path the resulting jar entries should be relative to.  If this is
        ``None`` then each element will be relative to the root in the jar file.

        :param config: the language level configuration.
        :return: a list of tuples representing extra content to include.
        """
        if len(self._extra_content) == 0:
            # If this is our first time, then create all our extra content path tuples.
            for include in self.include:
                source = config.project.project_dir(include['source'])
                under = None

                if 'under' in include:
                    under = Path(include['under'])

                self._extra_content.append((source, under))

        return self._extra_content

    def _build_path_dispositions(self):
        """
        A helper function for converting our raw file disposition related configuration
        information into the patterns and actions we will act upon.
        """
        manifest_files = '|'.join(['license.txt', 'license', 'notice'])

        self._add_path_dispositions(r'~(?i:meta-inf/manifest.mf)\Z', 'exclude')

        for text in self.exclude:
            self._add_path_dispositions(text, 'exclude')

        self._add_path_dispositions(r'~(?i:meta-inf/(?:' + manifest_files + r'))\Z', 'merge')
        self._add_path_dispositions(
            r'~(?i:meta-inf)/services/[a-zA-Z_$][a-zA-Z\d_$]*(?:\.[a-zA-Z_$][a-zA-Z\d_$]*)*\Z', 'merge'
        )

        for text, action in self.duplicates.items():
            self._add_path_dispositions(text, action)

    def _add_path_dispositions(self, text: str, action: str):
        """
        A helper method for converting and storing a file pattern along with the
        action to take when a path matches it.

        :param text: the string pattern to convert.
        :param action: the action to take on matching paths.
        """
        if text[0] == '~':
            pattern = re.compile(text[1:])
        else:
            pattern = re.compile(fnmatch.translate(text))

        self._path_dispositions.append((pattern, action))

    def should_include(self, relative_path: Union[Path, ZipInfo]) -> bool:
        """
        A function that takes a relative path or archive entry and returns whether
        it should be included in a packing operation.

        :param relative_path: the relative ``Path`` or a ``ZipInfo``.
        :return: ``True`` if the path/entry should be included in the archive being
        built or ``False`` if not.
        """
        if len(self._path_dispositions) == 0:
            # If this is our first time, then create all our regular expressions.
            self._build_path_dispositions()

        return self.get_path_disposition(relative_path) != 'exclude'

    def get_path_disposition(self, relative_path: Union[Path, ZipInfo]) -> Optional[str]:
        """
        A function that determines the action that should be taken for a relative path.
        The action returned will be one of ``exclude``, ``merge``, ``first``, ``last``,
        ``newest``, ``oldest``, ``largest``, ``smallest`` or ``None``.  With the exception
        of ``exclude`` all actions apply in the case where a file is encountered more than
        once while building a jar.

        :param relative_path: the relative ``Path`` or a ``ZipInfo``.
        :return: the disposition for the path or ``None``.
        """
        if len(self._path_dispositions) == 0:
            # If this is our first time, then create all our regular expressions.
            self._build_path_dispositions()

        text = str(relative_path) if isinstance(relative_path, Path) else relative_path.filename

        for pattern, action in self._path_dispositions:
            if pattern.match(text):
                return action

        return None

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

    def package_doc(self, language_config: JavaConfiguration) -> bool:
        """
        A function that returns whether the packaging task should package up the
        project's JavaDoc as well as the compiled code.  If this is not configured
        in the project file, this will return ``True`` for library projects and
        ``False`` for application projects.

        :return: whether project JavaDoc should be packaged in their own jar along
        side the compiled code jar during the packaging task.
        """
        return language_config.type == 'library' if self.doc is None else self.doc


def get_javac_version() -> Tuple[Optional[str], Optional[int]]:
    """
    A function that shells out to the ``javac`` tool to determine the installed
    version.  We use ``javac`` as we want to make sure that the JDK is installed
    and not just the JRE.

    :return: a tuple with the version of the JDK that's installed as string and as
    a major number.  Both tuple entries will be ``None`` if a version  could not be
    determined..
    """
    try:
        process = checked_run(['javac', '-version'], 'Javac version check', capture=True)
        version = process.stdout.decode().split(' ')[1].strip()
        return version, int(version.split(".")[0])
    except FileNotFoundError:
        return None, None


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


def add_class_path(options: List[str], path_sets: List[DependencyPathSet], paths: List[Path] = None):
    """
    A function for adding the given set of dependency path sets to the specified
    array of (ostensibly) command line options.

    :param options: the options list to add verbose options to.
    :param path_sets: the list of path sets to make a class path option out of.
    :param paths: an optional list of paths to include in the class path.
    """
    if path_sets or paths:
        path_strings = [] if paths is None else [str(path) for path in paths]
        path_strings.extend([str(path_set.primary_path) for path_set in path_sets])
        options.append('--class-path')
        options.append(os.pathsep.join(path_strings))


def create_remote_resolver(group: Optional[str], name: str, version: Optional[str] = None) -> RemoteResolver:
    """
    A function that creates a remote resolver based on the given information.

    :param group: the group name to use.  If this is ``None``, then ``name`` will be used.
    :param name: the name to use.
    :param version: the version to use.
    :return: an appropriately configured remote resolver.
    """
    group = group if group else name
    group = group.replace('.', '/')
    directory_url = f'https://repo1.maven.org/maven2/{group}/{name}'

    if version:
        directory_url = f'{directory_url}/{version}'

    return RemoteResolver(directory_url, Path(name))


def build_names(dependency: Dependency, version_in_url: bool = True) -> Tuple[RemoteResolver, str, str]:
    """
    A function to build directory and file names based on the given dependency..

    :param dependency: the dependency to create the file container for.
    :param version_in_url: a flag noting whether the dependency version should be included
    in the URL we build.
    :return: a tuple containing an appropriate remote resolver, a classified base file name
    and a base file name.
    """
    resolver = create_remote_resolver(
        dependency.group, dependency.name, dependency.version if version_in_url else None
    )
    name = dependency.name
    version = dependency.version
    classifier = dependency.classifier
    base_name = f'{name}-{version}'
    classified_name = f'{base_name}-{classifier}' if classifier else base_name

    return resolver, classified_name, base_name


java_version, java_version_number = get_javac_version()
