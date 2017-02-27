from scipy.signal import fftconvolve
from scipy.signal import filtfilt, butter
import os.path
import pytest
from bark.stream import Stream, read
import bark
import numpy as np

eq = np.allclose

data1 = np.arange(30).reshape(10, 3)
data2 = np.arange(500).reshape(100, 5)
data3 = np.arange(1000).reshape(500, 2)
data4 = np.arange(11111).reshape(-1, 1)
def dummyf(x): return x


def test_stream():
    stream = Stream(data1, sr=10)
    assert eq(data1, stream.call())
    assert eq(data2, Stream(data2, sr=10).call())
    assert eq(data3, Stream(data3, sr=10).call())


def test_stream_chunksize():
    stream = Stream(data1, sr=10, chunksize=3)
    assert eq(data1, stream.call())


def test_stream_add():
    stream = Stream(data1, sr=10, chunksize=3)
    stream2 = stream + 4
    assert eq(data1 + 4, stream2.call())


def test_stream_subtract():
    stream = Stream(data1, sr=10, chunksize=3)
    stream2 = stream - 4
    assert eq(data1 - 4, stream2.call())


def test_stream_multiply():
    stream = Stream(data1, sr=10, chunksize=3)
    stream2 = stream * 4
    assert eq(data1 * 4, stream2.call())


def test_stream_divide():
    stream = Stream(data1, sr=10, chunksize=3)
    stream2 = stream / 4
    assert eq(data1 / 4, stream2.call())


def test_stream_floor_divide():
    stream = Stream(data1, sr=10, chunksize=3)
    stream2 = stream // 4
    assert eq(data1 // 4, stream2.call())


def test_stream_stream_subtract():
    stream = Stream(data1, sr=10, chunksize=3)
    stream2 = Stream(data1, sr=10, chunksize=3)
    assert eq(data1 - data1, (stream - stream2).call())


def test_stream_stream_mult():
    stream = Stream(data1, sr=10, chunksize=3)
    stream2 = Stream(data1, sr=10, chunksize=3)
    assert eq(data1 * data1, (stream * stream2).call())


def test_stream_stream_div():
    stream = Stream(data1 + 100, sr=10, chunksize=3)
    stream2 = Stream(data1, sr=10, chunksize=3)
    assert eq((data1 + 100) / data1, (stream / stream2).call())


def test_stream_stream_floordiv():
    stream = Stream(data1 + 100, sr=10, chunksize=3)
    stream2 = Stream(data1, sr=10, chunksize=3)
    assert eq((data1 + 100) // data1, (stream // stream2).call())


def test_stream_stream_add():
    stream = Stream(data1, sr=10, chunksize=3)
    stream2 = Stream(data1, sr=10, chunksize=3)
    assert eq(data1 + data1, (stream + stream2).call())


def test_stream_chaining():
    stream = Stream(data1, sr=10, chunksize=3)
    stream2 = stream + 4
    stream3 = stream2 + 3
    assert eq(data1 + 7, stream3.call())


def test_map():
    assert eq(data1, Stream(data1, sr=1).map(dummyf).call())
    assert eq(data1 + 1, Stream(data1, sr=1).map(lambda x: x + 1).call())
    for data in (data1, data2, data3, data4):
        assert eq(data, Stream(data, sr=1).map(dummyf).call())


def test_reduce_columns_by_map():
    myf = lambda x: np.mean(x, 1).reshape(-1, 1)
    assert eq(myf(data1), Stream(data1, sr=1).map(myf).call())


def test_vector_map():
    for data in (data1, data2, data3, data4):
        y = Stream(data, sr=1, chunksize=6).vector_map(dummyf).call()
        assert eq(data, y)


def test_vector_map2():
    for data in (data1, data2, data3, data4):
        y = Stream(data, sr=1, chunksize=7).vector_map(dummyf).call()
        assert eq(data, y)


def test_vector_map3():
    data = np.arange(2503107).reshape(-1, 1)
    y = Stream(data, sr=30000, chunksize=2e6).vector_map(dummyf).call()
    assert eq(data, y)


def test_filtfilt():
    sr = 1000
    freq = 100
    b, a = butter(3, freq / (sr / 2), 'high')
    for data in (data2, data3, data4):
        x = filtfilt(b, a, data, axis=0)
        y = Stream(data, chunksize=211, sr=sr).filtfilt(b, a).call()
        assert eq(x, y)


def test_convolve():
    win = [.1, 0, 3]
    for data in (data2, data3, data4):
        x = np.column_stack([fftconvolve(data[:, i], win)
                             for i in range(data.shape[1])])
        y = Stream(data, sr=1).convolve(win).call()
        assert eq(x, y)


def test_decimate():
    for data in (data2, data3, data4):
        x = data[::3]
        y = Stream(data, sr=1).decimate(3).call()
        assert eq(x, y)


def test_getitem():
    columns = {i: {'units': None, 'name': str(i)} for i in range(5)}
    y = Stream(data1, sr=1, attrs={'columns': columns})[-1:].call()
    assert eq(data1[:, -1].reshape(-1, 1), y)
def test_getitem2():
    columns = {i: {'units': None, 'name': str(i)} for i in range(5)}
    y = Stream(data1, sr=1, attrs={'columns': columns})[-1].call()
    assert eq(data1[:, -1].reshape(-1, 1), y)
def test_getitem3():
    columns = {i: {'units': None, 'name': str(i)} for i in range(5)}
    y = Stream(data1, sr=1, attrs={'columns': columns})[0, -1].call()
    assert eq(data1[:, [0, -1]], y)


def test_split():
    columns = {i: {'units': None, 'name': str(i)} for i in range(5)}
    attrs = {'columns': columns}
    s = Stream(data2, sr=1, attrs=attrs).split(1, 3)
    y = s.call()
    assert eq(data2[:, (1, 3)], y)
    assert len(s.attrs['columns']) == 2
    assert s.attrs['columns'][0]['name'] == '1'
    assert s.attrs['columns'][1]['name'] == '3'



def test_rechunk():
    assert eq(data1, Stream(data1, sr=1, chunksize=10).rechunk(11).call())
    assert eq(data1, Stream(data1, sr=1, chunksize=12).rechunk(11).call())


def test_rechunk2():
    assert eq(data3, Stream(data3, sr=1, chunksize=12).rechunk(1).call())
    assert eq(data3, Stream(data3, sr=1, chunksize=12).rechunk(1000000).call())


def test_merge():
    assert eq(
        np.hstack((data1, data1)),
        Stream(data1,
               sr=1,
               chunksize=10).merge(Stream(data1,
                                          sr=1,
                                          chunksize=10)).call())

    assert eq(
        np.hstack((data1, data1)),
        Stream(data1,
               sr=1,
               chunksize=10).merge(Stream(data1,
                                          sr=1,
                                          chunksize=11)).call())
def test_merge_columns():
    dat1 = np.arange(20).reshape(10,2)
    dat1attrs = {'columns': {0: {'units': None, 'name': 'a'},
                            1: {'units': None, 'name': 'b'}}}
    dat2 = np.arange(10).reshape(10,1)
    dat2attrs = {'columns': {0: {'units': None, 'name': 'c'}}}
    s1 = Stream(dat1, sr=1, attrs=dat1attrs)
    s2 = Stream(dat2, sr=1, attrs=dat2attrs)
    s3 = s1.merge(s2)
    for index, name in zip(range(3), 'abc'):
        assert s3.attrs['columns'][index]['name'] == name


def test_peek():
    data = np.arange(10).reshape(5,2)
    s = Stream(data, chunksize=3)
    xpeek = s.peek()
    assert eq(xpeek, data[:3, :])
    xfull = s.call()
    assert eq(xfull, data)




def test_chain():
    assert eq(
        np.vstack((data1, data1)),
        Stream(data1,
               sr=1,
               chunksize=5).chain(Stream(data1,
                                         sr=1,
                                         chunksize=6)).call())


def test_write(tmpdir):
    fname = os.path.join(tmpdir.strpath, "mydat")
    columns = bark.sampled_columns(data1)
    attrs = dict(sampling_rate=100, columns=columns, fluffy="cat")
    a = Stream(data1, attrs=attrs)
    a.write(fname)
    sdataset = bark.read_sampled(fname)
    sdata = sdataset.data
    assert eq(data1, sdata)
    sattrs = sdataset.attrs
    for key in attrs:
        assert attrs[key] == sattrs[key]


def test_write_read(tmpdir):
    fname = os.path.join(tmpdir.strpath, "mydat")
    columns = bark.sampled_columns(data1)
    attrs = dict(sampling_rate=100, columns=columns, fluffy="cat")
    a = Stream(data1, attrs=attrs)
    a.write(fname)
    b = read(fname)
    assert eq(data1, b.call())
    for key in attrs:
        assert attrs[key] == b.attrs[key]
