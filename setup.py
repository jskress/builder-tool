from setuptools import setup, find_packages
from builder import VERSION

with open('README.md') as fd:
    read_me = fd.read()

# noinspection SpellCheckingInspection
setup(
    name='builder',
    version=VERSION,
    description='Software Builder Tool',
    long_description=read_me,
    url='https://github.com/jskress/builder',
    project_urls={
        "Documentation": "https://github.com/jskress/builder/README.md",
        "Code": "https://github.com/jskress/builder",
        "Issue tracker": "https://github.com/jskress/builder/issues",
    },
    author='Stephen Kress',
    author_email='jskress@gmail.com',
    packages=find_packages(),
    include_package_data=True,
    package_data={'': ['version.txt']},
    install_requires=[
        'click', 'requests', 'PyYAML', 'stringcase'
    ],
    python_requires='>=3.7.0',
    entry_points='''
        [console_scripts]
        builder=builder.main:cli
    ''',
)
