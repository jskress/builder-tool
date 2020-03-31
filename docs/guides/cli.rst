.. _cli:

Using the CLI
=============
The builder tool expects to be given at least one task to perform.  If you don't
give it one, as in:

.. code-block:: bash

   --> builder

you'll see a banner showing the name (and title, if present) of the current
project and a note about no tasks being given.  It will then show you the set
of known languages and the tasks each one makes available.  Something like
this:

.. code-block:: bash

   --> builder
   Project: my-cool-project -- A project to save the world!
   No tasks specified.  Available tasks are:

       java
           clean   -- Removes build artifacts from other Java tasks.
           compile -- Compiles Java source code for the project.
           test    -- Tests the compiled Java code for the project.
           doc     -- Produces javadoc documentation from the Java source in the project.
           package -- Packages artifacts for the project.
           build   -- Build everything in the project.

The builder tool comes with complete online help by doing:

.. code-block:: bash

   --> builder --help

All the options should be reasonably self-explanatory but here are some details about
a few of them that require a bit more information.

.. _language-option:

``--language`` *<name>*
    Specifying this will act as if the value given were included in the ``languages``
    field of the project file's ``info`` object.  This allows the use of language
    tasks on an ad-hoc basis, without requiring its physical reference in the
    ``project.yaml`` file.  This is most useful for things like synchronizing
    dependency information from the ``project.yaml`` file to an IDE, say, or other
    one-off tasks.

``--verbose``
    Specifying this option enables more verbose output, both from the builder tool
    itself and the languages in use.  Specifying it once causes the builder tool itself
    to produce more output.  Specifying it a second or more times will, in addition,
    trigger even more verbose output (if supported) in any tasks used.  For example,
    specifying ``-vv`` for a Java project will tell the Java support to include specific
    verbose-like options.  Specifying ``-vvv`` for a Java project will also include
    its ``-verbose`` command line option to produce even more verbose output.

.. _set-option:

``--set`` *<name=value>[,...]*
    This is the means by which string values may be assigned to arbitrary names.  It
    is typically used to provide input data for tasks.  The value of the ``--set``
    option can be a simple ``name=value`` expression or a comma-delimited list of
    them as in:

    .. code-block:: bash

       --set key1=value1,key2=value2

    The option may also be repeated like so:

    .. code-block:: bash

       --set key1=value1 --set key2=value2

    This is equivalent to the previous example. If a name is repeated, the last value
    specified wins.

    See :ref:`variables <variables>` for more details about how the variable mechanism
    works.  Any values set with ``--set`` will take precedence over all other value
    sources.

As noted in the online help, all options have both a long and a short form.
