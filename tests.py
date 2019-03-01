from unittest import TestCase, main
from itertools import product

import pytest

from permspace import Namespace, PermutationSpace

def test_namespace():

    key = 'test_key'
    value = 0
    namespace = Namespace(**{key: value})

    # basic usage
    assert list(namespace.keys_()) == ['test_key']
    assert namespace.test_key == namespace['test_key'] == 0

    # update
    namespace.test_key = 1
    assert list(namespace.keys_()) == ['test_key']
    assert namespace.test_key == namespace['test_key'] == 1
    namespace['test_key'] = 2
    assert sorted(namespace.keys_()) == ['test_key']
    assert namespace.test_key == namespace['test_key'] == 2

    # delete
    del namespace.test_key
    assert not hasattr(namespace, 'test_key')
    assert 'test_key' not in namespace
    namespace.test_key = 2
    del namespace['test_key']
    assert not hasattr(namespace, 'test_key')
    assert 'test_key' not in namespace


def test_permspace():
    pspace = PermutationSpace(
        ['arabic', 'letter_lower', 'roman_lower'],
        arabic=range(1, 4),
        letter_lower=list('abc'),
        roman_lower=['i', 'ii', 'iii'],
        question_name=(lambda arabic: str(arabic)),
        part_name=(lambda question_name, letter_lower: question_name + '.' + letter_lower),
        subpart_name=(lambda part_name, roman_lower: part_name + '.' + roman_lower),
        constant='constant',
    )

    # basic usage
    assert len(pspace) == 27
    assert pspace.order == ['arabic', 'letter_lower', 'roman_lower']
    subpart_names = [parameters.subpart_name for parameters in pspace]
    correct_subpart_names = [
        '.'.join(values) for values in product('123', 'abc', ['i', 'ii', 'iii'])
    ]
    assert subpart_names == correct_subpart_names
    assert pspace.dependents_topo == ['question_name', 'part_name', 'subpart_name']

    # filter
    pspace.add_filter((lambda arabic: arabic < 3))
    assert len(pspace) == 18
    with pytest.raises(ValueError):
        pspace.add_filter((lambda undefined: undefined is None))

    # iter_from
    assert sum(
        1 for parameters
        in pspace.iter_from(Namespace(arabic=2))
    ) == 9

    # iter_only
    assert sum(
        1 for parameters
        in pspace.iter_only('letter_lower', 'b')
    ) == 3

    # ordering errors
    with pytest.raises(ValueError):
        PermutationSpace(
            ['arabic', 'arabic'],
            arabic=range(1, 4),
        )
    with pytest.raises(ValueError):
        PermutationSpace(
            ['arabic', 'letter_lower'],
            arabic=range(1, 4),
        )
    with pytest.raises(ValueError):
        PermutationSpace(
            ['arabic'],
            arabic=range(1, 4),
            letter_lower=list('abc'),
        )
