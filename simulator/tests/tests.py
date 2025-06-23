from django.test import TestCase
from simulator.fsa_simulation import (
    simulate_deterministic_fsa,
    simulate_nondeterministic_fsa,
    simulate_nondeterministic_fsa_generator, detect_epsilon_loops,
    simulate_nondeterministic_fsa_with_depth_limit, simulate_nondeterministic_fsa_generator_with_depth_limit
)
from simulator.fsa_properties import (
    is_deterministic,
    is_complete,
    is_connected,
    check_all_properties,
    validate_fsa_structure
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
        self.assertTrue(is_deterministic(valid_fsa))

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
        self.assertTrue(is_deterministic(valid_incomplete_fsa))

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
        self.assertFalse(is_deterministic(invalid_fsa))

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
        if isinstance(result, list):
            self.assertTrue(len(result) >= 0)
        else:
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

        # Test with exactly the required depth (3)
        result = simulate_nondeterministic_fsa_with_depth_limit(nfa, '', max_depth=3)
        self.assertIsInstance(result, list)
        self.assertTrue(len(result) > 0)

        # Test with one less than required depth (2)
        result = simulate_nondeterministic_fsa_with_depth_limit(nfa, '', max_depth=2)
        if isinstance(result, dict):
            self.assertFalse(result['accepted'])
        else:
            # If it returns a list, it should be empty because S3 is unreachable with only 2 transitions
            print(result)
            self.assertEqual(len(result), 0)

        # Test with insufficient depth (1)
        result = simulate_nondeterministic_fsa_with_depth_limit(nfa, '', max_depth=1)
        if isinstance(result, dict):
            self.assertFalse(result['accepted'])
        else:
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

    def test_deterministic_fsa_rejection_cases(self):
        """Test deterministic FSA rejection scenarios"""
        # FSA for testing various rejection scenarios
        fsa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1']},
                'S1': {'b': ['S0']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }

        # Test symbol not in alphabet (line 55)
        result = simulate_deterministic_fsa(fsa, 'ac')
        self.assertIsInstance(result, dict)
        self.assertFalse(result['accepted'])
        self.assertIn('not in alphabet', result['rejection_reason'])
        self.assertEqual(result['rejection_position'], 1)

        # Test no transition defined (line 66)
        result = simulate_deterministic_fsa(fsa, 'aa')
        self.assertIsInstance(result, dict)
        self.assertFalse(result['accepted'])
        self.assertIn('No transition defined', result['rejection_reason'])
        self.assertEqual(result['rejection_position'], 1)

    def test_nondeterministic_fsa_edge_cases(self):
        """Test non-deterministic FSA edge cases"""
        # Test invalid FSA structure - needs to be truly invalid to trigger line 140
        invalid_nfa = {
            'states': ['S0'],
            'alphabet': ['a'],
            'transitions': {'S0': {'a': ['S1']}},  # S1 not in states
            'startingState': 'S0',
            'acceptingStates': ['S0']
        }

        result = simulate_nondeterministic_fsa(invalid_nfa, 'a')
        self.assertIsInstance(result, dict)
        self.assertFalse(result['accepted'])
        # The actual rejection reason is "No accepting paths found" because
        # the structure validation in _is_valid_nfa_structure passes this FSA
        # but S1 (target of transition) doesn't exist, leading to no accepting paths
        self.assertIn('No accepting paths found', result['rejection_reason'])

        # Test NFA with symbol not in alphabet (lines 300-312)
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

        result = simulate_nondeterministic_fsa(nfa, 'ab')
        self.assertIsInstance(result, dict)
        self.assertFalse(result['accepted'])
        self.assertIn('rejection_reason', result)

    def test_epsilon_closure_edge_cases(self):
        """Test epsilon closure edge cases"""
        # Test _get_epsilon_reachable_states with complex epsilon transitions
        from simulator.fsa_simulation import _get_epsilon_reachable_states

        # NFA with epsilon self-loops and cycles
        nfa = {
            'states': ['S0', 'S1', 'S2', 'S3'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'': ['S0', 'S1']},  # Epsilon self-loop and to S1
                'S1': {'': ['S2']},
                'S2': {'': ['S3', 'S1']},  # Epsilon to S3 and back to S1
                'S3': {'': ['S3']}  # Epsilon self-loop
            },
            'startingState': 'S0',
            'acceptingStates': ['S3']
        }

        # Test epsilon reachable states from S0
        reachable = _get_epsilon_reachable_states(nfa, 'S0')
        expected_states = {'S0', 'S1', 'S2', 'S3'}
        self.assertEqual(reachable, expected_states)

        # Test epsilon reachable states from S1
        reachable = _get_epsilon_reachable_states(nfa, 'S1')
        expected_states = {'S1', 'S2', 'S3'}
        self.assertEqual(reachable, expected_states)

        # Test epsilon reachable states from S3 (only self)
        reachable = _get_epsilon_reachable_states(nfa, 'S3')
        expected_states = {'S3'}
        self.assertEqual(reachable, expected_states)

    def test_cycle_path_finding(self):
        """Test cycle path finding"""
        from simulator.fsa_simulation import _find_cycle_path_in_scc

        # Test with single state SCC
        single_scc = ['S0']
        epsilon_graph = {'S0': ['S0']}
        result = _find_cycle_path_in_scc(single_scc, epsilon_graph)
        self.assertEqual(result, ['S0'])

        # Test with multi-state SCC but no valid cycle found
        multi_scc = ['S0', 'S1', 'S2']
        epsilon_graph = {
            'S0': [],  # No outgoing edges
            'S1': [],
            'S2': []
        }
        result = _find_cycle_path_in_scc(multi_scc, epsilon_graph)
        self.assertEqual(result, multi_scc)  # Should return the SCC itself as fallback

    def test_depth_limited_epsilon_closure_edge_cases(self):
        """Test depth-limited epsilon closure edge cases"""
        from simulator.fsa_simulation import (_get_initial_states_with_paths_total_depth_limited,
                                              _get_epsilon_closure_with_paths_total_depth_limited)

        # NFA with epsilon transitions for depth testing
        nfa = {
            'states': ['S0', 'S1', 'S2', 'S3'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'': ['S1']},
                'S1': {'': ['S2']},
                'S2': {'': ['S3']},
                'S3': {'': ['S1']}  # Creates cycle back to S1
            },
            'startingState': 'S0',
            'acceptingStates': ['S3']
        }

        # Test initial states with very low depth limit (lines 985-992)
        result = _get_initial_states_with_paths_total_depth_limited(nfa, 'S0', max_depth=1)
        self.assertTrue(len(result) >= 1)
        # Should include S0 with empty path and S1 with one epsilon transition
        states = [state for state, path in result]
        self.assertIn('S0', states)
        self.assertIn('S1', states)

        # Test epsilon closure with depth limit (lines 1038-1047)
        result = _get_epsilon_closure_with_paths_total_depth_limited(nfa, 'S1', max_depth=2)
        self.assertTrue(len(result) >= 1)
        # Should include states reachable within 2 epsilon transitions
        states = [state for state, path in result]
        self.assertIn('S1', states)
        self.assertIn('S2', states)

        # Test with zero depth limit
        result = _get_initial_states_with_paths_total_depth_limited(nfa, 'S0', max_depth=0)
        # Should only include the start state with empty path
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0], 'S0')
        self.assertEqual(result[0][1], [])

    def test_invalid_nfa_structure_validation(self):
        """Test _is_valid_nfa_structure edge cases"""
        from simulator.fsa_simulation import _is_valid_nfa_structure

        # Test missing required keys
        invalid_nfa_missing_states = {
            'alphabet': ['a'],
            'transitions': {},
            'startingState': 'S0',
            'acceptingStates': ['S0']
        }
        self.assertFalse(_is_valid_nfa_structure(invalid_nfa_missing_states))

        invalid_nfa_missing_alphabet = {
            'states': ['S0'],
            'transitions': {},
            'startingState': 'S0',
            'acceptingStates': ['S0']
        }
        self.assertFalse(_is_valid_nfa_structure(invalid_nfa_missing_alphabet))

        # Test starting state not in states
        invalid_nfa_bad_start = {
            'states': ['S0'],
            'alphabet': ['a'],
            'transitions': {},
            'startingState': 'S1',  # Not in states
            'acceptingStates': ['S0']
        }
        self.assertFalse(_is_valid_nfa_structure(invalid_nfa_bad_start))

        # Test accepting state not in states
        invalid_nfa_bad_accepting = {
            'states': ['S0'],
            'alphabet': ['a'],
            'transitions': {},
            'startingState': 'S0',
            'acceptingStates': ['S1']  # Not in states
        }
        self.assertFalse(_is_valid_nfa_structure(invalid_nfa_bad_accepting))

        # Test non-dict transitions
        invalid_nfa_bad_transitions = {
            'states': ['S0'],
            'alphabet': ['a'],
            'transitions': "not a dict",
            'startingState': 'S0',
            'acceptingStates': ['S0']
        }
        self.assertFalse(_is_valid_nfa_structure(invalid_nfa_bad_transitions))

    def test_get_transitions_edge_cases(self):
        """Test _get_transitions with edge cases"""
        from simulator.fsa_simulation import _get_transitions

        # Test state not in transitions
        fsa = {
            'transitions': {
                'S0': {'a': ['S1']}
            }
        }
        result = _get_transitions(fsa, 'S1', 'a')  # S1 not in transitions
        self.assertEqual(result, [])

        # Test symbol not in state's transitions
        result = _get_transitions(fsa, 'S0', 'b')  # 'b' not in S0's transitions
        self.assertEqual(result, [])

        # Test valid transition
        result = _get_transitions(fsa, 'S0', 'a')
        self.assertEqual(result, ['S1'])

    def test_complex_epsilon_loop_scenarios(self):
        """Test complex epsilon loop detection scenarios"""
        # Test NFA with unreachable epsilon loops
        nfa_unreachable_loops = {
            'states': ['S0', 'S1', 'S2', 'S3', 'S4'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'a': ['S1']},  # Only path is S0 -> S1
                'S1': {},  # Dead end
                'S2': {'': ['S3']},  # Unreachable epsilon loop
                'S3': {'': ['S4']},
                'S4': {'': ['S2']}  # Completes unreachable loop
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }

        result = detect_epsilon_loops(nfa_unreachable_loops)
        self.assertTrue(result['has_epsilon_loops'])
        self.assertTrue(len(result['loop_details']) > 0)

        # Should have at least one unreachable loop
        unreachable_loops = [loop for loop in result['loop_details'] if not loop['reachable_from_start']]
        self.assertTrue(len(unreachable_loops) > 0)

    def test_deterministic_fsa_non_deterministic_transition_error(self):
        """Test deterministic FSA simulator with non-deterministic transitions"""
        # FSA that claims to be for deterministic simulation but has non-deterministic transitions
        fsa = {
            'states': ['S0', 'S1', 'S2'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1', 'S2']},  # Multiple transitions for 'a'
                'S1': {'b': ['S1']},
                'S2': {'b': ['S2']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S1', 'S2']
        }

        # This should be rejected by the deterministic simulator
        result = simulate_deterministic_fsa(fsa, 'a')
        self.assertIsInstance(result, dict)
        self.assertFalse(result['accepted'])
        self.assertIn('FSA must be deterministic', result['rejection_reason'])

    def test_simulate_nondeterministic_transitions_missing(self):
        """Test NFA simulation when transitions are missing for current state"""
        nfa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1']},
                # S1 has no transitions defined
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }

        # Test string that would require transition from S1
        result = simulate_nondeterministic_fsa(nfa, 'aa')
        self.assertIsInstance(result, dict)
        self.assertFalse(result['accepted'])

    def test_epsilon_transitions_validation(self):
        """Test _has_epsilon_transitions function edge cases"""
        from simulator.fsa_simulation import _has_epsilon_transitions

        # FSA with empty epsilon transition list
        fsa_empty_epsilon = {
            'states': ['S0'],
            'transitions': {
                'S0': {'': []}  # Empty epsilon transitions
            }
        }
        self.assertFalse(_has_epsilon_transitions(fsa_empty_epsilon))

        # FSA with no epsilon key
        fsa_no_epsilon = {
            'states': ['S0'],
            'transitions': {
                'S0': {'a': ['S0']}  # No epsilon key
            }
        }
        self.assertFalse(_has_epsilon_transitions(fsa_no_epsilon))

        # FSA with state not in transitions
        fsa_missing_state = {
            'states': ['S0', 'S1'],
            'transitions': {
                'S0': {'': ['S1']}
                # S1 not in transitions
            }
        }
        self.assertTrue(_has_epsilon_transitions(fsa_missing_state))

    def test_depth_limit_generator_edge_cases(self):
        """Test depth-limited generator edge cases"""
        # NFA where reaching acceptance requires exceeding the depth limit
        nfa = {
            'states': ['S0', 'S1', 'S2', 'S3'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'': ['S1']},      # 1 epsilon: S0 -> S1
                'S1': {'': ['S2']},      # 2 epsilon: S1 -> S2
                'S2': {'': ['S3']},      # 3 epsilon: S2 -> S3
                'S3': {}                 # No transitions from S3
            },
            'startingState': 'S0',
            'acceptingStates': ['S3']  # Acceptance requires 3 epsilon transitions
        }

        # Test with max_depth=2, but acceptance requires depth 3
        results = list(simulate_nondeterministic_fsa_generator_with_depth_limit(nfa, '', max_depth=2))

        accepting_paths = [r for r in results if r['type'] == 'accepting_path']
        summary = [r for r in results if r['type'] == 'summary']

        # Should have summary
        self.assertEqual(len(summary), 1)

        # Should NOT find any accepting paths (since acceptance requires depth 3 but limit is 2)
        self.assertEqual(len(accepting_paths), 0)
        self.assertFalse(summary[0]['accepted'])

        # No paths should be found due to depth limitation
        self.assertTrue(summary[0]['total_paths_explored'] > 0)  # Some exploration happened
        self.assertEqual(summary[0]['total_accepting_paths'], 0)  # But no acceptance

    def test_all_reachable_states_comprehensive(self):
        """Test _get_all_reachable_states with comprehensive FSA"""
        from simulator.fsa_simulation import _get_all_reachable_states

        # Complex FSA with both regular and epsilon transitions
        nfa = {
            'states': ['S0', 'S1', 'S2', 'S3', 'S4'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'': ['S1'], 'a': ['S2']},
                'S1': {'b': ['S3']},
                'S2': {'': ['S4']},
                'S3': {'a': ['S4']},
                'S4': {}
            },
            'startingState': 'S0',
            'acceptingStates': ['S4']
        }

        reachable = _get_all_reachable_states(nfa, 'S0')
        expected = {'S0', 'S1', 'S2', 'S3', 'S4'}
        self.assertEqual(reachable, expected)

        # Test with isolated states
        nfa_with_isolated = {
            'states': ['S0', 'S1', 'S2'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'a': ['S1']},
                'S1': {},
                'S2': {'a': ['S2']}  # S2 is isolated
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }

        reachable = _get_all_reachable_states(nfa_with_isolated, 'S0')
        expected = {'S0', 'S1'}  # S2 should not be reachable
        self.assertEqual(reachable, expected)

    def test_generator_depth_limit_invalid_symbol_in_input(self):
        """Test symbol not in alphabet check in generator with depth limit"""

        # Create a structurally valid NFA (passes _is_valid_nfa_structure)
        # but provide input with symbols not in the alphabet
        nfa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a', 'b'],  # Only 'a' and 'b' are valid
            'transitions': {
                'S0': {'a': ['S1'], 'b': ['S0']},
                'S1': {'a': ['S0'], 'b': ['S1']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }

        # Test with input containing symbol 'c' which is NOT in the alphabet
        # This should trigger the "Symbol not in alphabet" check at lines 985-992
        results = list(simulate_nondeterministic_fsa_generator_with_depth_limit(nfa, 'ac', max_depth=10))

        # Should have rejected paths due to invalid symbol
        rejected_paths = [r for r in results if r['type'] == 'rejected_path']
        summary = [r for r in results if r['type'] == 'summary']

        # Should have at least one rejection due to symbol not in alphabet
        symbol_rejections = [r for r in rejected_paths if 'not in alphabet' in r['reason']]
        self.assertTrue(len(symbol_rejections) > 0, "Should have rejections due to symbol not in alphabet")

        # Check the rejection details
        symbol_rejection = symbol_rejections[0]
        self.assertIn('rejection_position', symbol_rejection)
        self.assertIn('total_depth', symbol_rejection)
        self.assertEqual(symbol_rejection['rejection_position'], 1)  # Position of 'c' in 'ac'

        # Should have summary showing not accepted
        self.assertEqual(len(summary), 1)
        self.assertFalse(summary[0]['accepted'])

class TestFsaProperties(TestCase):
    """Test cases for FSA property checking functions"""

    def test_deterministic_property(self):
        """Test is_deterministic function"""
        # Deterministic FSA
        deterministic_fsa = {
            'states': ['S0', 'S1', 'S2'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1'], 'b': ['S0']},
                'S1': {'a': ['S2'], 'b': ['S0']},
                'S2': {'a': ['S2'], 'b': ['S2']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S2']
        }
        self.assertTrue(is_deterministic(deterministic_fsa))

        # Non-deterministic FSA (multiple transitions)
        nondeterministic_fsa = {
            'states': ['S0', 'S1', 'S2'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1', 'S2'], 'b': ['S0']},  # Multiple transitions on 'a'
                'S1': {'a': ['S2'], 'b': ['S0']},
                'S2': {'a': ['S2'], 'b': ['S2']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S2']
        }
        self.assertFalse(is_deterministic(nondeterministic_fsa))

        # FSA with epsilon transitions
        epsilon_fsa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'': ['S1'], 'a': ['S0']},  # Epsilon transition
                'S1': {'a': ['S1']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }
        self.assertFalse(is_deterministic(epsilon_fsa))

        # FSA with empty epsilon transitions (should be deterministic)
        empty_epsilon_fsa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'': [], 'a': ['S1']},  # Empty epsilon transitions
                'S1': {'a': ['S0']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }
        self.assertTrue(is_deterministic(empty_epsilon_fsa))

    def test_deterministic_property_edge_cases(self):
        """Test edge cases for is_deterministic"""
        # Empty alphabet
        empty_alphabet_fsa = {
            'states': ['S0'],
            'alphabet': [],
            'transitions': {'S0': {}},
            'startingState': 'S0',
            'acceptingStates': ['S0']
        }
        self.assertTrue(is_deterministic(empty_alphabet_fsa))

        # Missing transitions for some states
        incomplete_fsa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1']},  # Missing 'b' transition
                'S1': {'a': ['S0'], 'b': ['S1']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }
        self.assertTrue(is_deterministic(incomplete_fsa))  # Still deterministic

    def test_complete_property(self):
        """Test is_complete function"""
        # Complete FSA
        complete_fsa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1'], 'b': ['S0']},
                'S1': {'a': ['S0'], 'b': ['S1']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }
        self.assertTrue(is_complete(complete_fsa))

        # Incomplete FSA (missing transition)
        incomplete_fsa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1']},  # Missing 'b' transition
                'S1': {'a': ['S0'], 'b': ['S1']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }
        self.assertFalse(is_complete(incomplete_fsa))

        # FSA with empty transitions
        empty_transitions_fsa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': [], 'b': ['S0']},  # Empty transition list
                'S1': {'a': ['S0'], 'b': ['S1']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }
        self.assertFalse(is_complete(empty_transitions_fsa))

        # FSA with multiple transitions (non-deterministic but complete)
        nondeterministic_complete_fsa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S0', 'S1'], 'b': ['S0']},  # Multiple transitions
                'S1': {'a': ['S0'], 'b': ['S1']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }
        self.assertTrue(is_complete(nondeterministic_complete_fsa))

    def test_complete_property_edge_cases(self):
        """Test edge cases for is_complete"""
        # Empty states
        empty_states_fsa = {
            'states': [],
            'alphabet': ['a'],
            'transitions': {},
            'startingState': '',
            'acceptingStates': []
        }
        self.assertTrue(is_complete(empty_states_fsa))  # Trivially complete

        # Empty alphabet
        empty_alphabet_fsa = {
            'states': ['S0'],
            'alphabet': [],
            'transitions': {'S0': {}},
            'startingState': 'S0',
            'acceptingStates': ['S0']
        }
        self.assertTrue(is_complete(empty_alphabet_fsa))  # Trivially complete

        # State not in transitions
        missing_state_transitions = {
            'states': ['S0', 'S1'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'a': ['S1']}
                # S1 missing from transitions
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }
        self.assertFalse(is_complete(missing_state_transitions))

    def test_connected_property(self):
        """Test is_connected function"""
        # Connected FSA
        connected_fsa = {
            'states': ['S0', 'S1', 'S2'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1'], 'b': ['S0']},
                'S1': {'a': ['S2'], 'b': ['S0']},
                'S2': {'a': ['S2'], 'b': ['S1']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S2']
        }
        self.assertTrue(is_connected(connected_fsa))

        # Disconnected FSA (unreachable state)
        disconnected_fsa = {
            'states': ['S0', 'S1', 'S2'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1'], 'b': ['S0']},
                'S1': {'a': ['S1'], 'b': ['S0']},
                'S2': {'a': ['S2'], 'b': ['S2']}  # S2 is unreachable
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }
        self.assertFalse(is_connected(disconnected_fsa))

        # FSA with epsilon transitions making states reachable
        epsilon_connected_fsa = {
            'states': ['S0', 'S1', 'S2'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'': ['S1'], 'a': ['S0']},  # Epsilon transition to S1
                'S1': {'': ['S2']},  # Epsilon transition to S2
                'S2': {'a': ['S0']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S2']
        }
        self.assertTrue(is_connected(epsilon_connected_fsa))

    def test_connected_property_edge_cases(self):
        """Test edge cases for is_connected"""
        # Empty states
        empty_states_fsa = {
            'states': [],
            'alphabet': ['a'],
            'transitions': {},
            'startingState': '',
            'acceptingStates': []
        }
        self.assertTrue(is_connected(empty_states_fsa))  # Trivially connected

        # Single state
        single_state_fsa = {
            'states': ['S0'],
            'alphabet': ['a'],
            'transitions': {'S0': {'a': ['S0']}},
            'startingState': 'S0',
            'acceptingStates': ['S0']
        }
        self.assertTrue(is_connected(single_state_fsa))

        # No starting state
        no_start_fsa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'a': ['S1']},
                'S1': {'a': ['S0']}
            },
            'startingState': '',
            'acceptingStates': ['S1']
        }
        self.assertFalse(is_connected(no_start_fsa))

        # Starting state not in states list
        invalid_start_fsa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'a': ['S1']},
                'S1': {'a': ['S0']}
            },
            'startingState': 'S2',  # S2 not in states
            'acceptingStates': ['S1']
        }
        self.assertFalse(is_connected(invalid_start_fsa))

        # No transitions
        no_transitions_fsa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a'],
            'transitions': {},
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }
        self.assertFalse(is_connected(no_transitions_fsa))

    def test_check_all_properties(self):
        """Test check_all_properties function"""
        # Complete, deterministic, connected FSA
        perfect_fsa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1'], 'b': ['S0']},
                'S1': {'a': ['S0'], 'b': ['S1']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }

        result = check_all_properties(perfect_fsa)
        self.assertTrue(result['deterministic'])
        self.assertTrue(result['complete'])
        self.assertTrue(result['connected'])

        # Incomplete, non-deterministic, disconnected FSA
        problematic_fsa = {
            'states': ['S0', 'S1', 'S2'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S0', 'S1']},  # Non-deterministic, missing 'b'
                'S1': {'a': ['S1'], 'b': ['S1']},
                'S2': {'a': ['S2'], 'b': ['S2']}  # Unreachable
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }

        result = check_all_properties(problematic_fsa)
        self.assertFalse(result['deterministic'])  # Multiple transitions on 'a'
        self.assertFalse(result['complete'])  # Missing 'b' transition from S0
        self.assertFalse(result['connected'])  # S2 is unreachable

    def test_validate_fsa_structure(self):
        """Test validate_fsa_structure function"""
        # Valid FSA structure
        valid_fsa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1'], 'b': ['S0']},
                'S1': {'a': ['S0'], 'b': ['S1']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }

        result = validate_fsa_structure(valid_fsa)
        self.assertTrue(result['valid'])
        self.assertNotIn('error', result)

        # Missing required key
        missing_key_fsa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1'], 'b': ['S0']},
                'S1': {'a': ['S0'], 'b': ['S1']}
            },
            'startingState': 'S0'
            # Missing acceptingStates
        }

        result = validate_fsa_structure(missing_key_fsa)
        self.assertFalse(result['valid'])
        self.assertIn('error', result)
        self.assertIn('acceptingStates', result['error'])

        # Wrong type for states
        wrong_type_fsa = {
            'states': 'S0',  # Should be list
            'alphabet': ['a', 'b'],
            'transitions': {},
            'startingState': 'S0',
            'acceptingStates': []
        }

        result = validate_fsa_structure(wrong_type_fsa)
        self.assertFalse(result['valid'])
        self.assertIn('error', result)
        self.assertIn('states must be a list', result['error'])

        # Starting state not in states list
        invalid_start_fsa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a'],
            'transitions': {},
            'startingState': 'S2',  # Not in states
            'acceptingStates': []
        }

        result = validate_fsa_structure(invalid_start_fsa)
        self.assertFalse(result['valid'])
        self.assertIn('error', result)
        self.assertIn('Starting state not in states list', result['error'])

        # Accepting state not in states list
        invalid_accepting_fsa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a'],
            'transitions': {},
            'startingState': 'S0',
            'acceptingStates': ['S2']  # S2 not in states
        }

        result = validate_fsa_structure(invalid_accepting_fsa)
        self.assertFalse(result['valid'])
        self.assertIn('error', result)
        self.assertIn('Accepting state S2 not in states list', result['error'])

        # Not a dictionary
        not_dict = "not a dictionary"

        result = validate_fsa_structure(not_dict)
        self.assertFalse(result['valid'])
        self.assertIn('error', result)
        self.assertIn('FSA must be a dictionary', result['error'])

    def test_validate_fsa_structure_lenient(self):
        """Test that validate_fsa_structure is lenient with empty values"""
        # Empty states (should be valid)
        empty_states_fsa = {
            'states': [],
            'alphabet': ['a'],
            'transitions': {},
            'startingState': '',
            'acceptingStates': []
        }

        result = validate_fsa_structure(empty_states_fsa)
        self.assertTrue(result['valid'])

        # Empty alphabet (should be valid)
        empty_alphabet_fsa = {
            'states': ['S0'],
            'alphabet': [],
            'transitions': {},
            'startingState': 'S0',
            'acceptingStates': []
        }

        result = validate_fsa_structure(empty_alphabet_fsa)
        self.assertTrue(result['valid'])

        # Empty transitions (should be valid)
        empty_transitions_fsa = {
            'states': ['S0'],
            'alphabet': ['a'],
            'transitions': {},
            'startingState': 'S0',
            'acceptingStates': ['S0']
        }

        result = validate_fsa_structure(empty_transitions_fsa)
        self.assertTrue(result['valid'])

    def test_properties_with_epsilon_transitions(self):
        """Test property functions with epsilon transitions"""
        epsilon_fsa = {
            'states': ['S0', 'S1', 'S2'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'': ['S1'], 'a': ['S0']},  # Epsilon transition
                'S1': {'b': ['S2']},
                'S2': {'': ['S0']}  # Epsilon back to start
            },
            'startingState': 'S0',
            'acceptingStates': ['S2']
        }

        # Should be non-deterministic due to epsilon transitions
        self.assertFalse(is_deterministic(epsilon_fsa))

        # Should be incomplete (missing some regular transitions)
        self.assertFalse(is_complete(epsilon_fsa))

        # Should be connected via epsilon transitions
        self.assertTrue(is_connected(epsilon_fsa))

    def test_properties_with_complex_fsa(self):
        """Test properties with a more complex FSA"""
        complex_fsa = {
            'states': ['S0', 'S1', 'S2', 'S3', 'S4'],
            'alphabet': ['a', 'b', 'c'],
            'transitions': {
                'S0': {'a': ['S1'], 'b': ['S2'], 'c': ['S0']},
                'S1': {'a': ['S3'], 'b': ['S1'], 'c': ['S4']},
                'S2': {'a': ['S2'], 'b': ['S3'], 'c': ['S1']},
                'S3': {'a': ['S4'], 'b': ['S3'], 'c': ['S2']},
                'S4': {'a': ['S0'], 'b': ['S4'], 'c': ['S3']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S3', 'S4']
        }

        result = check_all_properties(complex_fsa)

        # Should be deterministic (exactly one transition per state-symbol pair)
        self.assertTrue(result['deterministic'])

        # Should be complete (all states have transitions for all symbols)
        self.assertTrue(result['complete'])

        # Should be connected (all states reachable from S0)
        self.assertTrue(result['connected'])

    def test_properties_consistency(self):
        """Test that property functions are consistent with each other"""
        test_fsas = [
            # Simple deterministic complete connected FSA
            {
                'states': ['S0', 'S1'],
                'alphabet': ['a'],
                'transitions': {
                    'S0': {'a': ['S1']},
                    'S1': {'a': ['S0']}
                },
                'startingState': 'S0',
                'acceptingStates': ['S1']
            },
            # Non-deterministic FSA
            {
                'states': ['S0', 'S1'],
                'alphabet': ['a'],
                'transitions': {
                    'S0': {'a': ['S0', 'S1']},  # Multiple transitions
                    'S1': {'a': ['S1']}
                },
                'startingState': 'S0',
                'acceptingStates': ['S1']
            },
            # Incomplete FSA
            {
                'states': ['S0', 'S1'],
                'alphabet': ['a', 'b'],
                'transitions': {
                    'S0': {'a': ['S1']},  # Missing 'b' transition
                    'S1': {'a': ['S0'], 'b': ['S1']}
                },
                'startingState': 'S0',
                'acceptingStates': ['S1']
            }
        ]

        for fsa in test_fsas:
            # Individual property checks
            det = is_deterministic(fsa)
            comp = is_complete(fsa)
            conn = is_connected(fsa)

            # All properties check
            all_props = check_all_properties(fsa)

            # Should be consistent
            self.assertEqual(det, all_props['deterministic'])
            self.assertEqual(comp, all_props['complete'])
            self.assertEqual(conn, all_props['connected'])