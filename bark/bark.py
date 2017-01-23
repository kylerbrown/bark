# -*- coding: utf-8 -*-
# -*- mode: python -*-
from __future__ import division, print_function, absolute_import, \
        unicode_literals
from datetime import datetime, timedelta
import sys
import os.path
from os import listdir
from glob import glob
from uuid import uuid4
import yaml
import numpy as np
from bark import stream
import codecs
import collections

BUFFER_SIZE = 10000

spec_version = "0.1"
__version__ = version = "0.1"

__doc__ = """
This is BARK, a python library for storing and accessing audio and ephys data in
directories and simple file formats.

Library versions:
 bark: %s
""" % (version)

_Units = collections.namedtuple('_Units', ['TIME_UNITS'])
UNITS = _Units(TIME_UNITS=('s', 'samples'))

class DataTypes:
    """
    Available ARF data types, by name and integer code.
    
    Copied, with some modifications, from Dan Meliza's ARF repo.
    """

    UNDEFINED = 0
    ACOUSTIC = 1
    EXTRAC_HP, EXTRAC_LF, EXTRAC_EEG = range(2, 5)
    INTRAC_CC, INTRAC_VC = range(5, 7)
    EVENT, SPIKET, BEHAVET = range(1000, 1003)
    INTERVAL, STIMI, COMPONENTL = range(2000, 2003)

    @classmethod
    def _doc(cls):
        out = str(cls.__doc__)
        for code,name in sorted(cls._todict().items()):
            out += '\n{%s}:{%d}'.format(name, code)
        return out

    @classmethod
    def is_timeseries(cls, code):
        """Indicates whether the code corresponds to time series data."""
        if cls._fromcode(code) is None:
            raise KeyError('bad datatype code: {}'.format(code))
        else:
            if code < cls.EVENT:
                return True
            else:
                return False
    @classmethod
    def is_pointproc(cls, code):
        """Indicates whether the code corresponds to point process data."""
        return (not cls.is_timeseries(code))

    @classmethod
    def _todict(cls):
        """Generate a dictionary keyed by datatype code."""
        return dict((getattr(cls, attr), attr)
                     for attr in dir(cls)
                     if not attr.startswith('_'))

    @classmethod
    def _fromstring(cls, name):
        """Returns datatype code given the name, or None if undefined."""
        return getattr(cls, name.upper(), None)

    @classmethod
    def _fromcode(cls, code):
        """Returns datatype name given the code, or None if undefined."""
        return cls._todict().get(code, None)

# hierarchical classes
class Root():
    def __init__(self, path, entries=None, attrs=None):
        if entries is None or attrs is None:
            self.read(path)
        else:
            self.entries = entries
            self.path = path
            self.name = os.path.split(path)[-1]
            self.attrs = attrs

    def read(self, name):
        self.path = os.path.abspath(name)
        self.name = os.path.split(path)[-1]
        self.attrs = read_metadata(os.path.join(path, "meta"))
        all_sub = [os.path.join(name, x) for x in listdir(path)]
        subdirs = [x for x in all_sub if os.path.isdir(x) and x[-1] != '.']
        self.entries = {os.path.split(x)[-1]: read_entry(x) for x in subdirs}

    def __getitem__(self, item):
        return self.entries[item]

    def __len__(self):
        return self.entries.__len__()

    def __contains__(self, item):
        return self.entries.__contains__(item)


class Entry():
    def __init__(self, datasets, path, attrs):
        self.datasets = datasets
        self.path = path
        self.name = os.path.split(path)[-1]
        self.attrs = attrs
        self.timestamp = timestamp_to_datetime(attrs["timestamp"])
        self.uuid = attrs["uuid"]

    def __getitem__(self, item):
        return self.datasets[item]

    def __len__(self):
        return self.datasets.__len__()

    def __contains__(self, item):
        return self.datasets.__contains__(item)

    def __lt__(self, other):
        return self.timestamp < other.timestamp


class Data():
    def __init__(self, data, path, attrs):
        self.data = data
        self.path = path
        self.attrs = attrs
        self.name = os.path.split(path)[-1]

    def __getitem__(self, item):
        return self.data[item]
    
    @property
    def datatype_name(self):
        """Returns the name of the dataset's datatype, or None if unspecified."""
        return DataTypes._fromcode(self.attrs.get('datatype', None))


class SampledData(Data):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sampling_rate = self.attrs['sampling_rate']

    def toStream(self):
        return stream.read(self.path)

    def write(self, path=None):
        if path is None:
            path = self.path
        write_sampled(self.path, self.data, **self.attrs)


class EventData(Data):
    def write(self, path=None):
        "Saves data to file"
        if path is None:
            path = self.path
        write_events(path, self.data, **self.attrs)


def write_sampled(datfile, data, sampling_rate, units, **params):
    if len(data.shape) == 1:
        params["n_channels"] = 1
    else:
        params["n_channels"] = data.shape[1]
    params["dtype"] = data.dtype.name
    shape = data.shape
    mdata = np.memmap(datfile, dtype=params["dtype"], mode="w+", shape=shape)
    mdata[:] = data[:]
    params["filetype"] = "rawbinary"
    write_metadata(datfile + ".meta",
                   sampling_rate=sampling_rate,
                   units=units,
                   **params)
    params['sampling_rate'] = sampling_rate
    params['units'] = units
    return SampledData(mdata, datfile, params)


def load_dat(datfile, mode="r"):
    """ loads raw binary file

    mode may be "r" or "r+"; use "r+" for modifiying the data (not
    recommended).

    does NOT return a SampledData object - use read_sampled instead.
    """
    params = read_metadata(datfile)
    data = np.memmap(datfile, dtype=params["dtype"], mode=mode)
    data = data.reshape(-1, params["n_channels"])
    return data, params

def read_sampled(datfile, mode="r"):
    """ loads raw binary file

    mode may be "r" or "r+"; use "r+" for modifiying the data (not
    recommended).
    """
    path = os.path.abspath(datfile)
    params = read_metadata(datfile + ".meta")
    data = np.memmap(datfile, dtype=params["dtype"], mode=mode)
    data = data.reshape(-1, params["n_channels"])
    return SampledData(data, path, params)


def write_events(eventsfile, data, **params):
    assert "units" in params and params["units"] in UNITS.TIME_UNITS
    data.to_csv(eventsfile, index=False)
    params["filetype"] = "csv"
    write_metadata(eventsfile + ".meta", **params)
    return read_events(eventsfile)


def read_events(eventsfile):
    import pandas as pd
    data = pd.read_csv(eventsfile)
    params = read_metadata(eventsfile + ".meta")
    return EventData(data, eventsfile, params)


def read_dataset(fname):
    "determines if file is sampled or event data and reads accordingly"
    params = read_metadata(fname + ".meta")
    if "units" in params and params["units"] in UNITS.TIME_UNITS:
        dset = read_events(fname)
    else:
        dset = read_sampled(fname)
    return dset


def read_metadata(metafile):
    try:
        with codecs.open(metafile, 'r', encoding='utf-8') as fp:
            params = yaml.safe_load(fp)
        return params
    except IOError as err:
        fname = os.path.splitext(metafile)[0]
        if fname == "meta":
            return {}
        print("""
{dat} is missing an associated .meta file, which should be named {dat}.meta

The .meta is plaintext YAML file of the following format:

---
dtype: int16
n_channels: 4
sampling_rate: 30000.0

(you may include any other metadata you like, such as experimenter, date etc.)

to create a .meta file interactively, type:

$ dat-meta {dat}
        """.format(dat=metafile))
        sys.exit(0)

def write_metadata(filename, **params):
    for k, v in params.items():
        if isinstance(v, (np.ndarray, np.generic)):
            params[k] = v.tolist()
    with codecs.open(filename, 'w', encoding='utf-8') as yaml_file:
        header = """# metadata using YAML syntax\n---\n"""
        yaml_file.write(header)
        yaml_file.write(yaml.safe_dump(params, default_flow_style=False))


def create_root(name, parents=False, **attrs):
    """creates a new BARK top-level directory"""
    path = os.path.abspath(name)
    if os.path.isdir(path):
        if not parents:
            raise IOError("{} already exists".format(path))
    else:
        os.makedirs(path)
    write_metadata(os.path.join(path, "meta"), **attrs)
    return read_root(name)


def read_root(name):
    return Root(name)


def create_entry(name, timestamp, parents=False, **attributes):
    """Creates a new BARK entry under group, setting required attributes.

    An entry is an abstract collection of data which all refer to the same time
    frame. Data can include physiological recordings, sound recordings, and
    derived data such as spike times and labels. See add_data() for information
    on how data are stored.

    name -- the name of the new entry. any valid python string.

    timestamp -- timestamp of entry (datetime object, or seconds since
               January 1, 1970). Can be an integer, a float, or a tuple
               of integers (seconds, microsceconds)

    parents -- if True, no error is raised if file already exists. Metadata
                is overwritten

    Additional keyword arguments are set as attributes on created entry.

    Returns: newly created entry object
    """
    path = os.path.abspath(name)
    if os.path.isdir(path):
        if not parents:
            raise IOError("{} already exists".format(path))
    else:
        os.makedirs(path)

    if "uuid" not in attributes:
        attributes["uuid"] = str(uuid4())
    attributes["timestamp"] = convert_timestamp(timestamp)
    write_metadata(os.path.join(name, "meta"), **attributes)
    return read_entry(name)


def read_entry(name):
    path = os.path.abspath(name)
    dsets = {}
    attrs = read_metadata(os.path.join(path, "meta"))
    # load only files with associated metadata files
    dset_metas = glob(os.path.join(path, "*.meta"))
    dset_full_names = [x[:-5] for x in dset_metas]
    dset_names = [os.path.split(x)[-1] for x in dset_full_names]
    datasets = {name: read_dataset(full_name)
                for name, full_name in zip(dset_names, dset_full_names)}
    return Entry(datasets, path, attrs)


def convert_timestamp(obj):
    """Makes a BARK timestamp from an object.

    Argument can be a datetime.datetime object, a time.struct_time, an integer,
    a float, or a tuple of integers. The returned value is a numpy array with
    the integer number of seconds since the Epoch and any additional
    microseconds.

    Note that because floating point values are approximate, the conversion
    between float and integer tuple may not be reversible.

    """
    import numbers
    from datetime import datetime
    from time import mktime, struct_time

    out = np.zeros(2, dtype='int64')
    if isinstance(obj, datetime):
        out[0] = mktime(obj.timetuple())
        out[1] = obj.microsecond
    elif isinstance(obj, struct_time):
        out[0] = mktime(obj)
    elif isinstance(obj, numbers.Integral):
        out[0] = obj
    elif isinstance(obj, numbers.Real):
        out[0] = obj
        out[1] = (obj - out[0]) * 1e6
    else:
        try:
            out[:2] = obj[:2]
        except:
            raise TypeError("unable to convert %s to timestamp" % obj)
    return out


def timestamp_to_datetime(timestamp):
    """Converts a BARK timestamp to a datetime.datetime object (naive local time)"""
    obj = datetime.fromtimestamp(timestamp[0])
    return obj + timedelta(microseconds=int(timestamp[1]))


def timestamp_to_float(timestamp):
    """Converts a BARK timestamp to a floating point value (sec since epoch) """
    return np.dot(timestamp, (1.0, 1e-6))


def parse_timestamp_string(string):
    if len(string) == len("YYYY-MM-DD"):
        timestamp = datetime.strptime(string, "%Y-%m-%d")
    elif len(string) == len("YYYY-MM-DD_HH-MM_SS"):
        timestamp = datetime.strptime(string, "%Y-%m-%d_%H-%M-%S")
    else:
        timestamp = datetime.strptime(string, "%Y-%m-%d_%H-%M-%S.%f")
    return timestamp


def get_uuid(obj):
    """Returns the uuid for obj, or None if none is set"""
    return obj.attrs.get('uuid', None)
