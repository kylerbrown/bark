#! /bin/env python
#
# Michael Gibson 23 April 2015
# Graham Fetterman April 2018

import numpy as np

NAMES = ['time', 'amp', 'aux', 'supply', 'temp', 'adc', 'digin', 'digout']

TIME_SAMPLES = 60
AMP_SAMPLES = 60
AUX_SAMPLES = 15
SUPPLY_SAMPLES = 1
TEMP_SAMPLES = 1
ADC_SAMPLES = 60
DIGIN_SAMPLES = 60
DIGOUT_SAMPLES = 60
ALL_SAMPLES = [TIME_SAMPLES, AMP_SAMPLES, AUX_SAMPLES, SUPPLY_SAMPLES, TEMP_SAMPLES, ADC_SAMPLES, DIGIN_SAMPLES, DIGOUT_SAMPLES]

TIME_DTYPE_NEW = 'i4'
TIME_DTYPE_OLD = 'u4'
AMP_DTYPE = 'u2'
AUX_DTYPE = 'u2'
SUPPLY_DTYPE = 'u2'
TEMP_DTYPE = 'u2'
ADC_DTYPE = 'u2'
DIGIN_DTYPE = 'u2'
DIGOUT_DTYPE = 'u2'
ALL_DTYPES = [TIME_DTYPE_NEW, AMP_DTYPE, AUX_DTYPE, SUPPLY_DTYPE, TEMP_DTYPE, ADC_DTYPE, DIGIN_DTYPE, DIGOUT_DTYPE]

def preallocate_memory(header, num_datablocks):
    """Preallocates space for a chunk of data.

    Args:
        header (dict): metadata
        num_datablocks (int): size of chunk in datablocks

    Returns:
        dict of numpy arrays: array sizes and types depend on Intan specs
    """
    data = {}
    if ((header['version']['major'], header['version']['minor']) >= (1, 2)):
        time_dt = np.int
    else:
        time_dt = np.uint
    data['t_amplifier'] = np.zeros(AMP_SAMPLES * num_datablocks, dtype=time_dt)
    data['amplifier_data'] = np.zeros([header['num_amplifier_channels'],
                                       AMP_SAMPLES * num_datablocks],
                                      dtype=np.uint16)
    data['aux_input_data'] = np.zeros([header['num_aux_input_channels'],
                                       AUX_SAMPLES * num_datablocks],
                                      dtype=np.uint16)
    data['supply_voltage_data'] = np.zeros([header['num_supply_voltage_channels'],
                                            SUPPLY_SAMPLES * num_datablocks],
                                           dtype=np.uint16)
    data['temp_sensor_data'] = np.zeros([header['num_temp_sensor_channels'],
                                         TEMP_SAMPLES * num_datablocks],
                                        dtype=np.uint16)
    data['board_adc_data'] = np.zeros([header['num_board_adc_channels'],
                                       ADC_SAMPLES * num_datablocks],
                                      dtype=np.uint16)
    data['board_dig_in_data'] = np.zeros([header['num_board_dig_in_channels'],
                                          DIGIN_SAMPLES * num_datablocks],
                                         dtype=np.uint)
    data['board_dig_in_raw'] = np.zeros(DIGIN_SAMPLES * num_datablocks,
                                        dtype=np.uint)
    data['board_dig_out_data'] = np.zeros([header['num_board_dig_out_channels'],
                                           DIGOUT_SAMPLES * num_datablocks],
                                          dtype=np.uint)
    data['board_dig_out_raw'] = np.zeros(DIGOUT_SAMPLES * num_datablocks,
                                         dtype=np.uint)
    return data

def read_data_blocks(data, header, fid, datablocks_per_chunk=1):
    """Reads a number of 60-sample data blocks from fid into data.

    Args:
        data (dict of numpy arrays): having the same format as the return value
            of preallocate_memory() above
        header (dict): metadata
        fid (file object): file to read from
        datablocks_per_chunk (int): how many datablocks to read in
    """
    # In version 1.2, Intan moved from saving timestamps as unsigned
    # integers to signed integers to accommodate negative (adjusted)
    # timestamps for pretrigger data.
    if ((header['version']['major'], header['version']['minor']) >= (1, 2)):
        ALL_DTYPES[0] = TIME_DTYPE_NEW
    else:
        ALL_DTYPES[0] = TIME_DTYPE_OLD
    
    time_chan = 1
    amp_chan = header['num_amplifier_channels']
    aux_chan = header['num_aux_input_channels']
    supply_chan = header['num_supply_voltage_channels']
    temp_chan = header['num_temp_sensor_channels']
    adc_chan = header['num_board_adc_channels']
    digin_chan = header['num_board_dig_in_channels']
    digout_chan = header['num_board_dig_out_channels']
    all_chans = [time_chan, amp_chan, aux_chan, supply_chan, temp_chan, adc_chan, digin_chan, digout_chan]
    
    # create a structured dtype for one datablock
    db_dtype = [(name, (dt, (chans * samples))) for name,dt,chans,samples in zip(NAMES, ALL_DTYPES, all_chans, ALL_SAMPLES)]

    chunk = np.fromfile(fid, dtype=np.dtype(db_dtype), count=datablocks_per_chunk)
    
    for idx,db in enumerate(chunk):
        data['t_amplifier'][(idx * TIME_SAMPLES):((idx + 1) * TIME_SAMPLES)] = db['time']
        if amp_chan:
            data['amplifier_data'][range(amp_chan), (idx * AMP_SAMPLES):((idx + 1) * AMP_SAMPLES)] = db['amp'].reshape(amp_chan, AMP_SAMPLES)
        if aux_chan:
            data['aux_input_data'][range(aux_chan), (idx * AUX_SAMPLES):((idx + 1) * AUX_SAMPLES)] = db['aux'].reshape(aux_chan, AUX_SAMPLES)
        if supply_chan:
            data['supply_voltage_data'][range(supply_chan), (idx * SUPPLY_SAMPLES):((idx + 1) * SUPPLY_SAMPLES)] = db['supply'].reshape(supply_chan, SUPPLY_SAMPLES)
        if temp_chan:
            data['temp_sensor_data'][range(temp_chan), (idx * TEMP_SAMPLES):((idx + 1) * TEMP_SAMPLES)] = db['temp'].reshape(temp_chan, TEMP_SAMPLES)
        if adc_chan:
            data['board_adc_data'][range(adc_chan), (idx * ADC_SAMPLES):((idx + 1) * ADC_SAMPLES)] = db['adc'].reshape(adc_chan, ADC_SAMPLES)
        if digin_chan:
            data['board_dig_in_raw'][(idx * DIGIN_SAMPLES):((idx + 1) * DIGIN_SAMPLES)] = db['digin'].reshape(digin_chan, DIGIN_SAMPLES)
        if digout_chan:
            data['board_dig_out_raw'][(idx * DIGOUT_SAMPLES):((idx + 1) * DIGOUT_SAMPLES)] = db['digout'].reshape(digout_chan, DIGOUT_SAMPLES)

