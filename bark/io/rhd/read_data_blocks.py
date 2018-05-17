#! /bin/env python
#
# Michael Gibson 23 April 2015
# Graham Fetterman April 2018

import sys, struct
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

def read_data_blocks(data, header, indices, fid, datablocks_per_chunk=1):
    """Reads a number of 60-sample data blocks from fid into data, at the location indicated by indices."""

    # In version 1.2, Intan moved from saving timestamps as unsigned
    # integers to signed integers to accommodate negative (adjusted)
    # timestamps for pretrigger data.
    if (header['version']['major'] == 1 and header['version']['minor'] >= 2) or (header['version']['major'] > 1):
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
        data['t_amplifier'][(indices['amplifier'] + idx * TIME_SAMPLES):(indices['amplifier'] + (idx + 1) * TIME_SAMPLES)] = db['time']
        if amp_chan:
            data['amplifier_data'][range(amp_chan), (indices['amplifier'] + idx * AMP_SAMPLES):(indices['amplifier'] + (idx + 1) * AMP_SAMPLES)] = db['amp'].reshape(amp_chan, AMP_SAMPLES)
        if aux_chan:
            data['aux_input_data'][range(aux_chan), (indices['aux_input'] + idx * AUX_SAMPLES):(indices['aux_input'] + (idx + 1) * AUX_SAMPLES)] = db['aux'].reshape(aux_chan, AUX_SAMPLES)
        if supply_chan:
            data['supply_voltage_data'][range(supply_chan), (indices['supply_voltage'] + idx * SUPPLY_SAMPLES):(indices['supply_voltage'] + (idx + 1) * SUPPLY_SAMPLES)] = db['supply'].reshape(supply_chan, SUPPLY_SAMPLES)
        if temp_chan:
            data['temp_sensor_data'][range(temp_chan), (indices['supply_voltage'] + idx * TEMP_SAMPLES):(indices['supply_voltage'] + (idx + 1) * TEMP_SAMPLES)] = db['temp'].reshape(temp_chan, TEMP_SAMPLES)
        if adc_chan:
            data['board_adc_data'][range(adc_chan), (indices['board_adc'] + idx * ADC_SAMPLES):(indices['board_adc'] + (idx + 1) * ADC_SAMPLES)] = db['adc'].reshape(adc_chan, ADC_SAMPLES)
        if digin_chan:
            data['board_dig_in_raw'][(indices['board_dig_in'] + idx * DIGIN_SAMPLES):(indices['board_dig_in'] + (idx + 1) * DIGIN_SAMPLES)] = db['digin'].reshape(digin_chan, DIGIN_SAMPLES)
        if digout_chan:
            data['board_dig_out_raw'][(indices['board_dig_out'] + idx * DIGOUT_SAMPLES):(indices['board_dig_out'] + (idx + 1) * DIGOUT_SAMPLES)] = db['digout'].reshape(digout_chan, DIGOUT_SAMPLES)
