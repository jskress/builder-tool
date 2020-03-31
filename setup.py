from setuptools import setup, find_packages
from builder import VERSION

with open('README.md') as fd:
    read_me = fd.read()

# noinspection SpellCheckingInspection
setup(
    name='builder-tool',
    version=VERSION,
    description='Software Builder Tool',
    long_description=read_me,
    long_description_content_type='text/markdown',
    url='https://github.com/jskress/builder-tool',
    project_urls={
        "Documentation": "https://builder-tool.readthedocs.io/",
        "Code": "https://github.com/jskress/builder-tool",
        "Issue tracker": "https://github.com/jskress/builder-tool/issues",
    },
    author='Stephen Kress',
    author_email='jskress@gmail.com',
    license='Apache 2.0',
    packages=find_packages(),
    include_package_data=True,
    package_data={'': ['LICENSE.md', 'version.txt']},
    install_requires=[
        'click', 'requests', 'PyYAML', 'stringcase'
    ],
    python_requires='>=3.7.0',
    entry_points='''
        [console_scripts]
        builder=builder.main:cli
    ''',
)
