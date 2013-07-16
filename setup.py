#!/usr/bin/env python
# -*- coding: utf-8 -*-
# -*- mode: python -*-
import sys
from distutils.core import setup

if sys.hexversion < 0x02060000:
    raise RuntimeError("Python 2.6 or higher required")

VERSION = '2.1.0'

cls_txt = """
Development Status :: 5 - Production/Stable
Intended Audience :: Science/Research
License :: OSI Approved :: GNU General Public License (GPL)
Programming Language :: Python
Programming Language :: C++
Topic :: Scientific/Engineering
Operating System :: Unix
Operating System :: POSIX :: Linux
Operating System :: MacOS :: MacOS X
Natural Language :: English
"""

short_desc = "Advanced Recording Format for acoustic, behavioral, and physiological data"

long_desc = """
Library for reading and writing Advanced Recording Format files. ARF files
are HDF5 files used to store audio and neurophysiological recordings in a
rational, hierarchical format. Data are organized around the concept of an
entry, which is a set of data channels that all start at the same time.
Supported data types include sampled data and event data (i.e. spike times).
Requires h5py (at least 2.2) and numpy (at least 1.3).
"""

setup(
    name='arf',
    version=VERSION,
    description=short_desc,
    long_description=long_desc,
    classifiers=[x for x in cls_txt.split("\n") if x],
    author='Dan Meliza',
    author_email='"dan" at the domain "meliza.org"',
    maintainer='Dan Meliza',
    maintainer_email='"dan" at the domain "meliza.org"',
    url="https://github.com/dmeliza/arf",

    py_modules=['arf'],
    requires=["h5py (>=2.2)", "numpy (>=1.3)"],
)
# Variables:
# End:
