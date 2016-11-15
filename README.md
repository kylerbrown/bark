## Bark

What is Bark? Bark is [ARF](https://github.com/melizalab/arf), but 
uses simple file formats and the filesystem heirarchy to save experimental data and analysis.

The elements of a Bark tree:

- A Root directory grouping a set of entries together
- Entries (often trials) are directories containing datasets that share a common time base.
- Continuously sampled datasets are stored as raw binary arrays
- Event data is are stored in CSV files. 
- Every bark element (Root, Entry, SampledData, EventData) has metadata are stored in associated YAML files.

This repository contains:

-   The specification for bark (in specification.md)
-   A python interface for reading and writing bark files
-   Scripts for basic BARK tasks

### contributing

Bark was really just created to help the author process his own data. 
Contributions are vanishingly unlikely, but warmly welcomed.

### installation

The python interface requires Python 2.6+ or 3.2+, numpy, PyYAML and pandas.

    git clone https://github.com/kylerbrown/bark
    cd bark
    pip install -r requirements.txt 
    pip install .


    # optional tests
    pytest -v


## scripts

- `bark-root` -- create root directories for experiments
- `bark-entry` -- create entry directories for datasets

For data related scripts see the [datutils](https://github.com/kylerbrown/datutils) project.

### related projects

-   NEO <https://github.com/NeuralEnsemble/python-neo>
-   NWB <http://www.nwb.org/>
-   NIX <https://github.com/G-Node/nix>
-   neuroshare (<http://neuroshare.org>) is a set of routines for reading and
    writing data in various proprietary and open formats.

