from unittest import TestCase, main
from itertools import product

from permspace import PermutationSpace

class PermSpaceTest(TestCase):
    def setUp(self):
        self.pspace = PermutationSpace(['arabic', 'letter_lower', 'roman_lower', 'question_name', 'constant'],
            arabic=range(1, 4),
            letter_lower=list('abc'),
            roman_lower=['i', 'ii', 'iii'],
            question_name=(lambda arabic: str(arabic)),
            part_name=(lambda question_name, letter_lower: question_name + '.' + letter_lower),
            subpart_name=(lambda part_name, roman_lower: part_name + '.' + roman_lower),
            constant='constant',
        )
    def test_basic(self):
        self.assertEqual(len(self.pspace), 27)
        self.assertEqual(self.pspace.order, ['arabic', 'letter_lower', 'roman_lower'])
        subpart_names = [parameters.subpart_name for parameters in self.pspace]
        correct_subpart_names = ['.'.join(values) for values in product('123', 'abc', ['i', 'ii', 'iii'])]
        self.assertEqual(subpart_names, correct_subpart_names)
        self.assertEqual(self.pspace.dependents_topo, ['question_name', 'part_name', 'subpart_name'])
    def test_filter(self):
        self.pspace.add_filter((lambda arabic: arabic < 3))
        self.assertEqual(len(self.pspace), 18)
        with self.assertRaises(ValueError):
            self.pspace.add_filter((lambda undefined: undefined is None))
    def test_iter_from(self):
        self.assertEqual(sum(1 for parameters in self.pspace.iter_from(arabic=2)), 18)
    def test_ordering_errors(self):
        with self.assertRaises(ValueError):
            PermutationSpace(['arabic', 'arabic'],
                arabic=range(1, 4),
            )
        with self.assertRaises(ValueError):
            PermutationSpace(['arabic', 'letter_lower'],
                arabic=range(1, 4),
            )
        with self.assertRaises(ValueError):
            PermutationSpace(['arabic'],
                arabic=range(1, 4),
                letter_lower=list('abc'),
            )

if __name__ == '__main__':
    main()
