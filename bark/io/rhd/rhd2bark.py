import os.path
from datetime import datetime
import numpy as np
from bark.io.rhd.load_intan_rhd_format import read_data
from bark import create_entry, write_metadata

import re


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
        help=
        """format: YYYY-MM-DD or YYYY-MM-DD_HH-MM-SS.S, if left unspecified
            the timestamp will be inferred from the filename of the first RHD file.""")
    p.add_argument(
        "-p",
        "--parents",
        help=
        "No error if already exists, new meta-data written, and datasets will be overwritten.",
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
    rhds_to_entry(args.rhdfiles, args.out, args.timestamp, args.parents,
                  args.maxgaps, **attrs)


def rhd_filename_to_timestamp(fname):
    datetime_regex = r'\d{6}_\d{6}'
    tstring = re.findall(datetime_regex, os.path.basename(fname))[0]
    return datetime.strptime(tstring, "%y%m%d_%H%M%S")


def chan_names(result, key):
    if key in result:
        return [chan['native_channel_name'] for chan in result[key]]
    else:
        return []


amp_chan_names = lambda result: chan_names(result, 'amplifier_channels')
adc_chan_names = lambda result: chan_names(result, 'board_adc_channels')


def board_adc_metadata(result, dsetname):
    attrs = dict(dtype=str(result['board_adc_data'].dtype),
                 n_channels=len(result['board_adc_channels']),
                 sampling_rate=result['frequency_parameters'][
                     'board_adc_sample_rate'],
                 unit_scale=result['ADC_input_bit_volts'],
                 units="V")
    channel_attrs = {k: [] for k, v in result['amplifier_channels'][0].items()}
    for chan in result['board_adc_channels']:
        for key, value in chan.items():
            channel_attrs[key].append(value)
    attrs.update(channel_attrs)
    write_metadata(dsetname + ".meta", **attrs)


def amplifier_metadata(result, dsetname):
    attrs = dict(dtype=str(result['amplifier_data'].dtype),
                 n_channels=len(result['amplifier_channels']),
                 sampling_rate=result['frequency_parameters'][
                     'amplifier_sample_rate'],
                 unit_scale=result['amplifier_bit_microvolts'],
                 units="uV")
    spike_triggers = {'spike_trigger_' + k: []
                      for k, v in result['spike_triggers'][0].items()}
    for chan in result['spike_triggers']:
        for key, value in chan.items():
            spike_triggers['spike_trigger_' + key].append(value)
    channel_attrs = {k: [] for k, v in result['amplifier_channels'][0].items()}
    for chan in result['amplifier_channels']:
        for key, value in chan.items():
            channel_attrs[key].append(value)
    attrs.update(spike_triggers)
    attrs.update(channel_attrs)
    attrs.update(result['frequency_parameters'])
    write_metadata(dsetname + ".meta", **attrs)


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


def rhds_to_entry(rhd_paths,
                  entry_name,
                  timestamp=None,
                  parents=False,
                  max_gaps=10,
                  **attrs):
    """
    Converts a temporally contiguous list of .rhd files to a bark entry.
    """
    if not timestamp:
        timestamp = rhd_filename_to_timestamp(rhd_paths[0])
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
