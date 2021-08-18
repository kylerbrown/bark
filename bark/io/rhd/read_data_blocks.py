#! /bin/env python
#
# Michael Gibson 23 April 2015
# Graham Fetterman April 2018

import numpy as np

from . import constants as const

def preallocate_memory(header, num_datablocks, digital_io_data_dtype=np.uint):
    """Preallocates space for a chunk of data.

    Args:
        header (dict): metadata
        num_datablocks (int): size of chunk in datablocks
        digital_io_data_dtype (numpy dtype): what dtype the digital I/O data is
                                             stored as (default: np.uint)

    Returns:
        dict of numpy arrays: array sizes and types depend on Intan specs
    """
    data = {}
    if ((header['version']['major'], header['version']['minor']) >= (1, 2)):
        time_dtype = const.TIMESTAMP_DTYPE_GE_V1_2
    else:
        time_dtype = const.TIMESTAMP_DTYPE_LE_V1_1
    num_samples = header['num_samples_per_data_block']
    data['t_amplifier'] = np.zeros(num_samples * num_datablocks, dtype=time_dtype)
    data['amplifier_data'] = np.zeros([header['num_amplifier_channels'],
                                       num_samples * num_datablocks],
                                      dtype=const.AMPLIFIER_DTYPE)
    data['aux_input_data'] = np.zeros([header['num_aux_input_channels'],
                                       (num_samples // 4) * num_datablocks],
                                      dtype=const.AUXILIARY_DTYPE)
    data['supply_voltage_data'] = np.zeros([header['num_supply_voltage_channels'],
                                            1 * num_datablocks],
                                           dtype=const.SUPPLY_DTYPE)
    data['temp_sensor_data'] = np.zeros([header['num_temp_sensor_channels'],
                                         1 * num_datablocks],
                                        dtype=const.TEMP_DTYPE)
    data['board_adc_data'] = np.zeros([header['num_board_adc_channels'],
                                       num_samples * num_datablocks],
                                      dtype=const.ADC_DTYPE)
    data['board_dig_in_data'] = np.zeros([header['num_board_dig_in_channels'],
                                          num_samples * num_datablocks],
                                         dtype=digital_io_data_dtype)
    data['board_dig_in_raw'] = np.zeros(num_samples * num_datablocks,
                                        dtype=const.DIG_IN_DTYPE)
    data['board_dig_out_data'] = np.zeros([header['num_board_dig_out_channels'],
                                           num_samples * num_datablocks],
                                          dtype=digital_io_data_dtype)
    data['board_dig_out_raw'] = np.zeros(num_samples * num_datablocks,
                                         dtype=const.DIG_OUT_DTYPE)
    return data

def read_data_blocks(data, header, fid, datablocks_per_chunk=1):
    """Reads a number of data blocks from fid into data.

    Args:
        data (dict of numpy arrays): having the same format as the return value
            of preallocate_memory() above
        header (dict): metadata
        fid (file object): file to read from
        datablocks_per_chunk (int): how many datablocks to read in
    """
    all_names = ['time',
                 'amp',
                 'aux',
                 'supply',
                 'temp',
                 'adc',
                 'digin',
                 'digout']

    # In version 1.2, Intan moved from saving timestamps as unsigned
    # integers to signed integers to accommodate negative (adjusted)
    # timestamps for pretrigger data.
    if ((header['version']['major'], header['version']['minor']) >= (1, 2)):
        time_dtype = const.TIMESTAMP_DTYPE_GE_V1_2
    else:
        time_dtype = const.TIMESTAMP_DTYPE_LE_V1_1
    
    all_dtypes = [time_dtype,
                  const.AMPLIFIER_DTYPE,
                  const.AUXILIARY_DTYPE,
                  const.SUPPLY_DTYPE,
                  const.TEMP_DTYPE,
                  const.ADC_DTYPE,
                  const.DIG_IN_DTYPE,
                  const.DIG_OUT_DTYPE]

    num_time_chans = 1
    all_chans = [num_time_chans,
                 header['num_amplifier_channels'],
                 header['num_aux_input_channels'],
                 header['num_supply_voltage_channels'],
                 header['num_temp_sensor_channels'],
                 header['num_board_adc_channels'],
                 header['num_board_dig_in_channels'],
                 header['num_board_dig_out_channels']]

    num_samples = header['num_samples_per_data_block']
    all_samples = [num_samples,
                   num_samples,
                   num_samples // 4,
                   1,
                   1,
                   num_samples,
                   num_samples,
                   num_samples]
    
    # create a structured dtype for one datablock
    db_dtype = [(name, (dt, chans * samples))
                for name, dt, chans, samples
                in zip(all_names, all_dtypes, all_chans, all_samples)]

    chunk = np.fromfile(fid, dtype=np.dtype(db_dtype), count=datablocks_per_chunk)
    
    for idx, db in enumerate(chunk):

        # Timebase
        start = idx * num_samples
        stop = (idx + 1) * num_samples
        data['t_amplifier'][start:stop] = db['time']

        # Amplifier channels
        if header['num_amplifier_channels']:
            start = idx * num_samples
            stop = (idx + 1) * num_samples
            values = db['amp'].reshape(header['num_amplifier_channels'],
                                       num_samples)
            data['amplifier_data'][:,start:stop] = values

        # Auxiliary channels
        if header['num_aux_input_channels']:
            start = idx * (num_samples // 4)
            stop = (idx + 1) * (num_samples // 4)
            values = db['aux'].reshape(header['num_aux_input_channels'],
                                       num_samples // 4)
            data['aux_input_data'][:,start:stop] = values

        # Supply voltage channels
        if header['num_supply_voltage_channels'] > 0:
            start = idx * 1
            stop = (idx + 1) * 1
            values = db['supply'].reshape(header['num_supply_voltage_channels'],
                                          1)
            data['supply_voltage_data'][:,start:stop] = values

        # Temperature sensor channels
        if header['num_temp_sensor_channels'] > 0:
            start = idx * 1
            stop = (idx + 1) * 1
            values = db['temp'].reshape(header['num_temp_sensor_channels'], 1)
            data['temp_sensor_data'][:,start:stop] = values

        # Board ADC channels
        if header['num_board_adc_channels'] > 0:
            start = idx * num_samples
            stop = (idx + 1) * num_samples
            values = db['adc'].reshape(header['num_board_adc_channels'],
                                       num_samples)
            data['board_adc_data'][:,start:stop] = values

        # Board digital input channels (packed together)
        if header['num_board_dig_in_channels'] > 0:
            start = idx * num_samples
            stop = (idx + 1) * num_samples
            values = db['digin'].reshape(header['num_board_dig_in_channels'],
                                         num_samples)
            data['board_dig_in_raw'][start:stop] = values

        # Board digital output channels (packed together)
        if header['num_board_dig_out_channels'] > 0:
            start = idx * num_samples
            stop = (idx + 1) * num_samples
            values = db['digout'].reshape(header['num_board_dig_out_channels'],
                                          num_samples)
            data['board_dig_out_raw'][start:stop] = values
