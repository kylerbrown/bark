# -*- coding: utf-8 -*-
# -*- mode: python -*-
import numpy as nx
from h5py.version import version as h5py_version, hdf5_version

spec_version = "2.0"
__version__ = version = "2.1.0"

__doc__ = """
This is ARF, a python library for storing and accessing audio and ephys data in
HDF5 containers.

Library versions:
 arf: %s
 h5py: %s
 HDF5: %s
""" % (version, h5py_version, hdf5_version)

# some constants and enumerations
_interval_dtype = nx.dtype([('name', 'S256'), ('start', 'f8'), ('stop', 'f8')])


class DataTypes:

    """
    Available data types, by name and integer code:
    """
    UNDEFINED, ACOUSTIC, EXTRAC_HP, EXTRAC_LF, EXTRAC_EEG, INTRAC_CC, INTRAC_VC = range(
        0, 7)
    EVENT, SPIKET, BEHAVET = range(1000, 1003)
    INTERVAL, STIMI, COMPONENTL = range(2000, 2003)

    @classmethod
    def _doc(cls):
        out = str(cls.__doc__)
        for v, k in sorted(cls._todict().items()):
            out += '\n%s:%d' % (k, v)
        return out

    @classmethod
    def _todict(cls):
        """ generate a dict keyed by value """
        return dict((getattr(cls, attr), attr) for attr in dir(cls) if not attr.startswith('_'))

    @classmethod
    def _fromstring(cls, s):
        """ look up datatype by string; returns None if not defined """
        return getattr(cls, s.upper(), None)


def open_file(name, mode=None, driver=None, libver=None, userblock_size=None, **kwargs):
    """Open an ARF file, creating as necessary.

    Use this instead of h5py.File to ensure that root-level attributes and group
    creation property lists are set correctly.

    """
    from h5py import h5p
    from h5py._hl import files

    fcpl = h5p.create(h5p.FILE_CREATE)
    fcpl.set_link_creation_order(h5p.CRT_ORDER_TRACKED | h5p.CRT_ORDER_INDEXED)
    fapl = files.make_fapl(driver, libver, **kwargs)
    return files.File(files.make_fid(name, mode, userblock_size, fapl, fcpl))
    return fp


def create_entry(obj, name, timestamp, **attributes):
    """Create a new ARF entry under obj, setting required attributes.

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
    # create group using low-level interface to store creation order
    from h5py import h5p, h5g, _hl
    try:
        gcpl = h5p.create(h5p.GROUP_CREATE)
        gcpl.set_link_creation_order(
            h5p.CRT_ORDER_TRACKED | h5p.CRT_ORDER_INDEXED)
        grp = _hl.Group(h5g.create(obj.id, name, lcpl=None, gcpl=gcpl))
    except AttributeError:
        grp = obj.create_group(name)
    set_uuid(grp, attributes.pop("uuid", None))
    set_attributes(grp,
                   timestamp=convert_timestamp(timestamp),
                   **attributes)
    return grp


def create_dataset(obj, name, data, units='', datatype=DataTypes.UNDEFINED,
                   chunks=True, maxshape=None, compression=None,
                   **attributes):
    """Create an ARF dataset under obj, setting required attributes

    Required arguments:
    name --   the name of dataset in which to store the data
    data --   the data to store, as one of the types described above. convert to numpy array first!

    Data can be of the following types:

    * sampled data: an N-D numerical array of measurements
    * "simple" event data: a 1-D array of times
    * "complex" event data: a 1-D array of records, with field 'start' required

    Optional arguments:
    datatype --      a code defining the nature of the data in the channel
    units --         channel units (optional for sampled data, otherwise required)
    sampling_rate -- required for sampled data and event data with units=='samples'

    Arguments passed to h5py:
    maxshape --    make the node resizable up to this shape. Use None for axes that
                   need to be unlimited.
    chunks --      specify the chunk size. The optimal chunk size depends on the
                   intended use of the data. For single-channel sampled data the
                   auto-chunking (True) is probably best.
    compression -- compression strategy. Can be 'gzip', 'szip', 'lzf' or an integer
                   in range(10) specifying gzip(N).  Only gzip is really portable.

    Additional arguments are set as attributes on the created dataset

    Returns the created dataset
    """
    srate = attributes.get('sampling_rate', None)
    # check data validity before doing anything
    if not hasattr(data, 'dtype'):
        data = nx.asarray(data)
        if data.dtype.kind in ('S', 'O'):
            raise ValueError(
                "data must be in array with numeric or compound type")
    if not data.dtype.isbuiltin:
        if 'start' not in data.dtype.names:
            raise ValueError("complex event data requires 'start' field")
        if units == '' or (not isinstance(units, basestring) and len(units) != len(data.dtype.names)):
            raise ValueError(
                "complex event data requires array of units, one per field")
    if units == '':
        if not data.dtype.isbuiltin:
            raise ValueError("event data requires units")
        if srate is None or not srate > 0:
            raise ValueError(
                "unitless data assumed time series and requires sampling_rate attribute")
    elif units == 'samples':
        if srate is None or not srate > 0:
            raise ValueError(
                "data with units of 'samples' requires sampling_rate attribute")
    # NB: can't really catch case where sampled data has units but doesn't
    # have sampling_rate attribute

    dset = obj.create_dataset(
        name, data=data, maxshape=maxshape, chunks=chunks, compression=compression)
    set_attributes(dset, units=units, datatype=datatype, **attributes)
    return dset


def create_table(group, name, dtype, **attributes):
    """Create a new array dataset with compound datatype and maxshape=(None,)"""
    dset = group.create_dataset(
        name, shape=(0,), dtype=dtype, maxshape=(None,))
    set_attributes(dset, **attributes)
    return dset


def append_data(dset, data):
    """Append new data to a dataset along axis 0"""
    assert all(x == y for x, y in zip(dset.shape[1:], data.shape[1:]))
    if dset.dtype.fields is not None:
        assert dset.dtype == data.dtype
    if data.size == 0:
        return
    oldlen = dset.shape[0]
    newlen = oldlen + data.shape[0]
    dset.resize(newlen, axis=0)
    dset[oldlen:] = data


def check_file_version(file):
    """Check the ARF version attribute of a file for compatibility.

    Raises DeprecationWarning for backwards-incompatible files, FutureWarning
    for (potentially) forwards-incompatible files, and UserWarning for files
    that may not have been created an ARF library.

    Returns the version for the file

    """
    from distutils.version import StrictVersion as Version
    try:
        file_version = Version(
            file.attrs.get('arf_library_version', file.attrs['arf_version']))
    except KeyError:
        # attribute doesn't exist - may be a new file
        if file.mode == 'r+':
            file_version = Version(spec_version)
            set_attributes(file,
                           arf_library='python',
                           arf_library_version=__version__,
                           arf_version=spec_version)
            return file_version
        else:
            raise UserWarning(
                "Unable to determine ARF version for {0.filename}; created by another program?".format(file))
    # should be backwards compatible after 1.1
    if file_version < Version('1.1'):
        raise DeprecationWarning(
            "ARF library {} may have trouble reading file version {} (< 1.1)".format(version, file_version))
    elif file_version >= Version('3.0'):
        raise FutureWarning(
            "ARF library {} may be incompatible with file version {} (>= 3.0)".format(version, file_version))
    return file_version


def set_attributes(node, overwrite=True, **attributes):
    """Set multiple attributes on an HDF5 object.

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


def keys_by_creation(group):
    """Returns a list of links in group in order of creation.

    Raises an error if the group was not set to track creation order.

    """
    from h5py import h5
    out = []
    group._id.links.iterate(
        out.append, idx_type=h5.INDEX_CRT_ORDER, order=h5.ITER_INC)
    return out


def convert_timestamp(obj):
    """Make an ARF timestamp from various types.

    Argument can be a datetime.datetime object, a time.struct_time, an integer,
    a float, or a tuple of integers. The returned value is a numpy array with
    the integer number of seconds since the Epoch and any additional
    microseconds.

    Note that because floating point values are approximate, the conversion
    between float and integer tuple may not be reversible.

    """
    from datetime import datetime
    from time import mktime, struct_time
    out = nx.zeros(2, dtype='int64')
    if isinstance(obj, datetime):
        out[0] = long(mktime(obj.timetuple()))
        out[1] = obj.microsecond
    elif isinstance(obj, struct_time):
        out[0] = long(mktime(obj))
    elif isinstance(obj, float):
        out[1] = long((obj - long(obj)) * 1e6)
        out[0] = long(obj)
    elif isinstance(obj, (int, long)):
        out[0] = long(obj)
    else:
        try:
            out[:2] = obj[:2]
        except:
            raise TypeError("unable to convert %s to timestamp" % obj)
    return out


def timestamp_to_datetime(timestamp):
    """Convert an ARF timestamp a datetime.datetime object (naive local time)"""
    from datetime import datetime, timedelta
    obj = datetime.fromtimestamp(timestamp[0])
    return obj + timedelta(microseconds=int(timestamp[1]))


def timestamp_to_float(timestamp):
    """Convert an ARF timestamp to a floating point (sec since epoch) """
    return nx.dot(timestamp, (1.0, 1e-6))


def dataset_properties(dset):
    """Infer the type of data and some properties of an hdf5 dataset.

    Returns tuple: (sampled|event|interval|unknown), (array|table|vlarry), ncol
    """
    from h5py import h5t
    dtype = dset.id.get_type()

    if isinstance(dtype, h5t.TypeVlenID):
        return 'event', 'vlarray', dset.id.shape[0]

    if isinstance(dtype, h5t.TypeCompoundID):
        # table types; do a check on the dtype for backwards compat with 1.0
        names, ncol = dtype.dtype.names, dtype.get_nmembers()
        if 'start' not in names:
            contents = 'unknown'
        elif any(k not in names for k in _interval_dtype.names):
            contents = 'event'
        else:
            contents = 'interval'
        return contents, 'table', ncol

    dtt = dset.attrs.get('datatype', 0)
    ncols = len(dset.shape) < 2 and 1 or dset.shape[1]
    if dtt < DataTypes.EVENT:
        # assume UNKNOWN is sampled
        return 'sampled', 'array', ncols
    else:
        return 'event', 'array', ncols


def pluralize(n, sing='', plurl='s'):
    """Return 'sing' if n == 1; otherwise append 'plurl'"""
    if n == 1:
        return sing
    else:
        return plurl


def set_uuid(obj, uuid=None):
    """Set the uuid attribute of an HDF5 object. Use this method to ensure correct dtype """
    from uuid import uuid4, UUID
    if uuid is None:
        uuid = uuid4()
    elif isinstance(uuid, basestring):
        if len(uuid) == 16:
            uuid = UUID(bytes=uuid)
        else:
            uuid = UUID(hex=uuid)

    if "uuid" in obj.attrs:
        del obj.attrs["uuid"]
    obj.attrs.create("uuid", str(uuid), dtype="|S36")


def get_uuid(obj):
    """Return the uuid for an entry or other HDF5 object, or null uuid if none is set"""
    from uuid import UUID
    try:
        return UUID(obj.attrs['uuid'])
    except:
        return UUID(int=0)

# Variables:
# End:
