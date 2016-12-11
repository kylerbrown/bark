# Bark
[![Build Status](https://travis-ci.org/kylerbrown/bark.svg?branch=master)](https://travis-ci.org/kylerbrown/bark)

What is Bark? Bark is a standard for electrophysiology data. By emphasizing filesystem 
directories, plain text files and simple binary arrays, Bark data can leverage a broad tool set that includes Unix commands.

Bark is also the fibrous outer layer of [ARF](https://github.com/melizalab/arf), wrapped around a few standard
file types.

## Why use Bark instead of ARF?

Both systems have their advantages. Because ARF datasets are encapsulated 
within HDF5, they are harder to access without using ARF-specific tools.
This protects ARF datasets from accidental loss of metadata, and helps ensure
datasets conform to the ARF specification.

Bark takes the architecture of ARF and replaces HDF5 with common data storage  
formats. This makes Bark files more susceptible to loosing metadata and deviating
from the specification, but gives Bark a few advantages:

+ Use standard unix tools to explore your data (cd, ls, grep, find, mv)
+ Build robust data processing pipelines with shell scripting or
  [make](http://kbroman.org/minimal_make/).
+ Edit metadata with a standard text editor
+ Leverage any third party tools that use Barks common data formats.
  + Raw binary tools: [Aplot](https://github.com/melizalab/aplot), [Neuroscope](http://neurosuite.sourceforge.net/), 
[Plexon Offline Sorter](http://www.plexon.com/products/offline-sorter), [Wave_clus](https://github.com/csn-le/wave_clus), 
[spyking circus](https://spyking-circus.readthedocs.io), [phy](https://github.com/kwikteam/phy), 
[datutils](https://github.com/kylerbrown/datutils).
  + CSV tools: R, Pandas (Python), Excel, csvkit and unix tools like sed and
      awk.
+ Include non-standard data such as image or video in Bark entries.

## The elements of Bark
Bark trees are made from the following elements:

- A **Root** directory grouping a set of entries together, this is a standard
  filesystem directory containing one file named "meta" which contains top-level
  metadata, and any number of Entry subdirectories.
- **Entries** (often trials) are directories containing datasets that share a common time base.
  These directories also contain a "meta" file and any number of Datasets.
- **SampledData** stored as raw binary arrays, metadata is stored in another
  file with ".meta" appended to the datasets filename.
- **EventData** stored in CSV files, again, metadata is stored in a ".meta" file.
- Every Bark element (Root, Entry, SampledData, EventData) has metadata stored in associated YAML files.

Roots must only have Entries and Entries must only have Datasets.
However, Datasets can exist outside of Entries, and Entries can exists without Roots.

This repository contains:

-   The specification for bark (in [specification.md](specification.md))
-   A python interface for reading and writing Bark files
-   Scripts for Bark tasks

## Installation

The python interface is tested against Python 3.5. Installation with [Conda](http://conda.pydata.org/miniconda.html) recommended.

    git clone https://github.com/kylerbrown/bark
    cd bark
    pip install -r requirements.txt
    pip install .


    # optional tests
    pytest -v


# Shell Commands

Every command has help accessible with the flag `-h`, e.g. `bark-root -h`.

- `bark-root` -- create root directories for experiments
- `bark-entry` -- create entry directories for datasets
- `bark-entry-from-prefix` -- create an entry from datasets with matching file prefixes
- `bark-clean-orphan-metas` -- remove orphan `.meta` files without associated datafiles
- `bark-scope` -- opens a Bark SampledData file in [neuroscope](http://neurosuite.sourceforge.net/). (Requires an installation of neuroscope)  
- `bark-convert-rhd` -- converts [Intan](http://intantech.com/) .rhd files to datasets in a Bark entry
- `bark-convert-openephys` -- converts a folder of [Open-Ephys](http://www.open-ephys.org/) .kwd files to datasets in a Bark entry
- `csv-from-waveclus` -- converts a [wave_clus](https://github.com/csn-le/wave_clus) spike time file to a csv
- `csv-from-textgrid` -- converts a [praat](http://www.fon.hum.uva.nl/praat/) TextGrid file to a csv

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

