#! /bin/env python
#
# Michael Gibson 23 April 2015
# 2018 changes by Adrian Foy merged in 2021 by Graham Fetterman

import struct
import numpy as np

from . import constants as const

def read_one_data_block(data, header, indices, fid):
    """Reads one data block from fid into data, at location per indices."""

    num_samples = header['num_samples_per_data_block']

    # Timebase

    # Prior to version 1.2, timestamps are unsigned integers.
    # From version 1.2 onwards, timestamps are signed integers, to accommodate
    # negative (adjusted) timestamps for pretrigger data.
    if (header['version']['major'], header['version']['minor']) >= (1, 2):
        time_dtype = const.TIMESTAMP_DTYPE_GE_V1_2
    else:
        time_dtype = const.TIMESTAMP_DTYPE_LE_V1_1
    start = indices['amplifier']
    stop = indices['amplifier'] + num_samples
    byte_layout = '<' + time_dtype.char * num_samples
    byte_count = time_dtype.itemsize * num_samples
    values = np.array(struct.unpack(byte_layout, fid.read(byte_count)))
    data['t_amplifier'][start:stop] = values

    # Amplifier channels

    if header['num_amplifier_channels'] > 0:
        num_channels = header['num_amplifier_channels']
        start = indices['amplifier']
        stop = indices['amplifier'] + num_samples
        num_values = num_samples * num_channels
        values = np.fromfile(fid, dtype=const.AMPLIFIER_DTYPE, count=num_values)
        values = values.reshape(num_channels, num_samples)
        data['amplifier_data'][:,start:stop] = values

    # Auxiliary input channels

    if header['num_aux_input_channels'] > 0:
        num_channels = header['num_aux_input_channels']
        start = indices['aux_input']
        stop = indices['aux_input'] + num_samples // 4
        num_values = (num_samples // 4) * num_channels
        values = np.fromfile(fid, dtype=const.AUXILIARY_DTYPE, count=num_values)
        values = values.reshape(num_channels, num_samples // 4)
        data['aux_input_data'][:,start:stop] = values

    # Supply voltage channels

    if header['num_supply_voltage_channels'] > 0:
        num_channels = header['num_supply_voltage_channels']
        start = indices['supply_voltage']
        stop = indices['supply_voltage'] + 1
        num_values = 1 * num_channels
        values = np.fromfile(fid, dtype=const.SUPPLY_DTYPE, count=num_values)
        values = values.reshape(num_channels, 1)
        data['supply_voltage_data'][:,start:stop] = values

    # Temperature sensor channels

    if header['num_temp_sensor_channels'] > 0:
        num_channels = header['num_temp_sensor_channels']
        start = indices['supply_voltage']
        stop = indices['supply_voltage'] + 1
        num_values = 1 * num_channels
        values = np.fromfile(fid, dtype=const.TEMP_DTYPE, count=num_values)
        values = values.reshape(num_channels, 1)
        data['temp_sensor_data'][:,start:stop] = values

    # Board ADC channels

    if header['num_board_adc_channels'] > 0:
        num_channels = header['num_board_adc_channels']
        start = indices['board_adc']
        stop = indices['board_adc'] + num_samples
        num_values = num_samples * num_channels
        values = np.fromfile(fid, dtype=const.ADC_DTYPE, count=num_values)
        values = values.reshape(num_channels, num_samples)
        data['board_adc_data'][:,start:stop] = values

    # Board digital input channels (packed together)

    if header['num_board_dig_in_channels'] > 0:
        start = indices['board_dig_in']
        stop = indices['board_dig_in'] + num_samples
        byte_layout = '<' + const.DIG_IN_DTYPE.char * num_samples
        byte_count = const.DIG_IN_DTYPE.itemsize * num_samples
        values = np.array(struct.unpack(byte_layout, fid.read(byte_count)))
        data['board_dig_in_raw'][start:stop] = values

    # Board digital output channels (packed together)

    if header['num_board_dig_out_channels'] > 0:
        start = indices['board_dig_out']
        stop = indices['board_dig_out'] + num_samples
        byte_layout = '<' + const.DIG_OUT_DTYPE.char * num_samples
        byte_count = const.DIG_OUT_DTYPE.itemsize * num_samples
        values = np.array(struct.unpack(byte_layout, fid.read(byte_count)))
        data['board_dig_out_raw'][start:stop] = values
