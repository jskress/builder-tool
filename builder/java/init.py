"""
This file provides support for initializing projects for Java.
"""
from pathlib import Path

from builder.java.java import JavaConfiguration, java_version_number
from builder.jetbrains.intellij import IJProject, IJImlFile
from builder.project import Project
from builder.utils import global_options


def init_java_project(language_config: JavaConfiguration):
    project = global_options.project()
    ij_project = IJProject(project.directory)

    _create_project_yaml(project)
    create_ij_project_file(language_config, ij_project)
    _create_directory_tree(language_config)
    _create_misc_xml(ij_project)
    _create_modules_xml(ij_project, project.name)

    ij_project.save()


def _create_project_yaml(project: Project):
    title = global_options.var('title')
    version = global_options.var('version') or '1.0.0'
    lines = [
        f'# This is the project file for the ${project.name} project.',
        '',
        'info:',
        f'    name: {project.name}']

    if title:
        lines.append(f'    title: {title}')

    lines.append(f'    version: {version}')
    lines.append(f'    languages: java')
    lines.append('')

    path = project.directory / 'project.yaml'

    path.write_text('\n'.join(lines), encoding='utf-8')


def create_ij_project_file(config: JavaConfiguration, ij_project: IJProject):
    _ = ij_project.iml_file(
        source=f'{config.source}/{config.code_source}',
        resources=f'{config.source}/{config.code_resources}',
        tests=f'{config.source}/{config.tests_source}',
        test_resources=f'{config.source}/{config.test_resources}'
    )


def _create_directory_tree(language_config: JavaConfiguration):
    package = global_options.var('package')

    code_dir = language_config.code_dir(ensure=True)
    tests_dir = language_config.tests_dir(ensure=True)

    if package:
        sub_path = Path(package.replace('.', '/'))
        path = code_dir / sub_path

        path.mkdir(parents=True)

        path = tests_dir / sub_path

        path.mkdir(parents=True)

    language_config.resources_dir(ensure=True)
    language_config.test_resources_dir(ensure=True)


def _create_misc_xml(ij_project: IJProject):
    _ = ij_project.misc_file(
        java_version_number=java_version_number
    )


def _create_modules_xml(ij_project: IJProject, project_name: str):
    _ = ij_project.modules_file(
        project_name=project_name
    )
