"""
This file provides all the support we need around the `jar` tool and packaging stuff.
"""
import re
import shutil
import tempfile
from pathlib import Path
from typing import Optional, Sequence, Tuple, List, Dict, Union, Callable
from zipfile import ZipFile, ZipInfo

from builder import VERSION
from builder.models import DependencyPathSet
from builder.java.describe import describe_classes
from builder.java.java import _add_verbose_options, java_version, JavaConfiguration, PackageConfiguration, \
    java_version_number
from builder.java.modules import ModuleData, Component, Variant, API_ELEMENTS, RUNTIME_ELEMENTS, JAVADOC_ELEMENTS, \
    SOURCE_ELEMENTS
from builder.signing import sign_path, sign_path_to_files
from builder.utils import checked_run, TempTextFile, global_options

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


def _get_packaging_dirs(language_config: JavaConfiguration) -> Tuple[Path, Path, Path, Path, Path]:
    """
    A helper method that gets all our project-sensitive directories from the given
    configuration.  The compiled classes directory must already exist.

    :param language_config: the Java language configuration get the directories from.
    :return: a tuple containing the Java source code directory, the compiled classes
    directory, the JavaDoc directory, the source resources directory and the distribution
    directory.
    """
    code_dir = language_config.code_dir()
    classes_dir = language_config.classes_dir(required=True)
    doc_dir = language_config.doc_dir()
    resources_dir = language_config.resources_dir()

    if language_config.type == 'library':
        distribution_dir = language_config.library_dist_dir(ensure=True)
    else:  # language_config.type == 'application':
        distribution_dir = language_config.application_dist_dir(ensure=True)

    return code_dir, classes_dir, doc_dir, resources_dir, distribution_dir


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


def _create_module_data() -> ModuleData:
    """
    A function for creating the basic module data for what we're packaging.

    :return: the created and initialized module data.
    """
    project = global_options.project()
    component = Component(project.name, project.name, project.version)
    module_data = ModuleData.for_component(component)

    return module_data


def _set_file_attributes(variant: Variant, category: str, usage: str, docs_type: Optional[str]):
    """
    A helper function for setting the appropriate attributes on a variant.

    :param variant: the variant to set the attributes on.
    :param category: the value for the category attribute.
    :param usage: the value for the usage attribute.
    :param docs_type: the type of documentation (sources or javadoc) or ``None`` for code.
    """
    variant.set_attr('category', category)
    variant.set_attr('dependency.bundling', 'external')

    if docs_type:
        # noinspection SpellCheckingInspection
        variant.set_attr('docstype', docs_type)
    else:
        variant.set_attr('jvm.version', java_version_number)
        # noinspection SpellCheckingInspection
        variant.set_attr('libraryelements', 'jar')

    variant.set_attr('usage', f'java-{usage}')


def _add_variant(module_data: ModuleData, name: str, jar_file: Path, signatures: Dict[str, str], category: str,
                 usage: str, docs_type: Optional[str], dependencies: List[DependencyPathSet]):
    """
    A function to add a new variant to module data.

    :param module_data: the module data to add the new variant to.
    :param name: the name of the variant to add.
    :param jar_file: the path to the jar that is the main file for the variant.
    :param signatures: the digital signatures for the path.
    :param category: the value for the category attribute.
    :param usage: the value for the usage attribute.
    :param docs_type: the type of documentation (sources or javadoc) or ``None`` for code.
    :param dependencies: the set of dependencies to account for.
    """
    variant = module_data.add_variant(name)

    _set_file_attributes(variant, category, usage, docs_type)

    variant.add_path(jar_file, signatures)

    for path_set in dependencies:
        if not path_set.dependency.transient:
            variant.add_dependency(path_set.dependency)


def _run_packager(manifest: Optional[Sequence[str]], entry_point: Optional[str], jar_file: Path, source: Path,
                  resources: Optional[Path]) -> Dict[str, str]:
    """
    A function that executes the ``jar`` tool with appropriate parameters.  Once a jar
    file is created, it is signed with all known digital signatures.  A map of signature
    algorithm name to digital signature is returned for the generated jar file.

    :param manifest: the basic manifest to include in the generated jar file.
    :param entry_point: an optional entry point specified by the user.
    :param jar_file: the path to the jar file to create.
    :param source: the root directory of a sub-tree of files to include in the jar file.
    :param resources: the root directory of a sub-tree of resource files to include in
    the jar file.  This is optional.
    :return: the dictionary of digital signatures.
    """
    options = _build_jar_options(jar_file, entry_point)

    with TempTextFile() as temp_file:
        if manifest:
            temp_file.write_lines(manifest)
            options.append('--manifest')
            options.append(str(temp_file.file_name))

        options.insert(0, 'jar')

        _include_directory(options, source)

        if resources and resources.is_dir():
            _include_directory(options, resources)

        checked_run(options, 'Packing')

    return sign_path(jar_file)


_current_language_config: Optional[JavaConfiguration] = None
_current_task_config: Optional[PackageConfiguration] = None
_current_source_root: Optional[Path] = None


def _store_file(source: Union[Path, ZipInfo], target_path: Path, read_source: Callable[[], bytes],
                copy_source: Callable[[], str]):
    """
    A helper function that properly stores an individual file.  If the target does
    not exist, the source is simply put in place.  If the target exists, it is
    checked to see if it is merge-able and merged if so.  It is silently skipped if
    the source and target match.  Otherwise, an exception is produced.

    :param source: the relative ``Path`` or a ``ZipInfo`` which is the source.
    :param target_path: the path where the file data is to be stored.
    :param read_source: a function that produces the content of the source as bytes.
    :param copy_source: a function that does a straight copy of the source to the target.
    """
    if _current_task_config.should_include(source):
        if target_path.exists():
            if _current_task_config.can_merge(source):
                data = read_source()

                if len(data) > 0:
                    ch = data[-1]
                    if ch != b'\r' and ch != b'\n':
                        data = data + b'\n'

                target_path.write_bytes(data + target_path.read_bytes())
            else:
                if read_source() != target_path.read_bytes():
                    text = str(source) if isinstance(source, Path) else source.filename
                    raise ValueError(
                        f'Cannot package {text}, its contents differ from a previous entry with the '
                        'same name.'
                    )
        else:
            copy_source()


def _extract_archive(archive: Path, target: Path):
    """
    A function that extracts the contents of an archive (zip/jar) to the specified
    directory.

    :param archive: the zip/jar archive to extract.
    :param target: the target directory to write entries to.
    """
    with ZipFile(archive) as zip_file:
        for entry in zip_file.infolist():
            if entry.is_dir():
                zip_file.extract(entry, target)
            else:
                target_path = target / entry.filename

                _store_file(
                    entry, target_path,
                    lambda: zip_file.read(entry),
                    lambda: zip_file.extract(entry, target)
                )


def _copy_local_file(source: str, target: str):
    """
    A function to copy a file as part of directory tree copying.  We wrap the typical
    ``shutil.copy2()`` function to properly handle file collisions.

    :param source: the source file to copy.
    :param target: the target file to write.
    """
    source_path = Path(source)
    relative_path = source_path.relative_to(_current_source_root)
    target_path = Path(target)

    _store_file(
        relative_path, target_path, source_path.read_bytes,
        lambda: shutil.copy2(source, target)
    )


def _copy_tree(source: Path, target: Path):
    """
    A helper function to copy a full directory tree from one place to another.

    :param source: the root of the source tree to copy.
    :param target: the root to copy the tree under.
    """
    global _current_source_root

    try:
        _current_source_root = source

        shutil.copytree(source, target, copy_function=_copy_local_file, dirs_exist_ok=True)
    finally:
        _current_source_root = None


def _build_primary_jar(language_config: JavaConfiguration, task_config: PackageConfiguration,
                       dependencies: List[DependencyPathSet], classes_dir: Path,
                       resources_dir: Path, jar_file: Path) -> Dict[str, str]:
    """
    A function that builds a temporary directory structure representing the desired
    contents for a jar file and then creates it.  The directory structure is populated
    by copying local files and expanding class path dependency jar files.  File collisions
    will be handled as follows:

    - If the source and target files are the same, the duplicate is ignored.
    - If the file may be merged (like service definitions), they are merged.
    - Otherwise, an error is produced.

    :param language_config: the current Java language configuration information.
    :param task_config: the current ``package`` task configuration information.
    :param dependencies: the set of dependencies to account for.
    :param classes_dir: the directory containing the current project's compiled classes.
    :param resources_dir: the directory containing the current project's resources.
    :return: the dictionary of digital signatures for the jar we created.
    """
    global _current_language_config, _current_task_config, _current_source_root

    project = global_options.project()
    manifest = _create_manifest(project.version, project.description)
    entry_point = None if language_config.type != 'application' else \
        _find_entry_point(classes_dir, task_config.get_entry_point())

    # Build the jar contents from all our sources, handling duplicates as appropriate
    with tempfile.TemporaryDirectory(dir=language_config.build_dir(ensure=True)) as temp_dir:
        target_dir = Path(temp_dir) / 'jar_content'

        try:
            _current_language_config = language_config
            _current_task_config = task_config

            _copy_tree(classes_dir, target_dir)
            _copy_tree(resources_dir, target_dir)

            if task_config.include_dependencies(language_config):
                for path_set in dependencies:
                    if path_set.primary_path.is_dir():
                        _copy_tree(path_set.primary_path, target_dir)
                    elif path_set.primary_path.is_file():
                        _extract_archive(path_set.primary_path, target_dir)
        finally:
            _current_language_config = None
            _current_task_config = None

        return _run_packager(manifest, entry_point, jar_file, target_dir, None)


def java_package(language_config: JavaConfiguration, task_config: PackageConfiguration,
                 dependencies: List[DependencyPathSet]):
    """
    A function that will package a collection of compiled classes, and any resource
    files into a jar file with an appropriate manifest.  A jar file of sources may
    also be produced if the configuration so indicates.  The jar files generated may
    optionally be signed as well.

    :param language_config: the current Java language configuration information.
    :param task_config: the current ``package`` task configuration information.
    :param dependencies: the set of dependencies to account for.
    """
    project = global_options.project()
    code_dir, classes_dir, doc_dir, resources_dir, output_dir = _get_packaging_dirs(language_config)
    output_dir = output_dir / project.name
    jar_file = output_dir / f'{project.name}-{project.version}.jar'
    module_data = _create_module_data()

    output_dir.mkdir(parents=True, exist_ok=True)

    signatures = _build_primary_jar(language_config, task_config, dependencies, classes_dir, resources_dir, jar_file)

    _add_variant(module_data, API_ELEMENTS, jar_file, signatures, "library", "api", None, dependencies)
    _add_variant(module_data, RUNTIME_ELEMENTS, jar_file, signatures, "library", "runtime", None, dependencies)

    if task_config.package_doc(language_config):
        if not doc_dir.is_dir():
            raise ValueError(f'Cannot build a JavaDoc archive since {doc_dir} does not exist.')

        jar_file = output_dir / f'{project.name}-{project.version}-javadoc.jar'

        signatures = _run_packager(None, None, jar_file, doc_dir, None)

        _add_variant(module_data, JAVADOC_ELEMENTS, jar_file, signatures, "documentation", "runtime", 'javadoc', [])

    if task_config.package_sources(language_config):
        if not code_dir.is_dir():
            raise ValueError(f'Cannot build a sources archive since {code_dir} does not exist.')

        jar_file = output_dir / f'{project.name}-{project.version}-sources.jar'

        signatures = _run_packager(None, None, jar_file, code_dir, resources_dir)

        _add_variant(module_data, SOURCE_ELEMENTS, jar_file, signatures, "documentation", "runtime", 'sources', [])

    module_path = output_dir / f'{project.name}-{project.version}.module'

    module_data.write(module_path)

    sign_path_to_files(module_path)
