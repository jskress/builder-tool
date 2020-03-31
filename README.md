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

Full documentation may be found [here](https://builder-tool.readthedocs.io/).

## Installation

The tool is written in Python and requires Python 3.7 or better.  To install straight
from PyPi, just do:

```bash
pip install builder-tool
```

If you need to, you can install it from this repo by doing:

```bash
git clone https://github.com/jskress/builder-tool
cd builder-tool
python setup.py install
```

You may want to do the install in a virtual environment.  See the [setup.py](setup.py)
file for which other packages are required (there aren't many and mostly what you'd
expect).
