import pytest
import copy
import eventedit.eventedit as eved
import os
import tempfile
import yaml

TEST_COMMAND = '(set-name (interval 3 4.7 5.0 "d" "focus_bird") "b")'
TEST_LABELS = [{'start': 1.0, 'stop': 2.1, 'name': 'a', 'tier': 'tier0'},
               {'start': 2.1, 'stop': 3.5, 'name': 'b', 'tier': 'tier1'},
               {'start': 3.5, 'stop': 4.2, 'name': 'c', 'tier': 'tier2'},
               {'start': 4.7, 'stop': 5.0, 'name': 'd', 'tier': 'tier3'}]
TEST_OPS = ["""(set-name #:target (interval #:index 0 #:name "a") #:new-name "q")""",
            """(set-stop #:target (interval #:index 2 #:stop 4.2) #:new-stop 4.5)"""]

# test raw label correction operations

def test__set_value():
    labels = copy.deepcopy(TEST_LABELS)
    
    eved._set_value(labels, {'index': 3}, 'name', new_name='b', discard='spam')
    assert labels[3]['name'] == 'b'
    
    eved._set_value(labels, {'index': 3}, 'start', new_start=4.6)
    assert labels[3]['start'] == 4.6
    
    with pytest.raises(KeyError):
        eved._set_value(labels, {'index': 3}, 'sirnotappearinginthisfilm', new=3)

def test__merge_next():
    labels = copy.deepcopy(TEST_LABELS)
    eved._merge_next(labels, {'index': 1}, discard='spam')
    assert len(labels) == 3
    assert labels[1]['stop'] == 4.2
    assert labels[1]['name'] == 'b'
    assert labels[2]['name'] == 'd'

def test__split():
    labels = copy.deepcopy(TEST_LABELS)
    with pytest.raises(ValueError):
        eved._split(labels,
                  {'index': 3,
                   'name': 'd',
                   'stop': None,
                   'next_start': None,
                   'next_name': 'd'},
                  new_stop=1.0,
                  new_next_start=1.0)
    
    eved._split(labels,
              {'index': 3,
               'name': 'd',
               'stop': None,
               'next_start': None,
               'next_name': 'e'},
              new_stop=4.8,
              new_next_start=4.8)
    assert len(labels) == 5
    assert labels[3]['stop'] == 4.8
    assert labels[3]['name'] == 'd'
    assert labels[4]['start'] == 4.8
    assert labels[4]['stop'] == 5.0
    assert labels[4]['name'] == 'e'

def test__delete():
    labels = copy.deepcopy(TEST_LABELS)
    eved._delete(labels, {'index': 2})
    assert len(labels) == 3
    assert labels[2]['name'] == 'd'

def test__create():
    labels = copy.deepcopy(TEST_LABELS)
    new_interval = {'index': 2,
                    'start': 3.1,
                    'stop': 3.3,
                    'name': 'c2',
                    'tier': 'female'}
    eved._create(labels, new_interval)
    assert len(labels) == 5
    with pytest.raises(KeyError):
        labels[2]['index']
    assert labels[2]['start'] == 3.1
    assert labels[2]['stop'] == 3.3
    assert labels[2]['name'] == 'c2'
    assert labels[2]['tier'] == 'female'
    assert labels[3]['name'] == 'c'

# test parser functions

def test_tokenize():
    tkns = eved.tokenize(TEST_COMMAND)
    assert len(tkns) == 12
    assert tkns[0] == '('
    assert tkns[5] == '4.7'
    assert tkns[8] == '"focus_bird"'
    assert tkns[11] == ')'
    
    tkns = eved.tokenize('string "spaces preserved"')
    assert len(tkns) == 2
    assert tkns[0] == 'string'
    assert tkns[1] == '"spaces preserved"'

def test_atomize():
    assert eved.atomize('1') == 1
    assert eved.atomize('1.5') == 1.5
    assert eved.atomize('(') == '('
    assert eved.atomize('"focus_bird"') == 'focus_bird'
    assert isinstance(eved.atomize('set-name'), eved.Symbol)
    assert eved.atomize('set-name') == 'set_name'

def test_parse_and_read_from_tokens():
    with pytest.raises(SyntaxError):
        eved.read_from_tokens([])
    
    with pytest.raises(SyntaxError):
        eved.read_from_tokens([')'])
    
    nested_list = eved.parse(TEST_COMMAND)
    assert len(nested_list) == 3
    assert len(nested_list[1]) == 6
    assert nested_list[0] == 'set_name'
    assert nested_list[1][0] == 'interval'
    assert nested_list[1][5] == 'focus_bird'

def test_evaluate():
    def complex_proc(**kwargs):
        for a in kwargs:
            if isinstance(kwargs[a], float):
                kwargs[a] += 1.0
        return kwargs
    test_env = {'symbol': 'answer',
                'simple_proc': dict,
                'complex_proc': complex_proc}
    
    assert eved.evaluate(eved.Symbol('symbol'), test_env) == 'answer'
    
    assert eved.evaluate(1.5, test_env) == 1.5
    
    expr = [eved.Symbol('simple_proc'),
            eved.KeyArg('start'), 1.5,
            eved.KeyArg('stop'), 2.0,
            eved.KeyArg('name'), 'a']
    result = eved.evaluate(expr, test_env)
    assert isinstance(result, dict)
    assert result['start'] == 1.5
    assert result['stop'] == 2.0
    assert result['name'] == 'a'
    
    expr[0] = eved.Symbol('complex_proc')
    result = eved.evaluate(expr, test_env)
    assert isinstance(result, dict)
    assert result['start'] == 2.5
    assert result['stop'] == 3.0
    assert result['name'] == 'a'

def test_whole_stack():
    labels = copy.deepcopy(TEST_LABELS)
    test_env = eved.make_env(labels=labels)
    
    cmd = """(set-name #:target (interval #:index 0 #:name "a")
                       #:new-name "b")"""
    eved.evaluate(eved.parse(cmd), test_env)
    assert labels[0]['name'] == 'b'
    
    cmd = """(set-start #:target (interval #:index 1 #:start 3.141)
                           #:new-start 2.2)"""
    eved.evaluate(eved.parse(cmd), test_env)
    assert labels[1]['start'] == 2.2
    
    cmd = """(merge-next #:target (interval #:index 1
                                            #:name "b"
                                            #:stop 3.240
                                            #:next-start 3.240
                                            #:next-name "silence")
                         #:new_stop null
                         #:new_next_start null)"""
    eved.evaluate(eved.parse(cmd), test_env)
    assert len(labels) == len(TEST_LABELS) - 1
    assert labels[1]['stop'] == TEST_LABELS[2]['stop']
    
    cmd = """(split #:target (interval #:index 1
                                       #:name "b"
                                       #:stop null
                                       #:next-start null
                                       #:next-name "b")
                    #:new_stop 3.5
                    #:new_next_start 3.5)"""
    eved.evaluate(eved.parse(cmd), test_env)
    assert len(labels) == len(TEST_LABELS)
    assert labels[1]['stop'] == TEST_LABELS[1]['stop']

# test inverse parser operations and inverse generator

def test_deatomize():
    assert eved.deatomize(None) == 'null'
    
    assert eved.deatomize(eved.KeyArg('name')) == '#:name'
    
    assert eved.deatomize(eved.Symbol('split')) == 'split'
    assert eved.deatomize(eved.Symbol('merge_next')) == 'merge-next'
    assert eved.deatomize(eved.Symbol('_')) == '_'
    
    assert eved.deatomize('b') == '"b"'
    
    assert eved.deatomize(1.5) == '1.5'
    
    with pytest.raises(ValueError):
        eved.deatomize(ValueError)

def test_detokenize():
    token_list = ['(', 'merge-next', '#:target', '(',
                  'interval-pair', '#:index', '0', '#:name', 'null',
                   '#:sep', 'null', '#:next-name', 'null', ')',
                  '#:new-name', '"b"', '#:new-sep', '1.5',
                  '#:new-next-name', '"c"', ')']
    cmd = eved.detokenize(token_list)
    assert isinstance(cmd, str)
    assert cmd[0] == '('
    assert cmd[-1] == ')'
    assert cmd[12:20] == '#:target'
    ident = eved.tokenize(cmd)
    assert token_list == ident

def test_write_to_tokens():
    expr = [eved.Symbol('merge_next'), eved.KeyArg('target'),
            [eved.Symbol('interval_pair'), eved.KeyArg('index'), 0,
             eved.KeyArg('name'), None, eved.KeyArg('sep'), None,
             eved.KeyArg('next_name'), None],
            eved.KeyArg('new_name'), "b", eved.KeyArg('new_sep'), 1.5,
            eved.KeyArg('new_next_name'), "c"]
    token_list = eved.write_to_tokens(expr)
    assert token_list[0] == '('
    assert token_list[-1] == ')'
    assert token_list[3] == '('
    assert token_list[13] == ')'
    assert token_list[-3] == '#:new-next-name'
    assert token_list[-2] == '"c"'
    ident = eved.read_from_tokens(token_list)
    assert expr == ident

def test_deparse():
    s_exprs = [eved.parse(op) for op in TEST_OPS]
    deparsed = [eved.deparse(e) for e in s_exprs]
    assert deparsed == TEST_OPS

def test_invert():
    cmd = '(merge-next #:target (interval-pair #:index 0 #:name null #:sep null #:next-name null) #:new-name "b" #:new-sep 1.5 #:new-next-name "c")'
    hand_inv = '(split #:target (interval-pair #:index 0 #:name "b" #:sep 1.5 #:next-name "c") #:new-name null #:new-sep null #:new-next-name null)'
    inv = eved.invert(eved.parse(cmd))
    assert inv == eved.parse(hand_inv)
    
    ident = eved.invert(eved.invert(eved.parse(cmd)))
    assert cmd == eved.deparse(ident)

# test EditStack methods

def make_corr_file(tmpdir):
    tf = tempfile.NamedTemporaryFile(mode='w', dir=tmpdir.strpath, delete=False)
    for op in TEST_OPS:
        tf.write(op + '\n')
    tf.close()
    with open((tf.name + '.yaml'), 'w') as mdfp:
        mdfp.write("""# corrections metadata, YAML\n---\n""")
        file_metadata = {'hash_pre': eved.event_hash(TEST_LABELS)}
        mdfp.write(yaml.safe_dump(file_metadata))
    return tf

def test_CS_init(tmpdir):
    labels = copy.deepcopy(TEST_LABELS)
    tf = make_corr_file(tmpdir)
    
    cs = eved.EditStack(labels=labels,
                            ops_file=tf.name,
                            load=False)
    assert cs.labels == TEST_LABELS
    assert cs.file == tf.name
    assert len(cs.undo_stack) == 0
        
    cs = eved.EditStack(labels=labels,
                            ops_file=tf.name,
                            load=True)
    assert cs.file == tf.name
    assert len(cs.undo_stack) == 2
    assert cs.undo_stack[0] == eved.parse(TEST_OPS[0])
    assert cs.undo_stack[1] == eved.parse(TEST_OPS[1])
    assert cs.labels[1] == TEST_LABELS[1]
    assert cs.labels[3] == TEST_LABELS[3]
    assert cs.labels[0]['name'] == 'q'
    assert cs.labels[2]['stop'] == 4.5
    
    os.remove(tf.name)

def test_context_manager(tmpdir):
    labels = copy.deepcopy(TEST_LABELS)
    tf = make_corr_file(tmpdir)
    
    # exception is passed through, and .bak file is created
    with pytest.raises(ZeroDivisionError):
        with eved.EditStack(labels=labels,
                                ops_file=tf.name,
                                load=True) as cs:
            cs.rename(3, 'eggs')
            x = 3 / 0
    assert os.path.exists(tf.name + '.bak')
    
    # .bak file contains all operations in stack at time of exception
    labels = copy.deepcopy(TEST_LABELS)
    assert labels[3]['name'] == 'd'
    with eved.EditStack(labels=labels,
                            ops_file=(tf.name + '.bak'),
                            load=True) as cs:
        assert cs.labels[0]['name'] == 'q'
        assert cs.labels[2]['stop'] == 4.5
        assert cs.labels[3]['name'] == 'eggs'
    
    # regular file doesn't contain state written to .bak file
    labels = copy.deepcopy(TEST_LABELS)
    assert labels[3]['name'] == 'd'
    with eved.EditStack(labels=labels,
                            ops_file=tf.name,
                            load=True) as cs:
        assert cs.labels[0]['name'] == 'q'
        assert cs.labels[2]['stop'] == 4.5
        assert cs.labels[3]['name'] == 'd'
    
    # regular exit doesn't create .bak file
    tf2 = make_corr_file(tmpdir)
    labels = copy.deepcopy(TEST_LABELS)
    assert labels[3]['name'] == 'd'
    with eved.EditStack(labels=labels,
                            ops_file=tf2.name,
                            load=True) as cs:
        cs.rename(3, 'eggs')
    assert not os.path.exists(tf2.name + '.bak')
    
    # regular exit writes entire stack to regular file
    labels = copy.deepcopy(TEST_LABELS)
    assert labels[3]['name'] == 'd'
    with eved.EditStack(labels=labels,
                            ops_file=tf2.name,
                            load=True) as cs:
        assert cs.labels[0]['name'] == 'q'
        assert cs.labels[2]['stop'] == 4.5
        assert cs.labels[3]['name'] == 'eggs'

    os.remove(tf.name + '.bak')
    os.remove(tf.name)

def test_CS_read_from_file(tmpdir):
    labels = copy.deepcopy(TEST_LABELS)
    tf = make_corr_file(tmpdir)
    
    cs = eved.EditStack(labels=labels,
                            ops_file=tf.name,
                            load=False)
    cs.read_from_file(tf.name)
    assert cs.labels[0]['name'] == 'q'
    assert cs.labels[2]['stop'] == 4.5
    assert list(cs.undo_stack) == [eved.parse(op) for op in TEST_OPS]
    
    os.remove(tf.name)

def test_CS_write_to_file(tmpdir):
    labels = copy.deepcopy(TEST_LABELS)
    tf = make_corr_file(tmpdir)
    
    cs = eved.EditStack(labels=labels,
                            ops_file=tf.name,
                            load=True)
    new_cmd = """(set-name #:target (interval #:index 1 #:name "b") #:new-name "z")"""
    cs.push(eved.parse(new_cmd))
    os.remove(tf.name)
    cs.write_to_file()
    assert os.path.exists(cs.file)
    assert os.path.exists(cs.file + '.yaml')
    
    labels = copy.deepcopy(TEST_LABELS)
    cs_new = eved.EditStack(labels=labels,
                                ops_file=tf.name,
                                load=True)
    assert len(cs_new.undo_stack) == 3
    assert cs_new.undo_stack == cs.undo_stack
    assert cs_new.undo_stack[-1] == eved.parse(new_cmd)
    assert cs_new.hash_pre == cs.hash_pre
    
    os.remove(tf.name)

def test_CS_undo_and_redo(tmpdir):
    labels = copy.deepcopy(TEST_LABELS)
    tf = make_corr_file(tmpdir)
    
    cs = eved.EditStack(labels=labels,
                            ops_file=tf.name,
                            load=True)
    new_cmd = """(set-name #:target (interval #:index 1 #:name "b")
                           #:new-name "z")"""
    cs.push(eved.parse(new_cmd))
    assert len(cs.undo_stack) == 3
    assert len(cs.redo_stack) == 0
    assert cs.labels[1]['name'] == "z"
    assert cs.labels[2]['stop'] == 4.5
    assert cs.labels[0]['name'] == "q"

    cs.undo() # undo new_cmd
    assert len(cs.undo_stack) == 2
    assert len(cs.redo_stack) == 1
    assert cs.labels[1]['name'] == "b"
    assert cs.labels[2]['stop'] == 4.5
    assert cs.labels[0]['name'] == "q"
    
    cs.undo() # undo TEST_OPS[1]
    assert len(cs.undo_stack) == 1
    assert len(cs.redo_stack) == 2
    assert cs.labels[1]['name'] == "b"
    assert cs.labels[2]['stop'] == 4.2
    assert cs.labels[0]['name'] == "q"
    
    cs.undo() # undo TEST_OPS[0]
    assert len(cs.undo_stack) == 0
    assert len(cs.redo_stack) == 3
    assert cs.labels[1]['name'] == "b"
    assert cs.labels[2]['stop'] == 4.2
    assert cs.labels[0]['name'] == "a"
    
    # undo on an empty undo_stack raises exception
    with pytest.raises(IndexError):
        cs.undo()
    
    cs.redo() # redo TEST_OPS[0]
    assert len(cs.undo_stack) == 1
    assert len(cs.redo_stack) == 2
    assert cs.labels[1]['name'] == "b"
    assert cs.labels[2]['stop'] == 4.2
    assert cs.labels[0]['name'] == "q"
    
    cs.redo() # redo TEST_OPS[1]
    assert len(cs.undo_stack) == 2
    assert len(cs.redo_stack) == 1
    assert cs.labels[1]['name'] == "b"
    assert cs.labels[2]['stop'] == 4.5
    assert cs.labels[0]['name'] == "q"

    cs.redo() # redo new_cmd
    assert len(cs.undo_stack) == 3
    assert len(cs.redo_stack) == 0
    assert cs.labels[1]['name'] == "z"
    assert cs.labels[2]['stop'] == 4.5
    assert cs.labels[0]['name'] == "q"
    
    # redo on an empty redo_stack raises exception
    with pytest.raises(IndexError):
        cs.redo()
        
    os.remove(tf.name)

def test_CS_push(tmpdir):
    labels = copy.deepcopy(TEST_LABELS)
    tf = make_corr_file(tmpdir)
    
    cs = eved.EditStack(labels=labels,
                            ops_file=tf.name,
                            load=True)
    assert cs.labels[1]['name'] == "b"
    assert cs.labels[2]['stop'] == 4.5
    assert cs.labels[0]['name'] == "q"

    new_cmd = """(set-name #:target (interval #:index 1 #:name "b")
                           #:new-name "z")"""
    cs.push(eved.parse(new_cmd)) # push adds new_cmd to head of stack
    assert cs.labels[1]['name'] == "z"
    assert cs.labels[2]['stop'] == 4.5
    assert cs.labels[0]['name'] == "q"
    
    cs.undo()
    cs.undo()
    cs.push(eved.parse(new_cmd)) # TEST_OPS[1] is gone; new_cmd now at head of stack
    assert len(cs.undo_stack) == 2
    assert cs.labels[1]['name'] == "z"
    assert cs.labels[2]['stop'] == 4.2
    assert cs.labels[0]['name'] == "q"
    
    os.remove(tf.name)

def test_CS_peek(tmpdir):
    labels = copy.deepcopy(TEST_LABELS)
    tf = make_corr_file(tmpdir)
    
    cs = eved.EditStack(labels=labels,
                            ops_file=tf.name,
                            load=True)
    p = cs.peek() # default: show op at top of undo_stack
    assert p == eved.parse(TEST_OPS[1])
    
    with pytest.raises(IndexError):
        p = cs.peek(len(cs.undo_stack) + 10)
    
    with pytest.raises(IndexError):
        p = cs.peek(-10)
    
    p = cs.peek(0)
    assert p == eved.parse(TEST_OPS[0])
    
    os.remove(tf.name)

def test_CS__apply(tmpdir):
    labels = copy.deepcopy(TEST_LABELS)
    tf = make_corr_file(tmpdir)
    
    cs = eved.EditStack(labels=labels,
                            ops_file=tf.name,
                            load=True)
    new_cmd = """(set-name #:target (interval #:index 1 #:name "b")
                           #:new-name "z")"""
    cs._apply(eved.parse(new_cmd))
    # the stack is now in an undefined state
    # but we can still check that _apply performed the new_cmd operation
    assert cs.labels[1]['name'] == 'z'
    
    os.remove(tf.name)

# test operations

def test_CS_rename():
    labels = copy.deepcopy(TEST_LABELS)
    tf = tempfile.NamedTemporaryFile(delete=False)
    tf.close()
    cs = eved.EditStack(labels=labels,
                            ops_file=tf.name,
                            load=False)
    
    cs.rename(0, 'q')
    assert len(cs.undo_stack) == 1
    assert cs.labels[0]['name'] == 'q'
    
    os.remove(tf.name)

def test_CS_set_start():
    labels = copy.deepcopy(TEST_LABELS)
    tf = tempfile.NamedTemporaryFile(delete=False)
    tf.close()
    cs = eved.EditStack(labels=labels,
                            ops_file=tf.name,
                            load=False)
    
    cs.set_start(0, 1.6)
    assert len(cs.undo_stack) == 1
    assert cs.labels[0]['start'] == 1.6

    os.remove(tf.name)

def test_CS_set_stop():
    labels = copy.deepcopy(TEST_LABELS)
    tf = tempfile.NamedTemporaryFile(delete=False)
    tf.close()
    cs = eved.EditStack(labels=labels,
                            ops_file=tf.name,
                            load=False)
    
    cs.set_stop(0, 1.8)
    assert len(cs.undo_stack) == 1
    assert cs.labels[0]['stop'] == 1.8

    os.remove(tf.name)

def test_CS_merge_next():
    labels = copy.deepcopy(TEST_LABELS)
    tf = tempfile.NamedTemporaryFile(delete=False)
    tf.close()
    cs = eved.EditStack(labels=labels,
                            ops_file=tf.name,
                            load=False)
    
    for i in range(len(labels)):
        labels[i]['tier'] = 'tier' + str(i)
    cs.merge_next(0)
    assert len(cs.undo_stack) == 1
    assert len(cs.labels) == 3
    assert cs.labels[0]['start'] == 1.0
    assert cs.labels[0]['stop'] == 3.5
    assert cs.labels [0]['name'] == 'a'
    assert cs.labels[0]['tier'] == 'tier0'
    assert cs.labels[1]['tier'] == 'tier2'
    
    # merge saves all column info, for restoration on undo
    cs.undo()
    assert cs.labels[0]['start'] == 1.0
    assert cs.labels[0]['stop'] == 2.1
    assert cs.labels[0]['name'] == 'a'
    assert cs.labels[0]['tier'] == 'tier0'
    assert cs.labels[1]['start'] == 2.1
    assert cs.labels[1]['stop'] == 3.5
    assert cs.labels[1]['name'] == 'b'
    assert cs.labels[1]['tier'] == 'tier1'
    
    cs.merge_next(0)
    assert len(cs.labels) == 3
    assert cs.labels[0]['name'] == 'a'
    
    # can merge two intervals that don't share a boundary,
    # and their respective stop/start will be preserved after undo
    cs.merge_next(1)
    assert len(cs.labels) == 2
    assert cs.labels[1]['start'] == 3.5
    assert cs.labels[1]['stop'] == 5.0
    assert cs.labels[1]['name'] == 'c'
    assert cs.labels[1]['tier'] == 'tier2'
    cs.undo()
    assert len(cs.labels) == 3
    assert cs.labels[1]['start'] == 3.5
    assert cs.labels[1]['stop'] == 4.2
    assert cs.labels[1]['name'] == 'c'
    assert cs.labels[1]['tier'] == 'tier2'
    assert cs.labels[2]['start'] == 4.7
    assert cs.labels[2]['stop'] == 5.0
    assert cs.labels[2]['name'] == 'd'
    assert cs.labels[2]['tier'] == 'tier3'

    os.remove(tf.name)

def test_CS_split():
    labels = copy.deepcopy(TEST_LABELS)
    tf = tempfile.NamedTemporaryFile(delete=False)
    tf.close()
    cs = eved.EditStack(labels=labels,
                            ops_file=tf.name,
                            load=False)
    
    cs.split(0, 1.8)
    assert len(cs.undo_stack) == 1
    assert len(cs.labels) == 5
    assert cs.labels[0]['start'] == 1.0
    assert cs.labels[0]['stop'] == 1.8
    assert cs.labels[0]['name'] == 'a'
    assert cs.labels[1]['start'] == 1.8
    assert cs.labels[1]['stop'] == 2.1
    assert cs.labels[1]['name'] == 'a'
    
    os.remove(tf.name)

def test_CS_delete():
    labels = copy.deepcopy(TEST_LABELS)
    tf = tempfile.NamedTemporaryFile(delete=False)
    tf.close()
    cs = eved.EditStack(labels=labels,
                            ops_file=tf.name,
                            load=False)
    
    cs.create(0, 0.5, stop=0.9, name='q', tier='spam')
    assert len(cs.labels) == 5
    assert cs.labels[0]['start'] == 0.5
    assert cs.labels[0]['stop'] == 0.9
    assert cs.labels[0]['name'] == 'q'
    assert cs.labels[0]['tier'] == 'spam'
    
    cs.delete(0)
    assert len(cs.undo_stack) == 2
    assert len(cs.labels) == 4
    assert cs.labels[0]['start'] == 1.0
    assert cs.labels[0]['stop'] == 2.1
    assert cs.labels[0]['name'] == 'a'
    
    cs.undo()
    # extra data associated with deleted item are restored
    assert len(cs.labels) == 5
    assert cs.labels[0]['start'] == 0.5
    assert cs.labels[0]['stop'] == 0.9
    assert cs.labels[0]['name'] == 'q'
    assert cs.labels[0]['tier'] == 'spam'

    os.remove(tf.name)

def test_CS_create():
    labels = copy.deepcopy(TEST_LABELS)
    tf = tempfile.NamedTemporaryFile(delete=False)
    tf.close()
    cs = eved.EditStack(labels=labels,
                            ops_file=tf.name,
                            load=False)
    
    cs.create(0, 0.5, stop=0.9, name='q', tier='spam')
    assert len(cs.undo_stack) == 1
    assert len(cs.labels) == 5
    assert cs.labels[0]['start'] == 0.5
    assert cs.labels[0]['stop'] == 0.9
    assert cs.labels[0]['name'] == 'q'
    assert cs.labels[0]['tier'] == 'spam'
    assert cs.labels[1] == TEST_LABELS[0]

    os.remove(tf.name)
