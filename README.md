# Builder Tool

This is a Python project that provides a tool for building software.  It is
language agnostic and works by allowing a user to specify the build tasks which
should be performed.

There are two major reasons for writing this.  Build tools like `ant` and `gradle`
are plentiful but many are overly bloated with tons of stuff that's either unnecessary
or overly generalized and prone to being convoluted to learn.  I wanted something
simple to maintain from a project and development workflow perspective.

There are plenty of build related things this tool cannot do.  If you run across
those, I'm sure one of the others will suit you just fine.  This one is really meant
to be standalone or to play well with something simple like `make` at the top level
of the build process.  It is an attempt to have a straightforward build tool that is
not over-engineered.  The KISS rule reigns here.

Tasks themselves also support the notion of prerequisite tasks.  For example,
`test` type tasks usually require a `compile` type task to be performed first.  Each
language is responsible for providing this information for the tasks it publishes.
The user has the ability to bypass this prerequisite task processing, if necessary. 

The tool also provides first class support for dependency management, the key
reason for having any sort of build tool in the first place (otherwise, a language's
CLI tools are usually fine).  This refers to satisfying the need for libraries, APIs
and such that are needed to build a given piece of software, including any libraries
_those_ libraries or APIs need.

### Table of Contents

-   [Installation](#installation)
-   [Languages](#languages)
-   [Dependencies](#dependencies)
-   [Projects](#projects)
-   [Using the CLI](#using-the-cli)
-   [Supported Languages](#supported-languages)
    - [Java](#java)

## Installation

The tool is written in Python and requires Python 3.7 or better.  You can install
it from this repo by doing:

```bash
git clone https://github.com/jskress/builder
cd builder
python setup.py install
```

You may want to do the install in a virtual environment.  See the [setup.py](setup.py)
file for which other packages are required (there aren't many and mostly what you'd
expect).

Direct installation from PyPi (with `pip install`) will come when more of the tool's
functionality is complete.

## Languages

One of the keys of this tool is its formal understanding of a language, such as
Java.  The idea here is that each language can have its own dedicated tool chain.
That said, a language is really nothing more than its collection of tasks.  That
means you can have a "language" like `idea` that does not correspond to a real
programming language but contains tasks that allow this tool to inter-operate with
(say) an IDE by synchronizing dependency information or other useful work.

Currently, languages are supported by implementing an appropriately named sub-module
under the main `builder` module.  It is on the road map to support a more formal
extension scheme at a future time that does not require that all languages be part
of the `builder` project.

The name of each language must match the name of the sub-module that implements
the support for it.  Support for a language is surfaced as a collection of tasks
that the builder will expose to the user.  Each language may also specify a
schema for any configuration information it might want from the `project.yaml`
file.

Currently supported languages:

- **`java`** -- Tasks for building [Java based projects](#java).

## Dependencies

The builder tool provides formal support for dependency fetching.  It maintains
a local file cache for this.  The dependency concept is abstract at the tool
level and requires support from a language for things to really work.

A dependency comes from a repository which a language must make known to the
tool.  The language's support provides the means to convert a dependency
definition into a URL from which the tool can then download the dependency and
cache it.  Signature verification is fully supported to help guarantee the
integrity of downloaded files.

If a language supports the concept, the tool also allows for the notion of a
meta-file which can contain nested (sometimes referred to as _transient_)
dependencies.  For example, the Java language support understands the concept
of POM files for this.  Such files are also downloaded, verified and cached
as appropriate. 

## Projects

The tool defines a project as nothing more than a directory with an optional
`projects.yaml` file in it.  Everything else is dependent on the language(s)
your project is written in.

Any further constraints on project directory structure are controlled by the
languages involved.

A `project.yaml` file **must** have an `info` object at the top level of the
document.  It _may_ have a `dependencies` object.  Configuration objects may
also be present for languages, tasks, repositories and other configurable items.
The constraints on such configuration objects are defined by the things they
configure.

### The `info` Object

The `info` object _may_ contain these fields:

-   **`name`** -- The simple name for the project.  If this is not present, it
    will default to the name of the directory containing the `project.yaml`.

-   **`title`** -- An optional short title for the project.

-   **`version`** -- The version of the project, _semver_ style.  If this is not
    present, it will default to `0.0.1`.

-   **`languages`** -- The language(s) needed by this project.  This may be either
    a single string or an array of strings, each referring to a known language.

### The `dependencies` Object

The `dependencies` object contains dependencies keyed by a simple name mapped to
the definition of a dependency.  Each dependency may have these fields:

-   **`repo`** -- The type of the repository where this dependency lives.  Its
    value must be the name of a repository type made known by a language.  The
    language may also allow for a configuration object at the top level of the
    `project.yaml` file keyed by the name.  The allowed contents of that
    configuration information is defined by the language that published support
    for the repository type.

-   **`group`** -- An optional group identifier for the dependency.  If this is
    is not provided, it will default to the name as necessary.

-   **`name`** -- The name of the dependency.

-   **`version`** -- The version of the dependency, _semver_ style.  This must
    be an exact version number.

-   **`scope`** -- The tasks this dependency applies to.  It may be either a
    single task name or an array of task names.

## Using the CLI

The builder expects to be given at least one task to perform.  If you don't
give it one, as in:

```bash
builder
```

you'll see a banner showing the name of the current project and a note about
no tasks being given.  This will also show you the set of known languages and
the tasks each one makes available.

The `builder` tool does come with complete help by doing:

```bash
builder --help
```

It should be reasonably self-explanatory but here are some more details about
some of the options.

-   **`--language`** -- Specifying this will act as if the value given were
    included in the `languages` list of the project file's `info` object.  This
    allows the use of language tasks on an ad-hoc basis, without requiring its
    physical presence in the `project.yaml` file.  This is most useful for things
    like synchronizing dependency information from the `project.yaml` file to
    an IDE, say.

-   **`--verbose`** -- Specifying this option enables more verbose output from
    the builder tool itself.  Specifying it a second time will also trigger
    verbose output (if supported) on any tools used.  For example, specifying
    `-vv` for a Java project will also tell the Java CLI tools to produce
    verbose output, plus enable other verbose related options.

-   **`--set`** -- This is the means to assign string values to arbitrary names.
    It is typically used to provide input data for tasks.  The value of the `--set`
    option can be a simple `name=value` expression or a comma-delimited list of
    them as in:
    
    ```bash
    --set key1=value1,key2=value2
    ```
    
    The option may also be repeated like so:
    
    ```bash
    --set key1=value1 --set key2=value2
    ```
    
    This is equivalent to the previous example. If a name is repeated, the last value
    specified wins.

## Supported Languages

This section provides all the details you should need about each supported language.

### Java

The Java language provides the tasks you should need to build Java based projects.
The various configurations supported by the Java language support are built with
sensible defaults.

#### Project Directory Structure 

The default directory structure for a Java project is simple and looks like this:

```
├── project.yaml
└── src
    ├── code
    ├── resources
    ├── test_resources
    └── tests
```

The appropriate contents of each directory should be pretty self-explanatory.
The `build` and `dist` directories (with appropriate sub-directories) will
also be created during compiles and packaging operations.

All these directory names are configurable by adding a `java` top-level
configuration object in the `project.yaml` file.

#### Language Tasks

The Java language makes the following tasks available:

-   **`clean`** -- Removes the build and distribution directories, if they exist.
    It's not an error if they don't.

-   **`compile`** -- Compiles the code in the project's source code directory.
    Any dependencies that specify `compile` in their scope will reference those
    dependencies.

-   **`test`** -- Compiles the code in the project's test code directory and
    executes the tests.  Any dependencies that specify `test` in their scope
    will reference those dependencies.  The `compile` task is a prerequisite
    for this task.

-   **`doc`** -- Runs `javadoc` against all the sources in the project's source
    code directory.

-   **`package`** -- Builds a jar file of the compiled classes in the project's
    code target and source resources directories.  If indicated by the packaging
    section of the language configuration, a second jar file containing the
    project's source code and source resources.  Also, the generated jar files
    will be signed if a signature algorithm is configured.  The `compile` and
    `test` tasks are prerequisites for this task.

-   **`build`** -- A pseudo task that causes all other tasks to be run.
  
#### Language Configuration

The Java language configuration may contain these fields:

-   **`type`** -- The type of Java project this is which will affect how the
    various tasks behave.  Allowed values are:
    
    *   **`library`** -- The project is a library or API.  This implies that the
        sources for the project will also be packaged into a jar (as IDEs can
        make use of such jars).  This is the default.

    *   **`application`** -- The project is an application.  This implies that an
        entry point is required.  When packaging occurs, this entry point will be
        scanned for.  If an entry point is specified in the configuration, it will
        be validated to exist.  If not, it will be discovered.

-   **`source`** -- The name of the root source directory.  The default is `src`.

-   **`build`** -- The name of the root build directory.  The default is `build`.

-   **`code_source`** -- The name of the source code directory.  It is relative to
    the `source` field.  The default is `code`.

-   **`code_resources`** -- The name of the resources directory required by the
    source code.  It is relative to the `source` field.  The default is `resources`.

-   **`code_target`** -- The name of the directory where compiled code will be placed.
    It is relative to the `build` field.  The default is `code/classes`.

-   **`tests_source`** -- The name of the source code directory for tests.  It is
    relative to the `source` field.  The default is `tests`.

-   **`test_resources`** -- The name of the resources directory required by the
    tests.  It is relative to the `source` field.  The default is `test_resources`.

-   **`tests_target`** -- The name of the directory where compiled test code will be
    placed.  It is relative to the `build` field.  The default is `tests/classes`.

-   **`dist`** -- The name of the root distribution directory.  The default is `dist`.

-   **`app_target`** -- The name of the directory where packaged app assets will be
    placed.  It is relative to the `dist` field.  It will be used only when `type` is
    set to `application`.  The default is `app`.

-   **`lib_target`** -- The name of the directory where packaged library assets will be
    placed.  It is relative to the `dist` field.  It will be used only when `type` is
    set to `library`.  The default is `lib`.

-   **`packaging`** -- The configuration information specific to the `package` task.
    It must be an object that may contain these fields:

    *   **`entry_point`** -- The class name that is the entry point for an application.
        If this is not specified, an attempt will be made to find one automatically.
        It is ignored for libraries.

    *   **`sources`** -- A flag that indicates whether a jar file of the project
        sources should be created in addition to the standard jar file.  If this is
        not specified it will default to `true` for libraries and `false` for
        applications.

    *   **`sign_with`** -- The name of a signature algorithm (common ones are `sha1`
        and `md5`) to use to sign generated jar files.  Generated signatures are
        written to a file of the same name as the jar file with the signature
        algorithm name as the extension.  If this is not specified, no signing
        happens.
