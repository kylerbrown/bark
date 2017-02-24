from __future__ import unicode_literals, print_function, division, \
absolute_import

from shutil import copyfile
import numpy as np
import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from scipy.signal import butter, lfilter, argrelmax, argrelmin
from bark import read_sampled, write_sampled, BUFFER_SIZE
BUF = BUFFER_SIZE


def make_artifact_plots(data, outname, pos_arts, neg_arts, stds):
    colors = [cm.Dark2(x) for x in np.linspace(0, 1, len(stds))]
    f, (ax1, ax2, ax3) = plt.subplots(3, 1)
    if len(pos_arts) == 0 and len(neg_arts) == 0:
        # nothing to do
        plt.savefig(outname + ".png")
        return
    for c, (poss, negs) in enumerate(zip(pos_arts, neg_arts)):
        extrema = np.array(poss + negs, dtype=int)
        for i in extrema:
            ax1.plot(data[i - 10:i + 10, c] / stds[c],
                     linewidth=0.5, color=colors[c])
            plt.sca(ax2)
            plt.hist(data[extrema, c] / stds[c], bins=20, fill=None, edgecolor=colors[c])
            ax3.vlines(extrema, 0, 1, color=colors[c])
        ax1.set_ylabel("standard deviation")
        ax1.set_title("artifacts")
        ax2.set_title("amplitude distribution")
        ax3.set_title("artifact locations")
    plt.savefig(outname + ".png")


def datartifact(datfile, outfile, std_lim):
    assert datfile != outfile
    copyfile(datfile, outfile)
    copyfile(datfile + ".meta.yaml", outfile + ".meta.yaml")
    dataset = read_sampled(datfile)
    data, params = dataset.data, dataset.attrs
    out_dataset = read_sampled(outfile, mode="r+")
    out, outparams = out_dataset.data, dataset.attrs
    n_channels = len(params["columns"])

    # compute standard deviation
    stds = np.std(data[0:BUF * 50], axis=0)
    print("standard deviations: {}".format(stds))
    # find locations of artifacts
    pos_artifacts = [[] for x in range(n_channels)]
    neg_artifacts = [[] for x in range(n_channels)]
    assert len(stds) == n_channels
    for i in range(0, len(out), BUF):
        for c in range(n_channels):
            x = data[i:i + BUF, c].copy().flatten()
            x[x < stds[c] * std_lim] = 0
            peaks, = argrelmax(x)
            pos_artifacts[c] += [int(pe) + i for pe in peaks]

            x = data[i:i + BUF, c].copy().flatten()
            x[x > -stds[c] * std_lim] = 0
            peaks, = argrelmin(x)
            neg_artifacts[c] = neg_artifacts[c] + [int(pe) + i for pe in peaks]
    # remove artifacts
    print("{}\t negative artifacts".format([len(x) for x in neg_artifacts]))
    print("locations: {}".format([np.array(x) / params[
        "sampling_rate"] for x in neg_artifacts]))
    print("{}\t positive artifacts".format([len(x) for x in pos_artifacts]))
    print("locations: {}".format([np.array(x) / params[
        "sampling_rate"] for x in pos_artifacts]))
    for c in range(n_channels):
        print([data[x, c] / stds[c] for x in pos_artifacts[c]])
        print([data[x, c] / stds[c] for x in neg_artifacts[c]])

    make_artifact_plots(data, outfile, pos_artifacts, neg_artifacts, stds)
    for chan in range(n_channels):
        for samp in pos_artifacts[c]:
            out[samp, chan] = 0
            t = samp + 1
            while out[t, chan] > stds[chan]:
                out[t, chan] = 0
                t += 1
            t = samp - 1
            while out[t, chan] > stds[chan]:
                out[t, chan] = 0
                t -= 1

        for samp in neg_artifacts[c]:
            out[samp, chan] = 0
            t = samp + 1
            while out[t, chan] < -stds[chan]:
                out[t, chan] = 0
                t += 1
            t = samp - 1
            while out[t, chan] < -stds[chan]:
                out[t, chan] = 0
                t -= 1

def main():
    import argparse
    p = argparse.ArgumentParser(description="""
    removes artifacts based on standard deviation
    """)
    p.add_argument("dat", help="dat file")
    p.add_argument("-s",
                   "--std",
                   help="standard deviation cutoff",
                   type=float,
                   required=True)
    p.add_argument("-o", "--out", help="name of output dat file")
    opt = p.parse_args()
    datartifact(opt.dat, opt.out, opt.std)

if __name__ == "__main__":
    main()
