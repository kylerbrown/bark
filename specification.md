# Bark
Bark is a minimal implementation of [ARF](https://github.com/melizalab/arf).

Much of this specification is adapted directly from the ARF spec. Unless a
divergence from the ARF spec is explicitly noted, any ambiguities must be
resolved in favor of the ARF spec.

This implementation leverages the hierarchical nature of the file system and three common data formats:

+ Comma separated values (CSV) text files
+ YAML
+ Raw binary arrays

All Bark data files have associated metadata files. Files that do not have
associated metadata files are ignored. Metafiles must have associated datasets.

By ignoring extra files, this system flexibly allows the inclusion of non-standard data such as videos, screenshots and notes.

An example Bark tree:

    experiment.bark/            <- root directory, optional extension
        meta                    <- top level YAML metadata
        day1/                   <- first entry; all datasets within have the same timebase
            meta                <- first entry metadata
            emg.dat             <- a first dataset
            emg.dat.meta        <- the metadata (ARF attributes) of emg.dat in YAML format
            mic.dat             <- a second dataset
            mic.dat.meta        <- metadata for the second dataset
            mic.flac            <- a file with no corresponding .meta file - it is thus ignored
            song.label          <- a third dataset, in CSV format
            song.label.meta     <- metadata for the third dataset
        
        day2_session2/          <- second entry
            emg.dat             <- a dataset in the second entry
            emg.dat.meta    
        ... etc ...


## Goals and conceptual framework

The goal of Bark is to provide an open, unified, flexible, and portable format
for storing time-varying data, along with sufficient metadata to reconstruct
the conditions of how the data were recorded for many decades in the future.

Time-varying data can be represented in two ways
([Brillinger 2008](http://dx.doi.org/10.2307/3315583)):

-   **time series:** A quantitative physical property of a system (e.g., sound
    pressure or voltage) measured as a function of time. In digital
    computers, time series data are always sampled at discrete
    moments in time, usually at fixed intervals. The *sampling
    rate* of the data is the number of times per second the value
    is sampled.
-   **point process:** A sequence of events taking place at discrete times. In a
    simple point process, events are defined only by the times
    of occurrence. In a *marked* point process, additional
    information is associated with the events.

Bioacoustic, electrophysiological, and behavioral data can all be represented
in this framework. Some examples:

-   An acoustic recording is a time series of the sound pressure level detected
    by a microphone.
-   An extracellular neural recording is a time series of the voltage measured by
    an electrode.
-   A spike train is a point process defined by the times of the action
    potentials. A spike train may also be marked by the waveforms of the spikes.
-   Stimulus presentations are a marked point process, with times indicating the
    onsets and offsets and marks indicating the identity of the presented stimulus.
-   A series of behavioral events can be represented by a point process,
    optionally marked by measurable features of the event (location, intensity,
    etc).

Clearly all of these types of data can be represented in computers as arrays. The
challenge is to organize and annotate the data in such a way that it can

1.  be unambiguously identified,
2.  be aligned with data from different sources,
3.  support a broad range of experimental designs, and
4.  be accessed with generic and widely available software.

## Implementation

A Bark tree can consist of four elements:

+ Standard filesystem directories
+ Raw binary files containing numerical data
+ Comma separated value (CSV) plain text files with a header line (see [RFC 4180](https://tools.ietf.org/html/rfc4180))
+ Strictly-named [YAML](https://en.wikipedia.org/wiki/YAML) plain text files, containing metadata following a specific structure and naming format

Standard filesystem directories support hierarchical organization of
datasets, and plaintext YAML files provide metadata attributes. BARK specifies the layout used to store data
within this framework, plus a minimal set of metadata necessary to make sense of the datasets,
while allowing the user to add metadata specific to an application.


### Roots

A *root* is a top-level directory containing a `meta` file and zero or more
*entries*.

There are no required attributes in the root `meta` file.

Root directories must not contain datasets.

### Entries

An *entry* is an abstract grouping of zero or more *datasets* that
all share a common start time. Each entry shall be represented by a directory.
The directory shall contain all the data objects associated with that entry, 
and all the metadata associated with the entry, stored
as YAML key-value pairs in a file named `meta`.

The following attributes are **required**:

-   **timestamp:** The start time of the entry. This attribute shall consist of a
    two-element array, with the first element indicating the POSIX time (number of
    seconds since January 1, 1970 UTC), and the second element
    indicating the rest of the elapsed time, in microseconds. Must
    have at least 64-bit integer precision.
-   **uuid:** A universally unique ID for the entry (see [RFC 4122](http://tools.ietf.org/html/rfc4122.html)).
    Must be stored as a string in the `meta` file; internal programmatic
    representation is handled by standard libraries.

In addition, the following optional attributes are defined. They do not need to
be present in an entry's `meta` file if not applicable.

-   **animal:** Indicates the name or ID of the experimental subject.
-   **experimenter:** Indicates the name or ID of the experimenter.
-   **protocol:** Comment field indicating the treatment, stimulus, or any other
    user-specified data.
-   **recuri:** The URI of an external database where `uuid` can be looked up.

Any other attributes may be included in an entry's `meta` file.

Example `meta` file for an entry:

    ---
    timestamp:
    - 1452891725
    - 0
    uuid: b05c865d-fb68-44de-86fc-1e95b273159c
    animal: bk196

Entry directories must not contain root or entry directories.
Any subdirectories are ignored.

### Datasets

A *dataset* is a concrete time series or point process.  Multiple
datasets may be stored in an entry, and may have different lengths or
timebases (i.e., an *offset* and a *sampling rate*).

Datasets must have a corresponding YAML file containing metadata. The name of this
metadata file must be `<dataset_filename>.meta`.

The *offset* (attribute `offset`) applies to all datasets. All time values in a
dataset are relative to the entry's timestamp plus the dataset's offset. The 
offset does not need to be explicitly specified for every dataset. If it is not
specified, it is assumed to be zero. If it is specified, its units (attribute 
`offset_units`) must also be specified. Two datasets in the same entry may have 
different offsets.

The *sampling rate* (attribute `sampling_rate`) allows discrete times to be
converted to real times. If the dataset contains time series (or *sampled*) 
data, this attribute must be present. Alternatively, if the dataset contains 
point process (or *event*) data, and the units of these data are samples, the 
sampling rate must also be specified. The only datasets which may omit the 
sampling rate attribute are point process datasets with units of seconds.

Real-valued times must be in units of seconds (`s`). Discrete-valued times must 
be in units of samples (`samples`).

#### Sampled data

Sampled data are stored in raw binary files as outlined in
[the Neurosuite documentation](http://neurosuite.sourceforge.net/formats.html).

These data shall be represented as 2-dimensional arrays of scalar values,
corresponding to the measurement during each sampling interval. The first  
dimension of the array must correspond to time, and the second to channels.

(The spec as written does not accommodate vector-valued time series such as
video, but does not disallow them.)

For multi-channel files, samples are interleaved, so files should be written
in C (or row-major) order.

ARF allows user-specified endianness, but Bark does not. All sampled data files
**must** be little-endian. This is the default for Intel x86 architectures, and
thus the vast majority of modern systems.

A raw binary file with N channels and M samples looks like this:

    c1s1, c2s1, c3s1, ..., cNs1, c1s2, c2s2, c3s2, ..., c1sM, c2sM, c3sM,...,cNsM 

There is no required extension, but `.dat` or `.pcm` are common choices.

The disadvantage of simple raw binary files is that no metadata are stored
within the file itself. Three metadata attributes are thus **required**:

- `sampling_rate`: allows discrete times to be converted to real times (Hz)
- `dtype`: the numeric type of the data, such as 16-bit integer or 32-bit
  float
- `n_channels`: the number of channels in the dataset

All other attributes are optional.

An example `.meta` file for a sampled dataset:

    ---
    sampling_rate: 30000
    dtype: int16
    n_channels: 8
    trial: 1
    units: V
    unit_scale: 0.025

#### Units

The `units` attribute must, with two exceptions, be an SI unit abbreviation.
Inference of its meaning is case sensitive (e.g., `s` means seconds, but `S`
means Siemens).

The first exception is the value `samples`, which is dimensionless in SI notation.
The second exception is a null value, to be used if the units are unknown. The null
value in YAML is `null`; in Python, use `None`.

#### Event data

Event data are stored in CSV files with a header line. Simple event data should
be stored in a single-column CSV, with each element in the array indicating the
time of the event **relative to the start of the dataset**. The first line of
the file must contain `start,`, indicating that the column contains the times
of the event data. Event datasets may be distinguished from sampled datasets in
several ways, but the only method the Bark standard guarantees relies on the
`units` attribute. Event datasets must have `units` of time - either `s` (for
seconds) or `samples`. Sampled datasets **must not** have these units.

Complex event data must be stored as arrays with multiple columns. Only one
field or column is required: `start`, which indicates the times of the events;
these values may be either integers or floating-point numbers.

Intervals are a special class of event data, and are described by `start` and
`stop` columns. They are not treated differently by Bark.

#### Dataset attributes

All datasets must have the following attributes:

- **`filetype`:** A string specifying the format of the data. The currently
  accepted formats are "csv" and "rawbinary", though others may be added
  in the future.
- **`units`:** A string giving the units of the data, which, if present, should
  be either an SI unit abbreviation, "samples", or "null" (in Python, `None`).
  Alternatively, it may be an empty string, indicating sampled data for which
  the units are unknown. Event data must have units of "samples" (for a
  discrete timebase) or "s" (for a continuous timebase); sampled data must not
  use these units. For complex event data, this attribute must be an array,
  with each element of the array indicating the units of the associated field
  in the data.

The following attribute is only required for all sampled datasets, and for
event datasets with `units` of "samples":

- **`sampling_rate`:** A nonzero positive number indicating the sampling rate
  of the data, in samples per second (Hz). May be either an integer or a
  floating-point value.

The following attributes are defined by the spec, but are optional:

- **`unit_scale`:** A multiplier to scale the raw data to match the **units**.
  Useful when raw integer data must be converted to a floating point number to
  match the correct units. If `units` is an array, `unit_scale` must be an
  array of the same shape.
- **`offset`:** Indicates the start time of the dataset relative to the
  timestamp of the entry, defined by the timebase of the dataset. For discrete timebases, the
  units must be in samples; for continuous timebases, the units must be the same
  as the units of the dataset. If this attribute is missing, the offset shall be
  assumed to be zero.
- **`uuid`:** A universally unique ID for the dataset (see
  [RFC 4122](http://tools.ietf.org/html/rfc4122.html)). Multiple datasets in
  different entries of the same file may have the same `uuid`, indicating that
  they were obtained from the same source and experimental conditions. Must be
  stored as a string.

All other attributes are optional, and may be specified by the user.
