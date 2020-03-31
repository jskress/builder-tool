# This is our main make file.
all: docs dist

clean:
	@rm -rf dist

docs:
	${MAKE} -C docs html

dist:
	python3 setup.py sdist bdist_wheel
#	python3 -m twine upload dist/*

.PHONY: all docs dist
