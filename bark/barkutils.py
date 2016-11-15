from shutil import move
import os.path
from glob import glob
import bark
import argparse

class StoreNameValuePair(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        n, v = values.split('=')
        setattr(namespace, n, v)

def mk_root():
    p = argparse.ArgumentParser(description="create a bark root directory")
    p.add_argument("name", help="name of bark root directory")
    p.add_argument("-a", "--attributes", action='append',
            type=lambda kv: kv.split("="), dest='keyvalues',
            help="extra metadata in the form of KEY=VALUE")
    args = p.parse_args()
    if args.keyvalues:
        bark.create_root(args.name, **dict(args.keyvalues))
    else:
        bark.create_root(args.name)


def mk_entry():
    p = argparse.ArgumentParser(description="create a bark entry")
    p.add_argument("name", help="name of bark entry")
    p.add_argument("-a", "--attributes", action='append',
            type=lambda kv: kv.split("="), dest='keyvalues',
            help="extra metadata in the form of KEY=VALUE")
    p.add_argument("-t", "--timestamp", help="seconds since Jan 1 1970",
            default=0, type=float)
    args = p.parse_args()
    bark.create_entry(args.name, args.timestamp, **dict(args.keyvalues))


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
    p.add_argument("-t", "--timestamp", help="seconds since Jan 1 1970",
            default=0, type=float)
    args = p.parse_args()
    matching_files = glob(args.name + "*")
    print(matching_files)
    bark.create_entry(args.name, args.timestamp, **dict(args.keyvalues))
    for fname in matching_files:
        move(fname, os.path.join(args.name, fname[len(args.name):]))


