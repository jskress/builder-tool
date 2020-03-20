import click

from builder import VERSION
from builder.engine import Engine
from builder.project import get_project
from builder.utils import global_options, end, out


@click.command()
@click.option('--quiet', '-q', is_flag=True, help='Suppress normal output.')
@click.option('--verbose', '-v', count=True, help='Produce verbose output.  Repeat for more verbosity.')
@click.option('--language', '-l', multiple=True, help='Add "language" to this run. This option may be repeated.')
@click.option('--no-requires', '-r', is_flag=True, help='Run specified tasks without running required tasks first.')
@click.option('--force-fetch', '-f', is_flag=True,
              help="Do not read from the local file cache; always download dependencies. This still updates the local "
                   "file cache.")
@click.option('--set', '-s', 'set_var', multiple=True, metavar='<name=value[,...]>',
              help='Set a global variable to a value.  This is typically used to provide input data to a task.  '
                   'Allowed names of variables are determined by tasks that support them.  The value of this option '
                   'may be a comma-separated list of "name=value" pairs and/or the option may repeated.')
@click.version_option(version=VERSION, help="Show the version of builder and exit.")
@click.argument('tasks', nargs=-1)
def cli(quiet, verbose, language, no_requires, force_fetch, set_var, tasks):
    """
    Use this tool to build things based on a language.

    Each language has its own toolchain and associated tasks.  Describe a project
    in a "project.yaml" file at the root of your project.
    """

    # First, we need to store our global options.
    global_options.\
        set_quiet(quiet).\
        set_verbose(verbose).\
        set_languages(language).\
        set_independent_tasks(no_requires).\
        set_force_remote_fetch(force_fetch).\
        set_vars(set_var).\
        set_tasks(tasks)

    project = get_project()

    if project.has_no_languages():
        end('No language(s) specified in project.yaml or with --language option.')

    if project.has_unknown_languages():
        unsupported = ', '.join(project.get_unknown_languages())
        end(f'Unsupported language(s) specified in project.yaml/--language: {unsupported}')

    out(f'Project: {project.description()}', fg='bright_white')

    try:
        Engine(project).run()
    except ValueError as error:
        end(error.args[0])
