import os.path
from datetime import datetime
from bark.io.rhd.load_intan_rhd_format import read_data
from bark import create_entry, write_metadata

def bark_rhd_to_entry():
    import argparse
    p = argparse.ArgumentParser(
            description="""Create a Bark entry from RHD files
            RHD files must be contiguous in time.""")
    p.add_argument("rhdfiles", help="RHD file(s) to convert",
            nargs="+")
    p.add_argument("-o", "--out", help="name of bark entry")
    p.add_argument("-a", "--attributes", action='append',
            type=lambda kv: kv.split("="), dest='keyvalues',
            help="extra metadata in the form of KEY=VALUE")
    p.add_argument("-t", "--timestamp",
            help="""format: YYYY-MM-DD or YYYY-MM-DD_HH-MM-SS.S, if left unspecified
            the timestamp will be inferred from the filename of the first RHD file.""")
    p.add_argument("-p", "--parents", 
            help="No error if already exists, new meta-data written, and datasets will be overwritten.",
            action="store_true")
    args = p.parse_args()
    if args.keyvalues:
        rhds_to_entry(args.rhdfiles, args.out, args.timestamp, args.parents, **dict(args.keyvalues))
    else:
        rhds_to_entry(args.rhdfiles, args.out, args.timestamp, args.parents)



def rhd_filename_to_timestamp(fname):
    tstring = fname.split("_", 1)[-1].split(".")[0]
    return datetime.strptime(tstring, "%y%m%d_%H%M%S")


def rhds_to_entry(rhd_paths, entry_name, timestamp=None, parents=False, **attrs):
    """
    Converts a temporally contiguous list of .rhd files to a bark entry.
    """
    # attempt to parse time from first file name
    if not timestamp:
        try:
            timestamp = rhd_filename_to_timestamp(rhd_paths[0])
        except ValueError:
            print("could not extract timestamp from filename")
            timestamp = [0, 0]
    # extract data and metadata from first file
    result = read_data(rhd_paths[0], no_floats=True)
    entry_attrs = result['notes']
    attrs.update(entry_attrs)
    # make entry
    create_entry(entry_name, timestamp, parents, **attrs)
    # make datasets
    if 'board_adc_data' in result:
        dsetname = os.path.join(entry_name, 'board_adc.dat')
        # make metadata
        attrs = dict(dtype=str(result['board_adc_data'].dtype),
                     n_channels=len(result['board_adc_channels']),
                     sampling_rate=result['frequency_parameters'][
                         'board_adc_sample_rate'],
                     unit_scale=result['ADC_input_bit_volts'],
                     units="V")
        channel_attrs = {k: []
                         for k, v in result['amplifier_channels'][0].items()}
        for chan in result['board_adc_channels']:
            for key, value in chan.items():
                channel_attrs[key].append(value)
        attrs.update(channel_attrs)
        write_metadata(dsetname + ".meta", **attrs)
        # write data
        with open(dsetname, 'wb') as fp:
            fp.write(result['board_adc_data'].T.tobytes())

    if 'amplifier_data' in result:
        dsetname = os.path.join(entry_name, 'amplifier.dat')
        # make metadata
        attrs = dict(dtype=str(result['amplifier_data'].dtype),
                     n_channels=len(result['amplifier_channels']),
                     sampling_rate=result['frequency_parameters'][
                         'amplifier_sample_rate'],
                     unit_scale=result['amplifier_bit_microvolts'],
                     units="mV")
        spike_triggers = {'spike_trigger_' + k: []
                          for k, v in result['spike_triggers'][0].items()}
        for chan in result['spike_triggers']:
            for key, value in chan.items():
                spike_triggers['spike_trigger_' + key].append(value)
        channel_attrs = {k: []
                         for k, v in result['amplifier_channels'][0].items()}
        for chan in result['amplifier_channels']:
            for key, value in chan.items():
                channel_attrs[key].append(value)
        attrs.update(spike_triggers)
        attrs.update(channel_attrs)
        attrs.update(result['frequency_parameters'])
        write_metadata(dsetname + ".meta", **attrs)
        # write data
        with open(dsetname, 'wb') as fp:
            fp.write(result['amplifier_data'].T.tobytes())
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

    for rhdfile in rhd_paths[1:]:
        result = read_data(rhd_paths[0], no_floats=True)
        dsetname = os.path.join(entry_name, 'board_adc.dat')
        with open(dsetname, 'ab') as fp:
            fp.write(result['board_adc_data'].T.tobytes())
        dsetname = os.path.join(entry_name, 'amplifier.dat')
        with open(dsetname, 'ab') as fp:
            fp.write(result['amplifier_data'].T.tobytes())



