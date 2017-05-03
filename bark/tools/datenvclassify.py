import bark
import numpy as np
import pandas as pd
import os.path
from scipy.signal import filtfilt, butter
from scipy.io import wavfile


def abs_and_smooth(x, sr, lp=100):
    abs_x = np.abs(x)
    if len(x.shape) > 1:
        abs_x = np.sum(abs_x,
                       axis=-1)  # sum over last dimension eg sum over channels
    b, a = butter(3, lp / 2 / sr, btype="low")
    filtered_x = filtfilt(b, a, abs_x, axis=0)
    return filtered_x


def myresample(x, old_sr, new_sr):
    '''a dumb resampler that uses linear interpolation'''
    duration = len(x) / old_sr
    old_sample_times = np.arange(0, duration, 1 / old_sr)
    new_sample_times = np.arange(0, duration, 1 / new_sr)
    return np.interp(new_sample_times, old_sample_times, x)


def amplitude(x, sr, new_sr):
    '''finds amplitude, resamples and demeans'''
    x_amp = abs_and_smooth(x, sr)
    x_resamp = myresample(x_amp, sr, new_sr)
    return x_resamp - np.mean(x_resamp)


def wav_envelopes(wavnames, new_sr=22050):
    ''' From a list of wav files, find the envelope and resample them.
    Returns --
        names: a list of stimulus names
        envelopes: a list of amplitude envelopes
    '''
    names = []
    envelopes = []
    for wav in wavnames:
        name = os.path.splitext(os.path.basename(wav))[0]
        names.append(name)
        wavsr, wavdata = wavfile.read(wav)
        amp_env = amplitude(wavdata, wavsr, new_sr)
        envelopes.append(amp_env)
    return names, envelopes


def classify_stimuli(mic_data, mic_sr, starts, wav_names, wav_envs, common_sr):
    # get longest stimuli to determine how much data to grab
    max_stim_duration = int(max([len(x) for x in wav_envs]) / common_sr *
                            mic_sr)
    max_stim_dur_common_sr = max([len(x) for x in wav_envs])
    # convert trigfile starts to samples
    start_samps = np.array(starts * mic_sr, dtype=int)
    labels = []
    for start_samp in start_samps:
        x = amplitude(mic_data[start_samp:start_samp + max_stim_duration],
                      mic_sr, common_sr)
        if len(x) < max_stim_dur_common_sr:
            print('skipping {} ... too close to end of file'.format(
                start_samp))
            continue
        inner_prods = [x[0:len(y)] @y for y in wav_envs]
        best_match = wav_names[np.argmax(inner_prods)]
        labels.append(best_match)
    return labels


def get_stops(labels, starts, stim_names, stim_envs, sr):
    '''
    labels: sequence of identified stimuli names
    starts: seqence of stimuli times, in seconds
    stim_names: a vector of all stimulis names
    stim_enves: a corresponding vector of stimulus envelopes
    Returns a vector of times, indicating when the stimuli ended.'''
    length_lookup = {name: len(env) / sr
                     for name, env in zip(stim_names, stim_envs)}
    stops = [start + length_lookup[name]
             for start, name in zip(starts, labels)]
    return stops


def write(outfile, starts, stops, labels):
    outdset = pd.DataFrame(dict(start=starts, stop=stops, name=labels))
    columns = {'start': {'units': 's'},
               'stop': {'units': 's'},
               'name': {'units': None}}
    bark.write_events(outfile, outdset, columns=columns)


def main(datfile, trigfile, outfile, wavfiles):
    common_sr = 22050  # everything is resampled to this
    # get wav envelopes
    stim_names, stim_envs = wav_envelopes(wavfiles, common_sr)
    mic_dset = bark.read_sampled(datfile)
    mic_sr = mic_dset.sampling_rate
    starts = bark.read_events(trigfile).data.start
    # get most likely stimulus for each trigger time
    labels = classify_stimuli(mic_dset.data, mic_sr, starts, stim_names,
                              stim_envs, common_sr)
    stops = get_stops(labels, starts, stim_names, stim_envs, common_sr)
    write(outfile, starts, stops, labels)


def _run():
    ''' Function for getting commandline args.'''
    import argparse

    p = argparse.ArgumentParser(description='''
    Classify acoustic events by amplitude envelope. Uses a set of WAV files as
    templates. Useful for recovering the identity of acoustic stimuli, when
    their amplitude envelopes are significantly different. If not, use the stimulus
    log to reconstruct stimulus identity.
    ''')
    p.add_argument('dat', help='name of a sampled dataset')
    p.add_argument('trig',
                   help='name of an event dataset containing stimuli times')
    p.add_argument('out', help='name of output event dataset')
    p.add_argument('-w',
                   '--wavs',
                   nargs='+',
                   help='source stimulus wav files',
                   required=True)
    args = p.parse_args()
    main(args.dat, args.trig, args.out, args.wavs)


if __name__ == '__main__':
    _run()
