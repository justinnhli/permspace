from inspect import signature


class Namespace:

    def __init__(self, **kwargs):
        self._internal = {}
        self.update_(**kwargs)

    def __eq__(self, other):
        return isinstance(other, Namespace) and self._internal == other._internal_

    def __len__(self):
        return len(self._internal)

    def __add__(self, other):
        updated = self._internal_
        updated.update(other._internal_)
        return Namespace(**updated)

    def __contains__(self, key):
        return key in self._internal_

    def __getitem__(self, key):
        try:
            return getattr(self, key)
        except AttributeError as err:
            raise KeyError(str(err))

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def __delitem__(self, key):
        if key in self._internal:
            delattr(self, key)
        else:
            raise KeyError(key)

    def __getattr__(self, key):
        if key in self.__dict__:
            return self.__dict__[key]
        if key in self._internal:
            return self._internal[key]
        raise AttributeError('{} object has no attribute {}'.format(repr(self.__class__.__name__), repr(key)))

    def __setattr__(self, key, value):
        self.__dict__[key] = value
        if not (key.startswith('_') and key.endswith('_')):
            self._internal[key] = value

    def __delattr__(self, key):
        if key in self._internal:
            del self._internal[key]
            del self.__dict__[key]

    def __repr__(self):
        return 'Namespace(' + ', '.join('{}={}'.format(k, repr(v)) for k, v in sorted(self._internal.items())) + ')'

    def __str__(self):
        return repr(self)

    def update_(self, **kwargs):
        invalid_keys = set(kwargs.keys()).intersection(dir(self))
        if invalid_keys:
            message = '\n'.join([
                'The following are reserved and not allowed as keys:',
                *(f'    {key}' for key in sorted(invalid_keys)),
            ])
            raise ValueError(message)
        self._internal.update(kwargs)
        self.__dict__.update(kwargs)

    def keys_(self):
        return self._internal.keys()

    def values_(self):
        return self._internal.values()

    def items_(self):
        return self._internal.items()

    def _expand_order(self, order):
        order = list(order)
        return order + sorted(set(self.keys()) - set(order))

    def to_tuple_(self, order):
        order = self._expand_order(order)
        return tuple(self[k] for k in order)

    def to_dict_(self):
        return self._internal_

    def to_csv_row_(self, order):
        order = self._expand_order(order)
        return '\t'.join(str(self[k]) for k in order)


class MixedRadix:

    def __init__(self, radixes, init_values=None):
        self.radixes = radixes
        if init_values is None:
            self._state = len(radixes) * [0]
        else:
            assert len(radixes) == len(init_values)
            assert all(place < cap for place, cap in zip(init_values, radixes))
            self._state = list(init_values)
        self._state[-1] -= 1

    def __iter__(self):
        return self

    def __next__(self):
        return self.next()

    def next(self, min_place=None):
        if min_place is None:
            min_place = len(self._state) - 1
        for index in range(min_place + 1, len(self._state)):
            self._state[index] = 0
        for index in reversed(range(min_place + 1)):
            if self._state[index] < self.radixes[index] - 1:
                self._state[index] += 1
                break
            elif index == 0:
                raise StopIteration
            else:
                self._state[index] = 0
        return self._state_


class ParameterSpaceIterator:

    def __init__(self, pspace, start=None, end=None):
        if start is None:
            start = {}
        elif isinstance(start, Namespace):
            start = start.to_dict_()
        if end is None:
            end = {}
        elif isinstance(end, Namespace):
            end = end.to_dict_()
        self.pspace = pspace
        start_indices = len(self.pspace.order) * [0]
        for key, value in start.items():
            assert key in self.pspace.independents, 'unknown start parameter: {}'.format(key)
            assert value in self.pspace.independents[key], \
                'unknown value for start parameter {}: {}'.format(key, repr(value))
            index = self.pspace.order.index(key)
            start_indices[index] = self.pspace.independents[key].index(value)
        self._state = MixedRadix(self.pspace.ordered_sizes, start_indices)
        self._end_indices = None
        if end:
            self._end_indices = len(self.pspace.order) * [0]
            for key, value in end.items():
                assert key in self.pspace.independents, 'unknown end parameter: {}'.format(key)
                assert value in self.pspace.independents[key], \
                    'unknown value for end parameter {}: {}'.format(key, repr(value))
                index = self.pspace.order.index(key)
                self._end_indices[index] = self.pspace.independents[key].index(value)

    def __iter__(self):
        return self

    def __next__(self):
        conflicts = True
        min_place = len(self.pspace.order) - 1
        while conflicts:
            next_index = self._state.next(min_place)
            if self._end_indices and next_index >= self._end_indices:
                raise StopIteration
            next_state = self.pspace._get_namespace_from_indices_(next_index)
            conflicts = self._check_filters(next_state)
            if conflicts:
                min_place = min(
                    max(self.pspace.order.index(parameter) for parameter in parameters) for parameters in conflicts
                )
        return next_state

    def _check_filters_(self, result):
        conflicts = []
        for func in self.pspace.filters:
            if not func(**result.to_dict_()):
                conflicts.append(set.union(*(self.pspace.dependency_closure[argument] for argument in func.arguments)))
        return conflicts


class FunctionWrapper:

    def __init__(self, func):
        self.func = func
        self.arguments = tuple(signature(self.func).parameters.keys())

    def __call__(self, **kwargs):
        return self.func(**dict((k, v) for k, v in kwargs.items() if k in self.arguments))


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
        self._check_order()
        self._calculate_dependents_topo()
        self._calculate_dependency_closure()
        self._simplify_order()

    def __getitem__(self, key):
        if key in self.independents:
            return self.independents[key]
        if key in self.dependents:
            return self.dependents[key]
        if key in self.constants:
            return self.constants[key]
        raise KeyError(f'no parameter {key}; possible choices are {", ".join(self.parameters)}')

    def _calculate_dependents_topo_(self):
        prev_count = 0
        while len(self.dependents_topo) < len(self.dependents):
            for key, func in self.dependents.items():
                if key in self.dependents_topo:
                    continue
                reachables = self.parameters
                if set(func.arguments) <= reachables:
                    self.dependents_topo.append(key)
            if len(self.dependents_topo) == prev_count:
                unreachables = set(self.dependents.keys()) - set(self.dependents_topo)
                raise ValueError('undefined arguments in parameter: ' + ', '.join(sorted(unreachables)))
            prev_count = len(self.dependents_topo)

    def _calculate_dependency_closure_(self):
        for key in self.independents:
            self.dependency_closure[key] = set([key])
        for key in self.constants:
            self.dependency_closure[key] = set([key])
        for key in self.dependents_topo:
            self.dependency_closure[key] = set.union(
                set(), *(self.dependency_closure[argument] for argument in self.dependents[key].arguments)
            )

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
                raise ValueError(
                    'parameter ordering is missing independent parameters: ' + ', '.join(sorted(unreachables))
                )
            if not order_set <= set(self.independents.keys()):
                unreachables = order_set - set(self.independents.keys())
                raise ValueError(
                    'parameter ordering contains non-independent parameters: ' + ', '.join(sorted(unreachables))
                )

    def _simplify_order_(self):
        self.order = [parameter for parameter in self.order if parameter in self.independents]

    @property
    def parameters(self):
        return set.union(
            set(self.independents.keys()),
            set(self.dependents_topo),
            set(self.constants.keys()),
        )

    @property
    def approximate_size(self):
        product = 1
        for values in self.independents.values():
            product *= len(values)
        return product

    @property
    def ordered_sizes(self):
        return [len(self.independents[parameter]) for parameter in self.order]

    def __len__(self):
        return len(list(self.__iter__()))

    def __iter__(self):
        return ParameterSpaceIterator(self)

    def iter_from(self, start=None):
        return ParameterSpaceIterator(self, start=start)

    def iter_until(self, end=None):
        return ParameterSpaceIterator(self, end=end)

    def iter_between(self, start=None, end=None):
        return ParameterSpaceIterator(self, start=start, end=end)

    def iter_only(self, key, value):
        start_index = len(self.order) * [0]
        key_index = self.order.index(key)
        value_index = self.independents[key].index(value)
        start_index[key_index] = value_index
        end_index = MixedRadix(self.ordered_sizes, start_index).next(key_index)
        start = self._get_independents_from_indices(start_index)
        end = self._get_independents_from_indices(end_index)
        return ParameterSpaceIterator(self, start=start, end=end)

    def add_filter(self, filter_func):
        wrapped_function = FunctionWrapper(filter_func)
        if not set(wrapped_function.arguments) <= self.parameters:
            raise ValueError('filter contains undefined/unreachable arguments')
        self.filters.append(wrapped_function)

    def _get_independents_from_indices_(self, indices):
        assert len(indices) == len(self.order)
        assert all(index < len(self.independents[key]) for index, key in zip(indices, self.order))
        result = Namespace()
        for parameter, index in zip(self.order, indices):
            result[parameter] = self.independents[parameter][index]
        return result

    def _get_namespace_from_indices_(self, indices):
        result = self._get_independents_from_indices(indices)
        for parameter, value in self.constants.items():
            result[parameter] = value
        for parameter in self.dependents_topo:
            result[parameter] = self.dependents[parameter](**result.to_dict_())
        return result