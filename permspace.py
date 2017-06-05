from types import GeneratorType
from inspect import signature

class Namespace:
    def __init__(self, **kwargs):
        self.update(**kwargs)
    def __eq__(self, other):
        return isinstance(other, Namespace) and vars(self) == vars(other)
    def __len__(self):
        return len(self.__dict__)
    def __add__(self, other):
        updated = self.__dict__
        updated.update(other.__dict__)
        return Namespace(**updated)
    def __contains__(self, key):
        return key in self.__dict__
    def __getitem__(self, key):
        if key in self.__dict__:
            return self.__dict__[key]
        raise KeyError(key)
    def __setitem__(self, key, value):
        setattr(self, key, value)
    def __delitem__(self, key):
        if key in self.__dict__:
            delattr(self, key)
        raise KeyError(key)
    def __str__(self):
        return 'Namespace(' + ', '.join('{}={}'.format(k, repr(v)) for k, v in sorted(self.__dict__.items())) + ')'
    def update(self, **kwargs):
        for key, value in kwargs.items():
            self[key] = value
    def keys(self):
        return self.__dict__.keys()
    def values(self):
        return self.__dict__.values()
    def items(self):
        return self.__dict__.items()
    def to_tuple(self, order):
        return tuple(self[k] for k in order)
    def to_csv_row(self, order):
        return '\t'.join(str(self[k]) for k in order)

class ParameterSpaceIterator:
    def __init__(self, pspace):
        self.pspace = pspace
        self.state = (len(self.pspace.order) - 1) * [0] + [-1]
    def __iter__(self):
        return self
    def __next__(self):
        self._update_state_()
        result = self._expand_values_()
        conflicts = self._check_filters_(result)
        while conflicts:
            largest_index = min(max(self.pspace.order.index(parameter) for parameter in parameters) for parameters in conflicts)
            self._update_state_(largest_index=largest_index)
            result = self._expand_values_()
            conflicts = self._check_filters_(result)
        return result
    def _update_state_(self, largest_index=None):
        if largest_index is None:
            largest_index = len(self.state) - 1
        for index in range(largest_index + 1, len(self.state)):
            self.state[index] = 0
        parameters = self.pspace.order[:largest_index + 1]
        for index, parameter in reversed(tuple(enumerate(parameters))):
            if self.state[index] < len(self.pspace.independents[parameter]) - 1:
                self.state[index] += 1
                break
            elif index == 0:
                raise StopIteration
            else:
                self.state[index] = 0
    def _expand_values_(self):
        result = Namespace()
        for parameter, index in zip(self.pspace.order, self.state):
            value = self.pspace.independents[parameter][index]
            result[parameter] = value
        for parameter in self.pspace.independents.keys():
            if parameter not in result:
                result[parameter] = self.pspace.independents[parameter][0]
        changed = True
        while changed:
            changed = False
            for parameter in sorted(self.pspace.dependents.keys()):
                if parameter not in result:
                    try:
                        result[parameter] = self.pspace.dependents[parameter](**result)
                        changed = True
                    except TypeError:
                        pass
        return result
    def _check_filters_(self, result):
        conflicts = []
        for fn in self.pspace.filters:
            if not fn(**result):
                conflicts.append(set.union(*(self.pspace.dependencies[argument] for argument in fn.arguments)))
        return conflicts

class FunctionWrapper:
    def __init__(self, fn):
        self.fn = fn
        self.arguments = tuple(signature(self.fn).parameters.keys())
    def __call__(self, **kwargs):
        return self.fn(**dict((k, v) for k, v in kwargs.items() if k in self.arguments))

class PermutationSpace:
    def __init__(self, order, **kwargs):
        self.independents = {}
        self.dependents = {}
        self.filters = []
        self.dependencies = {}
        for key, value in kwargs.items():
            if isinstance(value, tuple):
                self.independents[key] = value
            elif any(isinstance(value, t) for t in (list, range, GeneratorType)):
                self.independents[key] = tuple(value)
            elif hasattr(value, '__call__'):
                self.dependents[key] = FunctionWrapper(value)
            else:
                self.independents[key] = (value,)
        order = tuple(order)
        if len(order) != len(set(order)):
            raise ValueError('order contains duplicates')
        if not (set(order) <= set(self.independents.keys())):
            raise ValueError('order contains undefined/unreachable arguments')
        for parameter, values in self.independents.items():
            if len(values) > 1 and parameter not in order:
                raise ValueError('variable parameter "{}" not in `order`'.format(parameter))
        self.order = tuple(set(self.independents.keys()) - set(order)) + order
        for parameter in self.independents:
            self.dependencies[parameter] = set([parameter,])
        changed = True
        while changed:
            changed = False
            for parameter, fn in self.dependents.items():
                if parameter in self.dependencies:
                    continue
                if all((argument in self.dependencies) for argument in fn.arguments):
                    self.dependencies[parameter] = set.union(set(*(self.dependencies[argument] for argument in fn.arguments)))
                    changed = True
        if len(self.dependencies) != len(self.independents) + len(self.dependents):
            raise ValueError('parameter contains undefined/unreachable arguments')
    def __len__(self):
        return len(list(self.__iter__()))
    def __iter__(self):
        return ParameterSpaceIterator(self)
    def add_filter(self, fn):
        wrapped_function = FunctionWrapper(fn)
        if not (set(wrapped_function.arguments) <= set(self.dependencies.keys())):
            raise ValueError('filter contains undefined/unreachable arguments')
        self.filters.append(wrapped_function)

def main():
    pspace = PermutationSpace(('decay_rate', 'spreading_depth', 'word'),
        word=('anger', 'army', 'black', 'bread', 'car', 'chair', 'city', 'cold', 'cup', 'doctor', 'flag', 'foot', 'fruit', 'girl', 'high', 'king', 'lion', 'man', 'mountain', 'music', 'needle', 'pen', 'river', 'rough', 'rubber', 'shirt', 'sleep', 'slow', 'smell', 'smoke', 'soft', 'spider', 'sweet', 'thief', 'trash', 'window'),
        spreading_depth=range(1, 7),
        decay_rate=(0.5, 0.25, 0.75, 0.9),
        boost_decay=1,
    )
    for parameters in pspace:
        print(parameters)

if __name__ == '__main__':
    main()
