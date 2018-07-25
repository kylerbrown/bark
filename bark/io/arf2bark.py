import arf
import sys
import argparse
import os
import bark
import h5py
import pandas
import numpy
import collections as coll

ENTRY_PREFIX = 'entry'

def _parse_args(raw_args):
    desc = 'Unspool an HDF5 ARF file into a Bark tree.'
    epi = 'Fails if bark_root already exists.'
    parser = argparse.ArgumentParser(description=desc, epilog=epi)
    parser.add_argument('-v',
                        '--verbose',
                        help='increase output verbosity',
                        action='store_true')
    parser.add_argument('-t',
                        '--timezone',
                        help='timezone for data, tz database format (default is "America/Chicago")',
                        default=None)
    parser.add_argument('-m',
                        '--mangle-prefix',
                        help='prefix for names which collide with bark function arguments (default: {})'.format(ENTRY_PREFIX),
                        default=ENTRY_PREFIX)
    parser.add_argument('arf_file', help='ARF file to convert')
    parser.add_argument('bark_root', help='location of new bark root')
    return parser.parse_args(raw_args)

def copy_attrs(attrs):
    """Semi-deep-copies an h5py attributes dictionary,
       and converts byte-strings to strings."""
    na = dict(attrs)
    na.update({k: v.decode() for k,v in na.items() if isinstance(v, bytes)})
    return na

def arf2bark(arf_file, root_path, timezone, verbose, mangle_prefix=ENTRY_PREFIX):
    with arf.open_file(arf_file, 'r') as af:
        os.mkdir(root_path)
        root = bark.Root(root_path)
        if verbose:
            print('Created Root: ' + root_path)
        tle = None
        found_trigin = False
        for ename, entry in af.items(): # entries and top-level datasets
            if isinstance(entry, h5py.Group): # entries
                entry_path = os.path.join(root_path, ename)
                entry_attrs = copy_attrs(entry.attrs)
                for pos_arg in ('name', 'parents'):
                    # along with 'timestamp' below, these are positional arguments to create_entry
                    # for now, I prefer hard-coding them over messing with runtime introspection
                    new_name = pos_arg
                    while new_name in entry_attrs:
                        new_name = '{}_{}'.format(mangle_prefix, new_name)
                    try:
                        entry_attrs[new_name] = entry_attrs.pop(pos_arg)
                    except KeyError:
                        pass
                    else:
                        if verbose:
                            print('Renamed attribute {} of entry {} to {}'.format(pos_arg,
                                                                                  ename,
                                                                                  new_name))
                timestamp = entry_attrs.pop('timestamp')
                if timezone:
                    timestamp = bark.convert_timestamp(timestamp, timezone)
                else:
                    timestamp = bark.convert_timestamp(timestamp)
                bark_entry = bark.create_entry(entry_path,
                                               timestamp,
                                               parents=False,
                                               **entry_attrs)
                if verbose:
                    print('Created Entry: ' + entry_path)
                for ds_name, dataset in entry.items(): # entry-level datasets
                    if ds_name == 'trig_in': # accessing trig_in -> segfault
                        found_trigin = True # and skip the dataset
                    else:
                        transfer_dset(ds_name, dataset, entry_path, verbose)
            elif isinstance(entry, h5py.Dataset): # top-level datasets
                if arf.is_time_series(entry) or arf.is_marked_pointproc(entry):
                    if tle is None:
                        path = os.path.join(root_path, 'top_level')
                        tle = bark.create_entry(path, 0, parents=False).path
                    transfer_dset(ename, entry, tle, verbose)
                else:
                    unknown_ds_warning(ename) # and skip, w/o creating TLE
        if found_trigin:
            print('Warning: found datasets named "trig_in". Jill-created ' +
                  '"trig_in" datasets segfault when read, so these datasets' +
                  ' were skipped. If you know the datasets are good, rename' +
                  ' them and try again.')
    return bark.Root(root_path)

def build_columns(units, column_names=None):
    if isinstance(units, (str, bytes)) or not isinstance(units, coll.Iterable):
        units = [units]
    if column_names is None:
        column_names = range(len(units))
    cols = {cn: {'units': u} for cn,u in zip(column_names, units)}
    for c,d in cols.items():
        d.update({k: v.decode() for k,v in d.items() if isinstance(v, bytes)})
        d.update({k: None for k,v in d.items() if (k == 'units' and v == '')})
    return cols

def unknown_ds_warning(ds_name):
    print('Warning: unknown dataset type - neither time series nor point' +
          ' process. Skipping dataset ' + ds_name)

def transfer_dset(ds_name, ds, e_path, verbose=False):
    ds_attrs = copy_attrs(ds.attrs)
    units = ds_attrs.pop('units', None)
    if arf.is_time_series(ds):
        ds_name += '.dat'
        ds_path = os.path.join(e_path, ds_name)
        ds_attrs['columns'] = build_columns(units)
        sr = ds_attrs.pop('sampling_rate')
        bark_ds = bark.write_sampled(ds_path, ds, sr, **ds_attrs)
        if verbose:
            print('Created sampled dataset: ' + ds_path)
    elif arf.is_marked_pointproc(ds):
        ds_name += '.csv'
        ds_path = os.path.join(e_path, ds_name)
        ds_data = pandas.DataFrame(ds[:])
        ds_attrs['columns'] = build_columns(units, column_names=ds_data.columns)
        for ser in ds_data:
            if ds_data[ser].dtype == numpy.dtype('O'): # bytes object
                ds_data[ser] = ds_data[ser].str.decode('utf-8')
        bark_ds = bark.write_events(ds_path, ds_data, **ds_attrs)
        if verbose:
            print('Created event dataset: ' + ds_path)
    else:
        unknown_ds_warning(ds_name)

def _main():
    args = _parse_args(sys.argv[1:])
    arf2bark(args.arf_file, args.bark_root, args.timezone, args.verbose, args.mangle_prefix)

if __name__ == '__main__':
    _main()

