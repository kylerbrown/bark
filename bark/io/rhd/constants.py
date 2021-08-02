import numpy as np

LAST_TESTED_MAJOR_VERSION = 3

# Datatypes for different channel types

TIMESTAMP_DTYPE_LE_V1_1 = np.dtype('uint32')
TIMESTAMP_DTYPE_GE_V1_2 = np.dtype('int32')

AMPLIFIER_DTYPE = np.dtype('uint16')

AUXILIARY_DTYPE = np.dtype('uint16')

SUPPLY_DTYPE = np.dtype('uint16')

TEMP_DTYPE = np.dtype('uint16')

ADC_DTYPE = np.dtype('uint16')

DIG_IN_DTYPE = np.dtype('uint16')
DIG_OUT_DTYPE = np.dtype('uint16')

# Voltage scaling for different channel types

AMPLIFIER_BIT_MICROVOLTS = 0.195

AUX_BIT_VOLTS = 37.4e-6

SUPPLY_BIT_VOLTS = 74.8e-6

ADC_BIT_VOLTS_MODE_0 = 50.354e-6
ADC_BIT_VOLTS_MODE_1 = 152.59e-6
ADC_BIT_VOLTS_MODE_13 = 312.5e-6

TEMP_BIT_CELCIUS = 0.01
