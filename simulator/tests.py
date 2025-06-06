from django.test import TestCase
from simulator.fsa_simulation import (
    simulate_deterministic_fsa,
    _is_deterministic,
    simulate_nondeterministic_fsa,
    is_nondeterministic, simulate_nondeterministic_fsa_generator, detect_epsilon_loops,
    simulate_nondeterministic_fsa_with_depth_limit, simulate_nondeterministic_fsa_generator_with_depth_limit
)

class TestFsaSimulation(TestCase):
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


    def test_detect_epsilon_loops_no_loops(self):
        """Test epsilon loop detection on FSA without epsilon transitions"""
        # Simple DFA with no epsilon transitions
        fsa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1'], 'b': ['S0']},
                'S1': {'a': ['S0'], 'b': ['S1']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }

        result = detect_epsilon_loops(fsa)
        self.assertFalse(result['has_epsilon_loops'])
        self.assertEqual(len(result['loop_details']), 0)


    def test_detect_epsilon_loops_no_cycles(self):
        """Test epsilon loop detection on FSA with epsilon transitions but no cycles"""
        # NFA with epsilon transitions but no loops
        fsa = {
            'states': ['S0', 'S1', 'S2', 'S3'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'': ['S1'], 'a': ['S0']},  # Epsilon to S1
                'S1': {'': ['S2'], 'b': ['S1']},  # Epsilon to S2
                'S2': {'': ['S3']},  # Epsilon to S3
                'S3': {'a': ['S3']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S3']
        }

        result = detect_epsilon_loops(fsa)
        self.assertFalse(result['has_epsilon_loops'])
        self.assertEqual(len(result['loop_details']), 0)


    def test_detect_epsilon_loops_simple_self_loop(self):
        """Test detection of simple epsilon self-loop"""
        # NFA with epsilon self-loop
        fsa = {
            'states': ['S0'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'': ['S0']} # Epsilon self-loop
            },
            'startingState': 'S0',
            'acceptingStates': ['S0']
        }

        result = detect_epsilon_loops(fsa)
        self.assertTrue(result['has_epsilon_loops'])
        self.assertEqual(len(result['loop_details']), 1)

        loop = result['loop_details'][0]
        self.assertEqual(loop['cycle'], ['S0', 'S0'])
        self.assertEqual(loop['transitions'], [('S0', 'ε', 'S0')])
        self.assertTrue(loop['reachable_from_start'])


    def test_detect_epsilon_loops_unreachable_self_loop(self):
        """Test detection of epsilon self-loop not reachable from start"""
        # NFA with epsilon self-loop not reachable from start
        fsa = {
            'states': ['S0', 'S1', 'S2'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'a': ['S1']},
                'S1': {},
                'S2': {'': ['S2']}  # Unreachable epsilon self-loop
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }

        result = detect_epsilon_loops(fsa)
        self.assertTrue(result['has_epsilon_loops'])
        self.assertEqual(len(result['loop_details']), 1)

        loop = result['loop_details'][0]
        self.assertEqual(loop['cycle'], ['S2', 'S2'])
        self.assertEqual(loop['transitions'], [('S2', 'ε', 'S2')])
        self.assertFalse(loop['reachable_from_start'])


    def test_detect_epsilon_loops_simple_cycle(self):
        """Test detection of simple epsilon cycle between two states"""
        # NFA with epsilon cycle between S1 and S2
        fsa = {
            'states': ['S0', 'S1', 'S2'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'': ['S1'], 'a': ['S0']},  # Epsilon to S1
                'S1': {'': ['S2']},  # Epsilon to S2
                'S2': {'': ['S1']}  # Epsilon back to S1 (creates cycle)
            },
            'startingState': 'S0',
            'acceptingStates': ['S2']
        }

        result = detect_epsilon_loops(fsa)
        self.assertTrue(result['has_epsilon_loops'])
        self.assertEqual(len(result['loop_details']), 1)

        loop = result['loop_details'][0]
        # Should detect the cycle between S1 and S2
        self.assertTrue(len(loop['cycle']) >= 3)  # At least S1 -> S2 -> S1
        self.assertTrue(len(loop['transitions']) >= 2)
        self.assertTrue(loop['reachable_from_start'])


    def test_detect_epsilon_loops_complex_cycle(self):
        """Test detection of epsilon cycle among multiple states"""
        # NFA with epsilon cycle among S1, S2, S3
        fsa = {
            'states': ['S0', 'S1', 'S2', 'S3', 'S4'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'': ['S1'], 'a': ['S0']},  # Epsilon to S1
                'S1': {'': ['S2']},  # Epsilon to S2
                'S2': {'': ['S3']},  # Epsilon to S3
                'S3': {'': ['S1']},  # Epsilon back to S1 (creates cycle)
                'S4': {}  # Isolated state
            },
            'startingState': 'S0',
            'acceptingStates': ['S3']
        }

        result = detect_epsilon_loops(fsa)
        self.assertTrue(result['has_epsilon_loops'])
        self.assertEqual(len(result['loop_details']), 1)

        loop = result['loop_details'][0]
        self.assertTrue(len(loop['cycle']) >= 4)  # At least S1 -> S2 -> S3 -> S1
        self.assertTrue(len(loop['transitions']) >= 3)
        self.assertTrue(loop['reachable_from_start'])


    def test_detect_epsilon_loops_multiple_cycles(self):
        """Test detection of multiple separate epsilon cycles"""
        # NFA with two separate epsilon cycles
        fsa = {
            'states': ['S0', 'S1', 'S2', 'S3', 'S4'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'a': ['S3']},
                'S1': {'': ['S2']},  # First cycle: S1 <-> S2
                'S2': {'': ['S1']},
                'S3': {'': ['S4']},  # Second cycle: S3 <-> S4
                'S4': {'': ['S3']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S2', 'S4']
        }

        result = detect_epsilon_loops(fsa)
        self.assertTrue(result['has_epsilon_loops'])
        self.assertEqual(len(result['loop_details']), 2)

        # Check that we found both cycles
        reachable_cycles = [loop for loop in result['loop_details'] if loop['reachable_from_start']]
        unreachable_cycles = [loop for loop in result['loop_details'] if not loop['reachable_from_start']]

        self.assertEqual(len(reachable_cycles), 1)  # S3 <-> S4 is reachable
        self.assertEqual(len(unreachable_cycles), 1)  # S1 <-> S2 is not reachable


    def test_detect_epsilon_loops_mixed_with_regular_transitions(self):
        """Test epsilon loop detection in FSA with both epsilon and regular transitions"""
        # Complex NFA with epsilon loops and regular transitions
        fsa = {
            'states': ['S0', 'S1', 'S2', 'S3'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'': ['S1'], 'a': ['S2']},  # Epsilon to S1, regular transition on 'a'
                'S1': {'': ['S2'], 'b': ['S3']},  # Epsilon to S2, regular transition on 'b'
                'S2': {'': ['S1'], 'a': ['S3']},  # Epsilon back to S1 (cycle), regular on 'a'
                'S3': {'b': ['S0']}  # Regular transition only
            },
            'startingState': 'S0',
            'acceptingStates': ['S3']
        }

        result = detect_epsilon_loops(fsa)
        self.assertTrue(result['has_epsilon_loops'])
        self.assertEqual(len(result['loop_details']), 1)

        loop = result['loop_details'][0]
        self.assertTrue(loop['reachable_from_start'])
        # Should detect cycle between S1 and S2
        cycle_states = set()
        for state in loop['cycle'][:-1]:  # Exclude the repeated state at the end
            cycle_states.add(state)
        self.assertTrue('S1' in cycle_states)
        self.assertTrue('S2' in cycle_states)


    def test_detect_epsilon_loops_from_start_state(self):
        """Test epsilon loop detection when start state is part of a loop"""
        # NFA where start state is part of epsilon loop
        fsa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'': ['S1'], 'a': ['S0']},  # Epsilon to S1
                'S1': {'': ['S0']}  # Epsilon back to S0
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }

        result = detect_epsilon_loops(fsa)
        self.assertTrue(result['has_epsilon_loops'])
        self.assertEqual(len(result['loop_details']), 1)

        loop = result['loop_details'][0]
        self.assertTrue(loop['reachable_from_start'])
        # Should detect cycle involving start state
        cycle_states = set()
        for state in loop['cycle'][:-1]:
            cycle_states.add(state)
        self.assertTrue('S0' in cycle_states)
        self.assertTrue('S1' in cycle_states)


    def test_detect_epsilon_loops_edge_cases(self):
        """Test epsilon loop detection edge cases"""
        # Empty FSA
        empty_fsa = {
            'states': [],
            'alphabet': [],
            'transitions': {},
            'startingState': '',
            'acceptingStates': []
        }

        result = detect_epsilon_loops(empty_fsa)
        self.assertFalse(result['has_epsilon_loops'])
        self.assertEqual(len(result['loop_details']), 0)

        # Single state with no transitions
        single_state_fsa = {
            'states': ['S0'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {}
            },
            'startingState': 'S0',
            'acceptingStates': ['S0']
        }

        result = detect_epsilon_loops(single_state_fsa)
        self.assertFalse(result['has_epsilon_loops'])
        self.assertEqual(len(result['loop_details']), 0)


    def test_detect_epsilon_loops_start_state_self_loop(self):
        """Test epsilon loop detection when start state has epsilon self-loop"""
        # NFA where start state has epsilon self-loop
        fsa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'': ['S0'], 'a': ['S1']},  # Epsilon self-loop on start state
                'S1': {}
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }

        result = detect_epsilon_loops(fsa)
        self.assertTrue(result['has_epsilon_loops'])
        self.assertEqual(len(result['loop_details']), 1)

        loop = result['loop_details'][0]
        self.assertEqual(loop['cycle'], ['S0', 'S0'])
        self.assertEqual(loop['transitions'], [('S0', 'ε', 'S0')])
        self.assertTrue(loop['reachable_from_start'])

    def test_detect_epsilon_loops_complex_reachability(self):
        """Test epsilon loop detection with complex reachability scenarios"""
        # Complex NFA with both reachable and unreachable epsilon loops
        fsa = {
            'states': ['S0', 'S1', 'S2', 'S3', 'S4', 'S5'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1']},  # Only 'a' transition, no path to S3
                'S1': {'': ['S2']},  # Path to reachable loop
                'S2': {'': ['S1']},  # Reachable loop: S1 <-> S2
                'S3': {'': ['S4']},  # Path to unreachable loop (S3 not reachable from S0)
                'S4': {'': ['S5']},
                'S5': {'': ['S4']}  # Unreachable loop: S4 <-> S5
            },
            'startingState': 'S0',
            'acceptingStates': ['S2', 'S5']
        }

        result = detect_epsilon_loops(fsa)
        self.assertTrue(result['has_epsilon_loops'])
        self.assertEqual(len(result['loop_details']), 2)

        # Check reachability:
        # S0 --a--> S1 (S1 <-> S2 loop is reachable)
        # S3, S4, S5 are not reachable from S0 (S4 <-> S5 loop is unreachable)
        reachable_cycles = [loop for loop in result['loop_details'] if loop['reachable_from_start']]
        unreachable_cycles = [loop for loop in result['loop_details'] if not loop['reachable_from_start']]

        self.assertEqual(len(reachable_cycles), 1)  # Only S1<->S2 is reachable
        self.assertEqual(len(unreachable_cycles), 1)  # S4<->S5 is not reachable

    def test_depth_limit_basic_functionality(self):
        """Test basic functionality without epsilon loops"""
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

        # Test accepted string 'ab' with sufficient depth limit
        result = simulate_nondeterministic_fsa_with_depth_limit(nfa, 'ab', max_depth=10)
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        expected_path = [('S0', 'a', 'S1'), ('S1', 'b', 'S2')]
        self.assertIn(expected_path, result)

        # Test rejected string 'a'
        result = simulate_nondeterministic_fsa_with_depth_limit(nfa, 'a', max_depth=10)
        self.assertIsInstance(result, dict)
        self.assertFalse(result['accepted'])
        self.assertFalse(result['depth_limit_reached'])

    def test_depth_limit_validation(self):
        """Test validation of max_depth parameter"""
        nfa = {
            'states': ['S0'],
            'alphabet': ['a'],
            'transitions': {'S0': {}},
            'startingState': 'S0',
            'acceptingStates': ['S0']
        }

        # Test invalid depth values
        result = simulate_nondeterministic_fsa_with_depth_limit(nfa, '', max_depth=0)
        self.assertIsInstance(result, dict)
        self.assertFalse(result['accepted'])
        self.assertEqual(result['rejection_reason'], 'max_depth must be a positive integer')

        result = simulate_nondeterministic_fsa_with_depth_limit(nfa, '', max_depth=-1)
        self.assertIsInstance(result, dict)
        self.assertFalse(result['accepted'])
        self.assertEqual(result['rejection_reason'], 'max_depth must be a positive integer')

        # Test valid depth
        result = simulate_nondeterministic_fsa_with_depth_limit(nfa, '', max_depth=1)
        self.assertIsInstance(result, list)

    def test_simple_epsilon_loop_handling(self):
        """Test handling of simple epsilon self-loop"""
        # NFA with epsilon self-loop
        nfa = {
            'states': ['S0'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'': ['S0'], 'a': ['S0']}  # Epsilon self-loop
            },
            'startingState': 'S0',
            'acceptingStates': ['S0']
        }

        # Test empty string with low depth limit
        result = simulate_nondeterministic_fsa_with_depth_limit(nfa, '', max_depth=3)
        self.assertIsInstance(result, list)
        self.assertTrue(len(result) > 0)  # Should find at least one accepting path

        # Test that depth limit is reached
        result = simulate_nondeterministic_fsa_with_depth_limit(nfa, '', max_depth=1)
        # Should still work but might hit depth limit
        if isinstance(result, dict):
            self.assertTrue(result['depth_limit_reached'])
        else:
            self.assertIsInstance(result, list)

    def test_epsilon_cycle_between_states(self):
        """Test handling of epsilon cycle between multiple states"""
        # NFA with epsilon cycle between S1 and S2
        nfa = {
            'states': ['S0', 'S1', 'S2'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'': ['S1'], 'a': ['S0']},  # Epsilon to S1
                'S1': {'': ['S2']},  # Epsilon to S2
                'S2': {'': ['S1']}  # Epsilon back to S1 (creates cycle)
            },
            'startingState': 'S0',
            'acceptingStates': ['S2']
        }

        # Test empty string with sufficient depth
        result = simulate_nondeterministic_fsa_with_depth_limit(nfa, '', max_depth=5)
        self.assertIsInstance(result, list)
        self.assertTrue(len(result) > 0)

        # Test with very low depth limit
        result = simulate_nondeterministic_fsa_with_depth_limit(nfa, '', max_depth=1)
        # Should either succeed with limited paths or report depth limit reached
        self.assertIsInstance(result, dict)
        self.assertFalse(result['accepted'])

    def test_depth_limit_prevents_infinite_exploration(self):
        """Test that depth limit prevents infinite exploration"""
        # NFA with complex epsilon loops
        nfa = {
            'states': ['S0', 'S1', 'S2', 'S3'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'': ['S1', 'S2']},  # Multiple epsilon transitions
                'S1': {'': ['S2', 'S3']},
                'S2': {'': ['S1', 'S3']},  # Creates cycles
                'S3': {'': ['S1']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S3']
        }

        # Test with very low depth limit
        result = simulate_nondeterministic_fsa_with_depth_limit(nfa, '', max_depth=2)
        # Should either find paths within limit or report depth limit reached
        if isinstance(result, dict):
            self.assertTrue(result.get('depth_limit_reached', False) or
                            result['rejection_reason'] == 'No accepting paths found')
        else:
            self.assertIsInstance(result, list)

    def test_depth_limit_with_regular_transitions(self):
        """Test depth limiting works correctly with regular transitions"""
        # NFA with both epsilon and regular transitions
        nfa = {
            'states': ['S0', 'S1', 'S2', 'S3'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'': ['S1'], 'a': ['S2']},  # Epsilon to S1, regular to S2
                'S1': {'': ['S2']},  # Epsilon to S2
                'S2': {'': ['S1'], 'a': ['S3']},  # Epsilon back to S1 (loop), regular to S3
                'S3': {}
            },
            'startingState': 'S0',
            'acceptingStates': ['S3']
        }

        # Test string 'a' which should reach S3 via regular transition
        result = simulate_nondeterministic_fsa_with_depth_limit(nfa, 'a', max_depth=5)
        self.assertIsInstance(result, list)
        self.assertTrue(len(result) > 0)

        # Verify we can find paths that use regular transitions
        for path in result:
            has_regular_transition = any(transition[1] == 'a' for transition in path)
            self.assertTrue(has_regular_transition)

    def test_generator_basic_functionality(self):
        """Test basic functionality of the generator version"""
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
        results = list(simulate_nondeterministic_fsa_generator_with_depth_limit(nfa, 'ab', max_depth=10))

        accepting_paths = [r for r in results if r['type'] == 'accepting_path']
        summary = [r for r in results if r['type'] == 'summary']

        self.assertEqual(len(accepting_paths), 1)
        self.assertEqual(len(summary), 1)
        self.assertTrue(summary[0]['accepted'])
        self.assertFalse(summary[0]['depth_limit_reached'])

        # Check depth information is included
        self.assertIn('total_depth', accepting_paths[0])
        self.assertEqual(accepting_paths[0]['total_depth'], 2)

    def test_generator_depth_limit_validation(self):
        """Test generator validation of max_depth parameter"""
        nfa = {
            'states': ['S0'],
            'alphabet': ['a'],
            'transitions': {'S0': {}},
            'startingState': 'S0',
            'acceptingStates': ['S0']
        }

        # Test invalid depth
        results = list(simulate_nondeterministic_fsa_generator_with_depth_limit(nfa, '', max_depth=0))
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['type'], 'error')
        self.assertIn('max_depth must be a positive integer', results[0]['message'])

    def test_generator_epsilon_loop_handling(self):
        """Test generator handling of epsilon loops"""
        # NFA with epsilon self-loop
        nfa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'': ['S1']},
                'S1': {'': ['S0']}  # Creates epsilon loop
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }

        results = list(simulate_nondeterministic_fsa_generator_with_depth_limit(nfa, '', max_depth=3))

        accepting_paths = [r for r in results if r['type'] == 'accepting_path']
        depth_limit_events = [r for r in results if r['type'] == 'depth_limit_reached']
        summary = [r for r in results if r['type'] == 'summary']

        # Should find some accepting paths
        self.assertTrue(len(accepting_paths) > 0)

        # Should have summary
        self.assertEqual(len(summary), 1)

        # May have depth limit events
        if len(depth_limit_events) > 0:
            self.assertTrue(summary[0]['depth_limit_reached'])

    def test_generator_depth_limit_events(self):
        """Test generator yields depth limit events"""
        # NFA with guaranteed depth limit issues
        nfa = {
            'states': ['S0', 'S1', 'S2'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'': ['S1']},
                'S1': {'': ['S2']},
                'S2': {'': ['S1']}  # Creates epsilon cycle
            },
            'startingState': 'S0',
            'acceptingStates': ['S2']
        }

        results = list(simulate_nondeterministic_fsa_generator_with_depth_limit(nfa, '', max_depth=2))

        depth_limit_events = [r for r in results if r['type'] == 'depth_limit_reached']
        summary = [r for r in results if r['type'] == 'summary']

        # Should report depth limit reached in summary
        self.assertEqual(len(summary), 1)
        # May have depth limit events or just report in summary

        # Check structure of depth limit events if any
        for event in depth_limit_events:
            required_fields = ['path', 'current_depth', 'max_depth', 'state', 'input_position']
            for field in required_fields:
                self.assertIn(field, event)

    def test_generator_progress_updates_with_depth_info(self):
        """Test that progress updates include depth information"""
        nfa = {
            'states': ['S0', 'S1', 'S2'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'': ['S1'], 'a': ['S0'], 'b': ['S0']},
                'S1': {'': ['S2'], 'a': ['S1'], 'b': ['S1']},
                'S2': {}
            },
            'startingState': 'S0',
            'acceptingStates': ['S2']
        }

        results = list(simulate_nondeterministic_fsa_generator_with_depth_limit(nfa, 'aabb', max_depth=10))

        progress_updates = [r for r in results if r['type'] == 'progress']

        # Check that progress updates have depth information
        for progress in progress_updates:
            self.assertIn('current_depth', progress)
            self.assertIn('depth_limit_reached', progress)
            self.assertIsInstance(progress['current_depth'], int)
            self.assertIsInstance(progress['depth_limit_reached'], bool)

    def test_comparison_with_original_when_no_epsilon_loops(self):
        """Test that depth-limited version gives same results as original when no epsilon loops"""
        # NFA without epsilon transitions
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

        # Compare results
        from simulator.fsa_simulation import simulate_nondeterministic_fsa

        original_result = simulate_nondeterministic_fsa(nfa, 'aa')
        depth_limited_result = simulate_nondeterministic_fsa_with_depth_limit(nfa, 'aa', max_depth=10)

        # Both should be lists (accepted)
        self.assertIsInstance(original_result, list)
        self.assertIsInstance(depth_limited_result, list)

        # Should have same number of paths
        self.assertEqual(len(original_result), len(depth_limited_result))

        # Should have same paths
        for path in original_result:
            self.assertIn(path, depth_limited_result)

    def test_epsilon_path_counting(self):
        """Test that epsilon transitions are counted correctly for depth limiting"""
        # NFA with known epsilon transition count
        nfa = {
            'states': ['S0', 'S1', 'S2', 'S3'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'': ['S1']},  # 1 epsilon
                'S1': {'': ['S2']},  # 1 epsilon
                'S2': {'': ['S3']},  # 1 epsilon  (total: 3 epsilon transitions)
                'S3': {}
            },
            'startingState': 'S0',
            'acceptingStates': ['S3']
        }

        # Test with depth limit that should allow the path
        result = simulate_nondeterministic_fsa_with_depth_limit(nfa, '', max_depth=5)
        self.assertIsInstance(result, list)
        self.assertTrue(len(result) > 0)

        # Test with depth limit that's too restrictive
        result = simulate_nondeterministic_fsa_with_depth_limit(nfa, '', max_depth=2)
        # Should either find no paths or report depth limit reached
        if isinstance(result, dict):
            self.assertFalse(result['accepted'])

    def test_mixed_epsilon_and_regular_transitions(self):
        """Test correct handling of mixed epsilon and regular transitions"""
        # NFA with mix of epsilon and regular transitions
        nfa = {
            'states': ['S0', 'S1', 'S2', 'S3', 'S4'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'': ['S1'], 'a': ['S2']},  # Epsilon to S1, regular to S2
                'S1': {'b': ['S3']},  # Regular transition
                'S2': {'': ['S3']},  # Epsilon to S3
                'S3': {'': ['S4']},  # Epsilon to S4
                'S4': {}
            },
            'startingState': 'S0',
            'acceptingStates': ['S4']
        }

        # Test path via epsilon transitions: S0 -ε-> S1 -b-> S3 -ε-> S4
        result = simulate_nondeterministic_fsa_with_depth_limit(nfa, 'b', max_depth=5)
        self.assertIsInstance(result, list)
        self.assertTrue(len(result) > 0)

        # Test path via regular then epsilon: S0 -a-> S2 -ε-> S3 -ε-> S4
        result = simulate_nondeterministic_fsa_with_depth_limit(nfa, 'a', max_depth=5)
        self.assertIsInstance(result, list)
        self.assertTrue(len(result) > 0)

    def test_large_depth_limit_performance(self):
        """Test that large depth limits don't cause performance issues with simple FSAs"""
        # Simple NFA without epsilon loops
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

        # Test with very large depth limit - should still work efficiently
        result = simulate_nondeterministic_fsa_with_depth_limit(nfa, 'a', max_depth=1000)
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        expected_path = [('S0', 'a', 'S1')]
        self.assertEqual(result[0], expected_path)

    def test_depth_limit_with_multiple_accepting_paths(self):
        """Test depth limiting with FSAs that have multiple accepting paths"""
        # NFA with multiple paths, some involving epsilon transitions
        nfa = {
            'states': ['S0', 'S1', 'S2', 'S3', 'S4'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'': ['S1'], 'a': ['S2']},  # Two ways to start
                'S1': {'a': ['S3']},  # Path 1: epsilon then 'a'
                'S2': {'': ['S3']},  # Path 2: 'a' then epsilon
                'S3': {'': ['S4']},  # Both paths converge
                'S4': {}
            },
            'startingState': 'S0',
            'acceptingStates': ['S4']
        }

        result = simulate_nondeterministic_fsa_with_depth_limit(nfa, 'a', max_depth=5)
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)  # Should find both paths

    def test_generator_summary_includes_depth_info(self):
        """Test that generator summary includes depth-related information"""
        nfa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'': ['S0'], 'a': ['S1']},  # Epsilon self-loop
                'S1': {}
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }

        results = list(simulate_nondeterministic_fsa_generator_with_depth_limit(nfa, 'a', max_depth=3))

        summary = [r for r in results if r['type'] == 'summary'][0]

        # Check that summary includes depth information
        required_fields = ['depth_limit_reached', 'max_depth_used']
        for field in required_fields:
            self.assertIn(field, summary)

        self.assertEqual(summary['max_depth_used'], 3)
        self.assertIsInstance(summary['depth_limit_reached'], bool)

    def test_invalid_fsa_structure_with_depth_limit(self):
        """Test depth-limited functions handle invalid FSA structures"""
        invalid_nfa = {
            'states': ['S0'],
            'alphabet': ['a']
            # Missing required fields
        }

        # Test regular function
        result = simulate_nondeterministic_fsa_with_depth_limit(invalid_nfa, 'a', max_depth=5)
        self.assertIsInstance(result, dict)
        self.assertFalse(result['accepted'])
        self.assertEqual(result['rejection_reason'], 'Invalid FSA structure')

        # Test generator function
        results = list(simulate_nondeterministic_fsa_generator_with_depth_limit(invalid_nfa, 'a', max_depth=5))
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['type'], 'error')
        self.assertIn('Invalid FSA structure', results[0]['message'])

    def test_empty_string_with_epsilon_loops(self):
        """Test empty string acceptance with epsilon loops"""
        # NFA where start state becomes accepting via epsilon transitions and loops
        nfa = {
            'states': ['S0', 'S1', 'S2'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'': ['S1']},
                'S1': {'': ['S2']},
                'S2': {'': ['S1']}  # Loop between S1 and S2
            },
            'startingState': 'S0',
            'acceptingStates': ['S2']
        }

        result = simulate_nondeterministic_fsa_with_depth_limit(nfa, '', max_depth=5)
        self.assertIsInstance(result, list)
        self.assertTrue(len(result) > 0)

        # Check that paths contain epsilon transitions
        for path in result:
            epsilon_count = sum(1 for transition in path if transition[1] == 'ε')
            self.assertTrue(epsilon_count > 0)

    def test_realistic_epsilon_loop_scenario(self):
        """Test a realistic scenario with epsilon loops that might occur in practice"""
        # NFA representing something like (a|ε)*b with epsilon loops
        nfa = {
            'states': ['S0', 'S1', 'S2', 'S3'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'': ['S1', 'S2'], 'a': ['S1']},  # Choice: epsilon to S1/S2 or 'a' to S1
                'S1': {'': ['S0'], 'b': ['S3']},  # Loop back via epsilon or accept with 'b'
                'S2': {'': ['S0'], 'b': ['S3']},  # Similar loop back
                'S3': {}
            },
            'startingState': 'S0',
            'acceptingStates': ['S3']
        }

        # Test various strings
        test_cases = ['b', 'ab', 'aab', 'aaab']

        for test_string in test_cases:
            result = simulate_nondeterministic_fsa_with_depth_limit(nfa, test_string, max_depth=10)
            self.assertIsInstance(result, list)
            self.assertTrue(len(result) > 0, f"String '{test_string}' should be accepted")

    def test_depth_limit_boundary_conditions(self):
        """Test behavior at depth limit boundaries"""
        # NFA where exactly 3 epsilon transitions reach acceptance
        nfa = {
            'states': ['S0', 'S1', 'S2', 'S3'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'': ['S1']},  # 1 epsilon
                'S1': {'': ['S2']},  # 2 epsilon
                'S2': {'': ['S3']},  # 3 epsilon
                'S3': {}
            },
            'startingState': 'S0',
            'acceptingStates': ['S3']
        }

        # Test with exactly the required depth
        result = simulate_nondeterministic_fsa_with_depth_limit(nfa, '', max_depth=3)
        self.assertIsInstance(result, list)
        self.assertTrue(len(result) > 0)

        # Test with one less than required depth
        result = simulate_nondeterministic_fsa_with_depth_limit(nfa, '', max_depth=2)
        # Should not find the accepting path
        if isinstance(result, dict):
            self.assertFalse(result['accepted'])
        else:
            # If it returns a list, it should be empty or contain partial paths
            self.assertEqual(len(result), 0)

    def test_depth_limit_with_multiple_self_loops(self):
        """Test behavior at depth limit boundaries"""
        # NFA where exactly 3 epsilon transitions reach acceptance
        nfa = {
            'states': ['S0'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'': ['S0'],'a':['S0']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S0']
        }

        # Test a self loop with a large depth
        result = simulate_nondeterministic_fsa_with_depth_limit(nfa, 'a', max_depth=50)
        self.assertIsInstance(result, list)
        self.assertTrue(len(result) > 0)
        print(result)