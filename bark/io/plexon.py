from __future__ import unicode_literals, print_function, division, absolute_import

import bark


def barkify_csv(csvname):
    '''
    Reads in a plexon csv, and changes the columns names
    to their bark standards.

    Returns a pandas dataframe.
    '''
    import pandas as pd
    csv = pd.read_csv(csvname)
    if 'Timestamp' not in csv.columns:
        raise LookupError('''
        Export the waveform csv from Plexon OFS with a header, please.
        ''')
    csv.rename(columns={'Timestamp': 'start',
                        'Channel': 'channel',
                        'Unit': 'name'},
               inplace=True)
    return csv


def _plexon_csv_to_bark_csv():
    "shell script"
    import argparse
    p = argparse.ArgumentParser(description="""
    Converts a plexon csv to a bark csv.
    """)
    p.add_argument("name",
                   help="""Name of plexon csv file.
            Don't foget to export a header column.
            """)
    p.add_argument("-o", "--out", help="name of output csv file",
            required=True)
    p.add_argument("-a",
                   "--attributes",
                   action='append',
                   type=lambda kv: kv.split("="),
                   dest='keyvalues',
                   help="extra metadata in the form of KEY=VALUE")
    args = p.parse_args()
    if args.keyvalues:
        attrs = dict(args.keyvalues)
    else:
        attrs = {}
    if "units" not in attrs:
        attrs["units"] = "s"
    attrs["filetype"] = "csv"
    attrs["creator"] = "plexon"
    data = barkify_csv(args.name)
    bark.write_events(args.out, data, **attrs)
