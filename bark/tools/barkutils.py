import os.path
from glob import glob
import bark
import argparse
from bark import stream
import arrow
from dateutil import tz


def meta_attr():
    p = argparse.ArgumentParser(
        description="Create/Modify a metadata attribute")
    p.add_argument("name", help="name of bark object (Entry or Dataset)")
    p.add_argument("attribute",
                   help="name of bark attribute to create or modify")
    p.add_argument("value", help="value of attribute")
    args = p.parse_args()
    name, attr, val = (args.name, args.attribute, args.value)
    attrs = bark.read_metadata(name)
    try:
        attrs[attr] = eval(val)  # try to parse
    except Exception:
        attrs[attr] = val  # assign as string
    bark.write_metadata(name, **attrs)

def meta_column_attr():
    p = argparse.ArgumentParser(
        description="Create/Modify a metadata attribute for a column of data")
    p.add_argument("name", help="name of bark object (Entry or Dataset)")
    p.add_argument("column", help="name of the column of a Dataset")
    p.add_argument("attribute",
                   help="name of bark attribute to create or modify")
    p.add_argument("value", help="value of attribute")
    args = p.parse_args()
    name, column, attr, val = (args.name, args.column, args.attribute, args.value)
    attrs = bark.read_metadata(name)
    columns = attrs['columns']
    if 'dtype' in attrs:
        column = int(column)
    try:
        columns[column][attr] = eval(val)  # try to parse
    except Exception:
        columns[column][attr] = val  # assign as string
    bark.write_metadata(name, **attrs)


def mk_entry():
    p = argparse.ArgumentParser(description="create a bark entry")
    p.add_argument("name", help="name of bark entry")
    p.add_argument("-a",
                   "--attributes",
                   action='append',
                   type=lambda kv: kv.split("="),
                   dest='keyvalues',
                   help="extra metadata in the form of KEY=VALUE")
    p.add_argument("-t",
                   "--timestamp",
                   help="format: YYYY-MM-DD or YYYY-MM-DD_HH-MM-SS.S")
    p.add_argument("-p",
                   "--parents",
                   help="no error if already exists, new meta-data written",
                   action="store_true")
    p.add_argument('--timezone',
                   help="timezone of timestamp, default: America/Chicago",
                   default='America/Chicago')
    args = p.parse_args()
    timestamp = arrow.get(args.timestamp).replace(
        tzinfo=tz.gettz(args.timezone)).datetime
    attrs = dict(args.keyvalues) if args.keyvalues else {}
    bark.create_entry(args.name, timestamp, args.parents, **attrs)


def _clean_metafiles(path, recursive, meta='.meta.yaml'):
    metafiles = glob(os.path.join(path, "*" + meta))
    for mfile in metafiles:
        if not os.path.isfile(mfile[:-len(meta)]):
            os.remove(mfile)
    if recursive:
        dirs = [x
                for x in os.listdir(path)
                if os.path.isdir(os.path.join(path, x))]
        for d in dirs:
            _clean_metafiles(os.path.join(path, d), True, meta)


def clean_metafiles():
    """
    remove x.meta.yaml files with no associated file (x)
    """
    p = argparse.ArgumentParser(
        description="remove x.meta.yaml files with no associated file (x)")
    p.add_argument("path", help="name of bark entry", default=".")
    p.add_argument("-r",
                   "--recursive",
                   help="search recursively",
                   action="store_true")
    args = p.parse_args()
    _clean_metafiles(args.path, args.recursive)


def rb_concat():
    p = argparse.ArgumentParser(
        description="""Concatenate raw binary files by adding new samples.
    Do not confuse with merge, which combines channels""")
    p.add_argument("input", help="input raw binary files", nargs="+")
    p.add_argument("-a",
                   "--attributes",
                   action='append',
                   type=lambda kv: kv.split("="),
                   dest='keyvalues',
                   help="extra metadata in the form of KEY=VALUE")
    p.add_argument("-o", "--out", help="name of output file", required=True)
    args = p.parse_args()
    if args.keyvalues:
        attrs = dict(args.keyvalues)
    else:
        attrs = {}
    streams = [stream.read(x) for x in args.input]
    streams[0].chain(*streams[1:]).write(args.out, **attrs)


def rb_decimate():
    ' Downsample raw binary file.'
    p = argparse.ArgumentParser(description="Downsample raw binary file")
    p.add_argument("input", help="input bark file")
    p.add_argument("--factor",
                   required=True,
                   type=int,
                   help="downsample factor")
    p.add_argument("-a",
                   "--attributes",
                   action='append',
                   type=lambda kv: kv.split("="),
                   dest='keyvalues',
                   help="extra metadata in the form of KEY=VALUE")
    p.add_argument("-o", "--out", help="name of output file", required=True)
    args = p.parse_args()
    if args.keyvalues:
        attrs = dict(args.keyvalues)
    else:
        attrs = {}
    stream.read(args.input).decimate(args.factor).write(args.out, **attrs)


def rb_select():
    p = argparse.ArgumentParser(description='''
    Select a subset of channels from a sampled dataset
    ''')
    p.add_argument('dat', help='dat file')
    p.add_argument('-o', '--out', help='name of output datfile')
    p.add_argument('-c',
                   '--channels',
                   help='''channels to extract,
                   zero indexed channel numbers
                   unless --col-attr is set, in which case
                   channels are metadata values''',
                   nargs='+',
                   required=True)
    p.add_argument('--col-attr',
                   help='name of column attribute to select channels with')
    args = p.parse_args()
    fname, outfname, channels, col_attr = (args.dat, args.out, args.channels,
                                           args.col_attr)
    stream = bark.read_sampled(fname).toStream()
    if col_attr:
        columns = stream.attrs['columns']
        channels = [i
                    for i in range(len(columns))
                    if columns[i][col_attr] in channels]
    else:
        channels = [int(c) for c in channels]
    stream[channels].write(outfname)


def rb_filter():
    p = argparse.ArgumentParser(description="""
    filter a sampled dataset
    """)
    p.add_argument("dat", help="dat file")
    p.add_argument("-o", "--out", help="name of output dat file")
    p.add_argument("--order", help="filter order", default=3, type=int)
    p.add_argument("--highpass", help="highpass frequency", type=float)
    p.add_argument("--lowpass", help="lowpass frequency", type=float)
    p.add_argument("-f",
                   "--filter",
                   help="filter type: butter or bessel",
                   default="bessel")

    opt = p.parse_args()
    dtype = bark.read_metadata(opt.dat)['dtype']
    stream.read(opt.dat)._analog_filter(opt.filter,
                                        highpass=opt.highpass,
                                        lowpass=opt.lowpass,
                                        order=opt.order).write(opt.out, dtype)
    attrs = bark.read_metadata(opt.out)
    attrs['highpass'] = opt.highpass
    attrs['lowpass'] = opt.lowpass
    attrs['filter'] = opt.filter
    attrs['filter_order'] = opt.order
    bark.write_metadata(opt.out, **attrs)


def rb_diff():
    p = argparse.ArgumentParser(description="""
    Subtracts one channel from another
    """)
    p.add_argument("dat", help="dat file")
    p.add_argument("-c",
                   "--channels",
                   help="""channels to difference, zero indexed, default: 0 1,
        subtracts second channel from first.""",
                   type=int,
                   nargs="+")
    p.add_argument("-o", "--out", help="name of output dat file")
    opt = p.parse_args()
    dat, out, channels = opt.dat, opt.out, opt.channels
    if not channels:
        channels = (0, 1)
    (stream.read(dat)[channels[0]] - stream.read(dat)[channels[1]]).write(out)


def rb_join():
    p = argparse.ArgumentParser(description="""
            Combines dat files by adding new channels with the same number
            samples. To add additional samples, use dat-cat""")
    p.add_argument("dat", help="dat files", nargs="+")
    p.add_argument("-o", "--out", help="name of output dat file")
    opt = p.parse_args()
    streams = [stream.read(fname) for fname in opt.dat]
    streams[0].merge(*streams[1:]).write(opt.out)


def rb_to_wav():
    p = argparse.ArgumentParser()
    p.add_argument("dat",
                   help="""dat file to convert to wav,
        can be any number of channels but you probably want 1 or 2""")
    p.add_argument("-o", "--out", help="name of output wav file")
    opt = p.parse_args()
    stream.to_wav(stream.read(opt.dat), opt.out)


def rb_to_wave_clus():
    import argparse
    p = argparse.ArgumentParser(prog="dat2wave_clus",
                                description="""
    Converts a raw binary file to a wav_clus compatible matlab file
    """)
    p.add_argument("dat", help="dat file")
    p.add_argument("-o", "--out", help="name of output .mat file")
    opt = p.parse_args()
    from scipy.io import savemat
    dataset = bark.read_sampled(opt.dat)
    savemat(opt.out,
            {'data': dataset.data.T,
             'sr': dataset.attrs['sampling_rate']},
            appendmat=False)


def _datchunk():
    p = argparse.ArgumentParser(description="split a dat file by samples")
    p.add_argument("dat", help="datfile")
    p.add_argument("stride",
                   type=float,
                   help="number of samples to chunk together")
    p.add_argument("--seconds",
                   help="specify seconds instead of samples",
                   action='store_true')
    args = p.parse_args()
    datchunk(args.dat, args.stride, args.seconds)


def datchunk(dat, stride, use_seconds):
    attrs = bark.read_metadata(dat)
    sr = attrs['sampling_rate']
    if use_seconds:
        stride = stride * sr
    stride = int(stride)
    basename = os.path.splitext(dat)[0]
    for i, chunk in enumerate(stream.read(dat, chunksize=stride)):
        filename = "{}-chunk-{}.dat".format(basename, i)
        attrs['offset'] = stride * i
        bark.write_sampled(filename, chunk, **attrs)
