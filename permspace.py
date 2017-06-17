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
    def __delattr__(self, key):
        if key in self._internal_:
            del self._internal_[key]
            del self.__dict__[key]
    def __str__(self):
        return 'Namespace(' + ', '.join('{}={}'.format(k, repr(v)) for k, v in sorted(self.__dict__.items())) + ')'
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

class ParameterSpaceIterator:
    def __init__(self, pspace, start=None, end=None):
        if start is None:
            start = {}
        if end is None:
            end = {}
        self.pspace = pspace
        self._state = len(self.pspace.order) * [0]
        for key, value in start.items():
            assert key in self.pspace.independents, 'unknown start parameter: {}'.format(key)
            assert value in self.pspace.independents[key], 'unknown value for start parameter {}: {}'.format(key, repr(value))
            index = self.pspace.order.index(key)
            self._state[index] = self.pspace.independents[key].index(value)
        self._state[-1] -= 1
        self._end_state = None
        if end:
            self._end_state = len(self.pspace.order) * [0]
            for key, value in end.items():
                assert key in self.pspace.independents, 'unknown end parameter: {}'.format(key)
                assert value in self.pspace.independents[key], 'unknown value for end parameter {}: {}'.format(key, repr(value))
                index = self.pspace.order.index(key)
                self._end_state[index] = self.pspace.independents[key].index(value)
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
            largest_index = len(self._state) - 1
        for index in range(largest_index + 1, len(self._state)):
            self._state[index] = 0
        parameters = self.pspace.order[:largest_index + 1]
        for index, parameter in reversed(tuple(enumerate(parameters))):
            if self._state[index] < len(self.pspace.independents[parameter]) - 1:
                self._state[index] += 1
                if self._end_state and self._state >= self._end_state:
                    raise StopIteration
                break
            elif index == 0:
                raise StopIteration
            else:
                self._state[index] = 0
    def _expand_values_(self):
        result = Namespace()
        for parameter, index in zip(self.pspace.order, self._state):
            value = self.pspace.independents[parameter][index]
            result[parameter] = value
        for parameter in self.pspace.independents.keys():
            if parameter not in result:
                result[parameter] = self.pspace.independents[parameter][0]
        for parameter, value in self.pspace.constants.items():
            result[parameter] = value
        for parameter in self.pspace.dependents_topo:
            fn = self.pspace.dependents[parameter]
            result[parameter] = fn(**result)
        return result
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
        self._calculate_dependents_topo_()
        self._calculate_dependency_closure_()
        self._check_order_()
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
        if not (order_set <= self.parameters):
            unreachables = order_set - self.parameters
            raise ValueError('parameter ordering contains undefined parameters: ' + ', '.join(sorted(unreachables)))
        if not (set(self.independents.keys()) <= order_set):
            unreachables = set(self.independents.keys()) - order_set
            raise ValueError('parameter ordering is missing independent parameters: ' + ', '.join(sorted(unreachables)))
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
