import numpy as np
import bark
from scipy.signal import argrelextrema

default_order = 10
default_std = -6.0


def thres_extrema(x, y, thresh):
    if thresh < 0:
        return (x < y) & (x < thresh)
    else:
        return (x > y) & (x > thresh)


def compute_std(dat):
    s = bark.stream.read(dat)
    std = np.zeros(len(s.attrs['columns']))
    for i, x in enumerate(bark.stream.read(dat)[:10]):
        std += np.std(x, 0)
    return std / (i+1)


def spikes(data, start_sample, threshs, pad_len, order):
    for col_i in range(data.shape[1]):
        column = data[:, col_i]
        rel_extremes, = argrelextrema(
            column,
            lambda x, y: thres_extrema(x, y, threshs[col_i]),
            order=order)
        mask = (rel_extremes >= pad_len) & (
            rel_extremes < data.shape[0] - pad_len)
        extreme_samples = rel_extremes[mask] + start_sample - pad_len
        yield from [(col_i, sample) for sample in extreme_samples]


def stream_spikes(stream, threshs, pad_len, order):
    for i, x in enumerate(stream.padded_chunks(pad_len)):
        start_sample = i * stream.chunksize
        yield from spikes(x, start_sample, threshs, pad_len, order)


def main(dat, csv, std_const, order=5):
    std = compute_std(dat)
    threshs = std_const * std
    s = bark.stream.read(dat)
    pad_len = order
    with open(csv, 'w') as fp:
        fp.write('channel,start\n')
        for (channel, sample) in stream_spikes(s, threshs, pad_len, order):
            fp.write('{},{}\n'.format(channel, sample/s.sr))
    bark.write_metadata(csv, datatype=1000, 
            columns={'channel': {'units': None},
                     'start': {'units', 's'}},
            thresholds=threshs,
            order=order,
            source=dat)


def _run():
    ''' Function for getting commandline args.'''
    import argparse

    p = argparse.ArgumentParser(description='''
    Finds spikes on all channels
    ''')
    p.add_argument('dat', help='name of a sampled dataset')
    p.add_argument('out', help='name of output event dataset')
    p.add_argument(
        '-s',
        '--std',
        help=
        'standard deviation cutoff, sign indicates detection direction, default: '
        .format(default_std),
        default=default_std,
        type=float)
    p.add_argument(
        '--order',
        help=
        'number of samples on either side to compare to find extrema point, default: '
        .format(default_order),
        default=default_order,
        type=int)
    args = p.parse_args()
    main(args.dat, args.out, args.std, args.order)


if __name__ == '__main__':
    _run()
