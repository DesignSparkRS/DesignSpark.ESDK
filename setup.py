# -*- coding: utf-8 -*-
# Copyright (c) 2021 RS Components Ltd
# SPDX-License-Identifier: MIT License

from setuptools import setup

setup(
    name = 'DesignSpark.ESDK',
    namespace_packages=['DesignSpark'],
    packages = ['DesignSpark.ESDK'],
    version = '23.2.0',
    description = 'DesignSpark ESDK support library',
    author = 'RS Components',
    author_email = 'maint@abopen.com',
    url = 'https://github.com/designsparkrs/DesignSpark.ESDK',
    install_requires = ['smbus2','toml','python-geohash','gpsdclient','paho-mqtt','requests', 'python-snappy', 'RPi.GPIO'],
    license = 'MIT License',
    long_description = open('README.rst').read(),
    long_description_content_type="text/x-rst",
    include_package_data = True,
    keywords = 'raspberry pi raspi designspark esdk',
    classifiers = [
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Topic :: Education',
        'Topic :: System :: Hardware',
        'Topic :: System :: Hardware :: Hardware Drivers'
    ]
)