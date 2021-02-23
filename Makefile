# This is our main make file.
all: clean test docs dist

clean:
	@rm -rf dist build builder_tool.egg-info

do-install:
	@python3 setup.py install

install: do-install clean

test:
	@pytest

docs:
	${MAKE} -C docs html

dist:
	@python3 setup.py sdist bdist_wheel

publish:
	@python3 -m twine upload dist/*

.PHONY: all clean do-install install test docs dist publish
