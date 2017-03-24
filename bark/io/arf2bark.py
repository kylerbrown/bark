import arf
import sys
import argparse
import os
import bark
import h5py
import pandas

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
       because h5py isn't smart enough to do it right."""
    new_attrs = {}
    for a in attrs:
        if isinstance(attrs[a], bytes):
            new_attrs[a] = attrs[a].decode()
        else:
            new_attrs[a] = attrs[a]
    return new_attrs

def arf2bark(arf_file, root_parent, verbose):
    with arf.open_file(arf_file) as af:
        # root
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
                        handle_dset(ds_name, dataset, entry_path, verbose)
            elif isinstance(entry, h5py.Dataset): # top-level datasets
                if tle is None:
                    path = os.path.join(root_path, 'top_level')
                    tle = bark.create_entry(path, 0, parents=False).path
                handle_dset(ename, entry, tle, verbose)
        if found_trigin:
            print('Warning: found datasets named "trig_in". Jill-created ' +
                  '"trig_in" datasets segfault when read, so these datasets' +
                  ' were skipped. If you know the datasets are good, rename' +
                  ' them and try again.')
    return bark.Root(root_path)

def handle_dset(ds_name, ds, e_path, verbose=False):
    ds_attrs = copy_attrs(ds.attrs)
    units = ds_attrs.pop('units', None)
    if units == '':
        units = None
    ds_attrs['columns'] = {0: {'units': units}}
    if arf.is_time_series(ds):
        ds_name += '.dat'
        ds_path = os.path.join(e_path, ds_name)
        sr = ds_attrs.pop('sampling_rate')
        bark_ds = bark.write_sampled(ds_path, ds, sr, **ds_attrs)
        if verbose:
            print('Created sampled dataset: ' + ds_path)
    elif arf.is_marked_pointproc(ds):
        ds_name += '.csv'
        ds_path = os.path.join(e_path, ds_name)
        ds_data = pandas.DataFrame(ds)
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

