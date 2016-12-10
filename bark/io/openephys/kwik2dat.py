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
from datetime import datetime

# number of data points to write at a time, prevents excess memory usage
BUFFERSIZE = 131072

def parse_timestamp_from_filename(fname):
    datetime_regex = r'[0-9]{4}-[0-9]{2}-[0-9]{2}_[0-9]{2}-[0-9]{2}-[0-9]{2}'
    tstring = re.findall(datetime_regex, fname)[0]
    return datetime.strptime(tstring, "%Y-%m-%d_%H-%M-%S")

def write_binary(filename, data):
    if not data.dtype == np.int16:
        raise TypeError("data should be of type int16")
    with open(filename, "ab") as f:
        for i in range(int(data.shape[0] / BUFFERSIZE) + 1):
            index = i * BUFFERSIZE
            buffer = data[index:index + BUFFERSIZE, :]
            f.write(buffer.tobytes())


def eofolder2entry(oefolder, entry_name, timestamp=None, parents=False, **attrs):
    if not timestamp:
        try:
            timestamp = parse_timestamp_from_filename(oefolder)
        except IndexError:
            timestamp = [0, 0]
    create_entry(entry_name, timestamp, parents, **attrs)
    kwds = glob(os.path.join(oefolder, "*.kwd"))
    dats = [os.path.join(entry_name, 
        os.path.splitext(os.path.split(kwd)[-1])[0] + '.dat')
        for kwd in kwds]
    for kwd, dat in zip(kwds, dats):
        write_from_kwd(kwd, dat)


def write_from_kwd(kwd, dat):
    all_data = load_all(kwd)
    sampling_rate = all_data[0]["info"]["sample_rate"]
    n_channels = all_data[0]['data'].shape[1]
    for group_i, data in enumerate(all_data):
        write_binary(dat, data["data"])
    # reopen to deterimine number of samples
    temp  = np.memmap(dat, dtype="int16", mode="r").reshape(-1, n_channels)
    n_samples = temp.shape[0]
    write_metadata(dat + ".meta", sampling_rate=sampling_rate, 
            n_samples=n_samples, n_channels=n_channels, dtype="int16")


def kwd_to_entry():
    import argparse
    p = argparse.ArgumentParser(
        description="""Converts Open-Ephys .kwd files to a bark entry""")
    p.add_argument("kwdfolder", help="input folder containing .kwd file(s)")
    p.add_argument("-o", "--out",
                   help="name and path of output bark entry")
    p.add_argument("-t", "--timestamp",
            help="""format: YYYY-MM-DD or YYYY-MM-DD_HH-MM-SS.S, if left unspecified
            the timestamp will be inferred from the foldername of the kwd file.""")
    p.add_argument("-a", "--attributes", action='append',
            type=lambda kv: kv.split("="), dest='keyvalues',
            help="extra metadata in the form of KEY=VALUE")
    args = p.parse_args()
    if args.keyvalues:
        eofolder2entry(args.kwdfolder, args.out, args.timestamp, **dict(args.keyvalues))
    else:
        eofolder2entry(args.kwdfolder, args.out, args.timestamp)
