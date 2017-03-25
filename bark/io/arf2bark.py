import arf
import sys
import argparse
import os
import bark
import h5py
import pandas
import numpy
import collections as coll

def _parse_args(raw_args):
    desc = 'Unspool an HDF5 ARF file into a Bark tree.'
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument('-v',
                        '--verbose',
                        help='increase output verbosity',
                        action='store_true')
    parser.add_argument('arf_file', help='ARF file to convert')
    parser.add_argument('root_parent', help='directory in which to place the Bark Root')
    return parser.parse_args(raw_args)

def copy_attrs(attrs):
    """Semi-deep-copies an h5py attributes dictionary,
       and converts byte-strings to strings."""
    na = dict(attrs)
    na.update({k: v.decode() for k,v in na.items() if isinstance(v, bytes)})
    return na

def arf2bark(arf_file, root_parent, verbose):
    with arf.open_file(arf_file, 'r') as af:
        root_dirname = os.path.splitext(arf_file)[0]
        root_path = os.path.join(os.path.abspath(root_parent), root_dirname)
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
                timestamp = entry_attrs.pop('timestamp')
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
                if tle is None:
                    path = os.path.join(root_path, 'top_level')
                    tle = bark.create_entry(path, 0, parents=False).path
                transfer_dset(ename, entry, tle, verbose)
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
        print('Warning: unknown dataset type - neither time series nor point' +
              ' process. Skipping dataset ' + ds_name)

def _main():
    arg_dict = _parse_args(sys.argv[1:])
    arf2bark(arg_dict.arf_file, arg_dict.root_parent, arg_dict.verbose)

if __name__ == '__main__':
    _main()

