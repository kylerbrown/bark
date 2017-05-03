import argparse
import subprocess
import os
import sys

def _parse_args(raw_args):
    desc = 'Run a command on a list of Bark entries.'
    epi = 'Paths not relative to entries must be absolute.'
    parser = argparse.ArgumentParser(description=desc, epilog=epi)
    parser.add_argument('-v', '--verbose',
                        help='increase verbosity',
                        action='store_true')
    parser.add_argument('cmd', help='(quoted) command to run')
    parser.add_argument('entries', nargs='+', help='entries')
    return parser.parse_args(raw_args)

def bark_for_each(cmd, entry_list, verbose):
    for ename in entry_list:
        os.chdir(ename)
        if verbose:
            print('Working on ' + ename)
        subprocess.run(cmd.split())

def _main():
    parsed_args = _parse_args(sys.argv[1:])
    bark_for_each(parsed_args.cmd, parsed_args.entries, parsed_args.verbose)

if __name__ == '__main__':
    _main()

