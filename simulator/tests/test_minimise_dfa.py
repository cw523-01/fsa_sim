from django.test import TestCase
from simulator.fsa_transformations import minimise_dfa
from simulator.fsa_properties import is_deterministic
from simulator.fsa_simulation import simulate_deterministic_fsa


class TestMinimiseDFA(TestCase):
    """Test cases for DFA minimization function"""

    def test_simple_dfa_minimization(self):
        """Test minimization of a simple DFA with equivalent states"""
        # DFA that accepts strings ending with 'a'
        # States S0, S1 and S2 are all equivalent (all non-accepting, same transition behavior)
        dfa = {
            'states': ['S0', 'S1', 'S2', 'S3'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S3'], 'b': ['S1']},  # Start state
                'S1': {'a': ['S3'], 'b': ['S2']},  # Non-accepting
                'S2': {'a': ['S3'], 'b': ['S1']},  # Non-accepting (equivalent to S0 and S1)
                'S3': {'a': ['S3'], 'b': ['S1']}  # Accepting
            },
            'startingState': 'S0',
            'acceptingStates': ['S3']
        }

        minimized = minimise_dfa(dfa)

        # Should have 2 states (merged S0+S1+S2, S3)
        # S0, S1, S2 are equivalent because they're all non-accepting and have same transition behavior:

        self.assertEqual(len(minimized['states']), 2)
        self.assertTrue(is_deterministic(minimized))
        self.assertEqual(minimized['alphabet'], ['a', 'b'])
        self.assertEqual(len(minimized['acceptingStates']), 1)

        # Test that both DFAs accept the same language
        test_strings = ['', 'a', 'b', 'ab', 'ba', 'aa', 'bb', 'aba', 'bab']
        for test_string in test_strings:
            original_result = simulate_deterministic_fsa(dfa, test_string)
            minimized_result = simulate_deterministic_fsa(minimized, test_string)

            if isinstance(original_result, list):
                original_accepted = True
            else:
                original_accepted = original_result.get('accepted', False)

            if isinstance(minimized_result, list):
                minimized_accepted = True
            else:
                minimized_accepted = minimized_result.get('accepted', False)

            self.assertEqual(original_accepted, minimized_accepted,
                             f"Disagreement on string '{test_string}'")

    def test_dfa_minimization_three_states(self):
        """Test minimization of DFA that results in exactly 3 states"""
        # DFA where states have different distances to acceptance
        dfa = {
            'states': ['S0', 'S1', 'S2'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1'], 'b': ['S0']},  # Can reach accepting in 2 steps
                'S1': {'a': ['S2'], 'b': ['S0']},  # Can reach accepting in 1 step
                'S2': {'a': ['S2'], 'b': ['S2']}  # Already accepting
            },
            'startingState': 'S0',
            'acceptingStates': ['S2']
        }

        minimized = minimise_dfa(dfa)

        # Should have 3 states - all have different behavior:
        # S0: needs 2 'a's to reach acceptance
        # S1: needs 1 'a' to reach acceptance
        # S2: already accepting
        self.assertEqual(len(minimized['states']), 3)
        self.assertTrue(is_deterministic(minimized))
        self.assertEqual(len(minimized['acceptingStates']), 1)

        # Test language equivalence
        test_strings = ['', 'a', 'aa', 'b', 'ab', 'ba', 'aaa', 'aba']
        for test_string in test_strings:
            original_result = simulate_deterministic_fsa(dfa, test_string)
            minimized_result = simulate_deterministic_fsa(minimized, test_string)

            original_accepted = isinstance(original_result, list)
            minimized_accepted = isinstance(minimized_result, list)

            self.assertEqual(original_accepted, minimized_accepted,
                             f"Disagreement on string '{test_string}'")

    def test_already_minimal_dfa(self):
        """Test minimization of a DFA that's already minimal"""
        # Simple DFA that's already minimal
        dfa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1'], 'b': ['S0']},
                'S1': {'a': ['S0'], 'b': ['S1']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }

        minimized = minimise_dfa(dfa)

        # Should remain the same size
        self.assertEqual(len(minimized['states']), 2)
        self.assertTrue(is_deterministic(minimized))

        # Test language equivalence
        test_strings = ['', 'a', 'b', 'ab', 'ba', 'aab', 'abb']
        for test_string in test_strings:
            original_result = simulate_deterministic_fsa(dfa, test_string)
            minimized_result = simulate_deterministic_fsa(minimized, test_string)

            original_accepted = isinstance(original_result, list)
            minimized_accepted = isinstance(minimized_result, list)

            self.assertEqual(original_accepted, minimized_accepted)

    def test_dfa_with_unreachable_states(self):
        """Test minimization of DFA with unreachable states"""
        # DFA with state S3 that's unreachable from start
        dfa = {
            'states': ['S0', 'S1', 'S2', 'S3'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1'], 'b': ['S0']},
                'S1': {'a': ['S2'], 'b': ['S0']},
                'S2': {'a': ['S2'], 'b': ['S2']},
                'S3': {'a': ['S3'], 'b': ['S3']}  # Unreachable
            },
            'startingState': 'S0',
            'acceptingStates': ['S2']
        }

        minimized = minimise_dfa(dfa)

        # Should have fewer states (S3 should be in a partition but effectively ignored)
        self.assertTrue(is_deterministic(minimized))

        # Test language equivalence
        test_strings = ['', 'a', 'aa', 'ab', 'ba', 'aaa', 'aab']
        for test_string in test_strings:
            original_result = simulate_deterministic_fsa(dfa, test_string)
            minimized_result = simulate_deterministic_fsa(minimized, test_string)

            original_accepted = isinstance(original_result, list)
            minimized_accepted = isinstance(minimized_result, list)

            self.assertEqual(original_accepted, minimized_accepted)

    def test_complex_dfa_minimization(self):
        """Test minimization of a more complex DFA"""
        # DFA that recognizes strings with even number of a's and even number of b's
        # Has multiple equivalent states that can be merged
        dfa = {
            'states': ['S00', 'S01', 'S10', 'S11', 'S01_dup', 'S10_dup'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S00': {'a': ['S10'], 'b': ['S01']},  # even a's, even b's (accepting)
                'S01': {'a': ['S11'], 'b': ['S00']},  # even a's, odd b's
                'S10': {'a': ['S00'], 'b': ['S11']},  # odd a's, even b's
                'S11': {'a': ['S01_dup'], 'b': ['S10_dup']},  # odd a's, odd b's
                'S01_dup': {'a': ['S11'], 'b': ['S00']},  # equivalent to S01
                'S10_dup': {'a': ['S00'], 'b': ['S11']}  # equivalent to S10
            },
            'startingState': 'S00',
            'acceptingStates': ['S00']
        }

        minimized = minimise_dfa(dfa)

        # Should have 4 states (the duplicates should be merged)
        self.assertEqual(len(minimized['states']), 4)
        self.assertTrue(is_deterministic(minimized))

        # Test language equivalence
        test_strings = ['', 'a', 'b', 'aa', 'ab', 'ba', 'bb', 'aabb', 'abab', 'baba']
        for test_string in test_strings:
            original_result = simulate_deterministic_fsa(dfa, test_string)
            minimized_result = simulate_deterministic_fsa(minimized, test_string)

            original_accepted = isinstance(original_result, list)
            minimized_accepted = isinstance(minimized_result, list)

            self.assertEqual(original_accepted, minimized_accepted)

    def test_single_state_dfa(self):
        """Test minimization of single-state DFA"""
        # Single accepting state with self-loops
        dfa = {
            'states': ['S0'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S0'], 'b': ['S0']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S0']
        }

        minimized = minimise_dfa(dfa)

        self.assertEqual(len(minimized['states']), 1)
        self.assertTrue(is_deterministic(minimized))
        self.assertEqual(minimized['acceptingStates'], ['S0'])

    def test_dfa_with_dead_states(self):
        """Test minimization of DFA with dead (trap) states"""
        # DFA with multiple dead states that should be merged
        dfa = {
            'states': ['S0', 'S1', 'Dead1', 'Dead2'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1'], 'b': ['Dead1']},
                'S1': {'a': ['S1'], 'b': ['Dead2']},
                'Dead1': {'a': ['Dead1'], 'b': ['Dead1']},  # Dead state
                'Dead2': {'a': ['Dead2'], 'b': ['Dead2']}  # Another dead state
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }

        minimized = minimise_dfa(dfa)

        # Dead states should be merged into one
        self.assertEqual(len(minimized['states']), 3)
        self.assertTrue(is_deterministic(minimized))

        # Test language equivalence
        test_strings = ['', 'a', 'b', 'aa', 'ab', 'ba', 'aaa']
        for test_string in test_strings:
            original_result = simulate_deterministic_fsa(dfa, test_string)
            minimized_result = simulate_deterministic_fsa(minimized, test_string)

            original_accepted = isinstance(original_result, list)
            minimized_accepted = isinstance(minimized_result, list)

            self.assertEqual(original_accepted, minimized_accepted)

    def test_dfa_all_states_accepting(self):
        """Test minimization when all states are accepting"""
        dfa = {
            'states': ['S0', 'S1', 'S2'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'a': ['S1']},
                'S1': {'a': ['S2']},
                'S2': {'a': ['S0']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S0', 'S1', 'S2']  # All accepting
        }

        minimized = minimise_dfa(dfa)

        # Should be reduced to single state since all accept and behavior is equivalent
        self.assertEqual(len(minimized['states']), 1)
        self.assertTrue(is_deterministic(minimized))

    def test_dfa_no_accepting_states(self):
        """Test minimization when no states are accepting"""
        dfa = {
            'states': ['S0', 'S1', 'S2'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1'], 'b': ['S2']},
                'S1': {'a': ['S0'], 'b': ['S2']},
                'S2': {'a': ['S2'], 'b': ['S2']}
            },
            'startingState': 'S0',
            'acceptingStates': []  # No accepting states
        }

        minimized = minimise_dfa(dfa)

        # Should minimize effectively since no states accept
        self.assertTrue(is_deterministic(minimized))
        self.assertEqual(minimized['acceptingStates'], [])

        # All strings should be rejected
        test_strings = ['', 'a', 'b', 'ab', 'ba']
        for test_string in test_strings:
            result = simulate_deterministic_fsa(minimized, test_string)
            self.assertIsInstance(result, dict)
            self.assertFalse(result.get('accepted', True))

    def test_empty_alphabet_dfa(self):
        """Test minimization with empty alphabet"""
        dfa = {
            'states': ['S0', 'S1'],
            'alphabet': [],
            'transitions': {
                'S0': {},
                'S1': {}
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }

        minimized = minimise_dfa(dfa)

        # Should maintain structure but potentially merge equivalent states
        self.assertTrue(is_deterministic(minimized))
        self.assertEqual(minimized['alphabet'], [])

    def test_dfa_with_self_loops(self):
        """Test minimization of DFA with various self-loops"""
        dfa = {
            'states': ['S0', 'S1', 'S2', 'S3'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1'], 'b': ['S0']},  # Self-loop on b
                'S1': {'a': ['S1'], 'b': ['S2']},  # Self-loop on a
                'S2': {'a': ['S3'], 'b': ['S2']},  # Self-loop on b
                'S3': {'a': ['S3'], 'b': ['S3']}  # Self-loops on both
            },
            'startingState': 'S0',
            'acceptingStates': ['S3']
        }

        minimized = minimise_dfa(dfa)

        self.assertTrue(is_deterministic(minimized))

        # Test language equivalence
        test_strings = ['', 'a', 'b', 'aa', 'ab', 'ba', 'bb', 'aab', 'abb']
        for test_string in test_strings:
            original_result = simulate_deterministic_fsa(dfa, test_string)
            minimized_result = simulate_deterministic_fsa(minimized, test_string)

            original_accepted = isinstance(original_result, list)
            minimized_accepted = isinstance(minimized_result, list)

            self.assertEqual(original_accepted, minimized_accepted)

    def test_minimization_preserves_start_state_behavior(self):
        """Test that minimization preserves start state behavior"""
        # DFA where start state is accepting
        dfa = {
            'states': ['S0', 'S1', 'S2'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'a': ['S1']},
                'S1': {'a': ['S2']},
                'S2': {'a': ['S0']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S0', 'S2']  # Start state is accepting
        }

        minimized = minimise_dfa(dfa)

        # Empty string should be accepted in both
        original_empty = simulate_deterministic_fsa(dfa, '')
        minimized_empty = simulate_deterministic_fsa(minimized, '')

        original_accepts_empty = isinstance(original_empty, list)
        minimized_accepts_empty = isinstance(minimized_empty, list)

        self.assertEqual(original_accepts_empty, minimized_accepts_empty)
        self.assertTrue(original_accepts_empty)  # Should accept empty string

    def test_state_naming_convention(self):
        """Test that minimized DFA uses proper state naming"""
        dfa = {
            'states': ['A', 'B', 'C'],
            'alphabet': ['0', '1'],
            'transitions': {
                'A': {'0': ['B'], '1': ['C']},
                'B': {'0': ['A'], '1': ['C']},
                'C': {'0': ['C'], '1': ['C']}
            },
            'startingState': 'A',
            'acceptingStates': ['A']
        }

        minimized = minimise_dfa(dfa)

        # Check that state names are properly formatted (joined with underscores)
        for state in minimized['states']:
            self.assertIsInstance(state, str)
            # State names should be non-empty
            self.assertGreater(len(state), 0)

        # Check that all transitions reference valid states
        for state in minimized['transitions']:
            self.assertIn(state, minimized['states'])
            for symbol in minimized['transitions'][state]:
                for target in minimized['transitions'][state][symbol]:
                    self.assertIn(target, minimized['states'])

    def test_non_deterministic_fsa_raises_error(self):
        """Test that non-deterministic FSA raises ValueError"""
        nfa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'a': ['S0', 'S1']},  # Non-deterministic: multiple transitions
                'S1': {'a': ['S1']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }

        with self.assertRaises(ValueError) as context:
            minimise_dfa(nfa)

        self.assertIn("deterministic", str(context.exception))

    def test_fsa_with_epsilon_transitions_raises_error(self):
        """Test that FSA with epsilon transitions raises ValueError"""
        fsa_with_epsilon = {
            'states': ['S0', 'S1'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'': ['S1'], 'a': ['S0']},  # Epsilon transition
                'S1': {'a': ['S1']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }

        with self.assertRaises(ValueError) as context:
            minimise_dfa(fsa_with_epsilon)

        self.assertIn("deterministic", str(context.exception))

    def test_minimization_result_structure(self):
        """Test that minimized DFA has correct structure"""
        dfa = {
            'states': ['S0', 'S1', 'S2'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1'], 'b': ['S2']},
                'S1': {'a': ['S0'], 'b': ['S2']},
                'S2': {'a': ['S2'], 'b': ['S2']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S0']
        }

        minimized = minimise_dfa(dfa)

        # Check all required keys are present
        required_keys = ['states', 'alphabet', 'transitions', 'startingState', 'acceptingStates']
        for key in required_keys:
            self.assertIn(key, minimized)

        # Check types
        self.assertIsInstance(minimized['states'], list)
        self.assertIsInstance(minimized['alphabet'], list)
        self.assertIsInstance(minimized['transitions'], dict)
        self.assertIsInstance(minimized['startingState'], str)
        self.assertIsInstance(minimized['acceptingStates'], list)

        # Check that start state is in states list
        self.assertIn(minimized['startingState'], minimized['states'])

        # Check that all accepting states are in states list
        for state in minimized['acceptingStates']:
            self.assertIn(state, minimized['states'])

        # Check that states are sorted
        self.assertEqual(minimized['states'], sorted(minimized['states']))

        # Check that accepting states are sorted
        self.assertEqual(minimized['acceptingStates'], sorted(minimized['acceptingStates']))

    def test_large_dfa_minimization(self):
        """Test minimization of larger DFA"""
        # Create DFA with many equivalent states
        states = [f'S{i}' for i in range(10)]

        # Create transitions where states S2-S9 are all equivalent
        transitions = {
            'S0': {'a': ['S1'], 'b': ['S2']},
            'S1': {'a': ['S0'], 'b': ['S2']}
        }

        # S2-S9 all have same behavior (equivalent states)
        for i in range(2, 10):
            transitions[f'S{i}'] = {'a': [f'S{(i + 1) if i < 9 else 2}'], 'b': [f'S{i}']}

        dfa = {
            'states': states,
            'alphabet': ['a', 'b'],
            'transitions': transitions,
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }

        minimized = minimise_dfa(dfa)

        # Should significantly reduce the number of states
        self.assertLess(len(minimized['states']), len(states))
        self.assertTrue(is_deterministic(minimized))

        # Test some strings for language equivalence
        test_strings = ['', 'a', 'b', 'ab', 'ba', 'aa', 'bb']
        for test_string in test_strings:
            original_result = simulate_deterministic_fsa(dfa, test_string)
            minimized_result = simulate_deterministic_fsa(minimized, test_string)

            original_accepted = isinstance(original_result, list)
            minimized_accepted = isinstance(minimized_result, list)

            self.assertEqual(original_accepted, minimized_accepted)

    def test_minimization_with_missing_transitions(self):
        """Test minimization when some transitions are missing"""
        # DFA with incomplete transition function
        dfa = {
            'states': ['S0', 'S1', 'S2'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1']},  # Missing 'b' transition
                'S1': {'a': ['S2'], 'b': ['S0']},
                'S2': {'a': ['S2'], 'b': ['S2']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S2']
        }

        minimized = minimise_dfa(dfa)

        self.assertTrue(is_deterministic(minimized))

        # Test language equivalence for valid inputs
        test_strings = ['a', 'aa', 'aba', 'aaa']
        for test_string in test_strings:
            original_result = simulate_deterministic_fsa(dfa, test_string)
            minimized_result = simulate_deterministic_fsa(minimized, test_string)

            # Both should handle the string the same way
            if isinstance(original_result, list) and isinstance(minimized_result, list):
                # Both accepted
                self.assertTrue(True)
            elif isinstance(original_result, dict) and isinstance(minimized_result, dict):
                # Both rejected - check same acceptance status
                self.assertEqual(original_result.get('accepted', False),
                                 minimized_result.get('accepted', False))
            else:
                # One accepted, one rejected - this shouldn't happen
                self.fail(f"Inconsistent results for '{test_string}'")

    def test_minimization_idempotency(self):
        """Test that minimizing a minimized DFA gives the same result"""
        dfa = {
            'states': ['S0', 'S1', 'S2', 'S3'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1'], 'b': ['S2']},
                'S1': {'a': ['S3'], 'b': ['S2']},
                'S2': {'a': ['S1'], 'b': ['S3']},  # S2 and S3 equivalent
                'S3': {'a': ['S3'], 'b': ['S3']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S3']
        }

        first_minimization = minimise_dfa(dfa)
        second_minimization = minimise_dfa(first_minimization)

        # Should have same number of states
        self.assertEqual(len(first_minimization['states']), len(second_minimization['states']))

        # Should accept same language
        test_strings = ['', 'a', 'b', 'ab', 'ba', 'aa', 'bb']
        for test_string in test_strings:
            first_result = simulate_deterministic_fsa(first_minimization, test_string)
            second_result = simulate_deterministic_fsa(second_minimization, test_string)

            first_accepted = isinstance(first_result, list)
            second_accepted = isinstance(second_result, list)

            self.assertEqual(first_accepted, second_accepted)