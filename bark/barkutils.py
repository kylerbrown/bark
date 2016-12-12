from os import listdir, remove
from shutil import move
import os.path
from glob import glob
import bark
import argparse
from bark import parse_timestamp_string
from bark import stream


def mk_root():
    p = argparse.ArgumentParser(description="create a bark root directory")
    p.add_argument("name", help="name of bark root directory")
    p.add_argument("-a", "--attributes", action='append',
            type=lambda kv: kv.split("="), dest='keyvalues',
            help="extra metadata in the form of KEY=VALUE")
    p.add_argument("-p", "--parents", help="no error if already exists, new meta-data written",
            action="store_true")
    args = p.parse_args()
    if args.keyvalues:
        attrs = dict(args.keyvalues)
    else:
        attrs = {}
    bark.create_root(args.name, args.parents, **attrs)


def mk_entry():
    p = argparse.ArgumentParser(description="create a bark entry")
    p.add_argument("name", help="name of bark entry")
    p.add_argument("-a", "--attributes", action='append',
            type=lambda kv: kv.split("="), dest='keyvalues',
            help="extra metadata in the form of KEY=VALUE")
    p.add_argument("-t", "--timestamp", help="format: YYYY-MM-DD or YYYY-MM-DD_HH-MM-SS.S")
    p.add_argument("-p", "--parents", help="no error if already exists, new meta-data written",
            action="store_true")
    args = p.parse_args()
    timestamp = parse_timestamp_string(args.timestamp)
    if args.keyvalues:
        attrs = dict(args.keyvalues)
    else:
        attrs = {}
    bark.create_entry(args.name, timestamp, args.parents, **attrsr)


def entry_from_glob():
    """
    given a string prefix, find all the matching files and stuff them in an entry,
    trimming the redundant prefix off the file name.
    """
    p = argparse.ArgumentParser(description="create a bark entry from matching files")
    p.add_argument("name", help="name of bark entry")
    p.add_argument("-a", "--attributes", action='append',
            type=lambda kv: kv.split("="), dest='keyvalues',
            help="extra metadata in the form of KEY=VALUE")
    p.add_argument("-t", "--timestamp", help="format: YYYY-MM-DD or YYYY-MM-DD_HH-MM-SS.S")
    args = p.parse_args()
    matching_files = glob(args.name + "*")
    timestamp = parse_timestamp_string(args.timestamp)
    print(matching_files)
    if args.keyvalues:
        attrs = dict(args.keyvalues)
    else:
        attrs = {}
    bark.create_entry(args.name, timestamp, **attrs)
    for fname in matching_files:
        move(fname, os.path.join(args.name, fname[len(args.name):]))


def _clean_metafiles(path, recursive):
    metafiles = glob(os.path.join(path, "*.meta"))
    for mfile in metafiles:
        if not os.path.isfile(mfile[:-5]):
            os.remove(mfile)
    if recursive:
        dirs = [x for x in os.listdir(path)
                if os.path.isdir(os.path.join(path, x))]
        for d in dirs:
            _clean_metafiles(os.path.join(path, d), True)




def clean_metafiles():
    """
    remove x.meta files with no associated file (x)
    """
    p = argparse.ArgumentParser(description="remove x.meta files with no associated file (x)")
    p.add_argument("path", help="name of bark entry", default=".")
    p.add_argument("-r", "--recursive",
            help="search recursively",
            action="store_true")
    args = p.parse_args()
    _clean_metafiles(args.path, args.recursive)



def rb_concat():
    p = argparse.ArgumentParser(description=
    """Concatenate raw binary files by adding new samples. 
    Do not confuse with merge, which combines channels""")
    p.add_argument("input", help="input raw binary files",
            nargs="+")
    p.add_argument("-a", "--attributes", action='append',
            type=lambda kv: kv.split("="), dest='keyvalues',
            help="extra metadata in the form of KEY=VALUE")
    p.add_argument("-o", "--out",
            help="name of output file", required=True)
    args = p.parse_args()
    if args.keyvalues:
        attrs = dict(args.keyvalues)
    else:
        attrs = {}
    streams = [stream.read(x) for x in args.input]
    streams[0].chain(*streams[1:]).write(args.out, **attrs)

def rb_decimate():
    ' Downsample raw binary file.'
    p = argparse.ArgumentParser(description="Downsample raw binary file")
    p.add_argument("input", help="input bark file")
    p.add_argument("--factor", required=True,
            type=int,
            help="downsample factor")
    p.add_argument("-a", "--attributes", action='append',
            type=lambda kv: kv.split("="), dest='keyvalues',
            help="extra metadata in the form of KEY=VALUE")
    p.add_argument("-o", "--out",
            help="name of output file", required=True)
    args = p.parse_args()
    if args.keyvalues:
        attrs = dict(args.keyvalues)
    else:
        attrs = {}
    stream.read(args.input).decimate(args.factor).write(args.out, **attrs)


