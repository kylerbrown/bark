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
dummyf = lambda x: x


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
        y = Stream(data, sr=1).vector_map(dummyf).call()
        assert eq(data, y)


def test_getitem():
    y = Stream(data1, sr=1)[-1].call()
    assert eq(data1[:, -1], y)
    y = Stream(data1, sr=1)[-1].call()
    assert eq(data1[:, -1], y)


def test_split():
    y = Stream(data2, sr=1).split(1, 3).call()
    assert eq(data2[:, (1, 3)], y)


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


def test_chain():
    assert eq( np.vstack((data1, data1)),
            Stream(data1, sr=1, chunksize=5).chain(Stream(data1,
                sr=1, chunksize=6)).call())



def test_write(tmpdir):
    fname = os.path.join(tmpdir.strpath, "mydat")
    attrs = dict(sampling_rate=100, n_channels=data1.shape[1], fluffy="cat")
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
    attrs = dict(sampling_rate=100, n_channels=data1.shape[1], fluffy="cat")
    a = Stream(data1, attrs=attrs)
    a.write(fname)
    b = read(fname)
    assert eq(data1, b.call())
    for key in attrs:
        assert attrs[key] == b.attrs[key]
        


