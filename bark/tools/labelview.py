import string
import yaml
import numpy as np
from scipy.signal import spectrogram
import matplotlib.pyplot as plt
import bark

help_string = """
Pressing any number or letter (uppercase or lowercase) will mark a segment.
To create custom label, create an external file with key: value pairs like this:
    1: c1
    2: c2
    z: a*

ctrl+s : saves the annotation data
ctrl+h : prints this message
ctrl+o : zoom out
ctrl+i : zoom in
ctrl+m : merge current syllable with previous
ctrl+x : delete segment
click on segment boundary : move boundary
ctrl+click inside a segment : split segment
ctrl+click outside a segment : new segment (TODO)
click on segment boundaries to adjust them.

The bottom panel is a map of all label locations.
Click on a label to travel to that location.

On close, you'll be prompted to save your work. Hit 'y <enter>' to save.
"""

# kill all the shorcuts
plt.rcParams['keymap.all_axes'] = ''
plt.rcParams['keymap.back'] = ''
plt.rcParams['keymap.forward'] = ''
plt.rcParams['keymap.fullscreen'] = ''
plt.rcParams['keymap.grid'] = ''
plt.rcParams['keymap.home'] = ''
plt.rcParams['keymap.pan'] = ''
plt.rcParams['keymap.quit'] = ''
plt.rcParams['keymap.save'] = ''
plt.rcParams['keymap.xscale'] = ''
plt.rcParams['keymap.yscale'] = ''
plt.rcParams['keymap.zoom'] = ''

SPLIT_PAD = 0.005


def seg_name(labels, idx, name):
    labels[idx]['name'] = name


def seg_delete(labels, idx):
    del labels[idx]


def seg_start(labels, idx, start):
    labels[idx]['start'] = start


def seg_stop(labels, idx, stop):
    labels[idx]['stop'] = stop


def seg_split(labels, idx, split_time):
    labels.insert(idx + 1, labels[idx].copy())
    seg_stop(labels, idx, split_time - SPLIT_PAD)
    seg_start(labels, idx + 1, split_time + SPLIT_PAD)


def seg_merge_prev(labels, idx):
    if idx > 0:
        labels[idx - 1]['stop'] = labels[idx]['stop']
        seg_delete(labels, idx)


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
                     **kwargs):
    """
    data : a vector of samples, first sample starts at time = 0
    sr : sampling rate
    start : start time to slice data, units: seconds
    stop : stop time to slice data, units: seconds
    ms_nfft : width of fourier transform in milliseconds
    decent colormaps: cm.viridis, cm.inferno, cm.magma, cm.plasma
    extra arguments are sent to plt.pcolorfast
    """
    nfft = int(ms_nfft / 1000. * sr)
    start_samp = int(start * sr) - nfft // 2
    stop_samp = int(stop * sr) - nfft // 2
    x = data[start_samp:stop_samp]
    f, t, Sxx = spectrogram(x,
                            sr,
                            nperseg=nfft,
                            noverlap=nfft - (int(sr * .001)),
                            mode='magnitude')
    freq_mask = (f > lowfreq) & (f < highfreq)
    fsub = f[freq_mask]
    Sxxsub = Sxx[freq_mask, :]
    t += start
    if ax is None:
        ax = plt.gca()
    image = ax.pcolorfast(t,
                          fsub,
                          Sxxsub,
                          cmap=plt.get_cmap('inferno'),
                          **kwargs)
    plt.sca(ax)
    plt.ylim(lowfreq, highfreq)
    return image


class SegmentReviewer:
    def __init__(self, figure, osc_ax, spec_ax, map_ax, sampled, labels,
                 shortcuts, outfile):
        self.figure = figure
        self.osc_ax = osc_ax
        self.spec_ax = spec_ax
        self.map_ax = map_ax
        self.data = sampled.data.ravel()
        self.sr = sampled.sampling_rate
        self.labels = labels.data.to_dict('records')
        self.label_attrs = labels.attrs
        self.outfile = outfile
        self.shortcuts = shortcuts
        self.i = 0
        self.label_units = labels.attrs["units"]
        assert self.label_units == "s"
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
                                            "",
                                            size='xx-large',
                                            color='r') for _ in range(20)]
        self.initialize_minimap()
        self.osc_ax.figure.tight_layout()

    def initialize_minimap(self):
        times, values = labels_to_scatter_coords(self.labels)
        self.map_ax.set_axis_bgcolor('k')
        self.map_ax.scatter(times,
                            values,
                            c=values,
                            vmin=0,
                            vmax=37,
                            cmap=plt.get_cmap('hsv'),
                            edgecolors='none')
        self.map_ax.vlines(self.labels[self.i]['start'],
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
        "labels for current syl and two on either side"
        for i in range(-10 + self.i, 11 + self.i):
            label_i = i - self.i
            if i >= 0 and i < len(self.labels):
                text = self.syl_labels[label_i]
                x = (self.labels[i]['start'] + self.labels[i]['stop']) / 2
                name = self.labels[i]['name']
                if isinstance(name, str):
                    text.set_x(x)
                    text.set_visible(True)
                    text.set_text(name)
                else:
                    text.set_visible(False)
            else:
                self.syl_labels[label_i].set_visible(False)

    def update_syl_boundaries(self):
        start = self.labels[self.i]['start']
        stop = self.labels[self.i]['stop']
        self.osc_boundary_start.set_xdata((start, start))
        self.osc_boundary_stop.set_xdata((stop, stop))

    def update_minimap(self):
        self.map_ax.clear()
        self.initialize_minimap()

    def update_plot_data(self):
        "updates plot data"
        self.selected_boundary = None
        i = self.i
        sr = self.sr
        labels = self.labels
        start = self.labels[i]['start']
        start_samp = int(start * sr)
        stop = self.labels[i]['stop']
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
        if i == 0:
            self.osc_ax.set_title('ctrl+h for help, prints to terminal')
        else:
            self.osc_ax.set_title('{} of {}'.format(i + 1, len(self.labels)))
        self.figure.canvas.draw()

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
        self.osc_line.set_data(t, x)
        self.osc_ax.set_xlim(self.buf_start, self.buf_stop)
        self.osc_ax.set_ylim(min(x), max(x))

    def connect(self):
        "creates all the event connections"
        self.cid_key_press = self.figure.canvas.mpl_connect('key_press_event',
                                                            self.on_key_press)
        self.cid_mouse_press = self.figure.canvas.mpl_connect(
            'button_press_event', self.on_mouse_press)
        self.cid_mouse_release = self.figure.canvas.mpl_connect(
            'button_release_event', self.on_mouse_release)

    def on_mouse_press(self, event):
        if event.inaxes is None:
            return
        if event.button != 1:
            return
        xlim1, xlim2 = self.osc_ax.get_xlim()
        xspan = xlim2 - xlim1
        start_pos = self.osc_boundary_start.get_xdata()[0]
        stop_pos = self.osc_boundary_stop.get_xdata()[0]
        if event.inaxes == self.map_ax:
            i = nearest_label(self.labels, event.xdata)
            self.i = i
            self.update_plot_data()
        # sylable splitting
        if event.key == 'control' and event.xdata > start_pos and event.xdata < stop_pos:
            seg_split(self.labels, self.i, event.xdata)
            self.update_plot_data()
        # boundary updates
        else:
            if abs(event.xdata - start_pos) / xspan < 0.006:
                self.selected_boundary = self.osc_boundary_start
            elif abs(event.xdata - stop_pos) / xspan < 0.006:
                self.selected_boundary = self.osc_boundary_stop
            if self.selected_boundary:
                self.selected_boundary.set_color('y')
                self.figure.canvas.draw()

    def on_mouse_release(self, event):
        if self.selected_boundary == self.osc_boundary_start:
            seg_start(self.labels, self.i, event.xdata)
        elif self.selected_boundary == self.osc_boundary_stop:
            seg_stop(self.labels, self.i, event.xdata)
        if self.selected_boundary:
            self.selected_boundary.set_color('r')
            self.update_syl_boundaries()
        self.selected_boundary = None
        self.figure.canvas.draw()

    def inc_i(self):
        "Go to next syllable."
        if self.i < len(self.labels) - 1:
            self.i += 1
        self.update_plot_data()

    def dec_i(self):
        "Go to previous syllable."
        if self.i > 0:
            self.i -= 1
        self.update_plot_data()

    def on_key_press(self, event):
        #print('you pressed ', event.key)
        if event.key in ('pagedown', ' '):
            self.inc_i()
        elif event.key in ('pageup', 'backspace'):
            self.dec_i()
        elif event.key in self.shortcuts:
            newlabel = self.shortcuts[event.key]
            seg_name(self.labels, self.i, newlabel)
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
        elif event.key == 'ctrl+m':
            seg_merge_prev(self.labels, self.i)
            self.update_plot_data()
        elif event.key == 'ctrl+x':
            seg_delete(self.labels, self.i)
            self.update_plot_data()

    def save(self):
        "Writes out labels to file."
        import pandas as pd
        label_data = pd.DataFrame(self.labels)
        bark.write_events(self.outfile, label_data, **self.label_attrs)
        print(self.outfile, "written")


def build_shortcut_map(mapfile=None):
    allkeys = string.digits + string.ascii_letters
    shortcut_map = {x: x for x in allkeys}
    # load keys from file
    if mapfile:
        custom = {str(key): value
                  for key, value in yaml.load(open(mapfile, 'r')).items()}
        print("custom keymaps:", custom)
        shortcut_map.update(custom)
    return shortcut_map


def main(datfile, labelfile, outfile, shortcutfile=None):
    sampled = bark.read_sampled(datfile)
    assert sampled.attrs['n_channels'] == 1
    labels = bark.read_events(labelfile)
    shortcuts = build_shortcut_map(shortcutfile)
    #f, (osc_ax, spec_ax) = plt.subplots(2, 1, sharex=True)
    f = plt.figure()
    osc_ax = plt.subplot2grid((7, 1), (0, 0), rowspan=3)
    spec_ax = plt.subplot2grid((7, 1), (3, 0), rowspan=3, sharex=osc_ax)
    map_ax = plt.subplot2grid((7, 1), (6, 0))
    f.tight_layout()
    reviewer = SegmentReviewer(f, osc_ax, spec_ax, map_ax, sampled, labels,
                               shortcuts, outfile)
    reviewer.connect()
    plt.show()
    response = input("Save to file {}? ".format(outfile))
    if response.lower() in ('y', 'yes', 'obvs bro'):
        reviewer.save()


def _run():
    import argparse

    p = argparse.ArgumentParser(description="""
    Review and annotate segments
    """)
    p.add_argument("dat", help="name of a sampled dataset")
    p.add_argument("-l",
                   "--labelfile",
                   required=True,
                   help="associated event dataset containing segments")
    p.add_argument("-o", "--out", help="output label file", required=True)
    p.add_argument("-k",
                   "--shortcut-keys",
                   help="""YAML file with keyboard shortcuts.
        Keys are digits, lowercase and uppercase characters""")

    args = p.parse_args()
    main(args.dat, args.labelfile, args.out, args.shortcut_keys)


if __name__ == "__main__":
    _run()
