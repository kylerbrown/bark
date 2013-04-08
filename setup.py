#!/usr/bin/env python
# -*- coding: utf-8 -*-
# -*- mode: python -*-
from distutils.core import setup

# --- Distutils setup and metadata --------------------------------------------

VERSION = '2.0.0-beta1'

cls_txt = \
"""
Development Status :: 5 - Production/Stable
Intended Audience :: Science/Research
License :: OSI Approved :: GNU General Public License (GPL)
Programming Language :: Python
Programming Language :: C++
Programming Language :: MATLAB
Topic :: Scientific/Engineering
Operating System :: Unix
Operating System :: POSIX :: Linux
Operating System :: MacOS :: MacOS X
Natural Language :: English
"""

short_desc = "Advanced Recording Format for acoustic, behavioral, and physiological data"

long_desc = \
"""
Library for reading and writing Advanced Recording Format files. ARF files are
HDF5 files used to store audio and neurophysiological recordings in a rational,
hierarchical format. Data are organized around the concept of an entry, which is
a set of data channels that all start at the same time. Supported data types
include sampled data and event data (i.e. spike times).
"""

setup(
    name = 'arf',
    version = VERSION,
    description = short_desc,
    long_description = long_desc,
    classifiers = [x for x in cls_txt.split("\n") if x],
    author = 'Dan Meliza',
    author_email = '"dan" at the domain "meliza.org"',
    maintainer = 'Dan Meliza',
    maintainer_email = '"dan" at the domain "meliza.org"',
    url = "https://github.com/dmeliza/arf",

    py_modules = ['arf'],
    requires = ["h5py (>=2.0)","numpy (>=1.3)"],
    )
# Variables:
# End:
