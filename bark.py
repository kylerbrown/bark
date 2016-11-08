# -*- coding: utf-8 -*-
# -*- mode: python -*-
from __future__ import division, print_function, absolute_import, \
        unicode_literals
import sys
import os.path
from collections import namedtuple
from uuid import uuid4
import yaml
import numpy as np
import pandas as pd

BUFFER_SIZE = 10000

spec_version = "1.0"
__version__ = version = "1.0"

__doc__ = """
This is BARK, a python library for storing and accessing audio and ephys data in
directories and simple file formats.

Library versions:
 bark: %s
""" % (version)

# heirarchical classes
Toplevel = namedtuple('Toplevel', ['entries', 'path', 'attrs'])
Entry = namedtuple('Entry', ['datasets', 'path', 'attrs'])
SampledData = namedtuple('SampledData', ['data', 'path', 'attrs'])
EventData = namedtuple('EventData', ['data', 'path', 'attrs'])

def create_toplevel(name, **attrs):
    os.makedirs(name)
    write_metadata(os.path.join(name, "meta"), **attrs)
    return Toplevel([], name)


def create_entry(name, toplevel, **attrs):
    path = os.path.join(toplevel.path, name)
    os.makedirs(path)
    write_metadata(os.path.join(name, "meta"), **attrs)
    topleve.entries[name] = Entry([], path, attrs)


def create_events(labelfile, data, **params):
    assert "units" in params and params["units"] in ["s" or "samples"]
    data.to_csv(eventsfile, index=False)
    write_metadata(eventsfile+".meta", **params)


def create_sampled(datfile, data=None, **params):
    if data is not None:
        shape = data.shape
        params["n_samples"] = shape[0]
        if len(data.shape) == 1:
            params["n_channels"] = 1 
        else: 
            params["n_channels"] = shape[1]
    elif "n_samples" in params and "n_channels" in params:
        shape = (params["n_samples"], params["n_channels"])
    else:
        shape = None
    mdata = np.memmap(datfile,
                     dtype=params["dtype"],
                     mode="w+",
                     shape=shape)
    if data is not None:
        mdata[:] = data[:]
    write_metadata(datfile + ".meta", **params)
    return SampleData(data, datfile, params)


def load_events(eventsfile)
    data = pd.read_csv(eventsfile)
    params = read_metadata(eventsfile + ".meta")
    return EventData(data, eventsfile, params)


def load_dat(datfile, mode="r"):
    """ loads raw binary file

    mode may be "r" or "r+", use "r+" for modifiying the data (not
    recommended).
    """
    params = read_metadata(datfile)
    data = np.memmap(datfile, dtype=params["dtype"], mode=mode)
    data = data.reshape(-1, params["n_channels"])
    return data, params


def read_metadata(metafile):
    try:
        with open(metafile, 'r') as fp:
            params = yaml.load(fp)
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
        """.format(dat=datfile))
        sys.exit(0)


def write_metadata(filename, **params):
    for k, v in params.items():
        if isinstance(v, (np.ndarray, np.generic)):
            params[k] = v.tolist()
    with open(filename, 'w') as yaml_file:
        header = """# metadata using YAML syntax\n---\n"""
        yaml_file.write(header)
        yaml_file.write(yaml.dump(params, default_flow_style=False))


def open_file(name, mode=None, **kwargs):
    """Opens an BARK "file", creating as necessary.
    """
    if os.path.isdir(name) and mode in ('r', None):
        pass  # TODO load entries as dictionary
    elif mode is ('w', None):
        os.makedirs(name)
        return Toplevel(entries={}, path=name)

def create_entry(group, name, timestamp, **attributes):
    """Creates a new BARK entry under group, setting required attributes.

    An entry is an abstract collection of data which all refer to the same time
    frame. Data can include physiological recordings, sound recordings, and
    derived data such as spike times and labels. See add_data() for information
    on how data are stored.

    name -- the name of the new entry. any valid python string.

    timestamp -- timestamp of entry (datetime object, or seconds since
               January 1, 1970). Can be an integer, a float, or a tuple
               of integers (seconds, microsceconds)

    Additional keyword arguments are set as attributes on created entry.

    Returns: newly created entry object
    """
    path = os.path.join(toplevel.path, name)
    os.makedirs(path)
    if "uuid" not in attributes:
        attributes["uuid"] = uuid4() 
    attributes["timestamp"] = convert_timestamp(timestamp)
    write_metadata(os.path.join(name, "meta"), **attributes)
    e = Entry([], path, attributes)
    topleve.entries[name] = e 
    return e


def create_dataset(group, name, data, units='', datatype=DataTypes.UNDEFINED,
                   chunks=True, maxshape=None, compression=None,
                   **attributes):
    """Creates an BARK dataset under group, setting required attributes

    Required arguments:
    name --   the name of dataset in which to store the data
    data --   the data to store

    Data can be of the following types:

    * sampled data: an N-D numerical array of measurements
    * a pandas dataframe, with the field 'start' required

    Optional arguments:
    datatype --      a code defining the nature of the data in the channel
    units --         channel units (optional for sampled data, otherwise required)
    sampling_rate -- required for sampled data and event data with units=='samples'

    Additional arguments are set as attributes on the created dataset

    Returns the created dataset
    """
    srate = attributes.get('sampling_rate', None)
    # check data validity before doing anything
    assert isinstance(data, pd.DataFrame) or "dtype" in attributes
    if units == '':
        if srate is None or not srate > 0:
            raise ValueError(
                "unitless data assumed time series and requires sampling_rate attribute")
    elif units == 'samples':
        if srate is None or not srate > 0:
            raise ValueError(
                "data with units of 'samples' requires sampling_rate attribute")
    # NB: can't really catch case where sampled data has units but doesn't
    # have sampling_rate attribute

    if isinstance(data, pd.DataFrame):
        create_events(labelfile, params
    dset = group.create_dataset(
        name, data=data,)
    set_attributes(dset, units=units, datatype=datatype, **attributes)
    return dset


def set_attributes(node, overwrite=True, **attributes):
    """Sets multiple attributes on node.

    If overwrite is False, and the attribute already exists, does nothing. If
    the value for a key is None, the attribute is deleted.

    """
    aset = node.attrs
    for k, v in attributes.items():
        if not overwrite and k in aset:
            pass
        elif v is None:
            if k in aset:
                del aset[k]
        else:
            aset[k] = v
    write_metadata(node.path + ".meta", aset)
    return aset


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
    """Converts an BARK timestamp a datetime.datetime object (naive local time)"""
    from datetime import datetime, timedelta
    obj = datetime.fromtimestamp(timestamp[0])
    return obj + timedelta(microseconds=int(timestamp[1]))


def timestamp_to_float(timestamp):
    """Converts an BARK timestamp to a floating point (sec since epoch) """
    return np.dot(timestamp, (1.0, 1e-6))


def get_uuid(obj):
    """Returns the uuid for obj, or None if none is set"""
    return obj.attrs.get('uuid', None)


def count_children(obj):
    """Returns the number of children of obj"""
    if isinstance(obj, Toplevel):
        return len(obj.entries)
    else:
        return len(obj.datasets)


def is_sampled(dset):
    """Returns True if dset is a sampled time series (units are not time)"""
    return isinstance(dset, np.memmap)


def is_events(dset):
    """Returns True if dset is a marked point process (a complex dtype with 'start' field)"""
    return isinstance(dset.data, pd.DataFrame) and 'start' in dset.data.columns

