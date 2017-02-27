#!/usr/bin/python

# Converts open-ephys .kwd files to raw binary, a format ready
# for spike sorting with the Phy spike sorting program

from __future__ import absolute_import, division, print_function, unicode_literals
import os.path
import re
from glob import glob
import yaml
import numpy as np
from bark.io.openephys.kwik import load, load_all
from bark import write_metadata, create_entry
import arrow
from dateutil import tz

# number of data points to write at a time, prevents excess memory usage
BUFFERSIZE = 131072

def filename_to_timestamp(fname, timezone):
    return arrow.get(fname, 'YYYY-MM-DD_HH-mm-ss').replace(tzinfo=tz.gettz(timezeone)).datetime

def input_string_to_timestamp(string, timezone):
    return arrow.get(string).replace(tzinfo=tz.gettz(timezone)).datetime

def write_binary(filename, data):
    if not data.dtype == np.int16:
        raise TypeError("data should be of type int16")
    with open(filename, "ab") as f:
        for i in range(int(data.shape[0] / BUFFERSIZE) + 1):
            index = i * BUFFERSIZE
            buffer = data[index:index + BUFFERSIZE, :]
            f.write(buffer.tobytes())


def eofolder2entry(oefolder, entry_name, timestamp=None, timezone='America/Chicago', parents=False, **attrs):
    if not timestamp:
        timestamp = filename_to_timestamp(oefolder, timezone)
    else:
        timestamp = input_string_to_timestamp(timestamp, timezone)
    create_entry(entry_name, timestamp, parents, **attrs)
    kwds = glob(os.path.join(oefolder, "*.kwd"))
    dats = [os.path.join(entry_name, 
        os.path.splitext(os.path.split(kwd)[-1])[0] + '.dat')
        for kwd in kwds]
    for kwd, dat in zip(kwds, dats):
        write_from_kwd(kwd, dat)


def write_from_kwd(kwd, dat):
    all_data = load_all(kwd)
    n_channels = all_data[0]['data'].shape[1]
    for group_i, data in enumerate(all_data):
        write_binary(dat, data["data"])
        assert data["data"].shape[1] == n_channels
    sampling_rate = data["info"]["sample_rate"]
    columns = {i: {'units': 'uV', 
                   'unit_scale': float(data['app_attrs']['channel_bit_volts'][i])} 
                   for i in range(n_channels)}
    write_metadata(dat, sampling_rate=sampling_rate, 
            dtype=data['data'].dtype.str, columns=columns)


def kwd_to_entry():
    import argparse
    p = argparse.ArgumentParser(
        description="""Converts Open-Ephys .kwd files to a bark entry""")
    p.add_argument("kwdfolder", help="input folder containing .kwd file(s)")
    p.add_argument("-o", "--out",
                   help="name and path of output bark entry")
    p.add_argument("-t", "--timestamp",
            help="""format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS.S, if left unspecified
            the timestamp will be inferred from the foldername of the kwd file.""")
    p.add_argument("-a", "--attributes", action='append',
            type=lambda kv: kv.split("="), dest='keyvalues',
            help="extra metadata in the form of KEY=VALUE")
    p.add_argument('--timezone', help="timezone of timestamp, default: America/Chicago",
            default='America/Chicago')
    args = p.parse_args()
    attrs = dict(args.keyvalues) if args.keyvalues else {}
    eofolder2entry(args.kwdfolder, args.out, args.timestamp, args.timezone, **attrs)
