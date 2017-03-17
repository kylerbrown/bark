from __future__ import division, print_function, absolute_import, \
        unicode_literals
import shutil
import os.path
import numpy as np
import pandas as pd
import bark


def get_segments(label_file, window=5):
    """
    deterimines chunks to extract based on label_file,
    which is a csv file with "start" and "stop" collumns
    with units in seconds

    returns:
    b: a union of chunks
    labels: a pandas array with updated label times, assuming
            chunks are concatenated.
    """
    labels = pd.read_csv(label_file).sort_values('start').reset_index(
        drop=True)
    wlabels = labels.copy()
    wlabels.start -= window
    wlabels.stop += window
    # union segments
    b = []
    for x in wlabels.itertuples():
        if len(b) == 0:
            b.append([x.start, x.stop])
        elif x.start > b[-1][1]:
            b.append([x.start, x.stop])
        elif x.stop > b[-1][1]:
            b[-1][1] = x.stop
    # update labels times to new chunks
    prevchunks = 0
    for j, (start, stop) in enumerate(b):
        mask = (labels.start >= start) & (labels.stop <= stop)
        offset = -start + prevchunks
        labels.loc[mask, ["start", "stop"]] += offset
        prevchunks += stop - start
    return np.array(b), labels


def datenrich(dat, channels, out, label, window):
    # load and reshape dat file
    dataset = bark.read_sampled(dat)
    data, params = dataset.data, dataset.attrs
    rate = params["sampling_rate"]
    nchannels = len(params["columns"])
    if not channels:
        channels = np.arange(nchannels)  # select all channels
    rootname = os.path.splitext(dat)[0]
    if not out:
        out = rootname + "_enr.dat"
    # cut out labelled segments
    segs, newlabels = get_segments(label, window)
    # convert to samples
    segs = np.array(segs * rate, dtype=int)
    n_samples = sum((b - a for a, b in segs))
    outparams = params.copy()
    outparams["n_samples"] = n_samples
    outparams["n_channels"] = len(channels)
    # write to new file
    with open(out, "wb") as outfp:
        for start, stop in segs:
            outfp.write(data[start:stop, channels].tobytes())
    bark.write_metadata(out, **outparams)
    newlabels.to_csv(
        os.path.splitext(out)[0] + ".csv",
        header=True,
        index=False)
    if os.path.isfile(label + ".meta.yaml"):
        shutil.copyfile(label + ".meta.yaml",
                        os.path.splitext(out)[0] + ".csv.meta.yaml")


def main():
    import argparse
    p = argparse.ArgumentParser(prog="datenrich")
    p.add_argument("dat", help="dat file")
    p.add_argument("label",
                   help="label file, a csv in seconds with 'label', 'start', \
                   'stop' as a header")
    p.add_argument("out", help="name of output dat file")
    p.add_argument("-c",
                   "--channels",
                   help="subset of channels, by index",
                   type=int,
                   nargs="+")
    p.add_argument("-w",
                   "--window",
                   type=float,
                   help="addition window in seconds around the labels to \
                   include",
                   default=3.0)
    opt = p.parse_args()
    datenrich(opt.dat, opt.channels, opt.out, opt.label, opt.window)


if __name__ == "__main__":
    main()
