# This is our main make file.
all: clean test docs dist

clean:
	@rm -rf dist build builder_tool.egg-info

test:
	@pytest

docs:
	${MAKE} -C docs html

dist:
	@python3 setup.py sdist bdist_wheel

publish:
	@python3 -m twine upload dist/*

.PHONY: all clean test docs dist publish
