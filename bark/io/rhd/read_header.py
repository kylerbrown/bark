#! /bin/env python
#
# Michael Gibson 23 April 2015
# 2018 changes by Adrian Foy merged in 2021 by Graham Fetterman

# Note that this file contains many unannotated byte counts.
# There really isn't any sensible way to annotate them, and they
# are only relevant here.

import struct

from .qstring import read_qstring
from .constants import LAST_TESTED_MAJOR_VERSION

def read_header(fid):
    """Reads the Intan File Format header from the given file."""

    # Check 'magic number' at beginning of file to make sure this is an Intan
    # Technologies RHD2000 data file.
    magic_number, = struct.unpack('<I', fid.read(4))
    if magic_number != int('c6912702', 16):
        raise ValueError('Unrecognized file type.')

    header = {}

    # Read version number.
    version = {}
    (version['major'], version['minor']) = struct.unpack('<hh', fid.read(4))
    header['version'] = version

    print('\nReading Intan Technologies RHD2000 data file,',
          'version {}.{}\n'.format(version['major'], version['minor']))

    if version['major'] < 1:
        msg = 'Intan GUI version {} unrecognized.'.format(version['major'])
        raise ValueError(msg)

    if version['major'] > LAST_TESTED_MAJOR_VERSION:
        print('Warning: this converter has only been tested up to major',
              'version {}.\n'.format(LAST_TESTED_MAJOR_VERSION))

    freq = {}

    # Read information of sampling rate and amplifier frequency settings.
    header['sample_rate'], = struct.unpack('<f', fid.read(4))
    (freq['dsp_enabled'],
     freq['actual_dsp_cutoff_frequency'],
     freq['actual_lower_bandwidth'],
     freq['actual_upper_bandwidth'],
     freq['desired_dsp_cutoff_frequency'],
     freq['desired_lower_bandwidth'],
     freq['desired_upper_bandwidth']) = struct.unpack('<hffffff', fid.read(26))

    # This tells us if a software 50/60 Hz notch filter was enabled during the
    # data acquisition.
    (notch_filter_mode,) = struct.unpack('<h', fid.read(2))
    if notch_filter_mode == 1:
        header['notch_filter_frequency'] = 50
    elif notch_filter_mode == 2:
        header['notch_filter_frequency'] = 60
    else:
        header['notch_filter_frequency'] = 0
    freq['notch_filter_frequency'] = header['notch_filter_frequency']

    (freq['desired_impedance_test_frequency'],
     freq['actual_impedance_test_frequency']) = struct.unpack('<ff',
                                                              fid.read(8))

    # Text notes written by experimenter during data collection.
    note1 = read_qstring(fid)
    note2 = read_qstring(fid)
    note3 = read_qstring(fid)
    header['notes'] = {'note1': note1, 'note2': note2, 'note3': note3}

    # If data file is from GUI v1.1 or later, see if temperature sensor data
    # was saved.
    if (version['major'], version['minor']) >= (1, 1):
        (header['num_temp_sensor_channels'],) = struct.unpack('<h', fid.read(2))
    else:
        header['num_temp_sensor_channels'] = 0

    # If data file is from GUI v1.3 or later, load eval board mode.
    if (version['major'], version['minor']) >= (1, 3):
        (header['eval_board_mode'],) = struct.unpack('<h', fid.read(2))
    else:
        header['eval_board_mode'] = 0

    # Set data block sizes appropriately according to version.
    if version['major'] == 1:
        header['num_samples_per_data_block'] = 60
    else:
        header['num_samples_per_data_block'] = 128

    # If data file is from GUI v2.0 or later (Intan Recording Controller), load
    # name of digital reference channel.
    if version['major'] > 1:
        header['reference_channel'] = read_qstring(fid)

    # Place frequency-related information in data structure.
    # (Note: much of this structure is set above)
    freq['amplifier_sample_rate'] = header['sample_rate']
    freq['aux_input_sample_rate'] = header['sample_rate'] / 4
    freq['supply_voltage_sample_rate'] = (header['sample_rate'] /
                                          header['num_samples_per_data_block'])
    freq['board_adc_sample_rate'] = header['sample_rate']
    freq['board_dig_in_sample_rate'] = header['sample_rate']

    header['frequency_parameters'] = freq

    # Create lists for each type of data channel.
    header['spike_triggers'] = []
    header['amplifier_channels'] = []
    header['aux_input_channels'] = []
    header['supply_voltage_channels'] = []
    header['board_adc_channels'] = []
    header['board_dig_in_channels'] = []
    header['board_dig_out_channels'] = []

    # Read signal summary from data file header.

    (number_of_signal_groups,) = struct.unpack('<h', fid.read(2))

    # This unfortunate divergence in loop index seems to have appeared in v2.0.
    if version['major'] == 1:
        signal_group_id_start = 0
    else:
        signal_group_id_start = 1
    for signal_group in range(signal_group_id_start,
                              number_of_signal_groups + signal_group_id_start):
        signal_group_name = read_qstring(fid)
        signal_group_prefix = read_qstring(fid)
        (signal_group_enabled,
         signal_group_num_channels,
         signal_group_num_amp_channels) = struct.unpack('<hhh', fid.read(6))

        if signal_group_num_channels > 0 and signal_group_enabled > 0:
            for signal_channel in range(0, signal_group_num_channels):
                new_channel = {'port_name': signal_group_name,
                               'port_prefix': signal_group_prefix,
                               'port_number': signal_group}
                new_channel['native_channel_name'] = read_qstring(fid)
                new_channel['custom_channel_name'] = read_qstring(fid)
                (new_channel['native_order'],
                 new_channel['custom_order'],
                 signal_type,
                 channel_enabled,
                 new_channel['chip_channel'],
                 new_channel['board_stream']) = struct.unpack('<hhhhhh',
                                                              fid.read(12))
                new_trigger_channel = {}
                trigger_info = struct.unpack('<hhhh', fid.read(8))
                (new_trigger_channel['voltage_trigger_mode'],
                 new_trigger_channel['voltage_threshold'],
                 new_trigger_channel['digital_trigger_channel'],
                 new_trigger_channel['digital_edge_polarity']) = trigger_info

                impedance_info = struct.unpack('<ff', fid.read(8))
                (new_channel['electrode_impedance_magnitude'],
                 new_channel['electrode_impedance_phase']) = impedance_info

                if channel_enabled:
                    if signal_type == 0:
                        header['amplifier_channels'].append(new_channel)
                        header['spike_triggers'].append(new_trigger_channel)
                    elif signal_type == 1:
                        header['aux_input_channels'].append(new_channel)
                    elif signal_type == 2:
                        header['supply_voltage_channels'].append(new_channel)
                    elif signal_type == 3:
                        header['board_adc_channels'].append(new_channel)
                    elif signal_type == 4:
                        header['board_dig_in_channels'].append(new_channel)
                    elif signal_type == 5:
                        header['board_dig_out_channels'].append(new_channel)
                    else:
                        raise ValueError('Unknown channel type.')

    # Summarize contents of data file.
    header['num_amplifier_channels'] = len(header['amplifier_channels'])
    header['num_aux_input_channels'] = len(header['aux_input_channels'])
    header['num_supply_voltage_channels'] = len(header['supply_voltage_channels'])
    header['num_board_adc_channels'] = len(header['board_adc_channels'])
    header['num_board_dig_in_channels'] = len(header['board_dig_in_channels'])
    header['num_board_dig_out_channels'] = len(header['board_dig_out_channels'])

    return header
