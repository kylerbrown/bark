import numpy as np
import bark
import pytest
from scipy.signal import argrelextrema
from bark.tools.datspike import main, spikes, thres_extrema, stream_spikes

data0 = np.array([[0], [1], [0], ])
data1 = np.array([[0, 0], [1, 0], [0, 0], ])


def test_thres_extrema():
    rs, = argrelextrema(data1[:, 0], lambda x, y: thres_extrema(x, y, 0.1))
    assert len(rs) == 1
    assert rs == 1


def test_spikes_1():
    spks = list(spikes(data1,
                       start_sample=0,
                       threshs=[0.1, 0.1],
                       pad_len=0,
                       order=1))
    assert len(spks) == 1
    assert spks[0][0] == 0
    assert spks[0][1] == 1


def test_stream_spikes():
    data = np.arange(100).reshape(-1, 1) % 10
    spikes = np.array(list(stream_spikes(
        bark.stream.Stream(data,
                           sr=4,
                           chunksize=6),
        threshs=[0.1],
        pad_len=5,
        order=3)))
    answer = np.arange(9, 100, 10)
    assert len(spikes) == len(answer)
    assert spikes[0][0] == 0
    assert spikes[0][1] == 9
    assert np.allclose(spikes[:, 1], np.arange(9, 100, 10))

def test_main(tmpdir):
    csvfile = str(tmpdir.join('test.csv'))
    datfile = str(tmpdir.join('test.dat'))
    data = np.arange(100).reshape(-1, 1) % 10
    bark.write_sampled(datfile, data, sampling_rate=10)
    main(datfile, csvfile, .1, 3)
    result = bark.read_events(csvfile)
    assert 'start' in result.data.columns
    assert 'channel' in result.data.columns
    assert np.allclose(result.data.start, np.arange(9, 100, 10)/10)

