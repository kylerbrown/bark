import copy
import itertools
import numbers
import tempfile
import codecs
import yaml
import uuid
import hashlib
import collections
import functools as ft

__version__ = "0.4.1"

class EditStack:
    def __init__(self, labels, ops_file, load):
        """Creates an EditStack.
        
           labels -- a list of dicts denoted event data
           ops_file -- filename string to save operations
           load -- bool; if True, load from ops_file and apply to labels"""
        self.labels = labels
        self.file = ops_file
        if load:
            self.read_from_file()
        else:
            self.undo_stack = collections.deque()
            self.redo_stack = collections.deque()
            self.hash_pre = event_hash(self.labels)
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_value, exc_trace):
        if exc_type is None:
            self.write_to_file()
            return True
        else:
            self.write_to_file(self.file + '.bak')
            return False
    
    def read_from_file(self, file=None):
        """Read a stack of corrections plus metadata from file.
           
           file -- if not present, use self.file
           
           Raises ValueError if pre-operation hashes don't match."""
        if file:
            self.file = file
        with codecs.open((self.file + '.yaml'), 'r', encoding='utf-8') as mdfp:
            file_data = yaml.safe_load(mdfp)
            self.hash_pre = file_data['hash_pre']
        if self.hash_pre != event_hash(self.labels):
            raise ValueError('label file hash does not match op file hash_pre')
        with codecs.open(self.file, 'r', encoding='utf-8') as fp:
            self.undo_stack = collections.deque()
            self.redo_stack = collections.deque()
            for op in fp:
                if op != '\n':
                    self.push(parse(op.strip()))
    
    def write_to_file(self, file=None):
        """Write stack of corrections plus metadata to file.
           
           file -- if not present, use self.file"""
        if file:
            self.file = file
        with codecs.open(self.file, 'w', encoding='utf-8') as fp:
            for op in self.undo_stack:
                fp.write(deparse(op) + '\n')
        with codecs.open((self.file + '.yaml'), 'w', encoding='utf-8') as mdfp:
            self.hash_post = event_hash(self.labels)
            file_data = {'hash_pre': self.hash_pre}
            mdfp.write("""# corrections metadata, YAML syntax\n---\n""")
            mdfp.write(yaml.safe_dump(file_data, default_flow_style=False))
    
    def undo(self):
        """Undoes last executed command, if any.
           Raises an IndexError if the undo_stack is empty."""
        inv = invert(self.undo_stack.pop())
        self.redo_stack.append(inv)
        self._apply(inv)
    
    def redo(self):
        """Redoes last undone command, if any.
           Raises an IndexError if the redo_stack is empty."""
        inv = invert(self.redo_stack.pop())
        self.undo_stack.append(inv)
        self._apply(inv)
    
    def push(self, cmd):
        """Executes command, discarding redo stack."""
        self.redo_stack.clear()
        self.undo_stack.append(cmd)
        self._apply(cmd)
    
    def peek(self, index=-1):
        """Returns command string at top of undo stack, or index."""
        return self.undo_stack[index]
    
    def _apply(self, s_expr):
        """Executes s-expression, applied to labels."""
        evaluate(s_expr, make_env(labels=self.labels))
    
    # operations
    
    def rename(self, index, new_name):
        """Renames an event."""
        self.push(self.codegen_rename(index, new_name))
    
    def set_start(self, index, new_start):
        """Changes the start time of an event."""
        self.push(self.codegen_set_start(index, new_start))
    
    def set_stop(self, index, new_stop):
        """Changes the stop time of an event."""
        self.push(self.codegen_set_stop(index, new_stop))
    
    def merge_next(self, index):
        """Merges an event with its successor."""
        self.push(self.codegen_merge_next(index))
    
    def split(self, index, new_sep):
        """Splits an event in two."""
        self.push(self.codegen_split(index, new_sep))
    
    def delete(self, index):
        """Deletes an event."""
        self.push(self.codegen_delete(index))
    
    def create(self, index, start, stop, name, **kwargs):
        """Creates a new event."""
        self.push(self.codegen_create(index, start, stop, name, **kwargs))
    
    # code generators
    
    def codegen_rename(self, index, new_name):
        """Generates s-expression to rename an event."""
        if '"' in new_name:
            raise ValueError('" character disallowed in event names')
        new_vals = {'name': new_name}
        old_vals = set()
        return gen_code(self.labels, 'set_name', index, new_vals, old_vals)
    
    def codegen_set_start(self, index, new_start):
        """Generates s-expression to move an event's start."""
        new_vals = {'start': new_start}
        old_vals = set()
        return gen_code(self.labels, 'set_start', index, new_vals, old_vals)
    
    def codegen_set_stop(self, index, new_stop):
        """Generates s-expression to move an event's stop."""
        new_vals = {'stop': new_stop}
        old_vals = set()
        return gen_code(self.labels, 'set_stop', index, new_vals, old_vals)
    
    def codegen_merge_next(self, index):
        """Generates an s-expression to merge an event with its successor.
           The new event inherits all non-boundary column values from the
           first parent."""
        new_vals = {'stop': None, 'next_start': None}
        old_vals = set(self.labels[index].keys())
        return gen_code(self.labels, 'merge_next', index, new_vals, old_vals)
    
    def codegen_split(self, index, split_pt):
        """Generates an s-expression to split an event in two at a point.
           The child events inherit all non-boundary column values from the
           parent."""
        new_vals = {'stop': split_pt, 'next_start': split_pt}
        old_vals = set(self.labels[index].keys())
        return gen_code(self.labels, 'split', index, new_vals, old_vals)
    
    def codegen_delete(self, index):
        """Generates an s-expression to delete an event."""
        new_vals = {}
        old_vals = set(self.labels[index].keys())
        return gen_code(self.labels, 'delete', index, new_vals, old_vals)
    
    def codegen_create(self, index, start, stop, name, **kwargs):
        """Generates an s-expression to create a new event with given values."""
        new_vals = {'start': start, 'stop': stop, 'name': name}
        new_vals.update(kwargs)
        old_vals = set(new_vals.keys())
        # trick: make 'create' s-expr with new_vals, invert to 'delete' s-expr
        # to inject them into #:target, remove the garbage new_values, then
        # invert again to generate the proper 'create' s-expr
        bad_create = gen_code(self.labels, 'create', index, new_vals, old_vals)
        good_create = invert(invert(bad_create)[:3])
        return good_create

# raw operations

def _set_value(labels, target, column, **kwargs):
    labels[target['index']][column] # raise KeyError if column not present
    labels[target['index']][column] = kwargs['new_' + column]

def _merge_next(labels, target, **_):
    # **_ contains throwaway args needed to allow inversion, but not used here
    index = target['index']
    labels[index]['stop'] = labels[index + 1]['stop']
    labels.pop(index + 1)

def _split(labels, target, **kwargs):
    if not (kwargs['new_stop'] > labels[target['index']]['start'] and
            kwargs['new_next_start'] < labels[target['index']]['stop']):
        raise ValueError('split point must be within interval')
    index = target['index']
    labels.insert(index + 1, copy.deepcopy(labels[index]))
    labels[index]['stop'] = kwargs['new_stop']
    for k in target:
        if k[:5] == 'next_':
            labels[index + 1][k[5:]] = target[k]
    labels[index + 1]['start'] = kwargs['new_next_start']

def _delete(labels, target):
    labels.pop(target['index'])

def _create(labels, target):
    idx = target['index']
    new_point = {'start': target['start'],
                 'stop': target['stop'],
                 'name': target['name']}
    del target['index']
    new_point.update(target)
    labels.insert(idx, new_point)

# code generation

def gen_code(labels, op, idx, new_vals, old_vals):
    """Generates an s-expression for the given op.
       
       labels -- list of dicts representing events
       op -- string
       idx -- integer
       new_vals -- dict; keys must be valid column names
       old_vals -- list of strings; must be valid column names"""
    sxpr = [Symbol(op), KeyArg('target'), [Symbol('interval')]]
    sxpr[-1].extend([KeyArg('index'), idx])
    query_keys = (old_vals | set(new_vals.keys())) - set(['next_start'])
    for c in query_keys:
        sxpr[-1].extend([KeyArg(c), labels[idx][c]])
    if op == 'merge_next': # include second event's data to allow inversion
        for c in query_keys:
            sxpr[-1].extend([KeyArg('next_' + c), labels[idx + 1][c]])
    elif op == 'split': # second child event's data is copied from first
        for c in query_keys:
            sxpr[-1].extend([KeyArg('next_' + c), labels[idx][c]])
    for c in new_vals:
        sxpr.extend([KeyArg('new_' + c), new_vals[c]])
    return sxpr


# invert operations

INVERSE_TABLE = {'set_name': 'set_name',
                 'set_start': 'set_start',
                 'set_stop': 'set_stop',
                 'merge_next': 'split',
                 'split': 'merge_next',
                 'delete': 'create',
                 'create': 'delete'}

def invert(s_expr):
    """Generates an s-expression for the inverse of s_expr."""
    op = s_expr[0]
    inverse = INVERSE_TABLE[op]
    target = s_expr[s_expr.index('target') + 1]
    for i in range(len(s_expr)):
        curr = s_expr[i]
        if isinstance(curr, KeyArg) and len(curr) >= 4 and curr[:4] == 'new_':
            oldname = curr[4:]
            oldval = copy.deepcopy(target[target.index(oldname) + 1])
            target[target.index(oldname) + 1] = copy.deepcopy(s_expr[i + 1])
            s_expr[i + 1] = oldval
    inverse_s_expr = [Symbol(inverse)]
    inverse_s_expr.extend(s_expr[1:])
    return inverse_s_expr

# reverse parsing

def detokenize(token_list):
    """Turns a flat list of tokens into a command."""
    cmd = token_list[0]
    for t in token_list[1:]:
        if t != ')' and cmd[-1] != '(':
            cmd += ' '
        cmd += t
    return cmd

def write_to_tokens(ntl):
    """Turns an s-expression into a flat token list."""
    token_list = ['(']
    for t in ntl:
        if isinstance(t, list):
            token_list.extend(write_to_tokens(t))
        else:
            token_list.append(deatomize(t))
    token_list.append(')')
    return token_list

def deatomize(a):
    """Turns an atom into a token."""
    if a is None:
        return 'null'
    elif isinstance(a, Symbol):
        ret = a[0] + a[1:].replace('_', '-')
        if isinstance(a, KeyArg):
            ret = '#:' + ret
        return ret
    elif isinstance(a, str):
        return '"' + a + '"'
    elif isinstance(a, numbers.Number):
        return str(a)
    else:
        raise ValueError('unknown atomic type: ' + str(a))

def deparse(s_expr):
    """Turns an s-expression into a command string."""
    return detokenize(write_to_tokens(s_expr))

# parser & evaluator

class Symbol(str): pass

class KeyArg(Symbol): pass

def tokenize(cmd):
    """Turns a command string into a flat token list."""
    second_pass = []
    in_string = False
    for token in cmd.split():
        if token[0] == '"' and not in_string: # open quote
            second_pass.append(token)
            if token.count('"') != 2:
                in_string = True
        elif '"' in token and in_string: # close quote
            if all(c == ')' for c in token[(token.index('"') + 1):]):
                second_pass[-1] += ' ' + token
                in_string = False
            else:
                raise ValueError('unexpected " character in command: ' + cmd)
        elif '"' not in token and in_string: # middle words in quote
            second_pass[-1] += ' ' + token
        elif '"' in token:
            raise ValueError('unexpected " character in command: ' + cmd)
        else:
            second_pass.append(token)
    third_pass = []
    for token in second_pass:
        if token[0] == '(':
            third_pass.append('(')
            if len(token) > 1:
                third_pass.append(token[1:])
        elif token[-1] == ')':
            pps = []
            while token[-1] == ')':
                pps.append(')')
                token = token[:-1]
            third_pass.extend([token] + pps)
        else:
            third_pass.append(token)
    return third_pass


def atomize(token):
    """Turns a token into an atom."""
    if token[0] == '"':
        try:
            return token[1:-1].decode('string_escape')
        except AttributeError: # python 2/3 support
            return token[1:-1]
    if token == 'null':
        return None
    try:
        return int(token)
    except ValueError:
        try:
            return float(token)
        except ValueError:
            token = token[0] + token[1:].replace('-', '_')
            if token[:2] == '#:':
                return KeyArg(token[2:])
            return Symbol(token)


def read_from_tokens(token_list):
    """Turns a flat token list into an s-expression."""
    if len(token_list) == 0:
        raise SyntaxError('unexpected EOF')
    token = token_list.pop(0)
    if token == '(':
        nested_list = []
        while token_list[0] != ')':
            nested_list.append(read_from_tokens(token_list))
        token_list.pop(0)
        return nested_list
    elif token == ')':
        raise SyntaxError('unexpected )')
    else:
        return atomize(token)


def parse(cmd):
    """Turns a command string into an s-expression."""
    return read_from_tokens(tokenize(cmd))


def make_env(labels=None, **kwargs):
    """Returns an environment for s-expression evaluation."""
    env = {'set_name': ft.partial(_set_value, labels=labels, column='name'),
           'set_start': ft.partial(_set_value, labels=labels, column='start'),
           'set_stop': ft.partial(_set_value, labels=labels, column='stop'),
           'merge_next': ft.partial(_merge_next, labels=labels),
           'split': ft.partial(_split, labels=labels),
           'delete': ft.partial(_delete, labels=labels),
           'create': ft.partial(_create, labels=labels),
           'interval': dict,
           'interval_pair': dict}
    env['labels'] = labels
    env.update(kwargs)
    return env


def evaluate(expr, env=make_env()):
    """Evaluates an s-expression in the context of an environment."""
    if isinstance(expr, Symbol):
        return env[expr]
    elif not isinstance(expr, list):
        return expr
    else:
        proc = evaluate(expr[0], env)
        kwargs = {p[0]: evaluate(p[1], env) for p in _grouper(expr[1:], 2)}
        return proc(**kwargs)


def _grouper(iterable, n):
    """Returns nonoverlapping windows of input of length n.
    
       Copied from itertools recipe suggestions."""
    args = [iter(iterable)] * n
    try:
        return itertools.izip_longest(*args)
    except AttributeError: # python 2/3 support
        return itertools.zip_longest(*args)

def event_hash(events):
    """Returns SHA-1 hash of given event list (assumed to be list of dicts)."""
    return hashlib.sha1(repr(events).encode()).hexdigest()
