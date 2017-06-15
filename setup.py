# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

data_files = [
    ('', ['__main__.py']),
]

scripts = [
    'bin/glistadmin',
]

setup(
    name='glistadmin',
    version='0.1.0',
    description='Sample package for Python-Guide.org',
    long_description='FIXME',
    author='Ronaldo Maia',
    author_email='romaia@async.com.br',
    url='https://github.com/romaia/listadmin',
    license='FIXME',
    include_package_data=True,
    packages=find_packages(),
    data_files=data_files,
    scripts=scripts,
)
