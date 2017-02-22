from copy import deepcopy
import json


class EventOp:
    def __init__(self, index):
        self.index = index

    def __str__(self):
        name, args = self.dump()
        return '{} with {}'.format(name, ' '.join(str(k) + ':' + str(v)
                                                  for k, v in args.items()))

    def __lshift__(self, other):
        '''Shorthand for applying the operation.'''
        self.operate(other)

    def dump(self):
        return (type(self).__name__, self.__dict__)


class UpdateOp(EventOp):
    def __init__(self, index, key, new_value):
        super().__init__(index)
        self.key = key
        self.new_value = new_value

    def operate(self, events):
        events[self.index][self.key] = self.new_value


class SplitOp(EventOp):
    def __init__(self, index, split):
        super().__init__(index)
        self.split = split

    def operate(self, events):
        events.insert(self.index + 1, events[self.index].copy())
        events << UpdateOp(self.index, 'stop', self.split)
        events << UpdateOp(self.index + 1, 'start', self.split)


class MergeOp(EventOp):
    def __init__(self, index):
        '''Merge with next segment'''
        super().__init__(index)

    def operate(self, events):
        events[self.index]['stop'] = events[self.index + 1]['stop']
        events << DeleteOp(self.index + 1)


class DeleteOp(EventOp):
    def __init__(self, index):
        super().__init__(index)

    def operate(self, events):
        del events[self.index]


class EventList(list):
    def __lshift__(self, other):
        return other.operate(self)

    def __eq__(self, other):
        if not isinstance(other, list):
            return False
        if len(self) != len(other):
            return False
        for item1, item2 in zip(self, other):
            if item1 != item2:
                return False
        return True


class OpStack:
    def __init__(self, events, ops=()):
        self.original_events = EventList(deepcopy(events))
        self.ops = list(ops)
        self.undo_ops = []
        self.generate()

    def generate(self):
        'computes all steps from original events'
        self.events = deepcopy(self.original_events)
        for op in self.ops:
            self.events << op

    def push(self, op):
        self.ops.append(op)
        self.events << op

    def undo(self):
        self.undo_ops.append(self.ops.pop())
        self.generate()

    def redo(self):
        self.ops.append(self.undo_ops.pop())
        self.events << self.ops[-1]

    def update(self, index, key, value):
        self.push(UpdateOp(index, key, value))

    def split(self, index, split):
        self.push(SplitOp(index, split))

    def merge(self, index):
        self.push(MergeOp(index))

    def delete(self, index):
        self.push(DeleteOp(index))


def write_stack(filename, opstack):
    ops_dump = [x.dump() for x in opstack.ops]
    save_data = {'operations': ops_dump,
                 'original_events': opstack.original_events}
    with open(filename, 'w') as fp:
        json.dump(save_data, fp)


def read_stack(filename):
    with open(filename, 'r') as fp:
        data = json.load(fp)
    ops = [parse_op(opname, **kwargs) for opname, kwargs in data['operations']]
    return OpStack(data['original_events'], ops)


op_lookup = {k: v
             for k, v in globals().items()
             if isinstance(v, type) and issubclass(v, EventOp)}


def parse_op(opname, **kwargs):
    return op_lookup[opname](**kwargs)
