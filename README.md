# PermSpace

`PermSpace` is a Python module that allows easy iteration over permutation space, similar to (but more powerful than) the built-in [`itertools.product`](https://docs.python.org/dev/library/itertools.html#itertools.product). The intended use case is for sweeping a parameter space when running computational experiments; this use case is reflected in the names of variables and methods.

## Usage

The module exposes a single class `PermutationSpace`.

### `class` **`PermutationSpace`**

This class represents the space over which parameters can exist. The simplest usage is as a replacement for `itertools.product`. The following example resembles the result of `product(range(1,3), 'ab', ['i', 'ii'])`:

```python
pspace = PermutationSpace(['question', 'part', 'subpart'],
    question=range(1,3),
    part=list('ab'),
    subpart=['i', 'ii'],
)

print(len(pspace)) # 8

for parameters in pspace:
    print(parameters.question, parameters.part, parameters.subpart)

# 1 a i
# 1 a ii
# 1 b i
# 1 b ii
# 2 a i
# 2 a ii
# 2 b i
# 2 b ii
```

However, a `PermutationSpace` allows for *dependent* parameters, which are parameters are defined based on the values of other parameters. For example:

```python
pspace = PermutationSpace(['question', 'part', 'subpart'],
    question=range(1,3),
    part=list('ab'),
    subpart=['i', 'ii'],
    subpart_name=(lambda question, part, subpart: '.'.join([str(question), part, subpart])),
)
for parameters in pspace:
    print(parameters.subpart_name)

# 1.a.i
# 1.a.ii
# 1.b.i
# 1.b.ii
# 2.a.i
# 2.a.ii
# 2.b.i
# 2.b.ii
```

The dependent parameters can themselves be depended upon. The following gives the same output as the above:


```python
pspace = PermutationSpace(['question', 'part', 'subpart'],
    question=range(1,3),
    part=list('ab'),
    subpart=['i', 'ii'],
    part_name=(lambda question, part: str(question) + '.' + part),
    subpart_name=(lambda part_name, subpart: part_name + '.' + subpart),
)
for parameters in pspace:
    print(parameters.subpart_name)
```

Additionally, a `PermutationSpace` can be *filtered* by boolean functions. As a trivial example, the following code would only give even-numbered coordinates:

```python
pspace = PermutationSpace(['x', 'y'],
    x=range(10),
    y=range(10),
)
pspace.filter((lambda x, y: x % 2 == y % 2 == 0))
for parameters in pspace:
    print(parameters.x, parameters.y)
```

## Documentation

Instance attributes (read-only):

* `PermutationSpace`. **`parameters`**: The `set` of all parameters names in this `PermutationSpace` instance.

Instance methods:

* `PermutationSpace(order, **kwargs)`: The `order` argument of the construct is the order in which parameter values should be changed, listed from most significant (changes least frequently) to least significant (changes most frequently). All other arguments are parameters.
                     
* `PermutationSpace`. **`filter`** `(filter_func)`: Filter the permutation space. The `filter_func` argument should be a function whose parameters are the same as a subset of the parameters for the `PermutationSpace`. Iteration on the `PermutationSpace` will not include any parameter sets were the function returns false. Multiple filters can be added to the same `PermutationSpace`.

* `PermutationSpace`. **`filter_if`** `(antecedent_func, consequent_func)`: Conditionally filter the permutation space. If the `antecedent_func` is true, then only the parameter sets where the `consequent_func` is also true will be allowed. This is mostly a convenience method, since by classical logic, `filter_if(A, B)` (where `A` and `B` are conditions) is equivalent to `filter(not A or B)`.

* `PermutationSpace`. **`filter_orthog`** `(k=1, **defaults)`: Filter the permutation space so the parameters defined in `defaults` will have the default value, with at most `k` parameters being different. Useful for exploring parameters independent of each other.

* `PermutationSpace`. **`__iter__`** `()`: The standard iteration method, which returns a generator of all permutations of the space.

* `PermutationSpace`. **`iter_from`** `(start=None, skip=0)`: Same as the standard `__iter__` function, except that it starts at (inclusive) the given dictionary of values. The `skip` argument skips however many permutations at the beginning.
                     
* `PermutationSpace`. **`iter_until`** `(end=None, skip=0)`: Same as the standard `__iter__` function, except that it ends at (exclusive) the given dictionary of values. The `skip` argument skips however many permutations at the beginning.
                     
* `PermutationSpace`. **`iter_between`** `(start=None, end=None, skip=0)`: Same as the standard `__iter__` function, except that it starts at (inclusive) and ends at (exclusive) the given dictionaries of values. The `skip` argument skips however many permutations at the beginning.

## Change Log

### 0.0.6 (next)

* add `filter_orthog` method

### 0.0.5 (2019-06-03)

* raise `ValueError` if independent parameter is not iterable
* cache dependent parameter function calls
* add `filter_if` convenience method

### 0.0.4 (2019-03-11)

* hide `parameter` in `PermutationSpace`

### 0.0.3 (2019-03-06)

* convert `filter()` to a fluent interface
* add `index_` and `uniqstr_` attributes to `Namespace`
* fix iteration bug if filtered

### 0.0.2 (2019-03-01)

* rewrite module
* rename `add_filter()` to `filter()` in `PermutationSpace`

### 0.0.1 (2019-01-11)

* release minimum viable product with `iter_*` and `add_filter`.
