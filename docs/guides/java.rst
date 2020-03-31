.. _java:

Java Language Support
=====================

The Java language provides the tasks you should need to build Java based projects.
The various configurations recognized by the Java language support are built with
sensible defaults to minimize the amount of customization you may need.

Project Directory Structure
---------------------------

The default directory structure for a Java project is simple and looks like this:

.. code-block::

   ├── project.yaml
   └── src
       ├── code
       ├── resources
       ├── test_resources
       └── tests

The appropriate contents of each directory should be pretty self-explanatory.
The ``build`` and ``dist`` directories (with appropriate sub-directories) will
also be created during compiles and packaging operations and may be cleaned up
with the ``clean`` task.

All these directory names are configurable by adding a ``java`` top-level
configuration object in your ``project.yaml`` file.  More on that below.

If you wanted your project structure to reflect the standard used in ``gradle``
projects, you'd specify this configuration:

.. code-block:: yaml

   java:
       code_source: main/java
       code_resources: main/resources
       code_target: classes/java/main
       tests_source: test
       tests_resources: test/resources
       tests_target: classes/java/test

plus appropriate settings for where jar files are placed.  There's not a straight
mapping between ``gradle`` and the build tool.

Language Tasks
--------------

The Java language support makes the following tasks available:

``clean``
    Removes the build and distribution directories, if they exist.  It is not an error
    error if they don't.

``compile``
    Compiles the code in the project's source code directory.  Any dependencies that
    specify ``compile`` in their scope will include those dependencies in the
    compilation class path.

``test``
    Compiles the code in the project's test code directory and executes the tests.  Any
    dependencies that specify ``test`` in their scope will include those dependencies in
    both the test compilation and execution class paths.  The ``compile`` task is a
    prerequisite for this task.

``doc``
    Runs ``javadoc`` against all the sources in the project's source code directory.

``package``
    Builds a jar file of the compiled classes in the project's code target and source
    resources directories.  If indicated by the packaging section of the language
    configuration, a second jar file containing the project's source code and source
    resource files will be generated.  Also, the generated jar files will be signed if
    a signature algorithm is configured.  The ``compile`` and ``test`` tasks are
    prerequisites for this task.

``build``
    A pseudo-task that causes all other tasks to be run.

Language Configuration
----------------------

The Java language configuration may contain these fields:

``type``
    The type of Java project this is which will affect how the
    various tasks behave.  Allowed values are:

    ``library``
        The project is a library or API.  This implies that the sources for the project
        will also be packaged into a jar (as IDEs can make use of such jars) unless
        specifically disabled.  This is the default.

    ``application``
        The project is an application.  This implies that an entry point is required.
        When packaging occurs, this entry point will be scanned for.  If an entry point
        is specified in the configuration, it will be validated to exist.  If not, it
        will be discovered.

``source``
    The name of the root source directory.  The default is ``src``.

``build``
    The name of the root build directory.  The default is ``build``.

``code_source``
    The name of the source code directory.  It is relative to the ``source`` field.
    The default is ``code``.

``code_resources``
    The name of the resources directory required by the source code.  It is relative
    to the ``source`` field.  The default is ``resources``.

``code_target``
    The name of the directory where compiled code will be placed.  It is relative to
    the ``build`` field.  The default is ``code/classes``.

``tests_source``
    The name of the source code directory for tests.  It is relative to the ``source``
    field.  The default is ``tests``.

``test_resources``
    The name of the resources directory required by the tests.  It is relative to the
    ``source`` field.  The default is ``test_resources``.

``tests_target``
    The name of the directory where compiled test code will be placed.  It is relative
    to the ``build`` field.  The default is ``tests/classes``.

``dist``
    The name of the root distribution directory.  The default is ``dist``.

``app_target``
    The name of the directory where packaged app artifacts will be placed.  It is
    relative to the ``dist`` field.  It will be used only when ``type`` is set to
    ``application``.  The default is ``app``.

``lib_target``
    The name of the directory where packaged library artifacts will be placed.  It is
    relative to the ``dist`` field.  It will be used only when ``type`` is set to
    ``library``.  The default is ``lib``.

``packaging``
    The configuration information specific to the ``package`` task.  It must be an
    object that may contain these fields:

    ``entry_point``
        The class name that is the entry point for an application.  If this is not
        specified, an attempt will be made to find one automatically. It is ignored for
        libraries.

    ``sources``
        A flag that indicates whether a jar file of the project sources should be
        created in addition to the compiled assets jar file.  If this is not specified
        it will default to ``true`` for libraries and ``false`` for applications.

    ``sign_with``
        The name of a signature algorithm (common ones are ``sha1`` and ``md5``) to use
        to sign generated jar files.  Generated signatures are written to a file of the
        same name as the jar file with the signature algorithm name as the extension.
        If this is not specified, no signing happens.

Repositories
------------

The Java language support makes known a repository type of ``maven``.  If the ``repo``
field of a dependency object specifies ``maven`` then the dependency will be retrieved
from Maven Central.  There is currently no support for other mirrors or separate Maven
repositories, though it is in the plan to support that.
