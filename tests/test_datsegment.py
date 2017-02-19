import numpy as np
from bark.tools import datsegment


def test_first_pass1():
    amp_stream = [(0, 0), (1, 1), (2, 1), (3, 1), (4, 0), (5, 0), (6, 11),
                  (7, 0)]
    thresh = 0.5
    starts, stops = datsegment.first_pass(amp_stream, thresh)
    assert starts == [1, 6]
    assert stops == [4, 7]


def test_first_pass2():
    # check behavior if systems ends on a syll
    amp_stream = [(0, 0), (1, 1), (2, 1), (3, 1), (4, 0), (5, 0), (6, 11),
                  (7, 1)]
    thresh = 0.5
    starts, stops = datsegment.first_pass(amp_stream, thresh)
    assert starts == [1, 6]
    assert stops == [4, 7]


def test_first_pass3():
    # check behavior if systems starts on a syll
    amp_stream = [(0, 1), (1, 1), (2, 0), (3, 0), (4, 0), (5, 0), (6, 0),
                  (7, 0)]
    thresh = 0.5
    starts, stops = datsegment.first_pass(amp_stream, thresh)
    assert starts == [0]
    assert stops == [2]


def test_third_pass1():
    # third syl should be removed
    starts = [0, 5, 6, 8]
    stops = [1, 5.4, 6.1, 10]
    min_syl = 0.2
    datsegment.third_pass(starts, stops, min_syl)
    assert len(starts) == 3
    assert len(stops) == 3
    assert starts == [0, 5, 8]
    assert stops == [1, 5.4, 10]


def test_third_pass2():
    # first syl should be removed
    starts = [0, 5, 6, 8]
    stops = [.1, 5.4, 7, 10]
    min_syl = 0.2
    datsegment.third_pass(starts, stops, min_syl)
    assert len(starts) == 3
    assert len(stops) == 3
    assert starts == [5, 6, 8]
    assert stops == [5.4, 7, 10]


def test_third_pass3():
    # first two syls should be removed
    starts = [0, 5, 6, 8]
    stops = [.1, 5.1, 7, 10]
    min_syl = 0.2
    datsegment.third_pass(starts, stops, min_syl)
    assert len(starts) == 2
    assert len(stops) == 2
    assert starts == [6, 8]
    assert stops == [7, 10]


def test_second_pass1():
    # last syl should be combined with second to last
    starts = [0, 5, 6, 8]
    stops = [1, 5.4, 7.9, 10]
    min_syl = 0.2
    datsegment.second_pass(starts, stops, min_syl)
    assert len(starts) == 3
    assert len(stops) == 3
    assert starts == [0, 5, 6]
    assert stops == [1, 5.4, 10]


def test_second_pass2():
    # first syl should be combined with second
    starts = [0, 5, 6, 8]
    stops = [4.95, 5.4, 7.8, 10]
    min_syl = 0.1
    datsegment.second_pass(starts, stops, min_syl)
    assert len(starts) == 3
    assert len(stops) == 3
    assert starts == [0, 6, 8]
    assert stops == [5.4, 7.8, 10]


def test_second_pass3():
    # all syls should be combined
    starts = [0, 5, 6, 8]
    stops = [0.495, 5.4, 7.8, 10]
    min_syl = 100
    datsegment.second_pass(starts, stops, min_syl)
    assert len(starts) == 1
    assert len(stops) == 1
    assert starts == [0]
    assert stops == [10]
