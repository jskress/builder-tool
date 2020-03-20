"""
This file provides all the support we need around the jar tool and packaging stuff.
"""
import re
from pathlib import Path
from typing import Any, Dict, Optional, Sequence, Tuple, List

from builder import VERSION
from builder.java.java import _add_verbose_options, java_version, JavaConfiguration, _describe_classes
from builder.project import Project
from builder.signing import sign_path
from builder.utils import checked_run, TempTextFile, get_matching_files

_class_name_pattern = re.compile(r'^public.*? class ([.\w]+) ')


def _build_jar_options(jar_path: Path, entry_point: Optional[str]) -> List[str]:
    options = ['--create', '--file', str(jar_path)]

    if entry_point:
        options.append('--main-class')
        options.append(entry_point)

    # noinspection SpellCheckingInspection
    _add_verbose_options(options, '-Xdiags:verbose')

    return options


def _include_directory(options: List[str], directory: Path):
    options.append('-C')
    options.append(str(directory))
    options.append('.')


def _get_packaging_dirs(language_config: JavaConfiguration) -> Tuple[Path, Path, Path, Path]:
    code_dir = language_config.code_dir()
    classes_dir = language_config.classes_dir(required=True)
    resources_dir = language_config.resources_dir()

    if language_config.type == 'library':
        output_dir = language_config.library_dist_dir(ensure=True)
    else:  # language_config.type == 'application':
        output_dir = language_config.application_dist_dir(ensure=True)

    return code_dir, classes_dir, resources_dir, output_dir


def _group_class_file_names(paths: Sequence[Path]):
    sets = []
    start = 0
    length = 0

    for index, path in enumerate(paths):
        path_length = len(str(path)) + 1
        if length + path_length > 3900:
            sets.append(paths[start:index])
            start = index
            length = 0
        else:
            length = length + path_length

    sets.append(paths[start:])

    return sets


def _split_class_info_output(lines: Sequence[str]) -> Sequence[Sequence[str]]:
    line_sets = []
    start = 1

    for index, line in enumerate(lines):
        if line.startswith('Compiled from '):
            if start < index:
                line_sets.append(lines[start:index])
            start = index + 1

    return line_sets


def _get_entry_point_from(lines: Sequence[str]) -> Optional[str]:
    match = _class_name_pattern.match(lines[0])

    if match:
        for line in lines[1:-1]:
            if line.strip() == 'public static void main(java.lang.String[]);':
                return match.group(1)

    return None


def _find_entry_point(classes_dir: Path, specified_entry_point: Optional[str]) -> str:
    class_files = get_matching_files(classes_dir, '**/*.class', path_like=True)
    class_file_sets = _group_class_file_names(class_files)
    entry_points = []

    for class_file_set in class_file_sets:
        output = _describe_classes(classes_dir, *class_file_set)
        for class_info in _split_class_info_output(output):
            entry_point = _get_entry_point_from(class_info)
            if entry_point:
                entry_points.append(entry_point)

    if specified_entry_point:
        if specified_entry_point in entry_points:
            return specified_entry_point
        raise ValueError(f'Specified entry point {specified_entry_point} not found in compiled classes.')

    if len(entry_points) == 0:
        raise ValueError('No entry point found for the application.')

    if len(entry_points) > 1:
        raise ValueError(f'Too many entry points found: {", ".join(entry_points)}.  You will need to specify one.')

    return entry_points[0]


def _create_manifest(info: Dict[str, Any], description: str) -> Sequence[str]:
    version = info['version']
    result = [
        'Manifest-Version: 1.0',
        f'Created-By: {java_version} (Builder, v{VERSION})',
        f'Specification-Title: {description}',
        f'Specification-Version: {version}'
        f'Implementation-Title: {description}',
        f'Implementation-Version: {version}'
    ]
    return result


def _run_packager(manifest: Sequence[str], entry_point: Optional[str], jar_file: Path, source: Path, resources: Path,
                  sign_with: Optional[str]):
    options = _build_jar_options(jar_file, entry_point)
    temp_file = TempTextFile()
    try:
        temp_file.write_lines(manifest)
        options.insert(0, 'jar')
        options.append('--manifest')
        options.append(temp_file.file_name)

        _include_directory(options, source)

        if resources.is_dir():
            _include_directory(options, resources)

        checked_run(options, 'Packing')
    finally:
        temp_file.remove()

    if sign_with:
        sign_path(sign_with, jar_file, save_to_file=True)


def java_package(project: Project, language_config: JavaConfiguration):
    code_dir, classes_dir, resources_dir, output_dir = _get_packaging_dirs(language_config)
    entry_point = None if language_config.type != 'application' else \
        _find_entry_point(classes_dir, language_config.entry_point())
    sign_with = language_config.sign_packages_with()
    manifest = _create_manifest(project.info, project.description())
    jar_file = output_dir / f'{project.info["name"]}-{project.info["version"]}.jar'

    _run_packager(manifest, entry_point, jar_file, classes_dir, resources_dir, sign_with)

    if language_config.package_sources():
        if not code_dir.is_dir():
            raise ValueError(f'Cannot build a sources archive since {code_dir} does not exist.')

        jar_file = output_dir / f'{project.info["name"]}-{project.info["version"]}-sources.jar'

        _run_packager(manifest, entry_point, jar_file, code_dir, resources_dir, sign_with)
