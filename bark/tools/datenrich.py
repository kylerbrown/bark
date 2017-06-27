from __future__ import division, print_function, absolute_import, \
        unicode_literals
import os.path
import numpy as np
import bark


def get_segments(labels, window=5):
    """
    deterimines chunks to extract based on label_file,
    which is a csv file with "start" and "stop" collumns
    with units in seconds

    returns:
    b: a union of chunks
    labels: a pandas array with updated label times, assuming
            chunks are concatenated.
    """
    wlabels = labels.copy()
    wlabels.start -= window
    wlabels.stop += window
    wlabels.sort(['start', 'stop'])
    wlabels.reset_index(drop=True, inplace=True)
    # union segments
    b = []
    for x in wlabels.itertuples():
        if len(b) == 0:
            b.append([x.start, x.stop]
                     )  # initialize to window around first segment
        elif x.start > b[-1][
                1]:  # no overlap between this segment and last
                     #  (b[-1][1] is last stop)
                     # add a new segment
            b.append([x.start, x.stop])
        elif x.stop > b[-1][1]:  # there an is overlap, so extend the segment.
            b[-1][1] = x.stop
        else:
            # syllable already fits inside segment
            assert b[-1][0] <= x.start <= b[-1][1]
            assert b[-1][0] <= x.stop <= b[-1][1]
    # update label times to new chunks
    nlabels = labels.copy()
    prevchunks = 0  # total length of all previous chunks
    for start, stop in enumerate(b):
        mask = (labels.start >= start) & (labels.stop <= stop
                                          )  # find labels in enriched chunk
        offset = -start + prevchunks  # set offset to the start of the chunk
        # plus the accumulated offset from all the previous chunks
        nlabels.loc[mask, ["start", "stop"]] += offset
        prevchunks += stop - start
    return np.array(b), nlabels


def datenrich(dat, out, label_file, window):
    dataset = bark.read_sampled(dat)
    data, params = dataset.data, dataset.attrs
    rate = params["sampling_rate"]
    total_samples = data.shape[0]
    # cut out labelled segments
    label_dset = bark.read_events(label_file)
    for x in label_dset.data.itertuples():
        assert x.start > 0
        assert x.start * rate < total_samples
        assert x.stop > 0
        assert x.stop * rate < total_samples
    segs, newlabels = get_segments(label_dset.data, window)
    # convert to samples
    segs = np.array(segs * rate, dtype=int)
    # write to new file
    with open(out, "wb") as outfp:
        for start, stop in segs:
            assert stop > 0
            assert start < total_samples
            if start < 0:
                print(
                    'warning, cannot place a full window at beginning of data')
                start = 0
            elif stop >= total_samples:
                print('warning, cannot place a full window at end of data')
                stop = total_samples - 1
            outfp.write(data[start:stop, :].tobytes())
    bark.write_metadata(out, **params)
    bark.write_events(
        os.path.splitext(out)[0] + ".csv", newlabels, **label_dset.attrs)


def main():
    import argparse
    p = argparse.ArgumentParser(prog="datenrich")
    p.add_argument("dat", help="dat file")
    p.add_argument("label",
                   help="label file, a csv in seconds with 'label', 'start', \
                   'stop' as a header")
    p.add_argument("out", help="name of output dat file")
    p.add_argument("-w",
                   "--window",
                   type=float,
                   help="addition window in seconds around the labels to \
                   include",
                   default=3.0)
    opt = p.parse_args()
    datenrich(opt.dat, opt.out, opt.label, opt.window)


if __name__ == "__main__":
    main()
