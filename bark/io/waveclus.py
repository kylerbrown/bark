from scipy.io import loadmat
import pandas as pd
import argparse
import bark


def load_clusters(matfile, channel=None):
    """ From a wave_clus *.m file, return a pandas dataframe."""

    cluster_classes = loadmat(matfile)["cluster_class"]
    times = pd.DataFrame({"name": cluster_classes[:, 0].astype(int),
                          "start": cluster_classes[:, 1] / 1000.})
    if channel is not None:
        times["channel"] = channel
    return times


def _waveclus2csv():
    "shell script"
    p = argparse.ArgumentParser(description="""
    Converts a wave_clus times_*.m file to a bark csv.
    """)
    p.add_argument("name",
                   help="""Name of wave_clus times*.m file(s),
            if mutltiple files, assume they are ordered by channel.
            """,
                   nargs="+")
    p.add_argument("-o", "--out", help="name of output csv file")
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
    attrs["filetype"] = "csv"
    attrs["creator"] = "wave_clus"
    attrs["columns"] = {"name": {"units": None}, "start": {"units": "s"}}
    data = pd.concat(load_clusters(x, i) for i, x in enumerate(args.name))
    bark.write_events(args.out, data, **attrs)
