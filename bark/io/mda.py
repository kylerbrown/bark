import argparse
import bark
import numpy as np
import pandas as pd
import struct
import sys

# the primary I/O functions below are adapted from those in mountainlab_pytools
# (https://github.com/magland/mountainlab_pytools)

_DATATYPE_FROM_DT_CODE = {-2: 'uint8',
                          -3: 'float32',
                          -4: 'int16',
                          -5: 'int32',
                          -6: 'uint16',
                          -7: 'float64',
                          -8: 'uint32'}
_DT_CODE_FROM_DATATYPE = {v: k for k, v in _DATATYPE_FROM_DT_CODE.items()}

class MdaHeader:
    def __init__(self, dtype, dimensions, uses_64bit_dims=False):
        self.uses64bitdims = uses_64bit_dims
        self.dt_code = _DT_CODE_FROM_DATATYPE[dtype]
        self.dt = dtype
        self.num_bytes_per_entry = np.dtype(dtype).itemsize
        self.num_dims = len(dimensions)
        self.dimprod = np.prod(dimensions)
        self.dims = dimensions
        self.header_size = 3 * 4 + self.num_dims * (8 if uses_64bit_dims else 4)

def read_mda_header(filename):
    """Read an .mda file's header information.
    
    Args:
        filename (str): path to the .mda file to read
    
    Returns:
        MdaHeader: object containing header information
    
    Raises:
        ValueError: if the header indicates dimension count < 1, or if the
            datatype code is not recognized
    """
    with open(filename, 'rb') as mda_file:
        # read first 3 header items to determine header size
        dt_code, _, num_dims = struct.unpack('<iii', mda_file.read(12))
        uses_64bit_dims = num_dims < 0
        if uses_64bit_dims:
            num_dims *= -1
        if num_dims < 1:
            raise ValueError('invalid dimension count: {}'.format(num_dims))
        # read variable-length portion of header containing dimension info
        dim_byte_format = '<' + ('q' if uses_64bit_dims else 'i') * num_dims
        dim_bytes = (8 if uses_64bit_dims else 4) * num_dims
        dimensions = struct.unpack(dim_byte_format, mda_file.read(dim_bytes))
        try:
            datatype = _DATATYPE_FROM_DT_CODE[dt_code]
        except KeyError:
            raise ValueError('invalid datatype code: {}'.format(dt_code))
        return MdaHeader(datatype, dimensions, uses_64bit_dims)

def read_mda_data(filename, chan_axis='columns'):
    """Read an .mda file's data.
    
    Args:
        filename (str): path to the .mda file to read
        chan_axis ('rows' or 'columns'): which axis of the array returned should
            correspond to channels. To get Bark-formatted data out, 'columns'
            is appropriate.
    
    Returns:
        numpy.ndarray: Numpy array containing the data

    Raises:
        ValueError: if `chan_axis` is neither 'rows' nor 'columns'
    """
    hdr = read_mda_header(filename)
    # a proper .mda file is written with channels as rows and serialization in
    # 'F' or "Fortran" format. To get channels as columns (i.e., the transpose
    # of the .mda standard) you read in 'C' format and reverse the dimensions
    if chan_axis == 'rows':
        order = 'F'
        array_shape = hdr.dims
    elif chan_axis == 'columns':
        order = 'C'
        array_shape = tuple(reversed(hdr.dims))
    else: 
        raise ValueError('chan_axis must be either "rows" or "columns"')
    with open(filename, 'rb') as mda_file:
        mda_file.seek(hdr.header_size)
        return np.fromfile(mda_file, dtype=hdr.dt).reshape(array_shape,
                                                           order=order)

def write_mda_file(filename, data, dtype=None, chan_axis='columns'):
    """Write an array to a .mda file (including a header).
    
    The only departure from the .mda spec is that the dimension sizes are
    always written as 64-bit integers (and this is reflected, per the spec, in
    the header). (This is more of a constraint within the spec rather than a
    departure. If this doesn't mean anything to you, don't worry about it.)
    
    Args:
        filename (str): path to the .mda file to write (created if absent,
            overwritten if present)
        data (ndarray): data to write
        dtype (str, or None): numpy-compatible datatype string; if `None`, the
            data is written in its current datatype
        chan_axis ('rows' or 'columns'): which axis of `data` corresponds to
            channels. For Bark datasets, 'columns' is the standard.
    
    Returns:
        None
    
    Raises:
        ValueError: if `dtype` is not supported, or if `chan_axis` is neither
            'rows' nor 'columns'
    """
    # 'order' and 'array_shape' are chosen so that a proper .mda file is written
    # this corresponds to channels as rows and serialization in 'F' or "Fortran"
    # format
    if chan_axis == 'rows':
        order = 'F'
        array_shape = data.shape
    elif chan_axis == 'columns':
        order = 'C'
        array_shape = tuple(reversed(data.shape))
    else:
        raise ValueError('chan_axis must be either "rows" or "columns"')
    if dtype is None:
        dtype = str(data.dtype)
    bytes_per_entry = np.dtype(dtype).itemsize
    try:
        dt_code = _DT_CODE_FROM_DATATYPE[dtype]
    except KeyError:
        raise ValueError('unsupported data type: {}'.format(dtype))
    with open(filename, 'wb') as mda_file:
        # write the header information
        # to save some needless complexity, always use 64-bit ints for dim sizes
        ndim_code = -1 * data.ndim
        mda_file.write(struct.pack('<iii', dt_code, bytes_per_entry, ndim_code))
        mda_file.write(struct.pack('<' + 'q' * data.ndim, *array_shape))
        if data.dtype != dtype:
            data = data.astype(dtype)
        if order == 'F': # if order == 'C', tofile() below will handle it
            data = data.transpose()
        data.tofile(mda_file)

def spike_times_dataframe_from_array(mda_hdr,
                                     mda_data,
                                     sampling_rate,
                                     chan_axis='columns',
                                     keep=None):
    """Converts data from an .mda file to a Pandas DataFrame usable by Bark.
    
    Args:
        mda_hdr (MdaHeader): the data's header information
        mda_data (numpy.ndarray): the data to convert, presumed to be the
            MountainSort output file 'firings.mda'
        sampling_rate (number): the sampling rate corresponding to the cluster
            times in the .mda data
        chan_axis('rows' or 'columns'): which axis of `mda_data` corresponds to
            channels. For Bark-formatted datasets, 'columns' is standard.
        keep (iterable or None): the clusters to keep (all others are dropped);
            if None, all clusters are kept
    
    Returns:
        pandas.DataFrame: with columns 'amplitude', 'name', and 'start'
    """
    df = pd.DataFrame(columns=['center_channel', 'amplitude', 'name', 'start'])
    # amplitude is not currently provided by MountainSort, so it'll be NaNs
    if chan_axis == 'rows':
        df['center_channel'] = mda_data[0]
        df['name'] = mda_data[2].astype('int16')
        df['start'] = mda_data[1] / sampling_rate
    elif chan_axis == 'columns':
        df['center_channel'] = mda_data[:, 0]
        df['name'] = mda_data[:, 2].astype('int16')
        df['start'] = mda_data[:, 1] / sampling_rate
    else:
        raise ValueError('chan_axis must be either "rows" or "columns"')
    if keep is None:
        keep = df['name'].unique()
    return df[df['name'].isin(keep)]

def bark_metadata_from_df(mda_hdr, df, sampling_rate):
    """Create Bark event dataset metadata for the data from an .mda file.
    
    Args:
        mda_hdr (MdaHeader): the data's header information
        df (pandas.DataFrame): the data post-conversion from numpy array
        sampling_rate (number): the sampling rate of the original data that
            MountainSort was run on
    
    Returns:
        dict: Bark attributes dictionary for an event dataset.
    """
    attrs = {}
    # looks like MountainSort always says a cluster has the same center channel
    centers = {n: int(df[df['name'] == n]['center_channel'].unique()[0])
               for n in df['name'].unique()}
    attrs['templates'] = {str(name): {'center_channel_mountainsort': chan}
                          for name, chan in centers.items()}
    df.drop(labels='center_channel', axis=1, inplace=True)
    attrs['columns'] = bark.event_columns(df)
    attrs['columns']['start']['units'] = 's'
    attrs['datatype'] = bark.DATATYPES.name_to_code['SPIKET']
    attrs['sampling_rate'] = sampling_rate
    return attrs

def bark_event_ds_from_mda(mda_file, out_file, sampling_rate, keep=None):
    """Convert an .mda file output from MountainSort into a Bark event dataset.
    
    The cluster names and event times are written out.
    
    MountainSort doesn't currently output the cluster amplitudes, so those are
    left blank, but the event dataset contains an 'amplitude' column
    nonetheless.
    
    The event times are converted from samples to seconds, to match other Bark
    spike time datasets.
    
    The 'templates' portion of the Bark dataset metadata contains the clusters'
    "center channels".
    
    Args:
        mda_file (str): path to .mda file, presumably firings.mda
        out_file (str): path to desired Bark event dataset to write
        sampling_rate (number): the sampling rate of the original data that
            MountainSort was run on
        keep (iterable or None): the clusters to keep (all others are dropped);
            if None, all clusters are kept
    
    Returns:
        bark.EventData: event dataset containing information from the .mda file
    """
    hdr = read_mda_header(mda_file)
    data = read_mda_data(mda_file)
    df = spike_times_dataframe_from_array(hdr, data, sampling_rate, keep=keep)
    metadata = bark_metadata_from_df(hdr, df, sampling_rate)
    return bark.write_events(out_file, df, **metadata)

def bark_from_mountainsort():
    d = 'Convert MountainSort .mda file output into a Bark event dataset.'
    p = argparse.ArgumentParser(description=d)
    p.add_argument('mda', help='.mda file to read')
    p.add_argument('out', help='Bark event dataset to create')
    p.add_argument('sr', type=float, help='sampling rate of sorted data')
    p.add_argument('-k', '--keep', nargs='+', default=None, type=int,
                   help='channels to keep (all kept if blank)')
    pargs = p.parse_args()
    bark_event_ds_from_mda(pargs.mda, pargs.out, pargs.sr, pargs.keep)

def mda_from_bark_sampled():
    d = 'Convert Bark sampled dataset to a .mda file.'
    p = argparse.ArgumentParser(description=d)
    p.add_argument('dataset', help='Bark sampled dataset to convert')
    p.add_argument('out', help='output filename')
    dt_help = 'NumPy-compatible datatype string (if absent, use dataset type)'
    p.add_argument('-d', '--dt', help=dt_help, default=None)
    pargs = p.parse_args()
    write_mda_file(pargs.out, bark.read_sampled(pargs.dataset).data, pargs.dt)

