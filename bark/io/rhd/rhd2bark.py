import sys
import os.path
import arrow
import itertools
from dateutil import tz
import numpy as np
import bark.io.rhd.load_intan_rhd_format as lirf
import bark.io.rhd.legacy_load_intan_rhd_format as legacy_lirf
from bark import create_entry, write_metadata

DEFAULT_MAX_MEM = '3GB'

def bark_rhd_to_entry():
    import argparse
    default_max_gaps = 10
    p = argparse.ArgumentParser(
        description="""Create a Bark entry from RHD files
            RHD files should be contiguous in time.

            An error is raised if the RHD files do not all have the same
            channels recorded.
            """)
    p.add_argument("rhdfiles", help="RHD file(s) to convert", nargs="+")
    p.add_argument("-o", "--out", help="name of bark entry", required=True)
    p.add_argument("-a",
                   "--attributes",
                   action='append',
                   type=lambda kv: kv.split("="),
                   dest='keyvalues',
                   help="extra metadata in the form of KEY=VALUE")
    p.add_argument(
        "-t",
        "--timestamp",
        help="""format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS.S, if left unspecified
            the timestamp will be inferred from the filename of the
            first RHD file.""")
    p.add_argument('--timezone',
                   help="timezone of timestamp, \
            default: America/Chicago",
                   default='America/Chicago')
    p.add_argument(
        "-p",
        "--parents",
        help="No error if already exists, new meta-data written, \
                and datasets will be overwritten.",
        action="store_true")
    p.add_argument(
        "-g",
        "--maxgaps",
        help="Maximum allowable gaps in continuous data, default: {}."
        .format(default_max_gaps),
        type=int,
        default=default_max_gaps)
    p.add_argument(
        "-l",
        "--legacy",
        help="Use original Intan-derived code (slower)",
        action="store_true")
    p.add_argument(
        "-m",
        "--max-memory",
        help='Rough maximum memory usage (default: "{}")'.format(DEFAULT_MAX_MEM),
        default=DEFAULT_MAX_MEM)
    args = p.parse_args()
    attrs = dict(args.keyvalues) if args.keyvalues else {}
    check_exists(args.rhdfiles)
    max_mem = max_mem_from_string(args.max_memory)
    rhds_to_entry(args.rhdfiles, args.out, args.timestamp, args.parents,
                  args.maxgaps, args.timestamp, legacy=args.legacy, max_mem=max_mem, **attrs)


def max_mem_from_string(s):
    mem_dict = {'kb': 10, 'mb': 20, 'gb': 30}
    if len(s) < 2:
        raise ValueError('{} is not a valid amount of memory'.format(s))
    s = ''.join(s.split()).lower()
    if s[-2:] in mem_dict:
        pwr = mem_dict[s[-2:]]
    elif s[-1] == 'b':
        pwr = 0
    else:
        raise ValueError('{} is not a valid amount of memory'.format(s))
    return int(float(s[:-2])) * (2 ** pwr)

def rhd_filename_to_timestamp(fname, timezone):
    return arrow.get(fname, 'YYMMDD_HHmmss').replace(
        tzinfo=tz.gettz(timezone)).datetime


def input_string_to_timestamp(string, timezone):
    return arrow.get(string).replace(tzinfo=tz.gettz(timezone)).datetime


def chan_names(result, key):
    if key in result:
        return [chan['native_channel_name'] for chan in result[key]]
    else:
        return []


def amp_chan_names(result):
    return chan_names(result, 'amplifier_channels')


def adc_chan_names(result):
    return chan_names(result, 'board_adc_channels')


def board_adc_metadata(result, dsetname):
    attrs = dict(dtype=result['board_adc_data'].dtype.str,
                 sampling_rate=result['frequency_parameters'][
                     'board_adc_sample_rate'], )
    columns = {i: chan_attrs
               for i, chan_attrs in enumerate(result['board_adc_channels'])}
    for k in columns:
        columns[k]['units'] = 'V'
        columns[k]['unit_scale'] = result['ADC_input_bit_volts']
    write_metadata(dsetname, columns=columns, **attrs)


def amplifier_metadata(result, dsetname):
    attrs = dict(dtype=result['amplifier_data'].dtype.str,
                 sampling_rate=result['frequency_parameters'][
                     'amplifier_sample_rate'], )
    attrs.update(result['frequency_parameters'])
    columns = {i: chan_attrs
               for i, chan_attrs in enumerate(result['amplifier_channels'])}
    for k in columns:
        columns[k]['units'] = 'uV'
        columns[k]['unit_scale'] = result['amplifier_bit_microvolts']
    write_metadata(dsetname, columns=columns, **attrs)


def not_implemented_warnings(result):
    if 'aux_input_channels' in result:
        print("AUX INPUT DATA CONVERSION NOT YET IMPLEMENTED")
    if 'supply_voltage_data' in result:
        print("SUPPLY VOLTAGE DATA CONVERSION NOT YET IMPLEMENTED")
    if 'board_dig_in_data' in result:
        print("DIGITAL INPUT DATA CONVERSION NOT YET IMPLEMENTED")
    if 'board_dig_out_data' in result:
        print("DIGITAL OUTPUT DATA CONVERSION NOT YET IMPLEMENTED")
    if 'temp_sensor_data' in result:
        print("TEMP SENSOR DATA CONVERSION NOT YET IMPLEMENTED")


def count_timestamp_gaps(data, last_chunk_last_timestamp):
    epsilon = 1. / data['frequency_parameters']['amplifier_sample_rate']
    num_gaps = 0
    if not np.isclose(data['t_amplifier'][0] - last_chunk_last_timestamp,
                      epsilon):
        num_gaps += 1
    num_gaps += np.sum(~np.isclose(np.diff(data['t_amplifier']), epsilon))
    return num_gaps


def check_exists(rhd_paths):
    for filepath in rhd_paths:
        if not os.path.exists(filepath):
            print("file {} does not exist".format(filepath))
            sys.exit(0)


def rhds_to_entry(rhd_paths,
                  entry_name,
                  timestamp=None,
                  parents=False,
                  max_gaps=10,
                  timezone='America/Chicago',
                  legacy=False,
                  max_mem=DEFAULT_MAX_MEM,
                  **attrs):
    """
    Converts a temporally contiguous list of .rhd files to a bark entry.
    """
    if not timestamp:
        timestamp = rhd_filename_to_timestamp(rhd_paths[0], timezone)
    else:
        timestamp = input_string_to_timestamp(timestamp, timezone)
    # process first file and create entry and datasets as needed
    first,rest = data_feed(rhd_paths[0], legacy, max_mem)
    attrs.update(first['notes'])
    create_entry(entry_name, timestamp, parents, **attrs)
    adc_channels = adc_chan_names(first)
    amp_channels = amp_chan_names(first)
    adc_dset_name = None
    amp_dset_name = None
    if adc_channels:
        adc_dset_name = os.path.join(entry_name, 'board_adc.dat')
        board_adc_metadata(first, adc_dset_name)
        open(adc_dset_name, 'wb').close()
    if amp_channels:
        amp_dset_name = os.path.join(entry_name, 'amplifier.dat')
        amplifier_metadata(first, amp_dset_name)
        open(amp_dset_name, 'wb').close()
    write_data_feed(first, rest, adc_dset_name, amp_dset_name, max_gaps)
    # process the rest of the files
    for rhd_file in rhd_paths[1:]:
        first,rest = data_feed(rhd_file, legacy, max_mem)
        # check that channels are all the same as first file
        for cur,old in zip((adc_channels, amp_channels),
                           (adc_chan_names(first), amp_chan_names(first))):
            if cur != old:
                msg = '{} has channels {}\n{} has channels {}'
                raise ValueError(msg.format(rhd_file, cur, rhd_paths[0], old))
        write_data_feed(first, rest, adc_dset_name, amp_dset_name, max_gaps)

def data_feed(rhd_file, legacy, max_memory):
    """Set up a stream to feed data from rhd_file in chunks.

    Args:
        rhd_file (str): filename
        legacy (bool): whether to use legacy Intan-provided code
        max_memory (number): memory size of chunks, in bytes

    Returns:
        tuple(dict, iterable): first chunk in stream, plus rest of stream
    """
    print(rhd_file)
    if legacy:
        # the legacy code reads the entire file's contents into memory at once,
        # so there's nothing left after the first chunk
        return (legacy_lirf.read_data(rhd_file, no_floats=True), [])
    else:
        feed = lirf.read_data(rhd_file, no_floats=True, max_memory=max_memory)
        return (next(feed), feed)

def write_data_feed(first, rest, adc_fn, amp_fn, max_gaps):
    """Write a data feed to disk.

    Args:
        first (dict): first chunk in the data feed
        rest (iterable): rest of the data feed
        adc_fn (str or None): filename of the ADC bark dataset
        amp_fn (str or None): filename of the amplifier bark dataset
        max_gaps (int): maximum number of "non-small" gaps in the timestamps
                        that will be tolerated
    """
    not_implemented_warnings(first)
    last_timestamp = first['t_amplifier'][0]
    timestamp_gaps = 0
    for data_chunk in itertools.chain([first], rest):
        timestamp_gaps += count_timestamp_gaps(data_chunk, last_timestamp)
        last_timestamp = data_chunk['t_amplifier'][-1]
        if adc_fn:
            with open(adc_fn, 'ab') as fp:
                 data_chunk['board_adc_data'].T.tofile(fp)
        if amp_fn:
            with open(amp_fn, 'ab') as fp:
                 data_chunk['amplifier_data'].T.tofile(fp)
    if timestamp_gaps > max_gaps:
        msg = '{} timestamp gaps in data exceed maximum limit {}'
        raise Exception(msg.format(timestamp_gaps, max_gaps))

