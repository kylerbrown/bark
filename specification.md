# Bark
Bark is a minimal implementation of [ARF](https://github.com/melizalab/arf).

Much of this specification is copied directly from the ARF spec, and the ARF spec is sole source of truth if there are any ambiguities.

This implementation leverages the hierarchical nature of the file system and three common data formats:

+ comma separated vectors (CSV)
+ YAML 
+ Raw binary arrays

Conversion between ARF and Bark files should be easy as 
only the implementation is different.

An example BARK tree:

    experiment.bark/        <- optional extension
        meta                <- top level YAML metadata
        day1/               <- first entry, all datasets within have the same timebase
            meta            <- first entry metadata
            emg.dat         <- an EMG dataset
            emg.dat.meta    <- the metadata (attributes of emg.dat in YAML format)
            mic.dat         <- a second dataset
            mic.dat.meta
            song.label      <- a third dataset, in CSV format
            song.label.meta     <- meta data for the third dataset
        
        day2_session2/      <- second entry
            emg.dat         <- a dataset in the second entry
            emg.dat.meta    
        ... etc ...

Files that do not have associated `.meta` files are ignored. Metafiles must have associated datasets.


## Goals and conceptual framework

The goal of BARK is to provide an open, unified, flexible, and portable format
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

-   an acoustic recording is a time series of the sound pressure level detected
    by a microphone
-   an extracellular neural recording is a time series of the voltage measured by
    an electrode
-   a spike train is an unmarked point process defined by the times of the action
    potentials. A spike train could also be marked by the waveforms of the spikes.
-   stimuli presentations are a marked point process, with times indicating the
    onsets and offsets and marks indicating the identity of the presented stimulus
-   a series of behavioral events can be represented by a point process,
    optionally marked by measurable features of the event (location, intensity,
    etc)

Clearly all these types of data can be represented in computers as arrays. The
challenge is to organize and annotate the data in such a way that it can

1.  be unambiguously identified,
2.  be aligned with data from different sources,
3.  support a broad range of experimental designs, and
4.  be accessed with generic and widely available software

## Implementation

A Bark tree can consist of four elements:

+ Standard filesystem directories
+ Raw binary files containing numerical data
+ comma separated vector (csv) plain text files with a header line
+ strictly named [YAML](https://en.wikipedia.org/wiki/YAML) plain text files, containing metadata, with a specific structure and naming format.

Standard filesystem directories support hierarchical organization of
datasets and plaintext YAML files provide metadata attributes. BARK specifies the layout used to store data
within this framework, while allowing the user to add metadata specific to an
application.

### Entries

An *entry* is defined as an abstract grouping of zero or more *datasets* that
all share a common start time. Each *entry* shall be represented by a directory.
The directory shall contain all the data objects associated with that entry, 
and all the metadata associated with the entry, stored
as YAML key-value pairs in a file named `meta`. The following attributes are required:

-   **timestamp:** The start time of the entry. This attribute shall consist of a
    two-element array with the first element indicating the number of
    seconds since January 1, 1970 UTC, and the second element
    indicating the rest of the elapsed time, in microseconds. Must
    have at least 64-bit integer precision.
-   **uuid:** A universally unique ID for the entry (see [RFC 4122](http://tools.ietf.org/html/rfc4122.html)). Must be stored
    as a 128-bit integer or a 36-byte `H5T_STRING` with `CTYPE` of
    `H5T_C_S1`. The latter is preferred as 128-bit integers are not
    supported on many platforms.

In addition, the following optional attributes are defined. They do not need to
be present in the group if not applicable.

-   **animal:** Indicates the name or ID of the animal.
-   **experimenter:** Indicates the name or ID of the experimenter.
-   **protocol:** Comment field indicating the treatment, stimulus, or any other
    user-specified data.
-   **recuri:** The URI of an external database where `uuid` can be looked up.

### Datasets

A *dataset* is defined as a concrete time series or point process.  Multiple
datasets may be stored in an entry, and may be unequal in length or have
different *timebases*.

Attributes are stored in a YAML file with `.meta` appended to the dataset name.

A *timebase* is defined by two quantities (with units), one of which is optional
under some circumstances. The required quantity is the *offset* of the data.
All time values in a dataset are relative to this time.  The default offset of
a dataset is the timestamp of the entry.  Individual datasets may have their
own offsets, which are calculated relative to the entry timestamp.

The second quantity in a timebase is the *sampling rate*, which allows discrete
times to be converted to real times. It is required if the data are sampled (as
in a time series) or if time values in a point process are in units of samples.
Only point processes with real-valued units of time may omit the sampling rate.

Real-valued times must be in units of seconds. Discrete-valued times must be in
units of samples.

#### Sampled data

Sampled data are stored in raw binary files as outlined 
[here](http://neurosuite.sourceforge.net/formats.html).

For multi-channel files, samples are interleaved. A raw binary file with N channels and M samples looks like this:

    c1s1, c2s1, c3s1, ..., cNs1, c1s2, c2s2, c3s2, ..., c1sM, c2sM, c3sM,...,cNsM 


There is no required extension, however `.dat` or `.pcm` are common choices.

Sampled data shall be stored as an N-dimensional array of scalar values
corresponding to the measurement at each sampling interval. The first dimension
of the array must correspond to time. The second dimension corresponds to channels.
The `sampling_rate` attribute is required.

The disadvantage of simple raw binary files is that no metadata are stored within the file itself. At a minimum three values a required to read a raw binary file:

- sampling rate, such as 30000
- numeric type, such as 16 bit integer or 32 bit float
- number of channels, such as 32

For all sampled data files, the endianness is *MUST* be little-endian. 
This is the default for Intel x86 and the vast majority of modern systems.

#### Event data

Event data are stored in CSV files. Simple event data should be
stored in a single column CSV, with each element in the array indicating the time of the
event **relative to the start of the dataset**. The first line of the file must contain `start,`,
indicating that the column contains the times of the event data. Event datasets can be
distinguished from sampled datasets because the file is a plaintext CSV and `units` attribute must be
"samples" or "s".

Complex event data must be stored as arrays with multiple columns. Only one field is required, `start`, which indicates the time of the event and can be any numerical type.

A special case of event data are intervals, which are defined by a start and
stop time. In previous versions of the specification, intervals were considered
a separate data type, with two additional required fields, `name` (a string) and
`stop` (a time with the same units as start). 

#### Dataset attributes

All datasets must have the following attributes.

- **units:** A string giving the units of the channel data, which should be in
  SI notation. May be an empty string for sampled data if units are not known.
  Event data must have units of "samples" (for a discrete timebase) or "s" (for
  a continuous timebase); sampled data must not use these units. For complex
  event data, this attribute must be an array, with each element of the array
  indicating the units of the associated field in the data.
- **datatype:** Indicates the source of data in the entry. Must have at least
  unsigned integer precision great enough to include all the values defined in
  5.2.4.

The following attribute is only required for datasets with a discrete timebase:

- **sampling\_rate:** A nonzero number indicating the sampling rate of the data,
  in samples per second (Hz). Required for all datasets with a sampled timebase.
  May be any numerical datatype.

The following attributes are optional:

- **unit\_scale** A multiplier to scale the raw data to match the **units**. Useful
  when raw integer data must be converted to a floating point number to match the correct units.
  If **units** is an array, **unit\_scale** must be an array of the same shape.
- **offset:** Indicates the start time of the dataset relative to the start of
  the entry, defined by the timebase of the dataset. For discrete timebases, the
  units must be in samples; for continuous timebases, the units must be the same
  as the units of the dataset. If this attribute is missing, the offset shall be
  assumed to be zero.
- **uuid:** A universally unique ID for the dataset (see
  [RFC 4122](http://tools.ietf.org/html/rfc4122.html)). Multiple datasets in
  different entries of the same file may have the same uuid, indicating that
  they were obtained from the same source and experimental conditions. Must be
  stored as a 128-bit integer or a 36-byte `H5T_STRING` with `CTYPE` of
  `H5T_C_S1`. The latter is preferred as 128-bit integers are not supported on
  many platforms.

####  Datatypes

The `datatype` attribute is an integer code indicating the type of data in a
channel. This field is purely advisory: it specifies how the data should be
interpreted but does not imply any contract as to the dataspace or storage type
of the dataset. The following values are defined:


       0    UNDEFINED   undefined or unknown
       1    ACOUSTIC    acoustic
       2    EXTRAC_HP   extracellular, high-pass (single-unit or multi-unit)
       3    EXTRAC_LF   extracellular, local-field
       4    EXTRAC_EEG  extracellular, EEG
       5    INTRAC_CC   intracellular, current-clamp
       6    INTRAC_VC   intracellular, voltage-clamp
      23    EXTRAC_RAW  extracellular, wide-band
    1000    EVENT       generic event times
    1001    SPIKET      spike event times
    1002    BEHAVET     behavioral event times
    2000    INTERVAL    generic intervals
    2001    STIMI       stimulus presentation intervals
    2002    COMPONENTL  component (e.g. motif) labels

Values below 1000 are reserved for sampled data types.

