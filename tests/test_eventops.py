import pytest
from bark.io.eventops import (OpStack, New, Update, Merge, Delete, Split,
                              write_stack, read_stack)


@pytest.fixture
def labels():
    return [{'name': 'a',
             'start': 0,
             'stop': 1},
            {'name': 'b',
             'start': 2,
             'stop': 3},
            {'name': 'c',
             'start': 4,
             'stop': 5}, ]


@pytest.fixture
def opstack(labels):
    return OpStack(labels)


@pytest.fixture
def tempfile(tmpdir):
    return str(tmpdir.join('temp.yaml'))


def test_new(labels):
    New(2, 'b2', 3.1, 3.6).on(labels)
    assert (len(labels) == 4)
    assert labels[1]['name'] == 'b'
    assert labels[2]['start'] == 3.1
    assert labels[2]['stop'] == 3.6
    assert labels[2]['name'] == 'b2'
    assert labels[3]['name'] == 'c'


def test_name(labels):
    Update(0, 'name', 'a2').on(labels)
    assert labels[0]['name'] == 'a2'


def test_start(labels):
    Update(1, 'start', 100).on(labels)
    assert labels[1]['start'] == 100


def test_stop(labels):
    Update(2, 'stop', 100).on(labels)
    assert labels[2]['stop'] == 100


def test_chain(labels):
    Update(2, 'stop', 100).on(labels)
    Update(1, 'start', 100).on(labels)
    assert labels[2]['stop'] == 100
    assert labels[1]['start'] == 100


def test_merge(labels):
    Merge(0).on(labels)
    assert len(labels) == 2
    assert labels[0]['name'] == 'a'
    assert labels[1]['name'] == 'c'


def test_delete(labels):
    Delete(0).on(labels)
    assert labels[0]['name'] == 'b'


def test_split(labels):
    Split(0, 0.5).on(labels)
    assert len(labels) == 4
    assert labels[1]['name'] == 'a'
    assert labels[0]['start'] == 0
    assert labels[1]['start'] == 0.5
    assert labels[0]['stop'] == 0.5
    assert labels[1]['stop'] == 1


def test_stack_push(opstack):
    opstack.push(Update(0, 'name', 'z'))
    assert len(opstack.ops) == 1
    assert opstack.events != opstack.original_events


def test_stack_undo(opstack):
    opstack.push(Update(0, 'name', 'z'))
    opstack.undo()
    assert len(opstack.ops) == 0
    assert len(opstack.undo_ops) == 1
    assert opstack.events == opstack.original_events


def test_read_write(tempfile, opstack):
    write_stack(tempfile, opstack)
    new_opstack = read_stack(tempfile)
    assert new_opstack.original_events == opstack.original_events
    assert new_opstack.events == opstack.events
    assert new_opstack.events == new_opstack.original_events


def test_read_write2(tempfile, opstack):
    opstack.push(Update(0, 'name', 'z'))
    write_stack(tempfile, opstack)
    new_opstack = read_stack(tempfile)
    assert new_opstack.original_events == opstack.original_events
    assert new_opstack.events == opstack.events
    assert new_opstack.events != new_opstack.original_events
