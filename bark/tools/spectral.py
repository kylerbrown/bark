from resin import Spectra
from resin.spectral_analysis import value_from_dB
import numpy as np



class BarkSpectra(Spectra):
    def spectrogram(self,
                  ax=None,
                  freq_range=None,
                  dB_thresh=35,
                  derivative=True,
                  colormap='inferno'):
      """Plots a spectrogram, requires matplotlib
      ax - axis on which to plot
      freq_range - a tuple of frequencies, eg (300, 8000)
      dB_thresh  - noise floor threshold value, increase to suppress noise,
                   decrease to improve detail
      derivative - if True, plots the spectral derivative, SAP style
      colormap   - colormap to use, good values: 'inferno', 'gray'

      Returns max spectral derivative, freqs, times, thresh
      """
      from matplotlib import colors
      if ax is None:
          import matplotlib.pyplot as plt
          ax = plt.gca()
      if derivative:
          pxx, f, t = self.max_spec_derivative(freq_range=freq_range)
          thresh = value_from_dB(dB_thresh, np.max(pxx))
      else:
          pxx, f, t = self.power(freq_range)
          thresh = value_from_dB(dB_thresh, np.max(pxx))
      return pxx, f, t, thresh




