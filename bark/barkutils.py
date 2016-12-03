from os import listdir, remove
from shutil import move
import os.path
from glob import glob
import bark
import argparse
from bark import parse_timestamp_string


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
        bark.create_root(args.name, args.parents, **dict(args.keyvalues))
    else:
        bark.create_root(args.name, args.parents)


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
        bark.create_entry(args.name, timestamp, args.parents, **dict(args.keyvalues))
    else:
        bark.create_entry(args.name, timestamp, args.parents)


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
        bark.create_entry(args.name, timestamp, **dict(args.keyvalues))
    else:
        bark.create_entry(args.name, timestamp)
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

