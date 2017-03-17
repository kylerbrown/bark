import sys
import os.path
import arrow
from dateutil import tz
import numpy as np
from bark.io.rhd.load_intan_rhd_format import read_data
from bark import create_entry, write_metadata


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
    p.add_argument("-o", "--out", help="name of bark entry")
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
    args = p.parse_args()
    attrs = dict(args.keyvalues) if args.keyvalues else {}
    check_exists(args.rhdfiles)
    rhds_to_entry(args.rhdfiles, args.out, args.timestamp, args.parents,
                  args.maxgaps, args.timestamp, **attrs)


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


def check_timestamp_gaps(data, max_gaps):
    num_gaps = np.sum(~np.isclose(
        np.diff(data['t_amplifier']), 1. / data['frequency_parameters'][
            'amplifier_sample_rate']))
    if num_gaps > max_gaps:
        raise Exception("{} data gaps exceeds maximum limit {}".format(
            num_gaps, max_gaps))


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
                  **attrs):
    """
    Converts a temporally contiguous list of .rhd files to a bark entry.
    """
    if not timestamp:
        timestamp = rhd_filename_to_timestamp(rhd_paths[0], timezone)
    else:
        timestamp = input_string_to_timestamp(timestamp, timezone)
    # extract data and metadata from first file
    print(rhd_paths[0])
    result = read_data(rhd_paths[0], no_floats=True)
    not_implemented_warnings(result)
    check_timestamp_gaps(result, max_gaps)
    # make entry
    entry_attrs = result['notes']
    attrs.update(entry_attrs)
    create_entry(entry_name, timestamp, parents, **attrs)
    # make datasets
    board_channels = adc_chan_names(result)
    if board_channels:
        dsetname = os.path.join(entry_name, 'board_adc.dat')
        board_adc_metadata(result, dsetname)
        with open(dsetname, 'wb') as fp:
            fp.write(result['board_adc_data'].T.tobytes())

    amplifier_channels = amp_chan_names(result)
    if amplifier_channels:
        dsetname = os.path.join(entry_name, 'amplifier.dat')
        amplifier_metadata(result, dsetname)
        with open(dsetname, 'wb') as fp:
            fp.write(result['amplifier_data'].T.tobytes())

    # now that the metadata has been written (and data from the first file)
    # write data for the remainder of the files
    for rhdfile in rhd_paths[1:]:
        print(rhdfile)
        result = read_data(rhdfile, no_floats=True)
        not_implemented_warnings(result)
        check_timestamp_gaps(result, max_gaps)
        cur_board_channels = adc_chan_names(result)
        cur_amplifier_channels = amp_chan_names(result)

        # check that the same channels are being recorded
        if board_channels != cur_board_channels:
            raise ValueError("""{} has channels {}
                    {} has channels {} """.format(
                rhdfile, cur_board_channels, rhd_paths[0], board_channels))
        if amplifier_channels != cur_amplifier_channels:
            raise ValueError("""{} has channels {}
                    {} has channels {}"""
                             .format(rhdfile, cur_amplifier_channels,
                                     rhd_paths[0], amplifier_channels))
        # write data
        if cur_board_channels:
            dsetname = os.path.join(entry_name, 'board_adc.dat')
            with open(dsetname, 'ab') as fp:
                fp.write(result['board_adc_data'].T.tobytes())
        if cur_amplifier_channels:
            dsetname = os.path.join(entry_name, 'amplifier.dat')
            with open(dsetname, 'ab') as fp:
                fp.write(result['amplifier_data'].T.tobytes())
