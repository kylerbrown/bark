import pytest
import datetime
import bark
import numpy as np
import pandas as pd
import os.path


def test_write_sampled_empty(tmpdir):
    with pytest.raises(TypeError):
        bark.write_sampled("test_sampled", sampling_rate=10, units="mV", 
                n_channels=10, dtype="int16")


def test_write_sampled(tmpdir):
    data = np.zeros((10,3),dtype="int16")
    params = dict(sampling_rate=30000, units="mV", unit_scale=0.025,
            extra="barley")
    dset = bark.write_sampled(os.path.join(tmpdir.strpath, "test_sampled"), data=data, **params)
    assert isinstance(dset, bark.SampledData)
    assert isinstance(dset.path, str)
    assert isinstance(dset.attrs, dict)
    assert isinstance(dset.data, np.memmap)


def test_read_sampled(tmpdir):
    test_write_sampled(tmpdir)  # create 'test_sampled'
    path = os.path.join(tmpdir.strpath, "test_sampled")
    assert os.path.exists(path)
    assert os.path.exists(path + ".meta")
    dset = bark.read_sampled(path)
    assert isinstance(dset, bark.SampledData)
    assert isinstance(dset.path, str)
    assert isinstance(dset.attrs, dict)
    assert isinstance(dset.data, np.memmap)
    assert np.allclose(np.zeros((10,3)), dset.data)
    assert np.allclose(dset.data.shape, (10, 3))

def test_write_events(tmpdir):
    path = os.path.join(tmpdir.strpath, "test_events")
    data = pd.DataFrame({'start': [0,1,2,3], 'stop': [1,2,3,4],
            'name': ['a','b','c','d']})
    events = bark.write_events(path, data, units='s')
    assert isinstance(events, bark.EventData)
    assert 'start' in events.data.columns
    assert 'stop' in events.data.columns
    assert 'name' in events.data.columns
    assert np.allclose([0, 1, 2, 3], events.data.start)

def test_create_root(tmpdir):
    path = os.path.join(tmpdir.strpath, "mybark")
    root = bark.create_root(path, experimenter="kjbrown",
            experiment="testbark")
    assert isinstance(root, bark.Root)
    assert root.attrs["experimenter"] == "kjbrown"
    assert root.attrs["experiment"] == "testbark"

def test_create_entry(tmpdir):
    path = os.path.join(tmpdir.strpath, "myentry")
    dtime = datetime.datetime(2020,1,1,0,0,0,0)
    entry = bark.create_entry(path, dtime, food="pizza")
    assert 'uuid' in entry.attrs
    assert dtime == bark.timestamp_to_datetime(entry.attrs["timestamp"])
    assert entry.attrs["food"] == "pizza"
