import unittest
from simulator.fsa_simulation import (
    simulate_deterministic_fsa,
    _is_deterministic,
    simulate_nondeterministic_fsa,
    is_nondeterministic, simulate_nondeterministic_fsa_generator
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

        # Test rejected strings - should return dict with 'accepted': False
        result = simulate_deterministic_fsa(fsa, '')
        self.assertIsInstance(result, dict)
        self.assertFalse(result['accepted'])

        result = simulate_deterministic_fsa(fsa, 'a')
        self.assertIsInstance(result, dict)
        self.assertFalse(result['accepted'])

        result = simulate_deterministic_fsa(fsa, 'aa')
        self.assertIsInstance(result, dict)
        self.assertFalse(result['accepted'])

        result = simulate_deterministic_fsa(fsa, 'aba')
        self.assertIsInstance(result, dict)
        self.assertFalse(result['accepted'])

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
        # This should return a dict with 'accepted': False because we end in S1 which is not an accepting state
        result = simulate_deterministic_fsa(fsa, 'aabba')
        self.assertIsInstance(result, dict)
        self.assertFalse(result['accepted'])

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

        # Test with a symbol not in the alphabet - should return dict with 'accepted': False
        result = simulate_deterministic_fsa(fsa, 'abc')
        self.assertIsInstance(result, dict)
        self.assertFalse(result['accepted'])

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

        # Test rejected strings - should return dict with 'accepted': False
        result = simulate_deterministic_fsa(fsa, '')
        self.assertIsInstance(result, dict)
        self.assertFalse(result['accepted'])

        result = simulate_deterministic_fsa(fsa, 'a')
        self.assertIsInstance(result, dict)
        self.assertFalse(result['accepted'])

        result = simulate_deterministic_fsa(fsa, 'ab')
        self.assertIsInstance(result, dict)
        self.assertFalse(result['accepted'])

        result = simulate_deterministic_fsa(fsa, 'aab')
        self.assertIsInstance(result, dict)
        self.assertFalse(result['accepted'])


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


    def test_nfa_generator_basic(self):
        """Test basic functionality of the generator version"""
        # Simple NFA that accepts strings ending with 'ab'
        nfa = {
            'states': ['S0', 'S1', 'S2'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S0', 'S1'], 'b': ['S0']},
                'S1': {'b': ['S2']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S2']
        }

        # Test accepted string 'ab'
        results = list(simulate_nondeterministic_fsa_generator(nfa, 'ab'))

        # Should have at least one accepting path and a summary
        accepting_paths = [r for r in results if r['type'] == 'accepting_path']
        summary = [r for r in results if r['type'] == 'summary']

        self.assertEqual(len(accepting_paths), 1)
        self.assertEqual(len(summary), 1)
        self.assertTrue(summary[0]['accepted'])
        self.assertEqual(summary[0]['total_accepting_paths'], 1)

        # Check the accepting path content
        expected_path = [('S0', 'a', 'S1'), ('S1', 'b', 'S2')]
        self.assertEqual(accepting_paths[0]['path'], expected_path)
        self.assertEqual(accepting_paths[0]['final_state'], 'S2')


    def test_nfa_generator_multiple_paths(self):
        """Test generator with multiple accepting paths"""
        # NFA that can accept 'aa' via multiple paths
        nfa = {
            'states': ['S0', 'S1', 'S2', 'S3'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'a': ['S1', 'S2']},
                'S1': {'a': ['S3']},
                'S2': {'a': ['S3']},
                'S3': {}
            },
            'startingState': 'S0',
            'acceptingStates': ['S3']
        }

        results = list(simulate_nondeterministic_fsa_generator(nfa, 'aa'))

        accepting_paths = [r for r in results if r['type'] == 'accepting_path']
        rejected_paths = [r for r in results if r['type'] == 'rejected_path']
        summary = [r for r in results if r['type'] == 'summary']

        # Should have exactly 2 accepting paths
        self.assertEqual(len(accepting_paths), 2)
        self.assertEqual(len(summary), 1)
        self.assertTrue(summary[0]['accepted'])
        self.assertEqual(summary[0]['total_accepting_paths'], 2)

        # Check both paths are present
        expected_path1 = [('S0', 'a', 'S1'), ('S1', 'a', 'S3')]
        expected_path2 = [('S0', 'a', 'S2'), ('S2', 'a', 'S3')]

        actual_paths = [path['path'] for path in accepting_paths]
        self.assertIn(expected_path1, actual_paths)
        self.assertIn(expected_path2, actual_paths)

        # Check path numbering
        path_numbers = [path['path_number'] for path in accepting_paths]
        self.assertEqual(sorted(path_numbers), [1, 2])


    def test_nfa_generator_rejected_string(self):
        """Test generator with rejected string"""
        nfa = {
            'states': ['S0', 'S1', 'S2'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S0', 'S1'], 'b': ['S0']},
                'S1': {'b': ['S2']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S2']
        }

        # Test rejected string 'a'
        results = list(simulate_nondeterministic_fsa_generator(nfa, 'a'))

        accepting_paths = [r for r in results if r['type'] == 'accepting_path']
        rejected_paths = [r for r in results if r['type'] == 'rejected_path']
        summary = [r for r in results if r['type'] == 'summary']

        self.assertEqual(len(accepting_paths), 0)
        self.assertTrue(len(rejected_paths) > 0)
        self.assertEqual(len(summary), 1)
        self.assertFalse(summary[0]['accepted'])
        self.assertEqual(summary[0]['total_accepting_paths'], 0)

        # Check rejection reasons
        for rejected in rejected_paths:
            self.assertIn('reason', rejected)
            # Should be rejected because final states are not accepting
            self.assertIn('not an accepting state', rejected['reason'])


    def test_nfa_generator_invalid_symbol(self):
        """Test generator with invalid symbol in input"""
        nfa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1'], 'b': ['S0']},
                'S1': {}
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }

        # Test with invalid symbol 'c'
        results = list(simulate_nondeterministic_fsa_generator(nfa, 'ac'))

        rejected_paths = [r for r in results if r['type'] == 'rejected_path']
        summary = [r for r in results if r['type'] == 'summary']

        # Should have at least one rejection due to invalid symbol
        symbol_rejections = [r for r in rejected_paths if 'not in alphabet' in r['reason']]
        self.assertTrue(len(symbol_rejections) > 0)

        self.assertEqual(len(summary), 1)
        self.assertFalse(summary[0]['accepted'])


    def test_nfa_generator_with_epsilon_diverging_path(self):
        """Test generator with epsilon transitions"""
        nfa = {
            'states': ['S0', 'S1', 'S2'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'': ['S1','S2'], 'a': ['S0']},
                'S1': {'': ['S2']},
                'S2': {}
            },
            'startingState': 'S0',
            'acceptingStates': ['S2']
        }

        # Test string '' which should be accepted via epsilon transitions
        results = list(simulate_nondeterministic_fsa_generator(nfa, ''))

        accepting_paths = [r for r in results if r['type'] == 'accepting_path']
        summary = [r for r in results if r['type'] == 'summary']

        self.assertTrue(len(accepting_paths) == 2)
        self.assertEqual(len(summary), 1)
        self.assertTrue(summary[0]['accepted'])

        # Check for epsilon transitions in the path
        found_epsilon = False
        for path_result in accepting_paths:
            for transition in path_result['path']:
                if transition[1] == 'ε':
                    found_epsilon = True
                    break
            if found_epsilon:
                break
        self.assertTrue(found_epsilon, "Expected epsilon transitions in the path")

    def test_nfa_generator_with_epsilon_transitions(self):
        """Test generator with epsilon paths that diverge but still reach acceptance"""
        nfa = {
            'states': ['S0', 'S1', 'S2', 'S3'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'': ['S1'], 'a': ['S0']},  # Epsilon transition to S1
                'S1': {'': ['S2']},
                'S2': {'': ['S3']},  # Epsilon transition to S3
                'S3': {}
            },
            'startingState': 'S0',
            'acceptingStates': ['S3']
        }

        # Test string 'a' which should be accepted via epsilon transitions
        results = list(simulate_nondeterministic_fsa_generator(nfa, 'a'))

        accepting_paths = [r for r in results if r['type'] == 'accepting_path']
        summary = [r for r in results if r['type'] == 'summary']

        self.assertTrue(len(accepting_paths) >= 1)
        self.assertEqual(len(summary), 1)
        self.assertTrue(summary[0]['accepted'])

        # Check for epsilon transitions in the path
        found_epsilon = False
        for path_result in accepting_paths:
            for transition in path_result['path']:
                if transition[1] == 'ε':
                    found_epsilon = True
                    break
            if found_epsilon:
                break
        self.assertTrue(found_epsilon, "Expected epsilon transitions in the path")


    def test_nfa_generator_progress_updates(self):
        """Test that generator yields progress updates for complex FSAs"""
        # Create an FSA that will generate many paths to trigger progress updates
        nfa = {
            'states': ['S0', 'S1', 'S2', 'S3'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S0', 'S1'], 'b': ['S0', 'S2']},  # Multiple non-deterministic choices
                'S1': {'a': ['S1'], 'b': ['S1', 'S3']},
                'S2': {'a': ['S2', 'S3'], 'b': ['S2']},
                'S3': {'a': ['S3'], 'b': ['S3']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S3']
        }

        # Use a longer string to generate more paths
        results = list(simulate_nondeterministic_fsa_generator(nfa, 'aaabbb'))

        progress_updates = [r for r in results if r['type'] == 'progress']

        # Should have some progress updates (though may not always trigger depending on path count)
        # This test verifies the structure is correct when progress updates do occur
        for progress in progress_updates:
            self.assertIn('paths_explored', progress)
            self.assertIn('queue_size', progress)
            self.assertIn('current_state', progress)
            self.assertIn('input_position', progress)
            self.assertIsInstance(progress['paths_explored'], int)
            self.assertIsInstance(progress['queue_size'], int)


    def test_nfa_generator_empty_string(self):
        """Test generator with empty string"""
        # NFA where start state is accepting
        nfa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'a': ['S1']},
                'S1': {}
            },
            'startingState': 'S0',
            'acceptingStates': ['S0']
        }

        results = list(simulate_nondeterministic_fsa_generator(nfa, ''))

        accepting_paths = [r for r in results if r['type'] == 'accepting_path']
        summary = [r for r in results if r['type'] == 'summary']

        self.assertEqual(len(accepting_paths), 1)
        self.assertEqual(len(summary), 1)
        self.assertTrue(summary[0]['accepted'])

        # Empty string should result in empty path
        self.assertEqual(accepting_paths[0]['path'], [])
        self.assertEqual(accepting_paths[0]['final_state'], 'S0')


    def test_nfa_generator_no_transitions(self):
        """Test generator when no transitions are possible"""
        nfa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1'], 'b': ['S0']},
                'S1': {}  # No transitions from S1
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }

        # Test string 'ab' - should be rejected because no transition on 'b' from S1
        results = list(simulate_nondeterministic_fsa_generator(nfa, 'ab'))

        accepting_paths = [r for r in results if r['type'] == 'accepting_path']
        rejected_paths = [r for r in results if r['type'] == 'rejected_path']
        summary = [r for r in results if r['type'] == 'summary']

        self.assertEqual(len(accepting_paths), 0)
        self.assertTrue(len(rejected_paths) > 0)
        self.assertFalse(summary[0]['accepted'])

        # Should have rejection due to no transition
        no_transition_rejections = [r for r in rejected_paths if 'No transition' in r['reason']]
        self.assertTrue(len(no_transition_rejections) > 0)


    def test_nfa_generator_invalid_fsa_structure(self):
        """Test generator with invalid FSA structure"""
        # Missing required keys
        invalid_nfa = {
            'states': ['S0'],
            'alphabet': ['a']
            # Missing transitions, startingState, acceptingStates
        }

        results = list(simulate_nondeterministic_fsa_generator(invalid_nfa, 'a'))

        # Should yield an error immediately
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['type'], 'error')
        self.assertIn('Invalid FSA structure', results[0]['message'])
        self.assertFalse(results[0]['accepted'])


    def test_nfa_generator_result_structure(self):
        """Test that all generator results have proper structure"""
        nfa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'a': ['S1']},
                'S1': {}
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }

        results = list(simulate_nondeterministic_fsa_generator(nfa, 'a'))

        for result in results:
            # Every result should have a 'type' field
            self.assertIn('type', result)

            if result['type'] == 'accepting_path':
                required_fields = ['path', 'path_number', 'final_state']
                for field in required_fields:
                    self.assertIn(field, result)

            elif result['type'] == 'rejected_path':
                required_fields = ['path', 'reason']
                for field in required_fields:
                    self.assertIn(field, result)

            elif result['type'] == 'progress':
                required_fields = ['paths_explored', 'queue_size', 'current_state', 'input_position']
                for field in required_fields:
                    self.assertIn(field, result)

            elif result['type'] == 'summary':
                required_fields = ['total_accepting_paths', 'total_paths_explored', 'accepted']
                for field in required_fields:
                    self.assertIn(field, result)


    def test_nfa_generator_comparison_with_regular_function(self):
        """Test that generator produces same final results as regular function"""
        nfa = {
            'states': ['S0', 'S1', 'S2', 'S3'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'a': ['S1', 'S2']},
                'S1': {'a': ['S3']},
                'S2': {'a': ['S3']},
                'S3': {}
            },
            'startingState': 'S0',
            'acceptingStates': ['S3']
        }

        test_string = 'aa'

        # Get results from regular function
        regular_result = simulate_nondeterministic_fsa(nfa, test_string)

        # Get results from generator
        generator_results = list(simulate_nondeterministic_fsa_generator(nfa, test_string))
        accepting_paths = [r['path'] for r in generator_results if r['type'] == 'accepting_path']
        summary = [r for r in generator_results if r['type'] == 'summary'][0]

        # Compare results
        if isinstance(regular_result, list):  # Accepted
            self.assertTrue(summary['accepted'])
            self.assertEqual(len(accepting_paths), len(regular_result))

            # Check that all paths from regular function are in generator results
            for path in regular_result:
                self.assertIn(path, accepting_paths)

        else:  # Rejected
            self.assertFalse(summary['accepted'])
            self.assertEqual(len(accepting_paths), 0)


if __name__ == '__main__':
    unittest.main()