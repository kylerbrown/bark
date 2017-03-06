from copy import deepcopy
import json


class EventOperation:
    def __init__(self, index):
        self.index = index

    def __str__(self):
        name, args = self.dump()
        return '{} on {}'.format(name, args)

    def dump(self):
        return (type(self).__name__, self.__dict__)


class New(EventOperation):
    def __init__(self, index, name, start, stop):
        super().__init__(index)
        self.name = name
        self.start = start
        self.stop = stop

    def on(self, events):
        events.insert(self.index,
                      dict(name=self.name,
                           start=self.start,
                           stop=self.stop))


class Update(EventOperation):
    def __init__(self, index, key, value):
        super().__init__(index)
        self.key = key
        self.value = value

    def on(self, events):
        events[self.index][self.key] = self.value


class Split(EventOperation):
    def __init__(self, index, split):
        super().__init__(index)
        self.split = split

    def on(self, events):
        events.insert(self.index + 1, events[self.index].copy())
        Update(self.index, 'stop', self.split).on(events)
        Update(self.index + 1, 'start', self.split).on(events)


class Merge(EventOperation):
    def on(self, events):
        events[self.index]['stop'] = events[self.index + 1]['stop']
        Delete(self.index + 1).on(events)


class Delete(EventOperation):
    def on(self, events):
        del events[self.index]


class OpStack:
    def __init__(self, events, ops=()):
        self.original_events = deepcopy(events)
        self.ops = list(ops)
        self.undo_ops = []
        self.regenerate()

    def regenerate(self):
        self.events = deepcopy(self.original_events)
        [op.on(self.events) for op in self.ops]

    def push(self, op):
        self.ops.append(op)
        op.on(self.events)
        self.undo_ops = []

    def undo(self):
        self.undo_ops.append(self.ops.pop())
        self.regenerate()

    def redo(self):
        self.ops.append(self.undo_ops.pop())
        self.ops[-1].on(self.events)


def write_stack(filename, opstack):
    ops_dump = [x.dump() for x in opstack.ops]
    save_data = {'operations': ops_dump,
                 'original_events': opstack.original_events}
    json.dump(save_data, open(filename, 'w'), indent=4)


operations = {k: v
              for k, v in globals().items()
              if isinstance(v, type) and issubclass(v, EventOperation)}


def read_stack(filename, operations=operations):
    data = json.load(open(filename, 'r'))
    ops = [parse_op(opname, operations, **kwargs)
           for opname, kwargs in data['operations']]
    return OpStack(data['original_events'], ops)


def parse_op(opname, operations=operations, **kwargs):
    '''Parse an operation name string and return EventOperation objects

    opname -- a string representation of the class
    operations -- a dictionary of class strings,
                  values are subclasses of EventOperation
    kwargs -- arguments to initialize the object
    '''
    return operations[opname](**kwargs)
