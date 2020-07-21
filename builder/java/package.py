"""
This file provides all the support we need around the `jar` tool and packaging stuff.
"""
import re
from pathlib import Path
from typing import Optional, Sequence, Tuple, List

from builder import VERSION
from builder.java.describe import describe_classes
from builder.java.java import _add_verbose_options, java_version, JavaConfiguration, PackageConfiguration
from builder.project import Project
from builder.signing import sign_path
from builder.utils import checked_run, TempTextFile

_class_name_pattern = re.compile(r'^public.*? class ([.\w]+) ')


def _build_jar_options(jar_path: Path, entry_point: Optional[str]) -> List[str]:
    """
    Build a list of the command line options we need to send to the ``jar`` tool.

    :param jar_path: the path representing the jar file that is to be created.
    :param entry_point: the entry point, if the jar is to be executable.
    :return: the list of basic options for the ``jar`` command.
    """
    options = ['--create', '--file', str(jar_path)]

    if entry_point:
        options.append('--main-class')
        options.append(entry_point)

    # noinspection SpellCheckingInspection
    _add_verbose_options(options)

    return options


def _include_directory(options: List[str], directory: Path):
    """
    A helper function for adding a directory inclusion into the set of options
    for the ``jar`` tool.

    :param options: the list of ``jar`` tool options to add to.
    :param directory: the directory to include.
    """
    options.append('-C')
    options.append(str(directory))
    options.append('.')


def _get_packaging_dirs(language_config: JavaConfiguration) -> Tuple[Path, Path, Path, Path]:
    """
    A helper method that gets all our project-sensitive directories from the given
    configuration.  The compiled classes directory must already exist.

    :param language_config: the Java language configuration get the directories from.
    :return: a tuple containing the Java source code directory, the compiled classes
    directory, the source resources directory and the distribution directory.
    """
    code_dir = language_config.code_dir()
    classes_dir = language_config.classes_dir(required=True)
    resources_dir = language_config.resources_dir()

    if language_config.type == 'library':
        distribution_dir = language_config.library_dist_dir(ensure=True)
    else:  # language_config.type == 'application':
        distribution_dir = language_config.application_dist_dir(ensure=True)

    return code_dir, classes_dir, resources_dir, distribution_dir


def _find_entry_point(classes_dir: Path, specified_entry_point: Optional[str]) -> str:
    """
    A function that scans the directory tree rotted at the given directory for
    compiled Java class files that contain the typical Java entry point method.
    An entry point will always be returned; if one cannot be, an exception is
    raised.  If an entry point is specified, it is validated as real.

    :param classes_dir: the directory of compiled classes to scan.
    :param specified_entry_point: an entry point specified by the user.
    :return: the entry point, validated or discovered.
    """
    entry_points = []

    for java_class in describe_classes(classes_dir):
        if java_class.is_entry_point():
            entry_points.append(java_class.name())

    if specified_entry_point:
        if specified_entry_point in entry_points:
            return specified_entry_point
        raise ValueError(f'Specified entry point {specified_entry_point} not found in compiled classes.')

    if len(entry_points) == 0:
        raise ValueError('No entry point found for the application.')

    if len(entry_points) > 1:
        raise ValueError(f'Too many entry points found: {", ".join(entry_points)}.  You will need to specify one.')

    return entry_points[0]


def _create_manifest(version: str, description: str) -> Sequence[str]:
    """
    A function that creates a basic manifest for a jar file based on information
    from a project.

    :param version: the version from a project.
    :param description: the description from a project.
    :return: a sequence of lines that represent the generated manifest.
    """
    result = [
        'Manifest-Version: 1.0',
        f'Created-By: {java_version} (Builder, v{VERSION})',
        f'Specification-Title: {description}',
        f'Specification-Version: {version}',
        f'Implementation-Title: {description}',
        f'Implementation-Version: {version}'
    ]
    return result


def _run_packager(manifest: Sequence[str], entry_point: Optional[str], jar_file: Path, source: Path,
                  resources: Optional[Path], sign_with: Optional[str]):
    """
    A function that executes the ``jar`` tool with appropriate parameters.  Support is
    provided for generating a signature for the generated jar file if a signature
    algorithm name is provided.

    :param manifest: the basic manifest to include in the generated jar file.
    :param entry_point: an optional entry point specified by the user.
    :param jar_file: the path to the jar file to create.
    :param source: the root directory of a sub-tree of files to include in the jar file.
    :param resources: the root directory of a sub-tree of resource files to include in
    the jar file.  This is optional.
    :param sign_with: an option signature name.  If this is specified, a digital
    signature file will be generated for the jar file we create.  A typical value might
    be ``sha256``.
    """
    options = _build_jar_options(jar_file, entry_point)

    with TempTextFile() as temp_file:
        temp_file.write_lines(manifest)
        options.insert(0, 'jar')
        options.append('--manifest')
        options.append(str(temp_file.file_name))

        _include_directory(options, source)

        if resources and resources.is_dir():
            _include_directory(options, resources)

        checked_run(options, 'Packing')

    if sign_with:
        sign_path(sign_with, jar_file, save_to_file=True)


def java_package(project: Project, language_config: JavaConfiguration, task_config: PackageConfiguration):
    """
    A function that will package a collection of compiled classes, and any resource
    files into a jar file with an appropriate manifest.  A jar file of sources may
    also be produced if the configuration so indicates.  The jar files generated may
    optionally be signed as well.

    :param project: the current project information.
    :param language_config: the current Java language configuration information.
    :param task_config: the current ``package`` task configuration information.
    """
    code_dir, classes_dir, resources_dir, output_dir = _get_packaging_dirs(language_config)
    entry_point = None if language_config.type != 'application' else \
        _find_entry_point(classes_dir, task_config.get_entry_point())
    sign_with = task_config.sign_packages_with()
    manifest = _create_manifest(project.version, project.description)
    jar_file = output_dir / f'{project.name}-{project.version}.jar'

    _run_packager(manifest, entry_point, jar_file, classes_dir, resources_dir, sign_with)

    if task_config.package_sources(language_config):
        if not code_dir.is_dir():
            raise ValueError(f'Cannot build a sources archive since {code_dir} does not exist.')

        jar_file = output_dir / f'{project.name}-{project.version}-sources.jar'

        _run_packager(manifest, entry_point, jar_file, code_dir, resources_dir, sign_with)
