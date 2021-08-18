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
    ct = 1
    total = len(entry_list)
    for ename in entry_list:
        os.chdir(base_dir)
        os.chdir(ename)
        if verbose:
            print('Working on {} ({} of {})'.format(ename, ct, total))
        expanded_cmd = glob_command(cmd)
        subprocess.run(expanded_cmd)
        ct += 1

def glob_command(cmd):
    expanded_cmd = []
    quote_split = cmd.split('"')
    if len(quote_split) % 2 == 0:
        raise ValueError('cannot parse command: un-paired quotation marks')
    for idx,chunk in enumerate(quote_split):
        if idx % 2 == 0: # if the chunk was not enclosed in quotes
            for token in chunk.split():
                token = os.path.expanduser(token)
                g = glob.glob(token)
                if g:
                    expanded_cmd.extend(g)
                else:
                    expanded_cmd.append(token)
        else: # if the chunk was enclosed in quotes
            expanded_cmd.append('"' + chunk + '"')
    return expanded_cmd

def _main():
    parsed_args = _parse_args(sys.argv[1:])
    bark_for_each(parsed_args.cmd, parsed_args.entries, parsed_args.verbose)

if __name__ == '__main__':
    _main()

