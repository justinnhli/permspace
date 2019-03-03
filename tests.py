from unittest import TestCase, main
from itertools import product

import pytest

from permspace import PermutationSpace


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

    # filter
    pspace.filter((lambda arabic: arabic < 3))
    assert len(pspace) == 18
    with pytest.raises(ValueError):
        pspace.filter((lambda undefined: undefined is None))

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

    # iter_from
    assert len(list(pspace.iter_from({'arabic': 3,}))) == 9

    # iter_until
    assert len(list(pspace.iter_until({'arabic': 2,}))) == 9

    # iter_between
    assert len(list(pspace.iter_between(
        {'arabic': 1,},
        {'arabic': 2,},
    ))) == 9

    # iter_between with skip
    assert len(list(pspace.iter_between(
        {'arabic': 1,},
        {'arabic': 2,},
        skip=4,
    ))) == 5

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
