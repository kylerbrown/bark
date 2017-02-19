# Bark
[![Build Status](https://travis-ci.org/kylerbrown/bark.svg?branch=master)](https://travis-ci.org/kylerbrown/bark)

What is Bark? Bark is a standard for electrophysiology data. By emphasizing filesystem 
directories, plain text files and simple binary arrays, Bark data can leverage a broad tool set that includes Unix commands.

Bark is also the fibrous outer layer of [ARF](https://github.com/melizalab/arf), wrapped around a few standard
file types.

Finally **BARK** is also an acronym for **B**ark is **A**rf **R**einterpreted by **K**yler.

## Why use Bark instead of ARF?

Both systems have their advantages. Because ARF datasets are encapsulated 
within HDF5, they are harder to access without using ARF-specific tools.
This protects ARF datasets from accidental loss of metadata, and helps ensure
datasets conform to the ARF specification.

Bark takes the architecture of ARF and replaces HDF5 with common data storage formats.
This makes Bark files more susceptible to losing metadata and deviating
from the specification, but gives Bark a few advantages:

+ Use standard Unix tools to explore your data (cd, ls, grep, find, mv)
+ Build robust data processing pipelines with shell scripting or
  [make](http://kbroman.org/minimal_make/).
+ Edit metadata with a standard text editor
+ Leverage any third party tools that use Bark's common data formats.
  + Raw binary tools: [Aplot](https://github.com/melizalab/aplot), [Neuroscope](http://neurosuite.sourceforge.net/), 
[Plexon Offline Sorter](http://www.plexon.com/products/offline-sorter), [Wave_clus](https://github.com/csn-le/wave_clus), 
[spyking circus](https://spyking-circus.readthedocs.io), [phy](https://github.com/kwikteam/phy), 
[datutils](https://github.com/kylerbrown/datutils), [sox](http://sox.sourceforge.net/sox.html).
  + CSV tools: R, Pandas (Python), Excel, csvkit and Unix tools like sed and
      awk.
+ Include non-standard data such as images or video in Bark entries.

## The elements of Bark
Bark trees are made from the following elements:

- A **Root** directory grouping a set of Entries together. This is a standard
  filesystem directory containing one file named "meta", which contains top-
  level metadata, and any number of Entry subdirectories.
- **Entries** (often trials) are directories containing Datasets that share a
  common time base. These directories also contain a "meta" file and any number
  of Datasets.
- **SampledData** stored as raw binary arrays. Metadata is stored in another
  file with ".meta" appended to the dataset's filename.
- **EventData** stored in CSV files. As above, metadata is stored in a ".meta"
  file.
- Every Bark element (Root, Entry, SampledData, EventData) has metadata stored in associated UTF-8-encoded YAML files.

Roots must only have Entries and Entries must only have Datasets.
However, Datasets can exist outside of Entries, and Entries can exist without Roots.

This repository contains:

-   The specification for bark (in [specification.md](specification.md))
-   A python interface for reading and writing Bark files
-   Tools to accomplish common Bark tasks

## Installation

The python interface is tested against Python 3.5. Installation with [Conda](http://conda.pydata.org/miniconda.html) is recommended.

    git clone https://github.com/kylerbrown/bark
    cd bark
    pip install -r requirements.txt
    pip install .


    # optional tests
    pytest -v


# Shell Commands

Every command has help accessible with the flag `-h` (e.g. `bark-root -h`).

- `bark-root` -- create root directories for experiments
- `bark-entry` -- create entry directories for datasets
- `bark-entry-from-prefix` -- create an entry from datasets with matching file prefixes
- `bark-clean-orphan-metas` -- remove orphan `.meta` files without associated datafiles
- `bark-scope` -- opens a Bark SampledData file in [neuroscope](http://neurosuite.sourceforge.net/). (Requires an installation of neuroscope)  
- `bark-convert-rhd` -- converts [Intan](http://intantech.com/) .rhd files to datasets in a Bark entry
- `bark-convert-openephys` -- converts a folder of [Open-Ephys](http://www.open-ephys.org/) .kwd files to datasets in a Bark entry
- `bark-split` -- splits a dataset according to the split times in a label file, either in a single entry or in an entire bark tree
- `csv-from-waveclus` -- converts a [wave_clus](https://github.com/csn-le/wave_clus) spike time file to a csv
- `csv-from-textgrid` -- converts a [praat](http://www.fon.hum.uva.nl/praat/) TextGrid file to a csv
- `csv-from-lbl` -- converts an [aplot](https://github.com/melizalab/aplot) [lbl](https://github.com/kylerbrown/lbl) file to a csv
- `csv-from-plexon-csv` -- converts a [Plexon OFS](http://www.plexon.com/products/offline-sorter) waveform csv to a bark csv.
- `dat-decimate` -- downsamples a raw binary data file by an integer factor, you want to low-pass filter your data first.
- `dat-segment` -- segments a file based on a band of spectral power, based on [Koumura & Okanoya](dx.doi.org/10.1371/journal.pone.0159188)
- `bark-label-view` -- Annotate or review events in relation to a sampled dataset, such as birdsong syllable labels on a microphone recording.

For processing continuously sampled data, try the included python moduled `bark.stream` or the 
[datutils](https://github.com/kylerbrown/datutils) project, which provide a command line interface
for common data pipelines and adhere to the Bark/ARF standard.

Over time, tools from `datutils` will migrate into `bark`.

There are many tools for processing CSV files, including [pandas](http://pandas.pydata.org/) and [csvkit](https://csvkit.readthedocs.io).

# Python interface

    import bark
    root = bark.read_root("black5")
    root.entries.keys()
    # dict_keys(['2016-01-18', '2016-01-19', '2016-01-17', '2016-01-20', '2016-01-21'])
    entry = root['2016-01-18']
    entry.attrs
    # {'bird': 'black5',
    # 'experiment': 'hvc_syrinx_screwdrive',
    # 'experimenter': 'kjbrown',
    # 'timestamp': [1453096800, 0],
    # 'uuid': 'a53d24af-ac13-4eb3-b5f4-0600a14bb7b0'}
    entry.datasets.keys()
    # dict_keys(['enr_emg.dat', 'enr_mic.dat', 'enr_emg_times.csv', 'enr_hvc.dat', 'raw.label', 'enr_hvc_times.csv', 'enr.label'])
    hvc = entry['enr_hvc.dat']
    hvc.data.shape
    # (7604129, 3)



The `Stream` object in the `bark.stream` module exposes a powerful data pipeline design system for sampled data.
Example usage:
![Example usage](bark-stream-example.png)



## Other common tasks

- Recursively search for datafile by metadata: `grep -R --include "*.meta" "source: hvc" PATH/TO/DATA`
- Recursively search for an entry or root by metadata: `grep -R --include "meta" "experimenter: kjbrown" PATH/TO/DATA`
- Add new metadata to file: `echo "condition: control" >> FILE.meta`

# Related projects

-   NEO <https://github.com/NeuralEnsemble/python-neo>
-   NWB <http://www.nwb.org/>
-   NIX <https://github.com/G-Node/nix>
-   neuroshare (<http://neuroshare.org>) is a set of routines for reading and
    writing data in various proprietary and open formats.

