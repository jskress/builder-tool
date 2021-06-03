.. _java:

Java Language Support
=====================

The Java language provides the tasks you should need to build Java based projects.
The various configurations recognized by the Java language support are built with
sensible defaults to minimize the amount of customization you may need.

Project Directory Structure
---------------------------

The default directory structure for a Java project is simple and looks like this:

.. code-block:: console

   ├── project.yaml
   └── src
       ├── code
       ├── resources
       ├── test_resources
       └── tests

The appropriate contents of each directory should be pretty self-explanatory.
The ``build`` and ``dist`` directories (with appropriate sub-directories) will
also be created during compile and packaging operations and may be cleaned up
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
mapping between ``gradle`` and the build tool, however.

Language Tasks
--------------

The Java language support makes the following tasks available:

``init``
    Initializes project files and directory structure for a Java project.  It assumes that
    IntelliJ is the IDE of choice and initializes those files as well.  The task will consume
    three variables (use the ``--set`` CLI option):

    ``title``
        The title for the project.

    ``version``
        The initial version number for the project.

    ``package``
        The top-level Java package to use.  This will produce the appropriate directory
        structure.

    You could set up a brand new project by creating a directory and running this command:

    .. code-block:: console

       builder -l java -s "title=My New Project" -s version=1.0.0 -s package=com.me.project init

    from within it.

``clean``
    Removes the build and distribution directories, if they exist.  It is not an error
    if they don't.

``compile``
    Compiles the code in the project's source code directory.  Any dependencies that
    specify ``compile`` in their scope will include those dependencies in the
    compilation class path.

``compile-tests``
    Compiles any unit tests in the project's source code directory.  Any dependencies
    that specify ``compile-tests`` in their scope will be included in the compilation
    class path.  The ``compile`` task is a prerequisite for this task.

``test``
    Executes the compiled unit tests in the project.  Any dependencies that specify
    ``test`` in their scope will be included in the test execution class path.  The
    ``compile-tests`` task is a prerequisite for this task.

``doc``
    Runs ``javadoc`` against all the sources in the project's source code directory.  You
    should include ``doc`` as a dependency scope on any dependency also used for compilation.

``package``
    Builds a jar file of the compiled classes in the project's code target and source
    resources directories.  If indicated by the packaging section of the language
    configuration, additional jar files containing the project's source code and source
    resource files and JavaDoc will be generated.  An appropriate module JSON file will
    also be generated for the generated jars.  The ``compile`` and ``test`` tasks are
    prerequisites for this task.

    See :ref:`this section <package-task-conf>` for details about configuring this task.

``build``
    A pseudo-task that causes all other tasks to be run.

``check-versions``
    Runs through the full list of dependencies specified for the current project and
    checks whether each dependency is at the latest level.  For remote dependencies,
    this is resolved using the ``maven-metadata.xml`` file (downloaded straight from
    Maven) for the dependency.  For local and project dependencies, the relevant
    directories are scanned for matching jar files.

``sync-ij``
    Takes all defined dependencies from ``project.yaml`` and notes them in the proper
    IntelliJ project files.

Language Configuration
----------------------

The Java language configuration may contain these fields:

``type``
    The type of Java project this is which will affect how the various tasks behave.
    Allowed values are:

    ``library``
        The project is a library or API.  This implies that the sources and JavaDoc for
        the project will also be packaged into jars (as IDEs can make use of such jars)
        unless specifically disabled.  This is the default.

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

``code_doc``
    The name of the directory where generated JavaDoc will be placed.  It is relative
    to the ``build`` field.  The default is ``code/javadoc``.

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

.. _package-task-conf:

``test`` Task Configuration
------------------------------

The ``test`` task configuration may contain these fields:

``test_executor``
    The symbolic name for the command line tool to use to run unit tests.  Currently,
    ``junit5`` is the only supported value.  It is the default.  For this to work,
    there must also be a dependency defined in the project that is also called ``junit5``
    which must resolve to the JUnit5 standalone command line tool.

``coverage_agent``
    The symbolic name for the tool that will be used as a JVM agent for capturing
    code coverage as tests are executed.  Currently, ``jacoco`` is the only supported
    value.  It is the default.  For this to work, there must also be a dependency
    defined in the project that is also called ``jacoco`` which must resolve to the
    JaCoCo agent.  Set this to ``null`` to disable code coverage completely.

``coverage_reporter``
    The symbolic name for the command line tool that will be used to convert captured
    code coverage information into a report.  Currently, ``jacoco-cli`` is the only
    supported value.  It is the default.  For this to work, there must also be a
    dependency defined in the project that is also called ``jacoco-cli`` which must
    resolve to to the no-dependencies JaCoCo command line tool.  Set this to ``null``
    to disable code coverage completely.

``test_reports``
    The relative directory where test result files will be written.  This is ``null``
    by default, thus disabling the output portion of test execution.  The directory
    is taken as relative to the ``build`` field at the language level.  If you want
    test result XML files, the value of ``reports/tests`` is suggested.

``coverage_reports``
    The relative directory where coverage capture and report files will be written.
    The default value is ``reports/coverage``.  Set this to ``null`` to disable code
    coverage completely.

``no_tests``
    For projects with no tests, setting this to ``true`` allows the ``test`` task to
    be effectively skipped without having to disable required task handling.

``package`` Task Configuration
------------------------------

The ``package`` task configuration may contain these fields:

``entry_point``
    The class name that is the entry point for an application.  If this is not
    specified, an attempt will be made to find one automatically. It is ignored for
    libraries.

``fat_jar``
    A flag that indicates whether dependencies scoped to the ``package`` task should
    be included in the archive being built.  This will default to ``true`` for
    application projects and ``false`` for library projects.

``include``
    An array of rules of extra things to include in the primary jar the task creates.
    Each entry in the array is an object that **must** have a field called ``source``
    which is the directory containing the extra contents to include.  If it is relative,
    it is resolved relative to the project root directory.  The object *may* have a
    field called ``under``.  If this is given, it is taken as the directory within the
    jar being built under which the extra content is included.  If ``under`` is not
    specified, the extra content is included at the root of the jar.  Note that the
    ``source`` directory is itself not included in the jar; only its children and all
    descendants.

``exclude``
    A list of strings that note file patterns to exclude from the archive being created.
    Each entry will be interpreted as a file name glob pattern unless the first character
    is the tilde (``~``).  In that case, the rest of the string is taken to be a regular
    expression pattern.  Any relative files that match an exclusion pattern are not
    included in the final archive.

``duplicates``
    An object where each field is an entry in the target jar file that may be
    duplicated as they are pulled from different sources (such as dependencies).  Each
    entry name must map to the action that the builder tool should take regarding the
    duplicate.  The action must be one of the following:

    ``merge``
        This tells the packager to merge the duplicate files.  This is appropriate for
        things like Java service files (these are handled automatically so you don't
        have to provide actions for them here).

    ``first``
        This tells the packager to keep the first occurrence of the file it runs across
        and ignore any later ones.

    ``last``
        This tells the packager to keep the last occurrence of the file it runs across
        and ignore all the earlier ones.

    ``newest``
        This tells the packager to keep the newest file (by modification time) it runs
        across and ignore all the others.

    ``oldest``
        This tells the packager to keep the oldest file (by modification time) it runs
        across and ignore all the others.

    ``largest``
        This tells the packager to keep the largest (in bytes) file it runs across and
        ignore all the others.

    ``smallest``
        This tells the packager to keep the smallest (in bytes) file it runs across and
        ignore all the others.

``sources``
    A flag that indicates whether a jar file of the project sources should be created
    in addition to the compiled assets jar file.  If this is not specified it will
    default to ``true`` for libraries and ``false`` for applications.

``doc``
    A flag that indicates where a jar file of the project's JavaDoc should be created
    in addition to the compiled assets jar file.  If this is not specified it will
    default to ``true`` for libraries and ``false`` for applications.
