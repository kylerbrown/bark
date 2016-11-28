from scipy.io import loadmat
import pandas as pd
import argparse
import bark


def load_clusters(matfile, channel=None):
    """ From a wave_clus *.m file, return a pandas dataframe."""

    cluster_classes = loadmat(matfile)["cluster_class"]
    times = pd.DataFrame({"label": cluster_classes[:, 0].astype(int),
                          "start": cluster_classes[:, 1] / 1000.})
    if channel is not None:
        times["channel"] = channel
    return times


def _waveclus2csv():
    "shell script"
    p = argparse.ArgumentParser(description="""
    Converts a wave_clus times_*.m file to a bark csv.
    """)
    p.add_argument("name", help="name of wave_clus times*.m file")
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
    if "units" not in attrs:
        attrs["units"] = "s" 
    attrs["filetype"] = "csv"
    attrs["creator"] = "wave_clus"

    data = load_clusters(args.name)
    bark.write_events(args.out,
                      data,
                      **attrs)
