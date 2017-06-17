from inspect import signature

class Namespace:
    def __init__(self, **kwargs):
        self._internal_ = {}
        self.update(**kwargs)
    def __eq__(self, other):
        return isinstance(other, Namespace) and self._internal_ == other._internal_
    def __len__(self):
        return len(self._internal_)
    def __add__(self, other):
        updated = self._internal_
        updated.update(other._internal_)
        return Namespace(**updated)
    def __contains__(self, key):
        return key in self._internal_
    def __getitem__(self, key):
        try:
            return getattr(self, key)
        except AttributeError as e:
            raise KeyError(str(e))
    def __setitem__(self, key, value):
        setattr(self, key, value)
    def __delitem__(self, key):
        if key in self._internal_:
            delattr(self, key)
        else:
            raise KeyError(key)
    def __getattr__(self, key):
        if key in self.__dict__:
            return self.__dict__[key]
        if key in self._internal_:
            return self._internal_[key]
        raise AttributeError('{} object has no attribute {}'.format(repr(self.__class__.__name__), repr(key)))
    def __setattr__(self, key, value):
        self.__dict__[key] = value
        if not (key.startswith('_') and key.endswith('_')):
            self._internal_[key] = value
    def __delattr__(self, key):
        if key in self._internal_:
            del self._internal_[key]
            del self.__dict__[key]
    def __str__(self):
        return 'Namespace(' + ', '.join('{}={}'.format(k, repr(v)) for k, v in sorted(self._internal_.items())) + ')'
    def update(self, **kwargs):
        for key, value in kwargs.items():
            try:
                stored_value = Namespace.__getattribute__(self, key)
                raise KeyError('{} is reserved and is not allowed as a key'.format(repr(key)))
            except:
                self._internal_[key] = value
                self.__dict__[key] = value
    def keys(self):
        return self._internal_.keys()
    def values(self):
        return self._internal_.values()
    def items(self):
        return self._internal_.items()
    def _expand_order_(self, order):
        order = list(order)
        return order + sorted(set(self.keys()) - set(order))
    def to_tuple(self, order):
        order = self._expand_order_(order)
        return tuple(self[k] for k in order)
    def to_csv_row(self, order):
        order = self._expand_order_(order)
        return '\t'.join(str(self[k]) for k in order)

class MixedRadix:
    def __init__(self, radixes, init_values=None):
        self.radixes = radixes
        if init_values is None:
            self._state_ = len(radixes) * [0]
        else:
            assert len(radixes) == len(init_values)
            assert all(place < cap for place, cap in zip(init_values, radixes))
            self._state_ = list(init_values)
        self._state_[-1] -= 1
    def __iter__(self):
        return self
    def __next__(self):
        return self.next()
    def next(self, min_place=None):
        if min_place is None:
            min_place = len(self._state_) - 1
        for index in range(min_place + 1, len(self._state_)):
            self._state_[index] = 0
        for index in reversed(range(min_place + 1)):
            if self._state_[index] < self.radixes[index] - 1:
                self._state_[index] += 1
                break
            elif index == 0:
                raise StopIteration
            else:
                self._state_[index] = 0
        return self._state_

class ParameterSpaceIterator:
    def __init__(self, pspace, start=None, end=None):
        if start is None:
            start = {}
        if end is None:
            end = {}
        self.pspace = pspace
        start_indices = len(self.pspace.order) * [0]
        for key, value in start.items():
            assert key in self.pspace.independents, 'unknown start parameter: {}'.format(key)
            assert value in self.pspace.independents[key], 'unknown value for start parameter {}: {}'.format(key, repr(value))
            index = self.pspace.order.index(key)
            start_indices[index] = self.pspace.independents[key].index(value)
        self._state_ = MixedRadix(self.pspace.ordered_sizes, start_indices)
        self._end_indices_ = None
        if end:
            self._end_indices_ = len(self.pspace.order) * [0]
            for key, value in end.items():
                assert key in self.pspace.independents, 'unknown end parameter: {}'.format(key)
                assert value in self.pspace.independents[key], 'unknown value for end parameter {}: {}'.format(key, repr(value))
                index = self.pspace.order.index(key)
                self._end_indices_[index] = self.pspace.independents[key].index(value)
    def __iter__(self):
        return self
    def __next__(self):
        conflicts = True
        min_place = len(self.pspace.order) - 1
        while conflicts:
            next_index = self._state_.next(min_place)
            if self._end_indices_ and next_index >= self._end_indices_:
                raise StopIteration
            next_state = self.pspace._get_namespace_from_indices_(next_index)
            conflicts = self._check_filters_(next_state)
            if conflicts:
                min_place = min(max(self.pspace.order.index(parameter) for parameter in parameters) for parameters in conflicts)
        return next_state
    def _check_filters_(self, result):
        conflicts = []
        for fn in self.pspace.filters:
            if not fn(**result):
                conflicts.append(set.union(*(self.pspace.dependency_closure[argument] for argument in fn.arguments)))
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
        self.dependents_topo = []
        self.dependency_closure = {}
        self.constants = {}
        self.filters = []
        self.order = list(order)
        for key, value in kwargs.items():
            if hasattr(value, '__iter__') and not isinstance(value, str):
                self.independents[key] = list(value)
            elif hasattr(value, '__call__'):
                self.dependents[key] = FunctionWrapper(value)
            else:
                self.constants[key] = value
        self._check_order_()
        self._calculate_dependents_topo_()
        self._calculate_dependency_closure_()
        self._simplify_order_()
    def _calculate_dependents_topo_(self):
        prev_count = 0
        while len(self.dependents_topo) < len(self.dependents):
            for key, fn in self.dependents.items():
                if key in self.dependents_topo:
                    continue
                reachables = self.parameters
                if set(fn.arguments) <= reachables:
                    self.dependents_topo.append(key)
            if len(self.dependents_topo) == prev_count:
                unreachables = set(self.dependents.keys()) - set(self.dependents_topo)
                raise ValueError('parameters contain undefined arguments:' + ', '.join(sorted(unreachables)))
            prev_count = len(self.dependents_topo)
    def _calculate_dependency_closure_(self):
        for key in self.independents:
            self.dependency_closure[key] = set([key])
        for key in self.constants:
            self.dependency_closure[key] = set([key])
        for key in self.dependents_topo:
            self.dependency_closure[key] = set.union(set(), *(self.dependency_closure[argument] for argument in self.dependents[key].arguments))
    def _check_order_(self):
        order_set = set(self.order)
        if len(self.order) != len(order_set):
            uniques = set()
            duplicates = set()
            for key in self.independents:
                if key in uniques:
                    duplicates.add(key)
                uniques.add(key)
            raise ValueError('parameter ordering contains duplicates: ' + ', '.join(sorted(duplicates)))
        if order_set != set(self.independents.keys()):
            if not order_set <= self.parameters:
                unreachables = order_set - self.parameters
                raise ValueError('parameter ordering contains undefined parameters: ' + ', '.join(sorted(unreachables)))
            if not set(self.independents.keys()) <= order_set:
                unreachables = set(self.independents.keys()) - order_set
                raise ValueError('parameter ordering is missing independent parameters: ' + ', '.join(sorted(unreachables)))
            if not order_set <= set(self.independents.keys()):
                unreachables = order_set - set(self.independents.keys())
                raise ValueError('parameter ordering contains non-independent parameters: ' + ', '.join(sorted(unreachables)))
    def _simplify_order_(self):
        self.order = [parameter for parameter in self.order if parameter in self.independents]
    @property
    def parameters(self):
        return set.union(
            set(self.independents.keys()),
            set(self.dependents_topo),
            set(self.constants.keys()),
        )
    def __len__(self):
        return len(list(self.__iter__()))
    def __iter__(self):
        return ParameterSpaceIterator(self)
    def iter_from(self, **starting_values):
        return ParameterSpaceIterator(self, **starting_values)
    def add_filter(self, fn):
        wrapped_function = FunctionWrapper(fn)
        if not (set(wrapped_function.arguments) <= self.parameters):
            raise ValueError('filter contains undefined/unreachable arguments')
        self.filters.append(wrapped_function)
