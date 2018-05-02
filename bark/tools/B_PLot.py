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
from bark.tools.spectral import BarkSpectra


help_string = '''

Shortcuts
---------
any letter or number    annotate segment
up arrow      zoom out
down arrow    zoom in
up left       move left
down right    move right
click on map to move through the graphic
drag the graphic to move the graphic

'''

zoom_size = 50000

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


class Plot:
    def __init__(self,
                 ax, 
                 sampled):
        
        self.ax = ax
        self.data = sampled.data.ravel()
        self.sr = sampled.sampling_rate

    def update_x_axis(self,start,stop):
        self.ax.set_xlim(start,stop)

    def clear_plot(self):
        self.ax.cla()
   
    '''
    class Osc_Plot

    parameter:

    ax : axis object to plot spectrogram on
    sampled : the data read from .dat file including sound data and sample rate
    opstack : the opstack stack contains label information

    '''
class Osc_Plot(Plot):
    def __init__(self,
                 ax, 
                 sampled):
        Plot.__init__(self,ax,sampled)
        self.N_points = 35000
        self.ax.set_axis_bgcolor('k')
        self.ax.tick_params(axis='x',
                                which='both',
                                bottom='off',
                                top='off',
                                labelbottom='off')
        self.osc_line, = self.ax.plot(
            np.arange(self.N_points),
            np.zeros(self.N_points),
            color='gray')
        self.ax.figure.tight_layout()

    def update_oscillogram(self,buf_start,buf_stop):
        self.selected_boundary = None
        self.buffer_start_samp = buf_start
        self.buffer_stop_samp = buf_stop
        self.buf_start = self.buffer_start_samp / self.sr
        self.buf_stop = self.buffer_stop_samp / self.sr
        self.update_oscillo()


    def update_oscillo(self):

        x = self.data[self.buffer_start_samp:self.buffer_stop_samp]
        t = np.arange(len(x)) / self.sr + self.buf_start
        if len(x) > 10000:
            t_interp = np.linspace(self.buf_start, self.buf_stop, 10000)
            x_interp = np.interp(t_interp, t, x)
        else:
            t_interp = t
            x_interp = x
        self.osc_line.set_data(t_interp, x_interp)
        self.ax.set_xlim(self.buf_start, self.buf_stop)
        self.ax.set_ylim(min(x), max(x))

    '''
    class Spec_Plot
    
    parameter:

    ax : axis object to plot spectrogram on
    sampled : the data read from .dat file including sound data and sample rate

    '''

class Spec_Plot(Plot):
    def __init__(self,
                 ax, 
                 sampled):
        Plot.__init__(self,ax,sampled)
        self.ax.set_axis_bgcolor('k')

    def update_spectrogram(self,start,stop):
        self.ax.clear()
        self.plot_spectrogram(self.data,
                         self.sr,
                         start,
                         stop,
                         ax=self.ax)
        self.ax.set_xlim(start, stop)
    
    def plot_spectrogram(self,data,
                     sr,
                     start,
                     stop,
                     ms_nfft=15,
                     ax=None,
                     lowfreq=300,
                     highfreq=8000,
                     n_tapers=2,
                     NW=1.5,
                     derivative=True,
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
        n_tapers : Number of tapers to use in a custom multi-taper Fourier
                   transform estimate
        NW : multi-taper bandwidth parameter for custom multi-taper Fourier
             transform estimate increasing this value reduces side-band
             ripple, decreasing sharpens peaks
        derivative: if True, plots the spectral derivative, SAP style

        '''
        nfft = int(ms_nfft / 1000. * sr)
        start_samp = int(start * sr) - nfft // 2
        if start_samp < 0:
            start_samp = 0
        stop_samp = int(stop * sr) - nfft // 2
        x = data[start_samp:stop_samp]

        # determine overlap based on screen size.
        # We don't need more points than pixels
        pixels = 1000
        samples_per_pixel = int((stop - start) * sr / pixels)
        noverlap = max(nfft - samples_per_pixel, 0)
        
        from matplotlib import colors
        
        spa = BarkSpectra(sr, 
                        NFFT=nfft, 
                        noverlap=noverlap, 
                        data_window=int(0.01 * sr), 
                        n_tapers=n_tapers, 
                        NW=NW,
                        freq_range=(lowfreq, highfreq))
        spa.signal(x)
        pxx, f, t, thresh = spa.spectrogram(ax=ax, derivative=derivative)  

        # calculate the parameter for the plot 
        freq_mask = (f > lowfreq) & (f < highfreq)
        fsub = f[freq_mask]
        Sxxsub = pxx[freq_mask, :]
        t += start
        
        # plot the spectrogram 
        if derivative:
            image = ax.pcolorfast(t,
                          fsub,
                          Sxxsub,
                          cmap='inferno',
                          norm=colors.SymLogNorm(linthresh=thresh)) 
        else:
            image = ax.pcolorfast(t,
                              fsub,
                              Sxxsub,
                              cmap='inferno',
                              norm=colors.LogNorm(vmin=thresh))

        plt.sca(ax)
        plt.ylim(lowfreq, highfreq)
        return image
    
    '''
    class Minimap_Plot

    parameter:

    ax : axis object to plot spectrogram on
    opstack : the opstack stack contains label information

    '''

class Minimap_Plot:

    def __init__(self,
                 ax, 
                 max_time):
        self.max_time =  max_time
        self.ax = ax 
        self.ax.set_axis_bgcolor('k')
        self.ax.tick_params(axis='y',
                                which='both',
                                left='off',
                                right='off',
                                labelleft='off')
        self.ax.set_xlim(0, self.max_time)     
        self.current = self.ax.axvline(color='r')
    def update_minimap(self, x_Data):
        self.current.set_xdata((x_Data, x_Data))





class SegmentReviewer:
    def __init__(self,
                 osc_ax,
                 spec_ax,
                 map_ax,
                 sampled):
        self.canvas = osc_ax.get_figure().canvas

        self.osc = Osc_Plot(ax = osc_ax, sampled = sampled)

        self.spec = Spec_Plot(ax = spec_ax, sampled = sampled)

        self.data = sampled.data.ravel()
        self.sr = sampled.sampling_rate
        self.max_time =int(round(len(self.data)/self.sr)) 
        self.N_points = 300000
        self.window_size = self.N_points/self.sr
        self.start = 0
        self.stop = self.window_size
        self.press_flag = 0
        zoom_size =  self.sr*5
        self.map = Minimap_Plot(ax = map_ax, max_time = self.max_time)

        self.update_plot_data()


    def update_plot_data(self):
        'updates plot data on all three axes'
        sr = self.sr
        start_samp = int(self.start * sr)
        stop_samp = int(self.stop * sr) 
        syl_samps = stop_samp - start_samp
        self.buffer_start_samp = start_samp - (self.N_points - syl_samps) // 2
        if self.buffer_start_samp < 0:
            self.buffer_start_samp = 0
        self.buffer_stop_samp = self.buffer_start_samp + self.N_points

        if self.buffer_stop_samp >= self.data.shape[0]:
            self.buffer_stop_samp = self.data.shape[0] - 1

        self.buf_start = self.buffer_start_samp / sr
        self.buf_stop = self.buffer_stop_samp / sr
        
        self.spec.update_spectrogram(self.buf_start,self.buf_stop)
        self.osc.update_oscillogram(self.buffer_start_samp,self.buffer_stop_samp)
        self.map.update_minimap((self.start+self.stop)/2)

        self.canvas.draw()

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
        if event.inaxes == self.map.ax:
            self.start = event.xdata - self.window_size/2
            self.stop = self.start + self.window_size
            if self.start < 0:
                self.start = 0
                self.stop = self.window_size
            if self.stop > self.max_time:
                self.start = self.max_time - self.window_size
                self.stop = self.max_time
            self.update_plot_data()
        if event.inaxes in (self.osc.ax, self.spec.ax):
            self.press_x = event.xdata
            self.press_flag = 1
        self.canvas.draw()

    def on_mouse_motion(self, event):
        self.canvas.draw()

    def on_mouse_release(self, event):
        if event.inaxes in (self.osc.ax, self.spec.ax) and self.press_flag == 1:
            self.start -= (event.xdata - self.press_x)
            self.stop = self.start + self.window_size
            if self.stop > self.max_time:
                self.start = self.stop - self.window_size
                self.stop = self.start
            if self.start < 0:
                self.start = 0
                self.stop = self.window_size
            self.update_plot_data()
            self.press_flag = 0
            self.canvas.draw()

    def inc_i(self):
        self.start += self.window_size/2
        self.stop = self.start + self.window_size
        if self.stop > self.max_time:
            self.start = self.stop - self.window_size
            self.stop = self.start
        self.update_plot_data()

    def dec_i(self):
        self.start -= self.window_size/2
        self.stop = self.start - self.window_size
        if self.start < 0:
            self.start = 0
            self.stop = self.window_size
        self.update_plot_data()

    def on_key_press(self, event):
        # print('you pressed ', event.key)
        if event.key in ('pagedown', ' ', 'right'):
            self.inc_i()
        elif event.key in ('pageup', 'backspace', 'left'):
            self.dec_i()
        elif event.key in ('ctrl+i', 'down'):
            if self.N_points > zoom_size:
                self.N_points -= zoom_size
                self.stop = self.start + self.window_size
                self.window_size = self.N_points/self.sr
                self.update_plot_data()
        elif event.key in ('ctrl+o', 'up'):
            if self.N_points - zoom_size < self.max_time * self.sr :
                self.N_points += zoom_size
                self.window_size = self.N_points/self.sr
                self.stop = self.start + self.window_size
                self.update_plot_data()


    def __enter__(self):
        return self

    def __exit__(self, *args):
        return 0


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




def main(datfile):
    
    kill_shortcuts(plt)
    sampled = bark.read_sampled(datfile)
    # assert len(sampled.attrs['columns']) == 1
    plt.figure()
    # Oscillogram and Spectrogram get
    osc_ax = plt.subplot2grid((7, 1), (0, 0), rowspan=3)
    spec_ax = plt.subplot2grid((7, 1), (3, 0), rowspan=3, sharex=osc_ax)
    map_ax = plt.subplot2grid((7, 1), (6, 0), rowspan=1)

    # Segement review is a context manager to ensure a save prompt
    # on exit. see SegmentReviewer.__exit__
    with SegmentReviewer(osc_ax, spec_ax, map_ax, sampled) as reviewer:
        reviewer.connect()
        plt.show(block=True)


def _run():
    import argparse

    p = argparse.ArgumentParser(description='''
    Review and annotate segments
    ''')
    p.add_argument('dat', help='name of a sampled dataset')

    args = p.parse_args()
    main(args.dat)


if __name__ == '__main__':
    _run()
