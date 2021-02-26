"""
This library provides the dependency resolution support for the Java language.
"""
from pathlib import Path
from typing import Optional, Dict

from builder.java.java import build_names
from builder.models import Dependency, DependencyContext, DependencyPathSet
from builder.java import JavaConfiguration
from builder.java.modules import ModuleData, API_ELEMENTS, SOURCE_ELEMENTS, JAVADOC_ELEMENTS
from builder.java.pom import read_pom_for_dependencies
from builder.utils import global_options


def project_to_dist_dir(configuration: JavaConfiguration) -> Optional[Path]:
    """
    A function that returns the primary library distribution directory for the given
    configuration.  This is used when resolving project dependencies.

    :param configuration: the configuration to get dependency directory for.
    :return: the configuration's library distribution directory.
    """
    return configuration.library_dist_dir() / global_options.project().name


def _try_for_variant(context: DependencyContext, dependency: Dependency, module_data: ModuleData, key: str,
                     path_set: DependencyPathSet):
    """
    A function that attempts to load the asset from the named variant.
    """
    variant = module_data.get_variant(key)

    if variant:
        variant_file = variant.files[0]

        _try_to_add_secondary_path(context, dependency, key, variant_file.name, path_set, variant_file.signatures)


def _use_module_resolution(context: DependencyContext, dependency: Dependency, module_path: Path) \
        -> Optional[DependencyPathSet]:
    """
    A function that resolves Java dependencies using module files (the new way).

    :param context: the current dependency context in play.
    :param dependency: the dependency we are to resolve.
    :param module_path: the local path to our module file.
    :return: the appropriate dependency path set or ``None``.
    """
    module_data = ModuleData.from_path(module_path)
    variant = module_data.get_variant(API_ELEMENTS)

    # If there's not an API variant, then we really can't do anything.
    if not variant:
        return None

    jar_variant_file = variant.files[0]
    jar_file = context.to_local_path(dependency, jar_variant_file.name, jar_variant_file.signatures)

    # If we couldn't get the jar file, report same.
    if not jar_file:
        return None

    # Ok, let's process any dependencies that may be involved.
    if not dependency.ignore_transients:
        for transient_dependency in variant.dependencies:
            context.add_dependency(transient_dependency.as_dependency(dependency))

    # Now, let's create and load up our result:
    result = DependencyPathSet(dependency, jar_file)

    _try_for_variant(context, dependency, module_data, SOURCE_ELEMENTS, result)
    _try_for_variant(context, dependency, module_data, JAVADOC_ELEMENTS, result)

    return result


def _try_to_add_secondary_path(context: DependencyContext, dependency: Dependency, key: str, name: str,
                               path_set: DependencyPathSet, signatures: Optional[Dict[str, str]] = None):
    """
    A function that attempts to load a secondary path (sources or javadoc) and, if
    successful, adds them to the given path set.

    :param context: the current dependency context in play.
    :param dependency: the dependency we are to resolve.
    :param key: the key by which the secondary path will be known.
    :param name: the name of the secondary path.
    :param path_set: the path set to add a successfully isolated path to.
    :param signatures: the set of signatures to verify against (if any).
    """
    path = context.to_local_path(dependency, name, signatures)

    if path:
        path_set.add_secondary_path(key, path)


def _use_pom_resolution(context: DependencyContext, dependency: Dependency, classified_name: str, base_name: str) \
        -> Optional[DependencyPathSet]:
    """
    A function that resolves Java dependencies using POM files (the old way).

    :param context: the current dependency context in play.
    :param dependency: the dependency we are to resolve.
    :param classified_name: the classified base name for the main asset.
    :param base_name: the base name for file assets.
    :return: the appropriate dependency path set or ``None``.
    """
    jar_file = context.to_local_path(dependency, f'{classified_name}.jar')

    if not jar_file:
        return None

    # Ok, we're good to go.
    # First, let's see if there's a POM file that can tell us about dependencies.
    pom_file = context.to_local_path(dependency, f'{base_name}.pom')

    if pom_file and not dependency.ignore_transients:
        read_pom_for_dependencies(pom_file, context, dependency)

    # Now, let's create and load up our result:
    result = DependencyPathSet(dependency, jar_file)

    _try_to_add_secondary_path(context, dependency, 'sources', f'{base_name}-sources.jar', result)
    _try_to_add_secondary_path(context, dependency, 'javadoc', f'{base_name}-javadoc.jar', result)

    return result


def resolve(context: DependencyContext, dependency: Dependency) -> Optional[DependencyPathSet]:
    """
    A function to resolve dependencies in Java-land.

    :param context: the current dependency context in play.
    :param dependency: the dependency we are to resolve.
    :return: the appropriate dependency path set or ``None``.
    """
    directory_url, directory_path, classified_name, base_name = build_names(dependency)

    context.set_remote_info(directory_url, directory_path)

    module_path = context.to_local_path(dependency, f'{base_name}.module')

    return _use_module_resolution(context, dependency, module_path) if module_path else \
        _use_pom_resolution(context, dependency, classified_name, base_name)
