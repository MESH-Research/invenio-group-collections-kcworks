# -*- coding: utf-8 -*-
#
# Copyright (C) 2023 MESH Research
#
# invenio-group-collections is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""Social groups infrastructure for InvenioRDM"""

from setuptools import find_packages, setup

readme = open('README.md').read()
history = open('CHANGES.md').read()

install_requires = [
    'click>=7.0',
]

tests_require = [
    'pytest>=7.3.2',
    'pytest-runner'
]

dev_requires = [
]

extras_require = {
    'tests': tests_require,
    'dev': dev_requires
}

extras_require['all'] = []
for reqs in extras_require.values():
    extras_require['all'].extend(reqs)

packages = find_packages(include=['invenio_group_collections',
                                  'invenio_group_collections.*'])

setup(
    name='invenio-group-collections',
    description=__doc__,
    long_description=readme + '\n\n' + history,
    long_description_content_type='text/markdown',
    keywords='invenio inveniordm groups collections social',
    license='MIT',
    author='MESH Research',
    author_email='scottia4@msu.edu',
    url='https://github.com/MESH-Research/invenio-group-collections',
    packages=packages,
    include_package_data=True,
    platforms='any',
    install_requires=install_requires,
    extras_require=extras_require,
    tests_require=tests_require,
    setup_requires=['pytest-runner'],
    classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],
)