.. _overview:

Builder Tool Overview
=====================

In this part of the documentation, we'll talk about some of the basic principles and
design assumptions baked into the builder tool.

Languages
---------

One of the keys of this tool is its formal understanding of a *language*, such as
Java.  The idea here is that each language can have its own dedicated and complete
tool chain.  That said, a language is really nothing more than its collection of
defined build tasks.  That means you can have a "language" like ``idea`` that does
not correspond to a real programming language but contains tasks that allow this
tool to inter-operate with (say) an IDE by synchronizing dependency information or
other useful work.

Currently, languages are supported by implementing an appropriately named sub-module
under the main ``builder`` module.  It is on the road map to support a more formal
extension scheme at a future time that does not require that all languages be part
of the ``builder-tool`` project.

The name of each language must match the name of the sub-module that implements
the support for it.  Support for a language is surfaced as a collection of tasks
that the builder tool will expose to the user.  Each language may also specify a
schema for any configuration information it might want to accept from the project
file.

See :ref:`The Language Guide <the-language-guide>` for details about all currently
supported languages.

Dependencies
------------

The builder tool provides formal support for dependencies, of which there are
three types, ``remote``, ``local`` and ``project``.  Support of remote dependencies
includes fetching and caching into a local file cache.  The dependency concept
is abstract at the tool level and requires support from a language for things to
really work.  This is because each language has its own unique way of defining
what a dependency actually is, in terms file naming and fetching.  Resolved
remote dependencies are also verified with digital signatures to verify transfer
if reference signatures are available.

When a language declares itself to the builder tool, it may include a *resolver*.
This resolver is used to take a dependency and resolve it into a set of dependency
files.  It may also include any needed transient dependencies which the tool
will also resolve.  If the language supports it, base URL and directory information
will be specified for remote dependency resolution.  It will also provide the
means for taking a language configuration (from a project file) and resolving that
to a path that may contain dependency files.  This is used to resolve project based
dependencies.

Projects
--------

The tool defines a project as nothing more than a directory with an optional
``project.yaml`` file in it.  Everything else, directory structure, required
files, etc., is dependent on the languages your project is written in.

A ``project.yaml`` file is a simple configuration file in (obviously) YAML
format.  Even though you *could* use JSON (as it's a proper subset of YAML)
the file must still be named ``project.yaml``.

See :ref:`Builder Tool Projects <projects>` for full details about what the
``project.yaml`` file can contain.
