import pytest
from bark.datutils import Stream
import numpy as np

data1 = np.arange(30).reshape(10, 3)
data2 = np.arange(500).reshape(100, 5)
data3 = np.arange(1000).reshape(500, 2)
data4 = np.arange(11111).reshape(-1, 1)
dummyf = lambda x: x


def test_stream():
    stream = Stream(data1, sr=10)
    assert np.allclose(data1, stream.call())
    assert np.allclose(data2, Stream(data2, sr=10).call())
    assert np.allclose(data3, Stream(data3, sr=10).call())


def test_stream_chunksize():
    stream = Stream(data1, sr=10, chunksize=3)
    assert np.allclose(data1, stream.call())


def test_stream_add():
    stream = Stream(data1, sr=10, chunksize=3)
    stream2 = stream + 4
    assert np.allclose(data1 + 4, stream2.call())


def test_stream_subtract():
    stream = Stream(data1, sr=10, chunksize=3)
    stream2 = stream - 4
    assert np.allclose(data1 - 4, stream2.call())


def test_stream_multiply():
    stream = Stream(data1, sr=10, chunksize=3)
    stream2 = stream * 4
    assert np.allclose(data1 * 4, stream2.call())


def test_stream_divide():
    stream = Stream(data1, sr=10, chunksize=3)
    stream2 = stream / 4
    assert np.allclose(data1 / 4, stream2.call())


def test_stream_floor_divide():
    stream = Stream(data1, sr=10, chunksize=3)
    stream2 = stream // 4
    assert np.allclose(data1 // 4, stream2.call())


def test_stream_chaining():
    stream = Stream(data1, sr=10, chunksize=3)
    stream2 = stream + 4
    stream3 = stream2 + 3
    assert np.allclose(data1 + 7, stream3.call())


def test_map():
    assert np.allclose(data1, Stream(data1, sr=1).map(dummyf).call())
    assert np.allclose(data1 + 1,
                       Stream(data1,
                              sr=1).map(lambda x: x + 1).call())
    for data in (data1, data2, data3, data4):
        assert np.allclose(data, Stream(data, sr=1).map(dummyf).call())


def test_reduce_columns_by_map():
    myf = lambda x: np.mean(x, 1).reshape(-1, 1)
    assert np.allclose(myf(data1), Stream(data1, sr=1).map(myf).call())


def test_vector_map():
    for data in (data1, data2, data3, data4):
        y = Stream(data, sr=1).vector_map(dummyf).call()
        assert np.allclose(data, y)


def test_getitem():
    y = Stream(data1, sr=1)[-1].call()
    assert np.allclose(data1[:, -1], y)
    y = Stream(data1, sr=1)[-1].call()
    assert np.allclose(data1[:, -1], y)


def test_split():
    y = Stream(data2, sr=1).split(1, 3).call()
    assert np.allclose(data2[:, (1, 3)], y)


def test_rechunk():
    assert np.allclose(data1,
                       Stream(data1,
                              sr=1,
                              chunksize=10).rechunk(11).call())
    assert np.allclose(data1,
                       Stream(data1,
                              sr=1,
                              chunksize=12).rechunk(11).call())


def test_rechunk2():
    assert np.allclose(data3,
                       Stream(data3,
                              sr=1,
                              chunksize=12).rechunk(1).call())
    assert np.allclose(data3,
                       Stream(data3,
                              sr=1,
                              chunksize=12).rechunk(1000000).call())


def test_merge():

    assert np.allclose(
        np.hstack((data1, data1)),
        Stream(data1,
               sr=1,
               chunksize=10).merge(Stream(data1,
                                          sr=1,
                                          chunksize=10)).call())
