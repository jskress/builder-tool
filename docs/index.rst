.. _index:

A Straightforward Build Tool
============================

Release v\ |version|. (:ref:`Installation <install>`)

This is a Python project that provides a tool for building software.  It is
language agnostic and works by allowing a user to specify the build tasks which
should be performed, as is true of most build tools.  You will need at least v3.9
of Python to run it.

There are two major reasons for writing this.  Build tools like ``ant`` and ``gradle``
are plentiful but many are overly bloated.  They come with tons of stuff that's either
unnecessary or overly generalized.  They are prone to being convoluted to learn.  I
wanted something simple to maintain from a project and development workflow perspective.
Under the simplest circumstances you might not even need a project file with this.

There are plenty of build related things this tool cannot do.  If you run across
those, I'm sure one of the others will suit you just fine.  This one is really meant
to be standalone or to play well with something simple like ``make`` at the top level
of your build process.  It is an attempt to have a straightforward build tool that is
not over-engineered.  The KISS principle reigns here.

Tasks support the notion of prerequisite tasks.  For example, ``test`` type tasks
usually require a ``compile`` type task to be performed first.  Each language is
responsible for providing this information for the tasks it publishes.  The user has
the ability to bypass this prerequisite task processing, if desired or necessary.
It's even possible that a language may make a task available that, in and of itself,
does nothing but by virtue of its prerequisites causes other work to be done.  A
``build`` task, for example, may cause compilation, testing, documentation and
packaging tasks to be performed because they are prerequisites.  This type of task
is referred to as a pseudo-task.  Obviously, disabling prerequisite processing and
specifying a pseudo-task will accomplish nothing.

The tool also provides first class support for dependency management, the key
reason for having any sort of non-trivial build tool in the first place.  (Otherwise,
a language's CLI tools are usually fine.)  This refers to satisfying the need for
libraries, APIs and such that are needed to build a given piece of software,
including any libraries *those* libraries or APIs need.  Dependencies are scoped to
task names as it is reasonable, say, for a compile task to require fewer dependencies
than a package task.

.. _the-language-guide:

The Builder Tool User's Guide
-----------------------------

This part of the documentation covers basic concepts, project structure requirements,
languages and the use of the ``builder`` command line interface.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   guides/install
   guides/overview
   guides/projects
   guides/cli

The Languages Guide
-------------------

This part of the documentation covers each supported language, its configuration and
operation within the builder tool.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   guides/java

The Languages Extension Guide
-----------------------------

This part of the documentation covers what it takes to provide support for a language
in the builder tool.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

Feel free to :ref:`search` the documentation if you're looking for something specific.
