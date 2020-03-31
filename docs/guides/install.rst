.. _install:

Installation of the Builder Tool
================================

Here, we cover the installation of the builder tool.  The first step to using any
software package is getting it properly installed.

You may want to do the install in a virtual environment.  See the
`setup.py <https://github.com/jskress/builder-tool/blob/master/setup.py#L26-L28>`_
file for which other packages are required (there aren't many and mostly what you'd
expect).

``$ pip install builder-tool``
------------------------------

To install Builder from PyPi, simply run this command in your terminal of choice::

    $ pip install builder-tool

You will need at least Python v3.7 to use the ``builder`` tool.

Get the Source Code
-------------------

The builder tool is actively developed on GitHub, where the code is
`always available <https://github.com/jskress/builder-tool>`_.

You can clone the public repository with this::

    $ git clone git://github.com/jskress/builder-tool.git


Once you have a copy of the source, you can install it into your site-packages easily::

    $ cd builder-tool
    $ python setup.py install

or just::

    $ cd builder-tool
    $ pip install .
