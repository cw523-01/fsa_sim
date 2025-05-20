import unittest
from simulator.fsa_simulation import simulate_deterministic_fsa, _is_deterministic


class TestFsaSimulation(unittest.TestCase):
    def test_basic_deterministic_fsa(self):
        # Simple FSA that accepts strings ending with 'b'
        fsa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S0'], 'b': ['S1']},
                'S1': {'a': ['S0'], 'b': ['S1']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }

        # Test accepted strings with their expected paths
        # Test 'b'
        expected_path = [('S0', 'b', 'S1')]
        self.assertEqual(simulate_deterministic_fsa(fsa, 'b'), expected_path)

        # Test 'ab'
        expected_path = [('S0', 'a', 'S0'), ('S0', 'b', 'S1')]
        self.assertEqual(simulate_deterministic_fsa(fsa, 'ab'), expected_path)

        # Test 'aab'
        expected_path = [('S0', 'a', 'S0'), ('S0', 'a', 'S0'), ('S0', 'b', 'S1')]
        self.assertEqual(simulate_deterministic_fsa(fsa, 'aab'), expected_path)

        # Test 'abb'
        expected_path = [('S0', 'a', 'S0'), ('S0', 'b', 'S1'), ('S1', 'b', 'S1')]
        self.assertEqual(simulate_deterministic_fsa(fsa, 'abb'), expected_path)

        # Test rejected strings
        self.assertFalse(simulate_deterministic_fsa(fsa, ''))
        self.assertFalse(simulate_deterministic_fsa(fsa, 'a'))
        self.assertFalse(simulate_deterministic_fsa(fsa, 'aa'))
        self.assertFalse(simulate_deterministic_fsa(fsa, 'aba'))

    def test_execution_path(self):
        # FSA that accepts strings with an even number of 'a's
        fsa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1'], 'b': ['S0']},
                'S1': {'a': ['S0'], 'b': ['S1']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S0']
        }

        # Test execution path for "aba"
        expected_path = [
            ('S0', 'a', 'S1'),
            ('S1', 'b', 'S1'),
            ('S1', 'a', 'S0')
        ]
        self.assertEqual(simulate_deterministic_fsa(fsa, 'aba'), expected_path)

        # Test execution path for "aabba"
        # This should return False because we end in S1 which is not an accepting state
        self.assertFalse(simulate_deterministic_fsa(fsa, 'aabba'))

        # Test additional accepted strings
        # Test "aa" (even number of 'a's, should be accepted)
        expected_path = [
            ('S0', 'a', 'S1'),
            ('S1', 'a', 'S0')
        ]
        self.assertEqual(simulate_deterministic_fsa(fsa, 'aa'), expected_path)

        # Test "abab" (even number of 'a's, should be accepted)
        expected_path = [
            ('S0', 'a', 'S1'),
            ('S1', 'b', 'S1'),
            ('S1', 'a', 'S0'),
            ('S0', 'b', 'S0')
        ]
        self.assertEqual(simulate_deterministic_fsa(fsa, 'abab'), expected_path)

    def test_invalid_input(self):
        fsa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1'], 'b': ['S0']},
                'S1': {'a': ['S0'], 'b': ['S1']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S0']
        }

        # Test with a symbol not in the alphabet
        self.assertFalse(simulate_deterministic_fsa(fsa, 'abc'))

    def test_deterministic_check(self):
        # Valid deterministic FSA
        valid_fsa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1'], 'b': ['S0']},
                'S1': {'a': ['S0'], 'b': ['S1']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S0']
        }
        self.assertTrue(_is_deterministic(valid_fsa))

        # Valid deterministic FSA with missing transitions (incomplete FSA)
        valid_incomplete_fsa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1']},  # Missing 'b' transition is okay
                'S1': {'a': ['S0'], 'b': ['S1']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S0']
        }
        self.assertTrue(_is_deterministic(valid_incomplete_fsa))

        # Invalid FSA - multiple transitions for one symbol
        invalid_fsa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S0', 'S1'], 'b': ['S0']},
                'S1': {'a': ['S0'], 'b': ['S1']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S0']
        }
        self.assertFalse(_is_deterministic(invalid_fsa))

    def test_more_complex_fsa(self):
        # FSA that accepts strings containing the substring "abb"
        fsa = {
            'states': ['S0', 'S1', 'S2', 'S3'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1'], 'b': ['S0']},
                'S1': {'a': ['S1'], 'b': ['S2']},
                'S2': {'a': ['S1'], 'b': ['S3']},
                'S3': {'a': ['S3'], 'b': ['S3']}  # Once in S3, stay in S3
            },
            'startingState': 'S0',
            'acceptingStates': ['S3']
        }

        # Test accepted strings with their expected paths
        # Test 'abb'
        expected_path = [
            ('S0', 'a', 'S1'),
            ('S1', 'b', 'S2'),
            ('S2', 'b', 'S3')
        ]
        self.assertEqual(simulate_deterministic_fsa(fsa, 'abb'), expected_path)

        # Test 'aabb'
        expected_path = [
            ('S0', 'a', 'S1'),
            ('S1', 'a', 'S1'),
            ('S1', 'b', 'S2'),
            ('S2', 'b', 'S3')
        ]
        self.assertEqual(simulate_deterministic_fsa(fsa, 'aabb'), expected_path)

        # Test 'abba'
        expected_path = [
            ('S0', 'a', 'S1'),
            ('S1', 'b', 'S2'),
            ('S2', 'b', 'S3'),
            ('S3', 'a', 'S3')
        ]
        self.assertEqual(simulate_deterministic_fsa(fsa, 'abba'), expected_path)

        # Test 'abbbb'
        expected_path = [
            ('S0', 'a', 'S1'),
            ('S1', 'b', 'S2'),
            ('S2', 'b', 'S3'),
            ('S3', 'b', 'S3'),
            ('S3', 'b', 'S3')
        ]
        self.assertEqual(simulate_deterministic_fsa(fsa, 'abbbb'), expected_path)

        # Test rejected strings
        self.assertFalse(simulate_deterministic_fsa(fsa, ''))
        self.assertFalse(simulate_deterministic_fsa(fsa, 'a'))
        self.assertFalse(simulate_deterministic_fsa(fsa, 'ab'))
        self.assertFalse(simulate_deterministic_fsa(fsa, 'aab'))


if __name__ == '__main__':
    unittest.main()