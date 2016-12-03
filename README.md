# Bark
[![Build Status](https://travis-ci.org/kylerbrown/bark.svg?branch=master)](https://travis-ci.org/kylerbrown/bark)

What is Bark? Bark is a hierarchical standard for electrophysiology data. By emphasizing filesystem 
directories, plain text files and simple binary arrays, Bark data can leverage a broad tool set that includes Unix commands.

Bark is also the fibrous outer layer of [ARF](https://github.com/melizalab/arf), wrapped around a few standard
file types.

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

The python interface is tested against Python 3.5. Installation with [Conda](http://conda.pydata.org/miniconda.html) recommended.

    git clone https://github.com/kylerbrown/bark
    cd bark
    pip install -r requirements.txt
    pip install .


    # optional tests
    pytest -v


# Usage

- `bark-root` -- create root directories for experiments
- `bark-entry` -- create entry directories for datasets
- `bark-entry-from-prefix` -- create an entry from datasets with matching file prefixes
- `bark-clean-orphan-metas` -- remove orphan `.meta` files without associated datafiles
- `csv-from-waveclus` -- converts a [wave_clus](https://github.com/csn-le/wave_clus) spike time file to a csv

For processing continuously sampled data, try the [datutils](https://github.com/kylerbrown/datutils) project, which attempts to adhere to the Bark/ARF standard.

There are many tools for processing CSV files, including [pandas](http://pandas.pydata.org/) and [csvkit](https://csvkit.readthedocs.io).

## Other common tasks

- recursively search for datafile by metadata: `grep -R --include "*.meta" "source: hvc" PATH/TO/DATA`
- recursively search for an entry or root by metadata: `grep -R --include "meta" "experimenter: kjbrown" PATH/TO/DATA`
- add new metadata to file `echo "condition: control" >> FILE.meta`


# related projects

-   NEO <https://github.com/NeuralEnsemble/python-neo>
-   NWB <http://www.nwb.org/>
-   NIX <https://github.com/G-Node/nix>
-   neuroshare (<http://neuroshare.org>) is a set of routines for reading and
    writing data in various proprietary and open formats.

