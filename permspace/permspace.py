"""A more powerful itertools.product."""

from collections import defaultdict, namedtuple
from inspect import signature


class PermutationSpace:
    """The space of permutations of iterables."""

    Parameter = namedtuple('Parameter', 'name, value, independencies, parameters')
    FilterFunction = namedtuple('FilterFunction', 'function, parameters, min_place')

    def __init__(self, order, **kwargs):
        """Initialize the PermutationSpace.

        Arguments:
            order (Sequence[str]): The order to permute the arguments.
            kwargs: Parameters to permute.
        """
        self.order = order
        self._parameters = {}
        self.filters = []
        self.order = list(order)
        self.topological_order = []
        self.cache = defaultdict(dict)
        self._process_parameters(kwargs)
        self._check_order()
        self.namespace_class = self._create_namespace_class(*self.topological_order)

    def _process_parameters(self, parameters):
        """Parse parameters into a usable format for later.

        1. Create Parameter objects that contain useful information
        2. Sort parameters topologically so we can calculate their values in
        one pass in the future.
        """
        constants = set()
        dependents = []
        dependencies = {}
        # process parameters depending on whether they are independent, dependent, or constants
        for parameter, value in parameters.items():
            if parameter in self.order:
                # independent parameters
                if not hasattr(value, '__iter__'):
                    raise ValueError(f'parameter "{parameter}" is not iterable: {value}')
                self._parameters[parameter] = PermutationSpace.Parameter(
                    parameter,
                    tuple(value),
                    set([parameter]),
                    set(),
                )
            elif hasattr(value, '__call__'):
                # dependent parameters
                dependencies[parameter] = set(signature(value).parameters)
            else:
                # constants
                self._parameters[parameter] = PermutationSpace.Parameter(
                    parameter,
                    value,
                    set([parameter]),
                    set(),
                )
                constants.add(parameter)
        # initialize the topological order with independent parameters
        self.topological_order.extend(self.order)
        # loop through dependents until they have all been added to the topological order
        to_delete = set(['__dummy__'])
        while to_delete and dependencies:
            to_delete = set()
            for parameter, parents in dependencies.items():
                if parents <= self._parameters.keys():
                    to_delete.add(parameter)
                    self._parameters[parameter] = PermutationSpace.Parameter(
                        parameter,
                        parameters[parameter],
                        self._get_dependencies(dependencies[parameter]),
                        parents,
                    )
                    dependents.append(parameter)
            if not to_delete and dependencies:
                raise ValueError(f'undefined arguments in parameters: {list(dependencies.keys())}')
            for parameter in to_delete:
                del dependencies[parameter]
        # add constants and dependent parameters  to the topological order at the end
        self.topological_order.extend(sorted(constants))
        self.topological_order.extend(dependents)

    def _check_order(self):
        """Check that the order of significance is valid.

        This means that the order:
        * contains only unique values
        * does not contain undefined values
        * does not contain un-iterable values
        """
        seen = set()
        for parameter in self.order:
            if parameter not in self._parameters:
                raise ValueError(f'parameter "{parameter}" in ordering not defined')
            if parameter in seen:
                raise ValueError(f'parameter "{parameter}" listed twice in ordering')
            if not hasattr(self[parameter], '__iter__'):
                raise ValueError(f'parameter "{parameter}" is not iterable')
            if isinstance(self[parameter], str):
                raise ValueError(f'parameter "{parameter}" is a string')
            seen.add(parameter)

    def _get_dependencies(self, parameters):
        """Get the dependencies of a set of parameters.

        Arguments:
            parameters (Iterable[str]): A collection of parameters.

        Returns:
            Set[str]: The set of independent parameters the arguments are
                dependent on.
        """
        return set().union(
            set(),
            *(self._parameters[parameter].independencies for parameter in parameters),
        )

    def __getitem__(self, key):
        return self._parameters[key].value

    def __len__(self):
        return len(list(self.__iter__()))

    def __iter__(self):
        yield from self.iter_between()

    @property
    def parameters(self):
        return {key: param.value for key, param in self._parameters.items()}

    def filter(self, filter_func):
        """Filter the permutation space.

        To efficiently skip the filtered parts of the permutation space, we
        cache the least significant argument of each filter. If a permutation
        is filtered, we then find the most significant of these arguments.
        Since changing anything less significant will not change the result of
        that filter, we know we directly increment that parameter instead.

        Arguments:
            filter_func (Callable[[*Any], bool]): A function that returns True
                only if a permutation is allowed.

        Returns:
            PermutationSpace: The current permutation space.

        Raises:
            ValueError: If the filter contains undefined arguments.
        """
        parameters = signature(filter_func).parameters.keys()
        if not parameters <= self._parameters.keys():
            raise ValueError('filter contains undefined parameters')
        min_place_arg = max(
            self._get_dependencies(parameters),
            key=self.order.index,
        )
        self.filters.append(PermutationSpace.FilterFunction(
            filter_func,
            parameters,
            self.order.index(min_place_arg),
        ))
        return self

    def filter_if(self, antecedent_func, consequent_func):
        parameters = (
            set(signature(antecedent_func).parameters.keys())
            | set(signature(consequent_func).parameters.keys())
        )
        min_place_arg = max(
            self._get_dependencies(parameters),
            key=self.order.index,
        )
        self.filters.append(PermutationSpace.FilterFunction(
            self._create_filter_if_func(antecedent_func, consequent_func),
            parameters,
            self.order.index(min_place_arg),
        ))
        return self

    def iter_from(self, start=None, skip=0):
        """Iterate starting from a particular assignment of values.

        Arguments:
            start (Mapping[str, Any]): The inclusive starting assignment of values.
            skip (int): The number of permutations to skip at the beginning.
                Defaults to 0.

        Yields:
            Namespace: The sequences of values through the permutation space.
        """
        yield from self.iter_between(start=start, skip=skip)

    def iter_until(self, end=None, skip=0):
        """Iterate ending with a particular assignment of values.

        Arguments:
            end (Mapping[str, Any]): The exclusive ending assignment of values.
            skip (int): The number of permutations to skip at the beginning.
                Defaults to 0.

        Yields:
            Namespace: The sequences of values through the permutation space.
        """
        yield from self.iter_between(end=end, skip=skip)

    def iter_between(self, start=None, end=None, skip=0):
        """Iterate between two particular assignments of values.

        Arguments:
            start (Mapping[str, Any]): The inclusive starting assignment of values.
            end (Mapping[str, Any]): The exclusive ending assignment of values.
            skip (int): The number of permutations to skip at the beginning.
                Defaults to 0.

        Yields:
            Namespace: The sequences of values through the permutation space.
        """
        if start is None:
            curr_index = (len(self.order) - 1) * [0] + [-1]
        else:
            curr_index = self._dict_to_index(start)
            curr_index[-1] -= 1
        if end is None:
            end_index = len(self.order) * [float('inf')]
        else:
            end_index = self._dict_to_index(end)
        count = 0
        while curr_index < end_index:
            change_place = len(self.order) - 1
            while change_place is not None:
                curr_index = self._increment_index(curr_index, change_place)
                if curr_index is None:
                    return
                change_place = None
                values = self._index_to_namespace(count, curr_index)
                for filter_func in self.filters:
                    filter_result = filter_func.function(**{
                        parameter: getattr(values, parameter)
                        for parameter in filter_func.parameters
                    })
                    if not filter_result:
                        if change_place is None or filter_func.min_place < change_place:
                            change_place = filter_func.min_place
            if curr_index < end_index:
                count += 1
                if skip < count:
                    yield values

    def _dict_to_index(self, values):
        for parameter, value in values.items():
            if parameter not in self._parameters:
                raise ValueError(f'no parameter "{parameter}"')
            if value not in self._parameters[parameter].value:
                raise ValueError(f'{repr(value)} is not a valid value of parameter "{parameter}"')
        result = []
        for parameter in self.order:
            if parameter in values:
                result.append(self._parameters[parameter].value.index(values[parameter]))
            else:
                result.append(0)
        return result

    def _index_to_namespace(self, count, index):
        result = {}
        for parameter, i in zip(self.order, index):
            result[parameter] = self._parameters[parameter].value[i]
        for parameter in self.topological_order[len(self.order):]:
            parameter = self._parameters[parameter]
            if parameter.parameters:
                key = tuple(result[key] for key in sorted(parameter.parameters))
                if key not in self.cache[parameter.name]:
                    self.cache[parameter.name][key] = parameter.value(**{
                        key: result[key] for key in parameter.parameters
                    })
                result[parameter.name] = self.cache[parameter.name][key]
            else:
                result[parameter.name] = parameter.value
        return self.namespace_class(self, count, **result)

    def _increment_index(self, index, change_place=None):
        if change_place is None:
            change_place = len(self.order) - 1
        for place in range(change_place, -1, -1):
            parameter = self.order[place]
            index[place] += 1
            index[place + 1:] = (len(self.order) - place - 1) * [0]
            if index[place] >= len(self._parameters[parameter].value):
                index[place] = 0
            else:
                return index
        return None

    @staticmethod
    def _create_namespace_class(*parameters):

        class Namespace(namedtuple('Namespace', ['pspace_', 'index_', *parameters])):

            def __str__(self):
                result = super().__str__()
                import re
                result = re.sub(r'Namespace\(pspace_=<[^>]*>, ', 'Namespace(', result)
                return result

            @property
            def uniqstr_(self):
                return ','.join(
                    f'{parameter}={getattr(self, parameter)}'
                    for parameter in self.pspace_.order
                )

        return Namespace

    @staticmethod
    def _create_filter_if_func(antecedent_func, consequent_func):
        antecedent_params = set(signature(antecedent_func).parameters.keys())
        consequent_params = set(signature(consequent_func).parameters.keys())
        def if_func(**kwargs):
            antecedent_args = {
                k: v for k, v in kwargs.items()
                if k in antecedent_params
            }
            consequent_args = {
                k: v for k, v in kwargs.items()
                if k in consequent_params
            }
            return (
                not antecedent_func(**antecedent_args)
                or consequent_func(**consequent_args)
            )
        return if_func
