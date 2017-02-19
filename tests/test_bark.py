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

def test_read_dataset(tmpdir):
    path = os.path.join(tmpdir.strpath, 'test_events')
    data = pd.DataFrame({'start': [0,1,2,3], 'stop': [1,2,3,4],
                         'name': ['a', 'b', 'c', 'd']})
    event_written = bark.write_events(path, data, units='s')
    event_read = bark.read_dataset(path)
    assert event_read.attrs['units'] == 's'
    
    path = os.path.join(tmpdir.strpath, 'test_samp')
    data = np.zeros((10,3),dtype="int16")
    params = {'sampling_rate': 30000, 'units': 'mV', 'unit_scale': 0.025}
    samp_written = bark.write_sampled(path, data=data, **params)
    samp_read = bark.read_dataset(path)
    assert samp_read.attrs['units'] == params['units']

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

def test_entry_sort(tmpdir):
    path1 = os.path.join(tmpdir.strpath, "myentry")
    dtime1 = datetime.datetime(2020,1,1,0,0,0,0)
    entry1 = bark.create_entry(path1, dtime1, food="pizza")
    path2 = os.path.join(tmpdir.strpath, "myentry2")
    dtime2 = datetime.datetime(2021,1,1,0,0,0,0)
    entry2 = bark.create_entry(path2, dtime2, food="pizza")
    mylist = sorted([entry2, entry1])
    assert mylist[0] == entry1
    assert mylist[1] == entry2

def test_datatypes():
    assert bark.DATATYPES.name_to_code['UNDEFINED'] == 0
    assert bark.DATATYPES.name_to_code['EVENT'] == 1000
    assert bark.DATATYPES.code_to_name[1] == 'ACOUSTIC'
    assert bark.DATATYPES.code_to_name[2002] == 'COMPONENTL'
    assert bark.DATATYPES.code_to_name[None] is None
