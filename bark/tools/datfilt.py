from __future__ import absolute_import, division, print_function, unicode_literals
from shutil import copyfile
import numpy as np
from scipy.signal import lfilter, bessel, butter, lfiltic
from datutils.utils import read_metadata, write_metadata, BUFFER_SIZE


def datfilt(dat, channels, out, order, highpass, lowpass, filttype):

    params = read_metadata(dat)
    dtype = params["dtype"]
    nchannels = params["n_channels"]
    rate = params["sampling_rate"]
    if highpass:
        params["highpass"] = highpass
    if lowpass:
        params["lowpass"] = lowpass
    params["filter_order"] = order
    if not channels:
        channels = np.arange(nchannels)  # select all channels
    params["filter_channels"] = channels
    if not out:
        out = dat + "_filt.dat"
    # load and reshape dat file
    data = np.memmap(dat, dtype=dtype, mode="r").reshape(-1, nchannels)
    if filttype == "butter":
        fil = butter
    elif filttype == "bessel":
        fil = bessel
    else:
        raise Exception("filter must be 'butter' or 'bessel'")
    if highpass and not lowpass:
        coefs = [fil(order,
                     highpass / (rate / 2.),
                     btype="highpass")] * nchannels
    elif lowpass and not highpass:
        coefs = [fil(order,
                     lowpass / (rate / 2.),
                     btype="lowpass")] * nchannels
    elif lowpass and highpass:
        coefs = [fil(order,
                     np.array((highpass, lowpass)) / (rate / 2.),
                     btype="bandpass")] * nchannels
    else:
        raise Exception("must set either '--lowpass' or '--highpass'")
    states = [lfiltic(c[0], c[1], [0]) for c in coefs]
    copyfile(dat, out)  # make a copy of the data to write over
    outdat = np.memmap(out, dtype=dtype, mode="r+", shape=data.shape)
    for i in range(0, len(data), BUFFER_SIZE):
        for c in channels:
            buffer = data[i:i + BUFFER_SIZE, c]
            outdat[i:i + BUFFER_SIZE, c], states[c] = lfilter(coefs[c][0],
                                                              coefs[c][1],
                                                              buffer,
                                                              zi=states[c])
    # run filter backwards (zero phase)
    for i in list(range(0, len(data), BUFFER_SIZE))[::-1]:
        for c in channels:
            buffer = data[i:i + BUFFER_SIZE, c][::-1]
            newbuffer, states[c] = lfilter(coefs[c][0],
                                           coefs[c][1],
                                           buffer,
                                           zi=states[c])
            outdat[i:i + BUFFER_SIZE, c] = newbuffer[::-1]
    write_metadata(out, **params)


def main():
    import argparse
    p = argparse.ArgumentParser(description="""
    dat file filtering program, uses zero-phase butterworth filter (filtfilt)
    """)
    p.add_argument("dat", help="dat file")
    p.add_argument("-c",
                   "--channels",
                   help="channels to filter, zero indexed, default:all",
                   type=int,
                   nargs="+")
    p.add_argument("-o", "--out", help="name of output dat file")
    p.add_argument("--order", help="filter order", default=3, type=int)
    p.add_argument("--highpass", help="highpass frequency", type=float)
    p.add_argument("--lowpass", help="lowpass frequency", type=float)
    p.add_argument("-f",
                   "--filter",
                   help="filter type: butter or bessel",
                   default="bessel")

    opt = p.parse_args()
    datfilt(opt.dat, opt.channels, opt.out, opt.order, opt.highpass,
            opt.lowpass, opt.filter)


if __name__ == "__main__":
    main()
