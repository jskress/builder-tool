from setuptools import setup, find_packages
from builder import VERSION

# noinspection SpellCheckingInspection
setup(
    name='builder',
    version=VERSION,
    description='Software Builder Tool',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'click', 'requests', 'PyYAML', 'stringcase'
    ],
    python_requires='>=3.7.0',
    entry_points='''
        [console_scripts]
        builder=builder.main:cli
    ''',
)
