#! /bin/env python
#
# Michael Gibson 23 April 2015
# Graham Fetterman April 2018

import sys, struct
import numpy as np

AMP_SAMPLES = 60
AUX_SAMPLES = 15
SUPPLY_SAMPLES = 1
TEMP_SAMPLES = 1
ADC_SAMPLES = 60

def read_one_data_block(data, header, indices, fid):
    """Reads one 60-sample data block from fid into data, at the location indicated by indices."""

    # In version 1.2, we moved from saving timestamps as unsigned
    # integers to signed integers to accommodate negative (adjusted)
    # timestamps for pretrigger data['
    if (header['version']['major'] == 1 and header['version']['minor'] >= 2) or (header['version']['major'] > 1):
        data['t_amplifier'][indices['amplifier']:(indices['amplifier']+60)] = np.array(struct.unpack('<' + 'i' *60, fid.read(240)))
    else:
        data['t_amplifier'][indices['amplifier']:(indices['amplifier']+60)] = np.array(struct.unpack('<' + 'I' *60, fid.read(240)))
    
    num_amp_chan = header['num_amplifier_channels']
    num_aux_chan = header['num_aux_input_channels']
    num_supply_chan = header['num_supply_voltage_channels']
    num_temp_chan = header['num_temp_sensor_channels']
    num_adc_chan = header['num_board_adc_channels']
    num_samples = (num_amp_chan * AMP_SAMPLES +
                   num_aux_chan * AUX_SAMPLES +
                   num_supply_chan * SUPPLY_SAMPLES +
                   num_temp_chan * TEMP_SAMPLES +
                   num_adc_chan * ADC_SAMPLES)

    tmp = np.fromfile(fid, dtype='uint16', count=num_samples)
    start = 0
    if num_amp_chan:
        data['amplifier_data'][range(num_amp_chan), indices['amplifier']:(indices['amplifier'] + AMP_SAMPLES)] = tmp[start:(num_amp_chan * AMP_SAMPLES)].reshape(num_amp_chan, AMP_SAMPLES)
        start += num_amp_chan * AMP_SAMPLES
    if num_aux_chan:
        data['aux_input_data'][range(num_aux_chan), indices['aux_input']:(indices['aux_input'] + AUX_SAMPLES)] = tmp[start:(start + num_aux_chan * AUX_SAMPLES)].reshape(num_aux_chan, AUX_SAMPLES)
        start += num_aux_chan * AUX_SAMPLES
    if num_supply_chan:
        data['supply_voltage_data'][range(num_supply_chan), indices['supply_voltage']:(indices['supply_voltage'] + SUPPLY_SAMPLES)] = tmp[start:(start + num_supply_chan * SUPPLY_SAMPLES)].reshape(num_supply_chan, SUPPLY_SAMPLES)
        start += num_supply_chan * SUPPLY_SAMPLES
    if num_temp_chan:
        data['temp_sensor_data'][range(num_temp_chan), indices['supply_voltage']:(indices['supply_voltage'] + TEMP_SAMPLES)] = tmp[start:(start + num_temp_chan * TEMP_SAMPLES)].reshape(num_temp_chan, TEMP_SAMPLES)
        start += num_temp_chan * TEMP_SAMPLES
    if num_adc_chan:
        data['board_adc_data'][range(num_adc_chan), indices['board_adc']:(indices['board_adc'] + ADC_SAMPLES)] = tmp[start:(start + num_adc_chan * ADC_SAMPLES)].reshape(num_adc_chan, ADC_SAMPLES)

    if header['num_board_dig_in_channels'] > 0:
        data['board_dig_in_raw'][indices['board_dig_in']:(indices['board_dig_in']+60)] = np.array(struct.unpack('<' + 'H' *60, fid.read(120)))

    if header['num_board_dig_out_channels'] > 0:
        data['board_dig_out_raw'][indices['board_dig_out']:(indices['board_dig_out']+60)] = np.array(struct.unpack('<' + 'H' *60, fid.read(120)))

