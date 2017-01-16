from __future__ import absolute_import
import argparse
import bark
import pandas
import functools
import copy
import base64
import os.path
import sys

def label_to_splits(sampled_ds, event_ds, split_on, point_mode):
    """
    Produces a DataFrame describing ranges of indices into the sampled
    dataset, according to the events in the event dataset. The DataFrame is
    sorted by range start, ascending.
    
    In Point mode, a sequence of split ranges is generated using the 'start'
    times from all events in the event dataset. These ranges fully span the
    sampled dataset. Any label names in the event dataset are dropped.
    
    In Interval mode (point_mode == False), the sequence of split ranges
    generated corresponds exactly to the intervals described in the event
    dataset. Obviously, unless the intervals themselves span the
    dataset, there is no guarantee of spanning. Label names are preserved in
    the output DataFrame.

    If split_on is an empty string, all events are used in the splitting
    process. Otherwise, only events with names matching split_on are used. This
    behavior applies to both modes.

    This function currently ignores tier identity.

    Inputs
    sampled_ds -> a SampledData object
    event_ds -> an EventData object
    point_mode -> boolean; True means point mode, False means interval mode
    split_on -> string; if empty, split on all labels regardless of name

    Output -> DataFrame with columns 'start', 'stop', 'name'
    """
    splits = event_ds.data.copy(deep=True)
    if split_on != '':
        try:
            splits = splits[splits['name'] == split_on]
        except KeyError:
            raise KeyError('label file does not contain label column')
    if event_ds.attrs['units'] == 's':
        map_fn = functools.partial(time_to_index, ds_attrs=sampled_ds.attrs)
        splits = splits.apply(map_fn, axis='columns')
    elif event_ds.attrs['units'] == 'samples':
        # no modification required
        pass
    else:
        msg = '{} units not recognized: {}'.format(event_ds.path,
                                                   event_ds.attrs['units'])
        raise KeyError(msg)
    if point_mode:
        splits = points_to_span(list(splits.loc[:,'start']), sampled_ds.attrs)
    return splits.sort_values(by='start').reset_index(drop=True)

def time_to_index(series, ds_attrs):
    """Transforms an event's limits from seconds to indices into an array."""
    sta = int(round(series['start'] * ds_attrs['sampling_rate']))
    if 'stop' in series:
        sto = int(round(series['stop'] * ds_attrs['sampling_rate']))
    else:
        sto = float('nan')
    return pandas.Series({'start': sta, 'stop': sto, 'name': series['name']})

def points_to_span(points, ds_attrs):
    """Produces a spanning split of an interval from a list of points."""
    if points[0] == 0:
        new_start = []
    else:
        new_start = [0]
    new_start.extend(points)

    new_stop = new_start[1:]
    last_elt = ds_attrs['n_channels'] * ds_attrs['n_samples']
    if new_start[-1] < last_elt:
        new_stop.append(last_elt)
    else:
        _ = new_start.pop()

    new_label = [''] * len(new_start)
    
    return pandas.DataFrame({'start': new_start,
                             'stop': new_stop,
                             'name': new_label})

def gen_split_files(entry, sampled_ds, event_ds, splits, split_on, point_mode):
    """
    Generates new sampled datasets, constructed by splitting the original
    sampled dataset according to the intervals described in splits. Also
    produces .meta files for each new dataset.
    
    To reduce the likelihood of filename collisions across successive uses
    of the splitting tool, the following format is used:
    '[parent_name]_via_[enc(split_on)]_[mode]_in_[event_ds_name]_split_[#]'
    The split_on label is URL-safe-encoded, and can be recovered by decoding.
    
    Inputs
    entry -> Entry object
    sampled_ds -> SampledData object
    event_ds -> EventData object
    splits -> DataFrame with columns 'start', 'stop', 'name'
    split_on -> string
    point_mode -> boolean
    
    Output -> list of SampledData objects
    """
    parent_dir, parent_fn = os.path.split(sampled_ds.path)
    parent_name, parent_ext = os.path.splitext(parent_fn)
    event_file = os.path.splitext(os.path.split(event_ds.path)[1])[0]
    if split_on == '':
        name = 'all'
    else:
        name = base64.urlsafe_b64encode(split_on)

    if point_mode:
        split_string = 'point'
        split_abbr = 'pt'
    else:
        split_string = 'interval'
        split_abbr = 'intvl'

    new_ds_list = []
    for i, series in splits.iterrows():
        child_fn = '{}_via_{}_{}_in_{}_split_{:d}{}'.format(parent_name,
                                                            name,
                                                            split_abbr,
                                                            event_file,
                                                            i,
                                                            parent_ext)
        path = os.path.join(parent_dir, child_fn)

        data = sampled_ds.data[series['start']:series['stop'],:]

        attrs = copy.deepcopy(sampled_ds.attrs)
        sr = attrs.pop('sampling_rate', None)
        units = attrs.pop('units', None)

        attrs['n_samples'] = series['stop'] - series['start']
        
        attrs['name'] = series['name']
        attrs['split_num'] = i
        attrs['total_splits'] = len(splits)
        attrs['parent_ds'] = sampled_ds.path
        attrs['split_loc_ds'] = event_ds.path
        attrs['entry_uuid'] = entry.attrs['uuid']
        attrs['offset'] = series['start']
        attrs['offset_units'] = 'samples'
        attrs['split_mode'] = split_string
        
        new_ds = bark.write_sampled(path,
                                    data,
                                    sr,
                                    units,
                                    **attrs)
        new_ds_list.append(new_ds)
    return new_ds_list

def parse_args(raw_args):
    desc = ('Splits a sampled-data record according to the split times in a ' +
            'label file. Works on both single entries and recursively over ' +
            'an entire BARK root.')
    epilog = 'Exactly one of --point and --interval is required.'
    parser = argparse.ArgumentParser(description=desc, epilog=epilog)
    parser.add_argument('-v', '--verbose', help='increase verbosity',
                        action='store_true')
    split_type_group = parser.add_mutually_exclusive_group(required=True)
    split_type_group.add_argument('-p',
                                  '--point',
                                  help='split on start values (spans dataset)',
                                  action='store_true')
    split_type_group.add_argument('-i',
                                  '--interval',
                                  help='extract only intervals (may not span)',
                                  action='store_true')
    parser.add_argument('-n',
                        '--name',
                        help='label to split on (default: split on all)',
                        default='')
    parser.add_argument('path', help='may be Entry or Root')
    parser.add_argument('sampled_data', help='sampled data file')
    parser.add_argument('label_file', help='label file containing splits')
    args = parser.parse_args(raw_args)
    return args

def split_dataset(path,
                  sampled_data,
                  label_file,
                  split_on,
                  point_mode,
                  verbose):
    # if path is not an Entry (i.e., if it is a Root), it will lack a 
    # timestamp or uuid, and read_entry will throw a KeyError
    try:
        entry = bark.read_entry(path)
    except KeyError:
        entry = None
    if entry:
        root = bark.Root('', {entry.path: entry}, {})
    else:
        root = bark.read_root(path)
    for ename,entry in root.entries.iteritems():
        if sampled_data not in entry.datasets.iterkeys():
            if verbose:
                print ('No dataset ' + sampled_data + ' in entry ' + entry.path)
        elif label_file not in entry.datasets.iterkeys():
            if verbose:
                print ('No dataset ' + label_file + ' in entry ' + entry.path)
        else:
            split_limits = label_to_splits(entry[sampled_data],
                                           entry[label_file],
                                           split_on,
                                           point_mode)
            new_ds_list = gen_split_files(entry,
                                          entry[sampled_data],
                                          entry[label_file],
                                          split_limits,
                                          split_on,
                                          point_mode)

def _main():
    args = parse_args(sys.argv[1:])
    split_dataset(args.path,
                  args.sampled_data,
                  args.label_file,
                  args.name,
                  args.point,
                  args.verbose)

if __name__ == '__main__':
    _main()
