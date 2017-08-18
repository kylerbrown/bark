import argparse
import glob
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

def bark_for_each(cmd, entry_list, verbose, base_dir=None):
    if base_dir is None:
        base_dir = os.getcwd()
    for ename in entry_list:
        os.chdir(base_dir)
        os.chdir(ename)
        if verbose:
            print('Working on ' + ename)
        expanded_cmd = glob_command(cmd)
        subprocess.run(expanded_cmd)

def glob_command(cmd):
    expanded_cmd = []
    for token in cmd.split():
        if not(token[0] == '"' and token[-1] == '"'):
            g = glob.glob(token)
            if g:
                expanded_cmd.extend(g)
            else:
                expanded_cmd.append(token)
        else:
            expanded_cmd.append(token)
    return expanded_cmd

def _main():
    parsed_args = _parse_args(sys.argv[1:])
    bark_for_each(parsed_args.cmd, parsed_args.entries, parsed_args.verbose)

if __name__ == '__main__':
    _main()

