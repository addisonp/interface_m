import ast
import os
import re

from setuptools import setup

_version_re = re.compile(r'__version__\s+=\s+(.*)')

NAME = 'mongo_interface'
DESCRIPTION = 'Access into the mongoDB containing SMPTE FLM data'
LONG_DESCRIPTION = """\
The library allows the user to insert/update/delete
a smpte flm document.  All return documents are valid json objects."""

with open(os.path.join('mongo_interface', '__init__.py'), 'rb') as f:
    VERSION = str(ast.literal_eval(_version_re.search(
        f.read().decode('utf-8')).group(1)
                                   ))

setup(
    name=NAME,
    version=VERSION,
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    author='Education',
    author_email='addisonp@gmail.com',
    packages=['mongo_interface', 'mongo_interface.util', 'test'],
    install_requires=[
        'arrow==0.12.0',
        'jsonschema==2.6.0',
        'pymongo==3.6.0',
        'regex',
        'gen_utils',
        'python-box',
        'pytz',
        'dryable',
        'PyYAML',
        'deepdiff',
        'jsondiff',
        'pyOpenSSL',
        'pika',
        'pathlib',
        'pyIsEmail',
        'tenacity',
    ],
    include_package_data=True,
    package_data={
        'mongo_interface': [
            'etc/schema/*.json',
            'etc/*.yml'
        ]
    },
    zip_safe=True,
    classifiers=[
        'Development Status :: 3 Alpha',
        'Environment :: Plugins',
        'Intended Audience :: Developers',
        'License :: Other/Propietary License',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Programming Language :: Python :: 3.6'
    ],
)