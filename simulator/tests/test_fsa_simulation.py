import unittest
from simulator.fsa_simulation import (
    simulate_deterministic_fsa,
    _is_deterministic,
    simulate_nondeterministic_fsa,
    is_nondeterministic
)

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


    def test_basic_nondeterministic_fsa(self):
        # Simple NFA that accepts strings ending with 'ab' (non-deterministic choice on 'a')
        nfa = {
            'states': ['S0', 'S1', 'S2'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S0', 'S1'], 'b': ['S0']},  # Non-deterministic: 'a' can go to S0 or S1
                'S1': {'b': ['S2']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S2']
        }

        # Test accepted strings with their expected paths
        # Test 'ab' - should have one accepting path
        result = simulate_nondeterministic_fsa(nfa, 'ab')
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        expected_path = [('S0', 'a', 'S1'), ('S1', 'b', 'S2')]
        self.assertIn(expected_path, result)

        # Test 'aab' - should have one accepting path
        result = simulate_nondeterministic_fsa(nfa, 'aab')
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        # The correct path should be: S0 -a-> S0 -a-> S1 -b-> S2
        expected_path = [('S0', 'a', 'S0'), ('S0', 'a', 'S1'), ('S1', 'b', 'S2')]
        self.assertIn(expected_path, result)

        # Test rejected strings
        result = simulate_nondeterministic_fsa(nfa, '')
        self.assertIsInstance(result, dict)
        self.assertFalse(result['accepted'])

        result = simulate_nondeterministic_fsa(nfa, 'a')
        self.assertIsInstance(result, dict)
        self.assertFalse(result['accepted'])

        result = simulate_nondeterministic_fsa(nfa, 'b')
        self.assertIsInstance(result, dict)
        self.assertFalse(result['accepted'])


    def test_nfa_with_epsilon_transitions(self):
        # NFA with epsilon transitions
        nfa = {
            'states': ['S0', 'S1', 'S2', 'S3'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'': ['S1'], 'a': ['S0']},  # Epsilon transition to S1
                'S1': {'b': ['S2']},
                'S2': {'': ['S3']},  # Epsilon transition to S3
                'S3': {}
            },
            'startingState': 'S0',
            'acceptingStates': ['S3']
        }

        # Test 'b' - should be accepted via epsilon transitions
        result = simulate_nondeterministic_fsa(nfa, 'b')
        self.assertIsInstance(result, list)
        self.assertTrue(len(result) >= 1)
        # Should contain epsilon transitions in the path
        found_epsilon = False
        for path in result:
            for transition in path:
                if transition[1] == 'ε':
                    found_epsilon = True
                    break
            if found_epsilon:
                break
        self.assertTrue(found_epsilon, "Expected epsilon transitions in the path")

        # Test 'ab'
        result = simulate_nondeterministic_fsa(nfa, 'ab')
        self.assertIsInstance(result, list)
        self.assertTrue(len(result) >= 1)

        # Test rejected string
        result = simulate_nondeterministic_fsa(nfa, 'a')
        self.assertIsInstance(result, dict)
        self.assertFalse(result['accepted'])


    def test_nfa_multiple_accepting_paths(self):
        # NFA that can accept the same string via multiple paths
        nfa = {
            'states': ['S0', 'S1', 'S2', 'S3'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'a': ['S1', 'S2']},  # Non-deterministic choice
                'S1': {'a': ['S3']},
                'S2': {'a': ['S3']},
                'S3': {}
            },
            'startingState': 'S0',
            'acceptingStates': ['S3']
        }

        # Test 'aa' - should have multiple accepting paths
        result = simulate_nondeterministic_fsa(nfa, 'aa')
        self.assertIsInstance(result, list)
        print(result)
        self.assertEqual(len(result), 2)  # Should have exactly 2 paths

        expected_path1 = [('S0', 'a', 'S1'), ('S1', 'a', 'S3')]
        expected_path2 = [('S0', 'a', 'S2'), ('S2', 'a', 'S3')]

        self.assertIn(expected_path1, result)
        self.assertIn(expected_path2, result)


    def test_nfa_with_loops(self):
        # NFA with self-loops
        nfa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S0'], 'b': ['S1']},  # Self-loop on 'a'
                'S1': {'b': ['S1']}  # Self-loop on 'b'
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }

        # Test strings with repeated characters
        result = simulate_nondeterministic_fsa(nfa, 'aaab')
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        expected_path = [('S0', 'a', 'S0'), ('S0', 'a', 'S0'), ('S0', 'a', 'S0'), ('S0', 'b', 'S1')]
        self.assertIn(expected_path, result)

        result = simulate_nondeterministic_fsa(nfa, 'abbb')
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        expected_path = [('S0', 'a', 'S0'), ('S0', 'b', 'S1'), ('S1', 'b', 'S1'), ('S1', 'b', 'S1')]
        self.assertIn(expected_path, result)


    def test_nfa_invalid_input(self):
        nfa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S0', 'S1'], 'b': ['S0']},
                'S1': {'b': ['S1']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }

        # Test with symbol not in alphabet
        result = simulate_nondeterministic_fsa(nfa, 'abc')
        self.assertIsInstance(result, dict)
        self.assertFalse(result['accepted'])
        self.assertIn('rejection_reason', result)


    def test_nondeterministic_check(self):
        # Valid non-deterministic FSA
        nfa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S0', 'S1'], 'b': ['S0']},  # Multiple transitions for 'a'
                'S1': {'b': ['S1']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }
        self.assertTrue(is_nondeterministic(nfa))

        # FSA with epsilon transitions
        nfa_epsilon = {
            'states': ['S0', 'S1'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'': ['S1'], 'a': ['S0']},  # Epsilon transition
                'S1': {}
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }
        self.assertTrue(is_nondeterministic(nfa_epsilon))

        # Deterministic FSA (should return False)
        dfa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1'], 'b': ['S0']},
                'S1': {'a': ['S0'], 'b': ['S1']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S0']
        }
        self.assertFalse(is_nondeterministic(dfa))


    def test_complex_nfa(self):
        # More complex NFA that accepts strings containing 'aba' or 'bb'
        nfa = {
            'states': ['S0', 'S1', 'S2', 'S3', 'S4', 'S5'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S0', 'S1'], 'b': ['S0', 'S4']},  # Non-deterministic choices
                'S1': {'b': ['S2']},  # Path for 'aba'
                'S2': {'a': ['S3']},
                'S3': {'a': ['S0', 'S1'], 'b': ['S0, S4']},  # Continue or accept
                'S4': {'b': ['S5']},  # Path for 'bb'
                'S5': {'a': ['S0', 'S1'], 'b': ['S0', 'S4']}  # Continue or accept
            },
            'startingState': 'S0',
            'acceptingStates': ['S3', 'S5']  # Accept after 'aba' or 'bb'
        }

        # Test 'aba'
        result = simulate_nondeterministic_fsa(nfa, 'aba')
        self.assertIsInstance(result, list)
        self.assertTrue(len(result) >= 1)

        # Test 'bb'
        result = simulate_nondeterministic_fsa(nfa, 'bb')
        self.assertIsInstance(result, list)
        self.assertTrue(len(result) >= 1)

        # Test 'ababb' - contains both patterns
        result = simulate_nondeterministic_fsa(nfa, 'ababb')
        self.assertIsInstance(result, list)
        self.assertTrue(len(result) >= 1)


    def test_nfa_empty_string(self):
        # NFA where start state is also accepting
        nfa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'a': ['S1']},
                'S1': {}
            },
            'startingState': 'S0',
            'acceptingStates': ['S0']  # Start state is accepting
        }

        # Empty string should be accepted
        result = simulate_nondeterministic_fsa(nfa, '')
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], [])  # Empty path


    def test_nfa_epsilon_loops(self):
        # NFA with epsilon loops (potential infinite loop scenario)
        nfa = {
            'states': ['S0', 'S1', 'S2'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'': ['S1']},  # Epsilon to S1
                'S1': {'': ['S2'], 'a': ['S2']},  # Epsilon to S2 or 'a' to S2
                'S2': {'': ['S1']}  # Epsilon back to S1 (creates loop)
            },
            'startingState': 'S0',
            'acceptingStates': ['S2']
        }

        # Test empty string - should be accepted via epsilon transitions
        result = simulate_nondeterministic_fsa(nfa, '')
        self.assertIsInstance(result, list)
        self.assertTrue(len(result) >= 1)

        # Test 'a' - should be accepted
        result = simulate_nondeterministic_fsa(nfa, 'a')
        self.assertIsInstance(result, list)
        self.assertTrue(len(result) >= 1)


if __name__ == '__main__':
    unittest.main()