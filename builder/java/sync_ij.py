"""
This file provides support for synchronizing project dependencies into the appropriate
places in IntelliJ project files.
"""
from builder.java.java import JavaConfiguration
from builder.java.init import create_ij_project_file
from builder.jetbrains.intellij import IJProject
from builder.models import DependencyContext
from builder.utils import global_options


def sync_dependencies_to_ij(language_config: JavaConfiguration):
    project = global_options.project()
    full_context: DependencyContext = project.get_full_dependency_context('java')
    ij_project = IJProject(project.directory)

    # This will make sure we have the primary IntelliJ project file.  Note that it
    # will not actually create it if it already exists.
    create_ij_project_file(language_config, ij_project)

    ij_project.iml_file().clear_libraries()

    for context in full_context.split():
        ij_project.add_library(context.resolve())

    # Now save everything.
    ij_project.save()
