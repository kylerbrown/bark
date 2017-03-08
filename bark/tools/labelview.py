import os
import sys
import string
import yaml
import numpy as np
from scipy.signal import spectrogram
import matplotlib.pyplot as plt
import bark
from bark.io.eventops import (OpStack, write_stack, read_stack, Update, Merge,
                              Split, Delete, New)

import warnings
warnings.filterwarnings('ignore')  # suppress matplotlib warnings

help_string = '''
Pressing any number or letter (uppercase or lowercase) will mark a segment.
To create custom label, create an external file with key: value pairs
like this:
    1: c1
    2: c2
    z: a*

ctrl+s : saves the annotation data
ctrl+h : prints this message
ctrl+o : zoom out
ctrl+i : zoom in
ctrl+m : merge current syllable with previous
ctrl+x : delete segment
ctrl+z : undo last operation
ctrl+y : redo
ctrl+w : close
click on segment boundary : move boundary
ctrl+click inside a segment : split segment
ctrl+click outside a segment : new segment (TODO)
click on segment boundaries to adjust them.

The bottom panel is a map of all label locations.
Click on a label to travel to that location.

On close, an operation file and the final event file will be written.
Do not kill from terminal unless you want to prevent a save.
'''


# kill all the shorcuts
def kill_shortcuts(plt):
    plt.rcParams['keymap.all_axes'] = ''
    plt.rcParams['keymap.back'] = ''
    plt.rcParams['keymap.forward'] = ''
    plt.rcParams['keymap.fullscreen'] = ''
    plt.rcParams['keymap.grid'] = ''
    plt.rcParams['keymap.home'] = ''
    plt.rcParams['keymap.pan'] = ''
    #plt.rcParams['keymap.quit'] = ''
    plt.rcParams['keymap.save'] = ''
    plt.rcParams['keymap.xscale'] = ''
    plt.rcParams['keymap.yscale'] = ''
    plt.rcParams['keymap.zoom'] = ''


def labels_to_scatter_coords(labels):
    times = [x['start'] for x in labels]
    values = []
    for record in labels:
        name = record['name']
        if not isinstance(name, str) or name == '':
            v = 0
        elif name.isdigit():
            v = int(name)
        elif name[0].isalpha():
            # alphabet in range 11-36
            v = 133 - ord(name[0].lower())
        else:
            v = 37
        values.append(v)
    return times, values


def nearest_label(labels, xdata):
    return np.argmin(np.abs(xdata - np.array([x['start'] for x in labels])))


def plot_spectrogram(data,
                     sr,
                     start,
                     stop,
                     ms_nfft=15,
                     ax=None,
                     lowfreq=300,
                     highfreq=8000,
                     window=('kaiser', 8),
                     **kwargs):
    '''
    data : a vector of samples, first sample starts at time = 0
    sr : sampling rate
    start : start time to slice data, units: seconds
    stop : stop time to slice data, units: seconds
    ms_nfft : width of fourier transform in milliseconds
    ax : axis object to plot spectrogram on.
    lowfreq : lowest frequency to plot
    highfreq : highest frequency to plot
    '''
    nfft = int(ms_nfft / 1000. * sr)
    start_samp = int(start * sr) - nfft // 2
    stop_samp = int(stop * sr) - nfft // 2
    x = data[start_samp:stop_samp]

    # determine overlap based on screen size.
    # We don't need more points than pixels
    pixels = 1000
    samples_per_pixel = int((stop - start) * sr / pixels)
    noverlap = max(nfft - samples_per_pixel, 0)
    f, t, Sxx = spectrogram(x,
                            sr,
                            nperseg=nfft,
                            noverlap=noverlap,
                            mode='magnitude',
                            window=window, )
    freq_mask = (f > lowfreq) & (f < highfreq)
    fsub = f[freq_mask]
    Sxxsub = Sxx[freq_mask, :]
    vmax = np.percentile(Sxxsub, 98)
    t += start
    if ax is None:
        ax = plt.gca()
    image = ax.pcolorfast(t,
                          fsub,
                          Sxxsub,
                          cmap=plt.get_cmap('viridis'),
                          vmax=vmax,
                          **kwargs)
    plt.sca(ax)
    plt.ylim(lowfreq, highfreq)
    return image


class SegmentReviewer:
    def __init__(self,
                 osc_ax,
                 spec_ax,
                 map_ax,
                 sampled,
                 opstack,
                 keymap,
                 outfile,
                 out_attrs,
                 opsfile=None):
        self.canvas = osc_ax.get_figure().canvas
        self.osc_ax = osc_ax
        self.spec_ax = spec_ax
        self.map_ax = map_ax
        self.data = sampled.data.ravel()
        self.sr = sampled.sampling_rate
        self.label_attrs = out_attrs
        self.opstack = opstack
        self.opsfile = opsfile
        self.outfile = outfile
        self.keymap = keymap
        if opstack.ops:
            self.i = opstack.ops[-1].index
        else:
            self.i = 0
        self.N_points = 20000
        self.initialize_plots()
        self.update_plot_data()

    def initialize_plots(self):
        self.osc_ax.set_axis_bgcolor('k')
        self.osc_ax.tick_params(axis='x',
                                which='both',
                                bottom='off',
                                top='off',
                                labelbottom='off')
        self.spec_ax.set_axis_bgcolor('k')
        self.osc_line, = self.osc_ax.plot(
            np.arange(self.N_points),
            np.zeros(self.N_points),
            color='gray')
        self.osc_boundary_start = self.osc_ax.axvline(color='r')
        self.osc_boundary_stop = self.osc_ax.axvline(color='r')
        self.syl_labels = [self.osc_ax.text(0,
                                            0,
                                            '',
                                            size='xx-large',
                                            color='r') for _ in range(20)]
        self.initialize_minimap()
        self.osc_ax.figure.tight_layout()

    def initialize_minimap(self):
        times, values = labels_to_scatter_coords(self.opstack.events)
        self.map_ax.set_axis_bgcolor('k')
        self.map_ax.scatter(times,
                            values,
                            c=values,
                            vmin=0,
                            vmax=37,
                            cmap=plt.get_cmap('hsv'),
                            edgecolors='none')
        self.map_ax.vlines(self.opstack.events[self.i]['start'],
                           -1,
                           38,
                           zorder=0.5,
                           color='w',
                           linewidth=1)
        self.map_ax.tick_params(axis='y',
                                which='both',
                                left='off',
                                right='off',
                                labelleft='off')
        self.map_ax.set_ylim(-1, 38)

    def label_nearby_syls(self):
        'labels for current syl and two on either side'
        for i in range(-10 + self.i, 11 + self.i):
            label_i = i - self.i
            if i >= 0 and i < len(self.opstack.events):
                text = self.syl_labels[label_i]
                x = (self.opstack.events[i]['start'] +
                     self.opstack.events[i]['stop']) / 2
                name = self.opstack.events[i]['name']
                if isinstance(name, str):
                    text.set_x(x)
                    text.set_visible(True)
                    text.set_text(name)
                else:
                    text.set_visible(False)
            else:
                self.syl_labels[label_i].set_visible(False)

    def update_syl_boundaries(self):
        start = self.opstack.events[self.i]['start']
        stop = self.opstack.events[self.i]['stop']
        self.osc_boundary_start.set_xdata((start, start))
        self.osc_boundary_stop.set_xdata((stop, stop))

    def update_minimap(self):
        # If perfomance lags, may need to adjust plot elements instead of
        # clearing everything and starting over.
        self.map_ax.clear()
        self.initialize_minimap()

    def update_plot_data(self):
        'updates plot data on all three axes'
        self.selected_boundary = None
        i = self.i
        sr = self.sr
        start = self.opstack.events[i]['start']
        start_samp = int(start * sr)
        stop = self.opstack.events[i]['stop']
        stop_samp = int(stop * sr)
        syl_samps = stop_samp - start_samp
        self.buffer_start_samp = start_samp - (self.N_points - syl_samps) // 2
        self.buffer_stop_samp = self.buffer_start_samp + self.N_points
        self.buf_start = self.buffer_start_samp / sr
        self.buf_stop = self.buffer_stop_samp / sr
        # update plots
        self.label_nearby_syls()
        self.update_syl_boundaries()
        self.update_spectrogram()
        self.update_oscillogram()
        self.update_minimap()
        if self.opstack.ops:
            last_command = str(self.opstack.ops[-1])
        else:
            last_command = 'none'
        if i == 0:
            self.osc_ax.set_title('ctrl+h for help, prints to terminal')
        else:
            self.osc_ax.set_title('{}/ {} {}'.format(i + 1, len(
                self.opstack.events), last_command))
        self.canvas.draw()

    def update_spectrogram(self):
        self.spec_ax.clear()
        plot_spectrogram(self.data,
                         self.sr,
                         self.buf_start,
                         self.buf_stop,
                         ax=self.spec_ax)

    def update_oscillogram(self):
        x = self.data[self.buffer_start_samp:self.buffer_stop_samp]
        t = np.arange(len(x)) / self.sr + self.buf_start
        if len(x) > 10000:
            t_interp = np.linspace(self.buf_start, self.buf_stop, 10000)
            x_interp = np.interp(t_interp, t, x)
        else:
            t_interp = t
            x_interp = x
        self.osc_line.set_data(t_interp, x_interp)
        self.osc_ax.set_xlim(self.buf_start, self.buf_stop)
        self.osc_ax.set_ylim(min(x), max(x))

    def connect(self):
        'creates all the event connections'
        self.cid_key_press = self.canvas.mpl_connect('key_press_event',
                                                     self.on_key_press)
        self.cid_mouse_press = self.canvas.mpl_connect('button_press_event',
                                                       self.on_mouse_press)
        self.cid_mouse_motion = self.canvas.mpl_connect('motion_notify_event',
                                                        self.on_mouse_motion)
        self.cid_mouse_release = self.canvas.mpl_connect(
            'button_release_event', self.on_mouse_release)

    def on_mouse_press(self, event):
        if event.inaxes in (None, self.spec_ax) or event.button != 1:
            return
        start_pos = self.osc_boundary_start.get_xdata()[0]
        stop_pos = self.osc_boundary_stop.get_xdata()[0]
        # jump to syllable from map click
        if event.inaxes == self.map_ax:
            i = nearest_label(self.opstack.events, float(event.xdata))
            self.i = i
            self.update_plot_data()
        # sylable splitting
        elif (event.key == 'control' and event.xdata > start_pos and
              event.xdata < stop_pos):
            self.opstack.push(Split(self.i, float(event.xdata)))
            self.update_plot_data()
        # new syllable before
        elif event.key == 'control' and event.xdata < start_pos:
            self.opstack.push(New(self.i,
                                  name='',
                                  start=float(event.xdata),
                                  stop=float(event.xdata) + .020))
            self.update_plot_data()
        elif event.key == 'control' and event.xdata > stop_pos:
            self.opstack.push(New(self.i + 1,
                                  name='',
                                  start=float(event.xdata),
                                  stop=float(event.xdata) + .020))
            self.i += 1
            self.update_plot_data()
        # boundary updates
        else:
            xlim1, xlim2 = self.osc_ax.get_xlim()
            xspan = xlim2 - xlim1
            if abs(event.xdata - start_pos) / xspan < 0.007:
                self.selected_boundary = self.osc_boundary_start
            elif abs(event.xdata - stop_pos) / xspan < 0.007:
                self.selected_boundary = self.osc_boundary_stop
            if self.selected_boundary:
                self.selected_boundary.set_color('y')
                self.canvas.draw()

    def on_mouse_motion(self, event):
        if self.selected_boundary is None:
            return
        self.selected_boundary.set_xdata((event.xdata, event.xdata))
        self.canvas.draw()

    def on_mouse_release(self, event):
        if self.selected_boundary == self.osc_boundary_start:
            self.opstack.push(Update(self.i, 'start', float(event.xdata)))
        elif self.selected_boundary == self.osc_boundary_stop:
            self.opstack.push(Update(self.i, 'stop', float(event.xdata)))
        if self.selected_boundary:
            self.selected_boundary.set_color('r')
            self.update_syl_boundaries()
        self.selected_boundary = None
        self.canvas.draw()

    def inc_i(self):
        'Go to next syllable.'
        if self.i < len(self.opstack.events) - 1:
            self.i += 1
        self.update_plot_data()

    def dec_i(self):
        'Go to previous syllable.'
        if self.i > 0:
            self.i -= 1
        self.update_plot_data()

    def on_key_press(self, event):
        #print('you pressed ', event.key)
        if event.key in ('pagedown', ' '):
            self.inc_i()
        elif event.key in ('pageup', 'backspace'):
            self.dec_i()
        elif event.key in self.keymap:
            newlabel = self.keymap[event.key]
            self.opstack.push(Update(self.i, 'name', newlabel))
            self.inc_i()
        elif event.key == 'ctrl+i':
            if self.N_points > 5000:
                self.N_points -= 5000
                self.update_plot_data()
        elif event.key == 'ctrl+o':
            self.N_points += 5000
            self.update_plot_data()
        elif event.key == 'ctrl+s':
            self.save()
        elif event.key == 'ctrl+h':
            print(help_string)
        elif event.key == 'ctrl+m' and self.i > 0:
            self.i -= 1
            self.opstack.push(Merge(self.i))
            self.update_plot_data()
        elif event.key == 'ctrl+x':
            self.opstack.push(Delete(self.i))
            self.update_plot_data()
        elif event.key == 'ctrl+z' and self.opstack.ops:
            self.opstack.undo()
            self.i = self.opstack.undo_ops[-1].index
            self.update_plot_data()
        elif event.key == 'ctrl+y' and self.opstack.undo_ops:
            self.opstack.redo()
            self.i = self.opstack.ops[-1].index
            self.update_plot_data()

    def save(self):
        'Writes out labels to file.'
        from pandas import DataFrame
        label_data = DataFrame(self.opstack.events)
        bark.write_events(self.outfile, label_data, **self.label_attrs)
        print(self.outfile, 'written')
        if self.opsfile:
            write_stack(self.opsfile, self.opstack)
            print(self.opsfile, 'written')

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.save()


def build_shortcut_map(mapfile=None):
    allkeys = string.digits + string.ascii_letters
    shortcut_map = {x: x for x in allkeys}
    # load keys from file
    if mapfile:
        custom = {str(key): value
                  for key, value in yaml.load(open(mapfile, 'r')).items()}
        print('custom keymaps:', custom)
        shortcut_map.update(custom)
    return shortcut_map


def to_seconds(dset):
    'TODO Converts bark EventData object to units of seconds.'
    if 'offset' in dset.attrs and dset.attrs['offset'] != 0:
        raise Exception('offsets are not yet supported in event file')
    if dset.attrs['units'] != 's':
        raise Exception('only units of s are supported in event file')
    return dset


def load_opstack(opsfile, labelfile, labeldata, use_ops):
    load_ops = os.path.exists(opsfile) and use_ops
    if load_ops:
        opstack = read_stack(opsfile)
        print('Reading operations from {}.'.format(opsfile))
        if len(opstack.original_events) != len(labeldata):
            print("The number of segments in autosave file is incorrect.")
            sys.exit(0)
        for stack_event, true_event in zip(opstack.original_events, labeldata):
            if (stack_event['name'] != true_event['name'] or
                    not np.allclose(stack_event['start'], true_event['start'])
                    or
                    not np.allclose(stack_event['stop'], true_event['stop'])):
                print("Warning! Autosave:\n {}\n Original:\n{}"
                      .format(stack_event, true_event))
    else:
        opstack = OpStack(labeldata)
    return opstack


def main(datfile, labelfile, outfile=None, shortcutfile=None, use_ops=True):
    if not labelfile:
        labelfile = os.path.splitext(datfile)[0] + '.csv'
    kill_shortcuts(plt)
    sampled = bark.read_sampled(datfile)
    assert len(sampled.attrs['columns']) == 1
    labels = bark.read_events(labelfile)
    labeldata = to_seconds(labels).data.to_dict('records')
    shortcuts = build_shortcut_map(shortcutfile)
    opsfile = labelfile + '.ops.json'
    opstack = load_opstack(opsfile, labelfile, labeldata, use_ops)
    if not outfile:
        outfile = os.path.splitext(labelfile)[0] + '_edit.csv'
    plt.figure()
    # Oscillogram and Spectrogram get
    # three times the vertical space as the minimap.
    osc_ax = plt.subplot2grid((7, 1), (0, 0), rowspan=3)
    spec_ax = plt.subplot2grid((7, 1), (3, 0), rowspan=3, sharex=osc_ax)
    map_ax = plt.subplot2grid((7, 1), (6, 0))
    # Segement review is a context manager to ensure a save prompt
    # on exit. see SegmentReviewer.__exit__
    with SegmentReviewer(osc_ax, spec_ax, map_ax, sampled, opstack, shortcuts,
                         outfile, labels.attrs, opsfile) as reviewer:
        reviewer.connect()
        plt.show(block=True)


def _run():
    import argparse

    p = argparse.ArgumentParser(description='''
    Review and annotate segments
    ''')
    p.add_argument('dat', help='name of a sampled dataset')
    p.add_argument('labelfile',
                   nargs='?',
                   help='Associated event dataset containing segments\
                   defaults to same name as dat but with a .csv extension.')
    p.add_argument('-o', '--out', help='output label file')
    p.add_argument('-i',
                   '--ignore',
                   help='ignore operations from LABELFILE.ops.json',
                   action='store_true')
    p.add_argument('-k',
                   '--shortcut-keys',
                   help='''YAML file with keyboard shortcuts.
        Keys are digits, lowercase and uppercase characters''')

    args = p.parse_args()
    main(args.dat, args.labelfile, args.out, args.shortcut_keys,
         not args.ignore)


if __name__ == '__main__':
    _run()
