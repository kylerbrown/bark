## BARK

What is BARK? BARK is [ARF](https://github.com/melizalab/arf), but is an alternative implementation that
uses simple file formats and the common filesystem directory heirarchy to save data.

By using common formats and folders, BARK can leverage standard UNIX tools and data can be readily manipulated in any language.

**BARK** is an open standard for storing data from
neuronal and behavioral experiments in a portable, minimal and easily extendable
format. The goal is for the author to finish his damn thesis, though by using standard formats,
valuable data can still be accessed and analyzed for many years in the future.

**ARF** was built on the the [HDF5](http://www.hdfgroup.org/HDF5/) format, and
all arf files are accessible through standard HDF5 tools, including interfaces
to HDF5 written for other languages (e.g. MATLAB, Python, etc). **ARF**
comprises a set of specifications on how different kinds of data are stored. The
organization of ARF files is based around the concept of an *entry*, a
collection of data channels associated with a particular point in time. An entry
might contain one or more of the following:

-   raw extracellular neural signals recorded from a multichannel probe
-   spike times extracted from neural data
-   acoustic signals from a microphone
-   times when an animal interacted with a behavioral apparatus
-   the times when a real-time signal analyzer detected vocalization

Entries and datasets have metadata attributes describing how the data were
collected. Datasets and entries retain these attributes when copied or moved
between arf files, helping to prevent data from becoming orphaned and
uninterpretable.

In BARK, HDF5 is replaced with a collection of common formats: entries are standard filesystem directories. 
Continuously sampled datasets are stored as raw binary arrays, while event data is
stored in standard CSV files. All metadata are stored in YAML files.

This repository contains:

-   The specification for bark (in specification.md)
-   A python interface for reading and writing bark files

### contributing

BARK was really just created to help the author process his own data in a simpler, more flexible version of ARF. 
Contributions are vanishingly unlikely, but warmly welcomed.

### installation

The python interface requires Python 2.6+ or 3.2+, numpy 1.6+, pyYAML and pandas.

### related projects

-   NEO <https://github.com/NeuralEnsemble/python-neo>
-   NWB <http://www.nwb.org/>
-   NIX <https://github.com/G-Node/nix>
-   neuroshare (<http://neuroshare.org>) is a set of routines for reading and
    writing data in various proprietary and open formats.

