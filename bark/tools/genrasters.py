import argparse
import bark
import collections as coll
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import os
import scipy.io.wavfile
import sys

# plot styling constants
AXIS_LABEL_SIZE = 12 # in pt
TITLE_SIZE = 16 # in pt
OFFSET_STEP = 1 # arbitrary units
RASTER_LH_PROP = 1 # line height proportion
RASTER_LW = 1 # line width; in pt
STIM_OFFSET = 1.1 # proportion of OFFSET_STEP
DFLT_PAD_BEF = 0.5 # in seconds
DFLT_PAD_AFT = 0.5 # in seconds
NUM_XTICKS = 8

Stimulus = coll.namedtuple('Stimulus', ['name', 'data', 'sampling_rate'])

def sec2samp(sec, sr):
    return int(round(sec * sr))

def pad_stimulus(stim, padding):
    """Returns a new Stimulus object with appropriate before and after padding
       stim     --  Stimulus object
       padding  --  2-tuple, in seconds, of before and after padding
    """
    extended = [0]*sec2samp(padding[0], stim.sampling_rate)
    extended.extend(stim.data)
    extended.extend([0]*sec2samp(padding[1], stim.sampling_rate))
    return Stimulus(stim.name, extended, stim.sampling_rate)

def aligned_raster(spikes, stim_ds, stim_name, padding, title, stim_data):
    """Returns a pyplot figure object with aligned rasters based on stim_ds
       and stim_name.
       spike_list  --  sequence of spike times, in seconds
       stim_ds     --  Bark event dataset, with time in seconds
       stim_name   --  string
       padding     --  2-tuple, in seconds, of before and after padding
       title       --  string
       stim_data   --  Stimulus object, or None
    """
    f = plt.figure()
    offset = 0
    stim_events = stim_ds[stim_ds['name'] == stim_name]
    if stim_events.empty:
        msg = 'stimulus "{}" not found in {}'
        raise KeyError(msg.format(stim_name, stim_ds.name))
    if stim_data is not None:
        extended_stimulus = pad_stimulus(stim_data, padding)
        arrstim = np.array(extended_stimulus.data)
        plt.plot((arrstim / max(abs(arrstim))) + STIM_OFFSET * OFFSET_STEP)
    for stim_event in stim_events.itertuples():
        start = stim_event.start - padding[0]
        stop = stim_event.stop + padding[1]
        offset -= OFFSET_STEP
        curr_spks = [s - start for s in spikes if s >= start and s <= stop]
        if stim_data is not None:
            curr_spks = [sec2samp(s, stim_data.sampling_rate)
                         for s in curr_spks]
        if curr_spks:
            col = 'black'
        else: # if there are no spikes, it messes with plot alignment
            curr_spks = [0]
            col = 'white'
        height = offset + RASTER_LH_PROP * OFFSET_STEP
        plt.vlines(curr_spks, offset, height, linewidths=RASTER_LW, color=col)
    plt.title(title, fontsize=TITLE_SIZE)
    xmax = stop - start
    xstep = xmax / NUM_XTICKS
    xt = np.arange(padding[0], xmax, xstep)
    if stim_data is not None:
        xmax = sec2samp(xmax, stim_data.sampling_rate)
        xt = [sec2samp(t, stim_data.sampling_rate) for t in xt]
    plt.xlim([(-0.05 * xmax), (1.05 * xmax)])
    plt.xticks(xt, ['{:.2f}'.format(xstep * t) for t in range(0, NUM_XTICKS)])
    plt.yticks([])
    plt.xlabel('Time (s)', fontsize=AXIS_LABEL_SIZE)
    plt.ylabel('Event repetitions', fontsize=AXIS_LABEL_SIZE)
    return f

def _parse_args(raw_args):
    desc = 'Produces aligned rasters for every spiking unit in a dataset.'
    epi = 'Spike and stimulus times should be in seconds.'
    parser = argparse.ArgumentParser(description=desc, epilog=epi)
    parser.add_argument('spikes', help='Bark event dataset of spike times')
    parser.add_argument('stimtimes', help='Bark event dataset of stim times')
    parser.add_argument('name', help='name of stim to align rasters')
    parser.add_argument('-s', '--stim',
                        help='.wav file or Bark sampled dataset of stim')
    parser.add_argument('-e', '--ext', default='png',
                        help='output format extension (default: png)')
    pad_help_str = 'padding {} stimulus onset (default: {}s)'
    parser.add_argument('-b', '--bef', type=float, default=DFLT_PAD_BEF,
                        help=pad_help_str.format('before', DFLT_PAD_BEF))
    parser.add_argument('-a', '--aft', type=float, default=DFLT_PAD_AFT,
                        help=pad_help_str.format('after', DFLT_PAD_AFT))
    return parser.parse_args(raw_args)

def _main():
    args = _parse_args(sys.argv[1:])
    spike_ds = bark.read_events(args.spikes)
    stim_time_ds = bark.read_events(args.stimtimes)
    if args.stim:
        if os.path.splitext(args.stim)[-1] == '.wav':
            sr, stim = scipy.io.wavfile.read(args.stim)
            stimulus = Stimulus(args.name, stim, sr)
        else:
            stim = bark.read_sampled(args.stim)
            stimulus = Stimulus(args.name, stim.data, stim.sampling_rate)
    else:
        stimulus = None
    title_str = '"{}"-aligned spike raster, unit {}'
    fn_str = '{}_aligned_raster_unit_{}.{}'
    for unit in set(spike_ds['name']):
        f = aligned_raster(spike_ds[spike_ds['name'] == unit]['start'],
                           stim_time_ds,
                           args.name,
                           padding=(args.bef, args.aft),
                           title=title_str.format(args.name, unit),
                           stim_data=stimulus)
        f.savefig(fn_str.format(args.name, unit, args.ext))
        plt.close(f)

if __name__ == '__main__':
    _main()
