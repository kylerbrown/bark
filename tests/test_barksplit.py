import pandas as pd
import bark
import random
from bark.tools import barksplit as bs
import os.path
import time
import numpy as np

def test_time_to_index():
    series = pd.Series({'start': 1.5, 'stop': 2.7, 'name': 'a'})
    attrs = {'sampling_rate': 13}
    output = bs.time_to_index(series, attrs)
    assert isinstance(output, pd.Series)
    assert isinstance(output['start'], int)
    assert isinstance(output['stop'], int)
    assert isinstance(output['name'], basestring)
    assert output['start'] == 20
    assert output['stop'] == 35
    assert output['name'] == series['name']

def test_points_to_span():
    attrs = {'n_channels': 3, 'n_samples': 31}
    def common(pts, attrs):
        output = bs.points_to_span(pts, attrs)
        assert isinstance(output, pd.DataFrame)
        assert 'start' in output
        assert 'stop' in output
        assert 'name' in output
        assert len(output) == 5
        assert output['start'][0] == 0
        assert output['start'][1] == 7
        assert output['stop'][4] == 93
        assert output['stop'][3] == 89
        assert output['name'][0] == ''
    # points includes neither start nor end of interval
    points = [7, 19, 53, 89]
    common(points, attrs)
    # points includes start of interval
    points = [0, 7, 19, 53, 89]
    common(points, attrs)
    # points includes end of interval
    points = [7, 19, 53, 89, 93]
    common(points, attrs)
    # points includes both start and end of interval
    points = [0, 7, 19, 53, 89, 93]
    common(points, attrs)

def test_label_to_splits():
    def common(output):
        assert isinstance(output, pd.DataFrame)
        assert 'start' in output
        assert 'stop' in output
        assert 'name' in output

    path = 'not/a/real/path'
    sdata = np.array(random.sample(xrange(100), 93)).reshape(-1, 3)
    sattrs = {'sampling_rate': 13, 'n_samples': 31, 'n_channels': 3}
    samp = bark.SampledData(sdata, path, sattrs)
    edata = pd.DataFrame({'start': [0.54, 1.46, 4.08, 6.85],
                              'name': ['a', 'b', 'a', 'c']})
    event = bark.EventData(edata, path, {})
    # point mode, split_on empty
    split_on = ''
    output = bs.label_to_splits(samp, event, split_on, point_mode=True)
    common(output)
    assert len(output['start']) == 5
    assert output['start'][0] == 0
    assert output['start'][1] == 7
    assert output['stop'][4] == 93
    assert output['stop'][3] == 89
    assert output['name'][0] == ''
    # interval mode, split_on empty
    edata['stop'] = [.77, 2.31, 6.15, 6.92]
    event = bark.EventData(edata, path, {})
    output = bs.label_to_splits(samp, event, split_on, point_mode=False)
    common(output)
    assert len(output['start']) == 4
    assert output['start'][0] == 7
    assert output['stop'][0] == 10
    assert output['name'][0] == event.data['name'][0]
    assert output['start'][1] == 19
    assert output['stop'][1] == 30
    assert output['name'][1] == event.data['name'][1]
    # interval mode, split_on given
    split_on = 'a'
    output = bs.label_to_splits(samp, event, split_on, point_mode=False)
    common(output)
    assert len(output['start']) == 2
    assert output['start'][0] == 7
    assert output['stop'][0] == 10
    assert output['name'][0] == event.data['name'][0]
    assert output['start'][1] == 53
    assert output['stop'][1] == 80
    assert output['name'][1] == event.data['name'][2]

def test_gen_split_files(tmpdir):
    entry_path = tmpdir
    spath = os.path.join(tmpdir.strpath, 'data.dat')
    sdata = np.array(random.sample(xrange(100), 93)).reshape(-1, 3)
    sattrs = {'sampling_rate': 13, 'n_samples': 31, 'n_channels': 3}
    samp = bark.SampledData(sdata, spath, sattrs)
    epath = os.path.join(tmpdir.strpath, 'times.csv')
    edata = pd.DataFrame({'start': [0.18, 0.49, 1.36, 2.28],
                              'name': ['a', 'b', 'a', 'c']})
    event = bark.EventData(edata, epath, {})
    entry = bark.Entry([samp, event],
                       entry_path,
                       {'uuid': 1, 'timestamp': [time.time(), 0]})
    split_on = ''
    pmode = True
    splits = bs.label_to_splits(samp, event, split_on, pmode)
    output = bs.gen_split_files(entry, samp, event, splits, split_on, pmode)
    assert len(output) == len(splits)
    for f in output:
        assert os.path.exists(f.path)
        assert os.path.exists(f.path + '.meta')
        fromfile = bark.read_sampled(f.path)
        assert (fromfile.data == f.data).all()
        index = int(fromfile.attrs['split_num'])
        this_split = splits.loc[index]
        assert (fromfile.data ==
                sdata[this_split['start']:this_split['stop'],:]).all()
