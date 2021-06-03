.. _projects:

Builder Tool Projects
=====================

Let's cover everything you need to know about what a ``project.yaml`` file can
contain.

A ``project.yaml`` file must contain one object in one document.  The builder tool
will ignore any document in the project file after the first one.  The object
**must** have an ``info`` object and *may* have any of ``dependencies``, ``vars``,
``conflicts``, ``conditions`` or ``locations`` objects.  These are the core of a
project file.

To support local directory and project based dependencies, the project file may
contain a ``locations`` object.  The locations object may contain either or both
the ``local`` and ``project`` keys.  Whichever ones are specified must be mapped
to a list of directories.  Relative directories are resolved against the project
root.  Each directory listed under ``local`` must directly contain the desired
dependency files.  Each directory listed under ``project`` must represent another
builder tool project (with or without its own ``project.yaml`` file).

There are times when, during the dependency resolution process, problems may occur
such as signature verification failure.  The ``conditions`` object allows you to
control what to do in such cases.  See :ref:`The conditions Object <conditions>`
below for more details.

The ``conflicts`` object allows you to control what happens when a transient
dependency is required but at different versions.  See :ref:`The conflicts Object <conflicts>`
below for more details.

The project file may also contain a ``vars`` top-level object.  See :ref:`The var Object <variables>`
below for more details about how variables work and what they're for.

If the languages in use in the project support it, there may also be a top-level
object that bears the same name as the language and is used to specify any
configuration that language can make use of.  Also, as supported by each language,
a top-level object named the same as a task from that language may be present.  It
too can be used to supply configuration information that is specific to that task.

It's important to note that, wherever possible, the contents of the project file
are validated with appropriate schemas.

The ``info`` Object
-------------------

The ``info`` object *may* contain these fields:

``name``
    The simple name for the project.  If this is not present, it will default to
    the name of the directory containing the project.

``title``
    An optional short title for the project.

``version``
    The version of the project, *semver* style.  If this is not present, it will
    default to ``0.0.1``.

``languages``
    The language(s) needed by this project.  This may be either a single string
    or an array of strings, each referring to a known language.  Languages may
    be used "ad-hoc" style by using the ``--language`` command line option.  See
    :ref:`here <language-option>` for more details.

Here's an example ``info`` block:

.. code-block:: yaml

   info:
       name: my-cool-project
       title: A project to save the world!
       version: 1.0.0
       languages: java

The ``dependencies`` Object
---------------------------

The ``dependencies`` object contains dependencies keyed by a simple name mapped to
the definition of a dependency.  Each dependency may have these fields:

``location``
    The location of files the dependency represents.  Its value must be one of
    ``remote``, ``local`` or ``project``.  This decides how a dependency is resolved
    to a physical file.

        ``remote``
            For remote dependencies, the builder will cooperate with the language to
            identify appropriate URLs, directory names and the like and caches the
            actual files locally.

        ``local``
            For local dependencies, dependent files will be searched in the directories
            listed under the ``locations/local`` section of the project file.

        ``project``
            For project dependencies, the builder will cooperate with the language to
            identify the appropriate subdirectory of the project to look in for
            dependent files.  The dependent project must use the same language as the
            one dependent on it.

``group``
    An optional group identifier for the dependency.  If this is not provided,
    it will default to the name as necessary (not everything cares about a group).

``name``
    The basic name of the dependency.  If this is not specified, it will default
    to the simple name this dependency information is mapped to.

``version``
    The version of the dependency, *semver* style.  This must be an exact version
    number; currently, the build tool does not support fuzzy or nearest version
    matching.

``spec``
    A more condensed form of specifying the location, group, name and version of
    the dependency.  The items must be separated by the colon character, ``:``.
    They must be in location, optional group, optional name, version order.  They
    must follow the same requirements and defaulting rules as the individual fields
    as noted above.

``classifier``
    Some language dependencies have the notion of a classifier.  This is where you
    would specify it.  It is ignored by the builder tool framework; a language is
    responsible for using this in its dependency resolution support.

``ignore_transients``
    A flag that, when set to ``true``, tells the language dependency resolution
    support that it should not process any transient dependencies.

``scope``
    The tasks this dependency applies to.  It may be either a single task name or
    an array of task names.

If the individual fields are used, then ``location`` and ``version`` are required.
Otherwise, ``spec`` is required.  In either case, ``scope`` is also required.

Here's an example ``dependencies`` block using the long form:

.. code-block:: yaml

   dependencies:
       junit5:
           location: remote
           group: org/junit/platform
           name: junit-platform-console-standalone
           version: 1.7.0
           scope: test

Here's the same example using the shorter form:

.. code-block:: yaml

   dependencies:
       junit5:
           spec: remote:org/junit/platform:junit-platform-console-standalone: 1.7.0
           scope: test

.. _variables:

The ``vars`` Object
-------------------

The ``vars`` top-level object is a simple, flat collection of name/value pairs.  The
variable system allows for text substitution in string values throughout the project
file.  They may also serve as input data to tasks that need it.  Variable values will
come from environment variables first.  Variables specified under the ``vars`` object
in the project file will override those.  Variable specified :ref:`on the command line <set-option>`
will override both.

To refer to a value in the project file, use the standard ``${varname}`` syntax to
refer to a variable.  All variable references in a project file are resolved during
load, before any processing.

.. note::

   If a variable name is not known, i.e., not an environment variable, not set in the
   ``vars`` object of the project file and not specified with a ``--set`` option, the
   variable reference will be replaced with the empty string.

Here's an example ``dependencies`` block that uses a value from the ``vars`` block:

.. code-block:: yaml

   vars:
       junit_version: 1.7.0

   dependencies:
       junit5:
           location: remote
           group: org/junit/platform
           name: junit-platform-console-standalone
           version: ${junit_version}
           scope: test

.. _conflicts:

The ``conflicts`` Object
------------------------

The ``conflicts`` top-level object is used to tell the builder tool what to do
in the event a particular transient dependency is required at different versions.
The builder tool assumes that dependency versioning follows *semver* rules.  As
such, if the versions differ only at the micro level, it will use the higher-numbered
version and display a warning.  If the versions differ at either the major or
minor level, an error is shown and processing stopped.  The ``conflicts`` section
is used to override this behavior.

The ``conflicts`` field maps in the project file to an object.  Each field in
the object is the name of a dependency in ``<group>:<name`` form.  Each of those
fields maps to an object that describes what to do when there is a version conflict
for that dependency.  Each of those objects may have these fields:

``action``
    The action to take when a conflict is encountered.  It must be one of ``error``,
    ``newer`` or ``older``.  The default is either ``newer`` or ``error``, depending
    on how different the versions are.

``warn``
    Whether to issue a warning to the end user or not.  It is only applicable to the
    ``newer`` or ``older`` actions and is ignored for the ``error`` action.  It defaults
    to ``false`` for defined conflicts.

Here's an example ``conflicts`` block:

.. code-block:: yaml

   conflicts:
       org.yaml:snakeyaml:
           action: newer
           warn: false

.. _conditions:

The ``conditions`` Object
-------------------------

There are times where the builder tool will encounter a situation which would
normally be an error but which may be ok to ignore.  This section allows you
to specify what to do in those cases.

The only field allowed under the ``conditions`` field is ``files``.  This
must map to an object where the fields are the names of files (with no directory
information).  Each file name must map to an object that describes what to do
when there are problems with the file.

Each file's object may only contain a ``signature`` field.  This field indicates
what the build tool should do when it cannot verify the signature of the file.
It must be one of ``ignore``, ``warn`` or ``error``.  The default is ``error``.
