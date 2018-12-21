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
pspace.add_filter((lambda x, y: x % 2 == y % 2 == 0))
for parameters in pspace:
	print(parameters.x, parameters.y)
```

Instance attributes (read-only):

* `PermutationSpace`. **`parameters`**: The `set` of all parameters names in this `PermutationSpace` instance.
                     
* `PermutationSpace`. **`approximate_size`**: An over-estimate of the size of the parameter, calculated as the product of the space of all independent parameters (without filtering).
                     
* `PermutationSpace`. **`ordered_sizes`**: A list of the sizes of each dependent parameter, in the given order.

Instance methods:

* `PermutationSpace(order, **kwargs)`: The `order` argument of the construct is the order in which parameter values should be changed, listed from most significant (changes least frequently) to least significant (changes most frequently).

* `PermutationSpace`. **`iter_from`** `(**kwargs)`:
                     
* `PermutationSpace`. **`iter_until`** `(**kwargs)`:
                     
* `PermutationSpace`. **`iter_between`** `(**kwargs)`:
                     
* `PermutationSpace`. **`iter_only`** `(**kwargs)`:
                     
* `PermutationSpace`. **`add_filter`** `(boolean_fn)`:

### `class` **`Namespace`**
