from copy import deepcopy
from unittest import TestCase, main
from itertools import product

import pytest

from permspace import PermutationSpace


def test_permspace():
    orig_pspace = PermutationSpace(
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
    pspace = deepcopy(orig_pspace)
    assert len(pspace) == 27
    assert pspace.order == ['arabic', 'letter_lower', 'roman_lower']
    subpart_names = [parameters.subpart_name for parameters in pspace]
    correct_subpart_names = [
        '.'.join(values) for values in product('123', 'abc', ['i', 'ii', 'iii'])
    ]
    assert subpart_names == correct_subpart_names
    assert next(iter(pspace)).uniqstr_ == 'arabic=1,letter_lower=a,roman_lower=i'

    # filter
    pspace = deepcopy(orig_pspace)
    pspace.filter((lambda arabic: arabic < 3))
    assert len(pspace) == 18
    with pytest.raises(ValueError):
        pspace.filter((lambda undefined: undefined is None))


    # iter_from
    pspace = deepcopy(orig_pspace)
    assert len(list(pspace.iter_from({'arabic': 3,}))) == 9

    # iter_until
    pspace = deepcopy(orig_pspace)
    assert len(list(pspace.iter_until({'arabic': 2,}))) == 9

    # iter_between
    pspace = deepcopy(orig_pspace)
    assert len(list(pspace.iter_between(
        {'arabic': 1,},
        {'arabic': 2,},
    ))) == 9

    # iter_between with skip
    pspace = deepcopy(orig_pspace)
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

def test_record_store():
    pspace = PermutationSpace(
        ['random_seed', 'agent_type', 'num_transfers', 'num_albums', 'max_internal_actions'],
        random_seed=[
            0.35746869278354254, 0.7368915891545381, 0.03439267552305503, 0.21913569678035283, 0.0664623502695384,
        ],
        num_episodes=150000,
        eval_frequency=100,
        agent_type=['naive', 'kb'],
        num_albums=[100, 500, 1000, 5000],
        max_internal_actions=range(1, 6),
        data_file='data/album_decade',
        num_transfers=range(1, 6),
        min_return=-100,
        save_weights=False,
    ).filter(
        lambda num_transfers: num_transfers == 1
    ).filter(
        lambda num_albums, max_internal_actions:
            num_albums == 5000 or max_internal_actions == 1
    ).filter(
        lambda num_albums, max_internal_actions:
            not (num_albums == 5000 and max_internal_actions == 1)
    )
    assert len(pspace) == 70
