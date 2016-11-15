# Bark
[![Build Status](https://travis-ci.org/kylerbrown/bark.svg?branch=master)](https://travis-ci.org/kylerbrown/bark)

What is Bark? Bark is the outer layer of [ARF](https://github.com/melizalab/arf) combined with an
implementation that attempts to adhere to the unix philosophy.

The elements of a Bark tree:

- A Root directory grouping a set of entries together
- Entries (often trials) are directories containing datasets that share a common time base.
- Continuously sampled datasets, stored as raw binary arrays
- Event data, stored in CSV files. 
- Every bark element (Root, Entry, SampledData, EventData) has metadata are stored in associated YAML files.

This repository contains:

-   The specification for bark (in specification.md)
-   A python interface for reading and writing bark files
-   Scripts for basic BARK tasks

## installation

The python interface requires Python 2.6+ or 3.2+, numpy, PyYAML and pandas.

    git clone https://github.com/kylerbrown/bark
    cd bark
    pip install -r requirements.txt 
    pip install .


    # optional tests
    pytest -v


# scripts

- `bark-root` -- create root directories for experiments
- `bark-entry` -- create entry directories for datasets
- `bark-entry-from-prefix` -- create an entry from datasets with matching file prefixes

For processing continuously sampled data, try the [datutils](https://github.com/kylerbrown/datutils) project, which attempts to adhere to the Bark/ARF standard.

There are many tools for processing CSV files, including [pandas](http://pandas.pydata.org/) and [csvkit](https://csvkit.readthedocs.io).

## related projects

-   NEO <https://github.com/NeuralEnsemble/python-neo>
-   NWB <http://www.nwb.org/>
-   NIX <https://github.com/G-Node/nix>
-   neuroshare (<http://neuroshare.org>) is a set of routines for reading and
    writing data in various proprietary and open formats.

