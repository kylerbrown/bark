from __future__ import division
import numpy as np
import pandas as pd
from scipy.signal import hamming
import bark

default_fftn = 512
default_step_ms = 1
default_min_syl = 30
default_min_silent = 20
default_threshold = 9
default_highcut = 8e3
default_lowcut = 1e3


def amplitude_stream(data, sr, fftn, step, lowcut, highcut):
    "returns an iterator with the start time in seconds and threshold value for each chunk"
    all_fft_freqs = np.fft.fftfreq(fftn, sr** -1)
    fft_freqs = (all_fft_freqs >= lowcut) & (all_fft_freqs <= highcut)
    window = hamming(fftn)
    data = data.ravel()
    for i in range(0, len(data) - fftn, step):
        x = data[i:i + fftn] * window
        fft = np.fft.fft(x, fftn)[fft_freqs]
        time = (i + fftn/2) / sr
        yield time, np.mean(np.log(np.abs(fft)))


def first_pass(amp_stream, thresh):
    "creates segments from all threshold crossings"
    starts = []
    stops = []
    in_syl = False
    for time, amp in amp_stream:
        if not in_syl and amp >= thresh:
            starts.append(time)
            in_syl = True
        if in_syl and amp < thresh:
            stops.append(time)
            in_syl = False
    # in case the recording ends in a syllable add last point to stops
    if in_syl:
        stops.append(time)
    return starts, stops


def second_pass(starts, stops, min_silent):
    " If two syllables are within min_silent, join them"
    i = 1
    while i < len(starts):
        if starts[i] - stops[i - 1] <= min_silent:
            stops[i - 1] = stops[i]
            del starts[i]
            del stops[i]
        else:
            i += 1


def third_pass(starts, stops, min_syl):
    " If a syllable is too short, remove"
    i = 0
    while i < len(starts):
        if stops[i] - starts[i] <= min_syl:
            del starts[i]
            del stops[i]
        else:
            i += 1


def main(datname,
         outfile,
         fftn=default_fftn,
         step_ms=default_step_ms,
         min_syl_ms=default_min_syl,
         min_silent_ms=default_min_silent,
         thresh=default_threshold,
         lowcut=default_lowcut,
         highcut=default_highcut):
    min_syl = min_syl_ms / 1000
    min_silent = min_silent_ms / 1000
    sampled = bark.read_sampled(datname)
    assert sampled.data.shape[1] == 1
    sr = sampled.sampling_rate
    step = int((step_ms / 1000) * sr)  # convert to samples
    amp_stream = amplitude_stream(sampled.data,
                                  sr,
                                  fftn,
                                  step,
                                  lowcut=lowcut,
                                  highcut=highcut)
    start, stop = first_pass(amp_stream, thresh)
    second_pass(start, stop, min_silent)
    third_pass(start, stop, min_syl)
    bark.write_events(outfile,
                      pd.DataFrame(dict(start=start,
                                        stop=stop,
                                        name='')),
                      units="s")


def _run():
    """ Function for getting commandline args."""
    import argparse

    p = argparse.ArgumentParser(description="""
    Create a segment label file.

    Uses method from Koumura & Okanoya 2016.

    First an amplitude envelope with a frequency band is computed.
    Then from these threshold crossings, any short gap is annealed,
    and any short syllable is removed.
    """)
    p.add_argument("dat", help="name of a sampled dataset")
    p.add_argument("-o",
                   "--out",
                   required=True,
                   help="name of output event dataset")
    p.add_argument("-n",
                   "--fftn",
                   help="number of fft coeficients",
                   type=int,
                   default=default_fftn)
    p.add_argument("-s",
                   "--step",
                   help="step size in milliseconds, default: {}"
                   .format(default_step_ms),
                   default=default_step_ms)
    p.add_argument("--min-syl",
                   help="minimum syllable length in ms, default: {}"
                   .format(default_min_syl),
                   type=int,
                   default=default_min_syl)
    p.add_argument("--min-silent",
                   help="minimum silence length in ms, default: {}"
                   .format(default_min_silent),
                   type=int,
                   default=default_min_silent)
    p.add_argument("-t",
                   "--threshold",
                   help="syllable threshold, default: {}"
                   .format(default_threshold),
                   default=default_threshold,
                   type=float)
    p.add_argument("--lowfreq",
                   help="low frequency to use for amplitude, default: {}"
                   .format(default_highcut),
                   default=default_lowcut,
                   type=float)
    p.add_argument("--highfreq",
                   help="highest frequency to use for amplitude, default: {}"
                   .format(default_highcut),
                   default=default_highcut,
                   type=float)

    args = p.parse_args()
    main(args.dat, args.out, args.fftn, args.step, args.min_syl,
         args.min_silent, args.threshold, args.lowfreq, args.highfreq)


if __name__ == "__main__":
    _run()
