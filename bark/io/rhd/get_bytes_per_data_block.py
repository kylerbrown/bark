#! /bin/env python
#
# Michael Gibson 23 April 2015
# 2018 changes by Adrian Foy merged in 2021 by Graham Fetterman

from . import constants as const

def get_bytes_per_data_block(header):
    """Calculates the number of bytes in each datablock."""

    num_samples = header['num_samples_per_data_block']
    bytes_per_block = 0

    # Timebase (with version-specific data type)
    if (header['version']['major'], header['version']['minor']) >= (1, 2):
        time_dtype = const.TIMESTAMP_DTYPE_GE_V1_2
    else:
        time_dtype = const.TIMESTAMP_DTYPE_LE_V1_1
    bytes_per_block += num_samples * time_dtype.itemsize

    # Each data block contains a version-specific number of amplifier samples.
    bytes_per_block += (num_samples *
                        const.AMPLIFIER_DTYPE.itemsize *
                        header['num_amplifier_channels'])

    # Auxiliary inputs are sampled 4x slower than amplifiers.
    bytes_per_block += ((num_samples / 4) *
                        const.AUXILIARY_DTYPE.itemsize *
                        header['num_aux_input_channels'])

    # Supply voltage is sampled only once per data block (i.e., 60x or 128x
    # slower than amplifiers).
    bytes_per_block += (1 *
                        const.SUPPLY_DTYPE.itemsize
                        * header['num_supply_voltage_channels'])

    # Board analog inputs are sampled at same rate as amplifiers.
    bytes_per_block += (num_samples *
                        const.ADC_DTYPE.itemsize *
                        header['num_board_adc_channels'])

    # Board digital inputs are sampled at same rate as amplifiers, and packed
    # together.
    if header['num_board_dig_in_channels'] > 0:
        bytes_per_block += num_samples * const.DIG_IN_DTYPE.itemsize

    # Board digital outputs are sampled at same rate as amplifiers, and packed
    # together.
    if header['num_board_dig_out_channels'] > 0:
        bytes_per_block += num_samples * const.DIG_OUT_DTYPE.itemsize

    # Temperature is sampled only once per data block (i.e., 60x or 128x slower
    # than amplifiers).
    if header['num_temp_sensor_channels'] > 0:
        bytes_per_block += (1 *
                            const.TEMP_DTYPE.itemsize *
                            header['num_temp_sensor_channels'])

    return bytes_per_block
