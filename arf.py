# -*- coding: utf-8 -*-
# -*- mode: python -*-
import os
import numpy as nx
import h5py as hp
from h5py.version import version as h5py_version, hdf5_version

spec_version = "2.0"
__version__ = version = "2.0.0"

__doc__ = \
"""
This is ARF, a python library for storing and accessing audio and ephys data in
HDF5 containers.

Versions:
 arf: %s
 h5py: %s
 HDF5: %s
""" % (version, h5py_version, hdf5_version)

# some constants and enumerations
class DataTypes:
    """
    Available data types, by name and integer code:
    """
    UNDEFINED, ACOUSTIC, EXTRAC_HP, EXTRAC_LF, EXTRAC_EEG, INTRAC_CC, INTRAC_VC = range(0,7)
    EVENT,SPIKET,BEHAVET = range(1000,1003)
    INTERVAL,STIMI,COMPONENTL = range(2000,2003)

    @classmethod
    def _doc(cls):
        out = str(cls.__doc__)
        for v,k in sorted(cls._todict().items()):
            out += '\n%s:%d' % (k,v)
        return out

    @classmethod
    def _todict(cls):
        """ generate a dict keyed by value """
        return dict((getattr(cls,attr),attr) for attr in dir(cls) if not attr.startswith('_'))

    @classmethod
    def _fromstring(cls,s):
        """ look up datatype by string; returns None if not defined """
        return getattr(cls,s.upper(),None)


_interval_dtype = nx.dtype([('name','S256'),('start','f8'),('stop','f8')])

# Helper classes
class entry(hp.Group):
    """
    An entry is an abstract collection of data which all refer to the
    same time frame.  Data can include physiological recordings, sound
    recordings, and derived data such as spike times and labels.  See
    add_data() for information on how data are stored.

    The entry class is not initialized directly; instead use the class
    method promote() to dynamically cast a Group to an entry.  In
    addition to the base methods inherited from Group, entry provides:

    Data access methods
    --------------------
    get_data(name):     reads the data in a dataset (including vlen data types)
    channels:           names of the datasets
    nchannels:          number of datasets

    Data manipulation
    --------------------
    add_data(name,data,...): add data to the entry

    Factories
    ------------------
    promote(Group): set class of a Group to entry
    """

    @classmethod
    def promote(cls, group):
        """ Promote an object to this class """
        group.__class__ = cls
        return group

    def add_data(self, name, data, units='', datatype=DataTypes.UNDEFINED,
                 replace=False, chunks=True, maxshape=None, compression=None,
                 **attributes):
        """
        Add data to the entry.  Data can be of the following types:

        * sampled data: an N-D numerical array of measurements
        * "simple" event data: a 1-D array of times
        * "complex" event data: a 1-D array of records, with field 'start' required

        name:   the name of dataset in which to store the data
        data:   the data to store, as one of the types described above. convert to numpy array first!


        Optional arguments:
        datatype:      a code defining the nature of the data in the channel
        units:         channel units (optional for sampled data, otherwise required)
        sampling_rate: required for sampled data and event data with units=='samples'
        replace:       if True and the node exists, delete it first. Otherwise
                       duplicate names will raise errors

        Arguments passed to h5py:
        maxshape:    make the node resizable up to this shape. Use None for axes that
                     need to be unlimited. Ignored for label and event data, which are
                     always expandable
        chunks:      specify the chunk size. The optimal chunk size depends on the
                     intended use of the data. For single-channel sampled data the
                     default is probably best.
        compression: compression strategy. Can be 'gzip', 'szip', 'lzf' or an integer
                     in range(10) specifying gzip(N).  Only gzip is really portable.

        Additional arguments are set as attributes on the created table/array
        Returns: the created dataset
        """
        from numbers import Number

        if self.file.mode=='r': raise IOError, "the file is not writable"

        # check data validity before deleting anything
        if not hasattr(data,'dtype'):
            data = nx.asarray(data)
            if data.dtype.kind in ('S','O'):
                raise ValueError, "data must be in array with numeric or compound type"
        if not data.dtype.isbuiltin:
            if 'start' not in data.dtype.names:
                raise ValueError, "complex event type is missing required start field"
        if units == '':
            if not data.dtype.isbuiltin:
                raise ValueError, "event data requires units"
            if not isinstance(attributes.get('sampling_rate',None),Number):
                raise ValueError, "missing sampling_rate attribute"
        elif units == 'samples' and not isinstance(attributes.get('sampling_rate',None),Number):
            raise ValueError, "data with units of 'samples' requires sampling_rate attribute"
        # NB: can't really catch case where sampled data has units but doesn't
        # have sampling_rate attribute

        if maxshape is None:
            maxshape = data.shape

        dset = self.create_dataset(name, data=data, maxshape=maxshape, chunks=chunks, compression=compression)

        # set user attributes
        set_attributes(dset, units=units, datatype=datatype, **attributes)

        return dset

    @property
    def nchannels(self):
        """ Number of channels/datasets in the entry """
        return len(self)

    @property
    def channels(self):
        """ Names of the channels/datasets in the entry """
        return self.keys()

    @property
    def timestamp(self):
        """
        Return the timestamp of the entry as a floating point scalar.
        For more precision, access the timestamp attribute directly.
        """
        return timestamp_to_float(self.attrs['timestamp'])

    @property
    def uuid(self):
        """ return the uuid for the entry """
        from uuid import UUID
        # numpy shortens strings ending in \0
        return UUID(bytes=self.attrs.get('uuid','').rjust(16,'\0'))

    def __repr__(self):
        return '%s: %d channel%s' % (self.name, self.nchannels,pluralize(self.nchannels))

    def __str__(self):
        attrs = self.attrs
        datatypes = DataTypes._todict()
        out = "%s" % (self.name)
        for k,v in attrs.items():
            if k.isupper(): continue
            if k=='timestamp':
                out += "\n  timestamp : %s" % datetime_timestamp(v).strftime("%Y-%m-%d %H:%M:%S.%f %z")
            elif k=='uuid':
                out += "\n  uuid : %s" % self.uuid
            else:
                out += "\n  %s : %s" % (k, v)
        for name,dset in self.iteritems():
            out += "\n  /%s :" % name
            if isinstance(dset.id.get_type(),hp.h5t.TypeVlenID):
                out += " vlarray"
            else:
                out += " array %s" % (dset.shape,)
                if 'sampling_rate' in dset.attrs:
                    out += " @ %.1f/s" % dset.attrs['sampling_rate']
                if dset.dtype.names is not None:
                    out += " (compound type)"

            out += ", type %s"  % datatypes[dset.attrs.get('datatype',DataTypes.UNDEFINED)]
            if dset.compression: out += " [%s%d]" % (dset.compression,dset.compression_opts)
        return out


class table(object):
    """
    A wrapper class with some useful methods for manipulating
    table-type datasets (i.e. with compound data type).

    __init__(DataSet):                   wrap an h5py dataset object
    create_table(group, name, dtype):    create a new table with specified dtype
    append(*record):                     append one or more records to the table
    """
    def __init__(self, dataset):
        self.dataset = dataset

    @classmethod
    def create_table(cls, group, name, dtype, **attributes):
        """
        Create a new array dataset with compound datatype and maxshape=(None,)
        """
        dset = group.create_dataset(name, shape=(0,), dtype=dtype, maxshape=(None,))
        set_attributes(dset, **attributes)
        return cls(dset)

    def append(self, *records):
        """
        Append new record(s) to the table
        """
        nrows = self.dataset.shape[0]
        nrec  = len(records)
        self.dataset.resize(nrows+nrec,axis=0)
        for i,rec in enumerate(records):
            self.dataset[nrows+i] = rec


# main interface
class file(object):
    """
    Represents an ARF file.  ARF files are HDF5 files, generated using
    HDF5 library version 1.8+. Data are organized into entries based
    on the time they occurred, and entries may contain multiple
    channels and data types.

    Constructor
    -------------------
    __init__(filename, dbms=None, ...): open 'filename', optionally
             specifying connection to an external database.

    Data access methods
    --------------------
    __getitem__(name): return entry by name
    __iter__(): iterates through entry names (in alphabetical order)
    items(key): iterate through name,entry pairs, with optional sorting

    File modification
    --------------------
    create_entry(name,...): create a new entry
    delete_entry(name): remove entry from the file

    File information
    --------------------
    __contains__(name): membership test, returns true if an entry 'name' exists
    entries: list of entry names
    nentries: number of entries
    """

    def __init__(self, name, mode='r', strict_version=False, **kwargs):
        """
        Open a new or existing ARF file.

        name:  the name of an arf file to open, or an open h5py handle

        Optional arguments:
        mode: 'r', 'r+', 'w', or 'a'. For 'r' and 'r+' the file must
               already exist; 'w' creates the file, overwriting the
               previous version, and 'a' opens the file for read and
               write access.

        Additional arguments are passed to the h5py File initializer
        """
        if isinstance(name, hp.File):
            self.h5 = name
            exists = True
        else:
            exists = os.path.isfile(name)
            self.h5 = hp.File(name, mode=mode, **kwargs)
        if not self.readonly:
            set_attributes(self.h5, overwrite=False,
                           arf_version=__version__,)
        try:
            self._check_version(exists)
        except Exception, e:
            if strict_version: raise e
            else: print e.message

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return self.h5.__exit__(*args)

    def __getitem__(self, name):
        try:
            el = self.h5.__getitem__(name)
            if isinstance(el,hp.Group):
                return entry.promote(self.h5.__getitem__(name))
            else:
                return el
        except AttributeError:
            raise TypeError, "wrong index type (basestring required)"
        except KeyError:
            raise KeyError, "no such entry %s" % name

    def __delitem__(self, name):
        try:
            del self.h5[name]
        except AttributeError:
            raise TypeError, "wrong index type (basestring required)"
        except KeyError:
            raise KeyError, "no such entry %s" % name

    def __iter__(self):
        """ Iterate through all entries in alphabetical order """
        return (k for k in self.h5.iterkeys() if self.h5.get(k,getclass=True)==hp.Group)

    def items(self, key=None):
        """
        Iterate through entries using a sorting function, key. If key
        is a string, sorting is based on the attribute, if it exists,
        with that name. Otherwise, key must be a function that takes
        the entry object and returns the key to be used for sorting
        """
        from itertools import ifilter
        it = ifilter(lambda ke: isinstance(ke[1],hp.Group), self.h5.iteritems())

        if key is None:
            return ((k,entry.promote(e)) for k,e in it)
        elif key == 'timestamp':
            keyfun = lambda ke: timestamp_to_float(ke[1].attrs['timestamp'])
        elif isinstance(key, basestring):
            keyfun = lambda ke: ke[1].attrs.get(key,None)
        else:
            keyfun = lambda ke: key(ke[1])
        return ((k,entry.promote(e)) for k,e in sorted(it, key=keyfun))

    def create_entry(self, name, timestamp, **attributes):
        """
        Create a new entry.

        name: the name of the new entry. any valid python string.
        timestamp: timestamp of entry (datetime object, or seconds since
                   January 1, 1970). Can be an integer, a float, or a tuple
                   of integers (seconds, microsceconds)
        attributes: additional attributes are set on created entry

        Returns: newly created entry object
        Raises: IOError for read-only file; ValueError if the entry name is taken
        """
        if self.readonly: raise IOError, "the file is not writable"
        ts = convert_timestamp(timestamp)
        if name in self.h5:
            raise ValueError, "the entry %s already exists" % name

        grp = self.h5.create_group(name)

        set_uuid_attr(grp)
        set_attributes(grp,
                       timestamp=ts,
                       **attributes)

        return entry.promote(grp)

    def set_attributes(self, node="/", **kwargs):
        if isinstance(node,basestring): node = self.h5[node]
        set_attributes(node, **kwargs)

    def get_attributes(self, node="/", *args, **kwargs):
        if isinstance(node,basestring): node = self.h5[node]
        return get_attributes(node, *args, **kwargs)


    @property
    def entries(self):
        """ A list of all the entries in the file """
        return [k for k in self]

    def __contains__(self, name):
        return name in self.h5

    @property
    def nentries(self):
        """ The number of entries defined in the file """
        # somewhat slow for large files
        return sum(1 for x in self.h5.values() if isinstance(x,hp.Group))

    @property
    def readonly(self):
        """ Whether the file is writable """
        return self.h5.mode=='r'

    def __repr__(self):
        nentries = self.nentries
        return "<ARF file %s at %s: %d entr%s>" % (self.h5.filename, hex(id(self)),
                                                   nentries, pluralize(nentries,'y','ies'))

    def __str__(self):
        out = self.__repr__()
        for i,entry in enumerate(self):
            out += '\n' + self[entry].__repr__()
            if i > 20: return out + '\n(list truncated)'

        return out

    def _check_version(self, exists=True):
        """
        Check the stored version in the file and compare to the
        version of this class.  Issues a warning if the class is older
        than the file.
        """
        from distutils.version import StrictVersion as Version
        file_version = Version(get_attributes(self.h5, key='arf_version') or "0.9")
        # 1.1 is not forwards compatible
        if file_version < Version('1.1'):
            raise DeprecationWarning, "ARF version %s (< 1.1) not fully supported by this library" % file_version
        elif file_version >= Version('3.0'):
            raise FutureWarning, "ARF version (%s) (>= 3.0) may not be backwards compatible with this library" % file_version

# module-level convenience functions:
def set_attributes(node, overwrite=True, **attributes):
    """
    Set attributes on a node. Attribute names are coerced to lowercase
    strings to avoid overwriting any important metadata. Values are coerced
    to numpy arrays, mostly to ensure strings are stored correctly. If the
    value for a key is None or '', the attribute is deleted.
    """
    aset = node.attrs
    for k,v in attributes.items():
        if not overwrite and k in aset: continue
        if v == None or v == '':
            if k.lower() in aset: del aset[k.lower()]
        else:
            aset[k.lower()] = nx.asarray(v)

def get_attributes(node, key=None):
    """
    Get attributes on a node. If Key is none, returns the
    AttributeSet; otherwise attempts to look up the key(s),
    returning None if it does not exist.
    """
    aset = node.attrs
    if key is not None:
        if hasattr(key,'__iter__'):
            return tuple(aset.get(k,None) for k in key)
        else:
            return aset.get(key, None)
    else:
        return aset



def nodes_by_creation(group):
    """ Iterate through nodes in a group in order of creation """
    def f(x):
        if x.find('/')<0: yield x
    # no iterate function
    group._id.links.visit(f, idx_type=hp.h5.INDEX_CRT_ORDER, order=hp.h5.ITER_DEC)


def convert_timestamp(obj):
    """
    Make the canonical timestamp from various types. Obj argument can
    be a datetime.datetime object, a time.struct_time, an integer, a
    float, or a tuple of integers.  The returned value is a numpy
    array with the integer number of seconds since the Epoch and
    any additional microseconds.

    Note that because floating point values are approximate, the conversion
    between float and integer tuple may not be reversible.
    """
    from datetime import datetime
    from time import mktime, struct_time
    out = nx.zeros(2,dtype='int64')
    if isinstance(obj, datetime):
        out[0] = long(mktime(obj.timetuple()))
        out[1]  = obj.microsecond
    elif isinstance(obj, struct_time):
        out[0] = long(mktime(obj))
    elif isinstance(obj, float):
        out[1]  = long((obj - long(obj)) * 1e6)
        out[0] = long(obj)
    elif isinstance(obj, (int, long)):
        out[0] = long(obj)
    elif isinstance(obj, (tuple,list)) and len(obj) >= 2:
        out[1]  = long(obj[1]) if obj[1] else 0
        out[0] = long(obj[0])
    else:
        raise TypeError, "unable to convert %s to timestamp" % obj
    return out

def datetime_timestamp(timestamp):
    """
    Convert a timestamp array (seconds, microseconds) into a
    datetime.datetime object.
    """
    from datetime import datetime, timedelta
    obj = datetime.fromtimestamp(timestamp[0])
    return obj + timedelta(microseconds=int(timestamp[1]))

def dataset_properties(dset):
    """
    Infer the type of data and some properties of an hdf5 dataset.

    Returns tuple: (sampled|event|interval|unknown), (array|table|vlarry), ncol
    """
    dtype = dset.id.get_type()

    if isinstance(dtype,hp.h5t.TypeVlenID):
        return 'event','vlarray',dset.id.shape[0]

    if isinstance(dtype,hp.h5t.TypeCompoundID):
        # table types; do a check on the dtype for backwards compat with 1.0
        names,ncol = dtype.dtype.names, dtype.get_nmembers()
        if 'start' not in names:
            contents = 'unknown'
        elif any(k not in names for k in _interval_dtype.names):
            contents = 'event'
        else:
            contents = 'interval'
        return contents,'table',ncol

    dtt = dset.attrs.get('datatype',0)
    ncols = len(dset.shape)<2 and 1 or dset.shape[1]
    if dtt < DataTypes.EVENT:
        # assume UNKNOWN is sampled
        return 'sampled','array',ncols
    else:
        return 'event','array',ncols


def pluralize(n,sing='',plurl='s'):
    if n == 1: return sing
    else: return plurl


def timestamp_to_float(arr):
    """ convert two-element timestamp (sec, usec) to a floating point (sec since epoch) """
    return nx.dot(arr, (1.0, 1e-6))

def set_uuid_attr(node, uuid=None):
    """ set the uuid attribute of a node. use this method to ensure correct dtype """
    from uuid import uuid4, UUID
    if uuid is None:
        uuid = uuid4()
    elif isinstance(uuid, basestring):
        uuid = UUID(bytes=uuid)

    if "uuid" in node.attrs:
        del node.attrs["uuid"]
    node.attrs.create("uuid", uuid.bytes, dtype="|S16")

__all__ = ['file', 'entry', 'table', 'DataTypes']

# Variables:
# End:
