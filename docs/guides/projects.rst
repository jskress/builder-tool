.. _projects:

Builder Tool Projects
=====================

Let's cover everything you need to know about what a ``project.yaml`` file can
contain.

A ``project.yaml`` file must contain one object in one document.  The builder tool
will ignore any document in the project file after the first one.  The object
**must** have an ``info`` object and *may* have a ``dependencies`` object.  These
two are the core of a project file.

The project file may also contain a ``vars`` top-level object.  See :ref:`The var Object <variables>`
below for more details about how variables work and what they're for.

If the languages in use in the project support it, there may also be a top-level
object that bears the same name as the language and is used to specify any
configuration that language can make use of.  Also, as supported by each language,
a top-level object named the same as a task from that language may be present.  It
too can be used to supply configuration information that is specific to that task.

Finally, there may be top-level objects that specify configuration information for
known repositories.  Such objects must also be named the same as what they
configure.

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

``repo``
    The type of the repository where this dependency lives.  Its value must be the
    name of a repository type made known by a language.  The language may allow for
    a configuration object at the top level of the ``project.yaml`` file keyed by
    that name.  The allowed contents of that configuration information is defined by
    the language that published support for the given repository type.

``group``
    An optional group identifier for the dependency.  If this is not provided,
    it will default to the name as necessary (not everything cares about a group).

``name``
    The basic name of the dependency.

``version``
    The version of the dependency, *semver* style.  This must be an exact version
    number; currently, the build tool does not support fuzzy or nearest version
    matching.

``scope``
    The tasks this dependency applies to.  It may be either a single task name or
    an array of task names.

Here's an example ``dependencies`` block:

.. code-block:: yaml

   dependencies:
       junit5:
           repo: maven
           group: org/junit/platform
           name: junit-platform-console-standalone
           version: 1.6.0
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
       junit_version: 1.6.0

   dependencies:
       junit5:
           repo: maven
           group: org/junit/platform
           name: junit-platform-console-standalone
           version: ${junit_version}
           scope: test
