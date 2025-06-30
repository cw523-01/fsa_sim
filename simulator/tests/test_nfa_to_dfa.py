from django.test import TestCase
from simulator.fsa_properties import is_deterministic
from simulator.fsa_simulation import simulate_nondeterministic_fsa, simulate_deterministic_fsa
from simulator.fsa_transformations import nfa_to_dfa


class TestNfaToDfa(TestCase):
    """Test cases for NFA to DFA conversion function"""

    def test_simple_nfa_conversion(self):
        """Test conversion of a simple NFA without epsilon transitions"""
        # NFA that accepts strings ending with 'ab'
        nfa = {
            'states': ['S0', 'S1', 'S2'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S0', 'S1'], 'b': ['S0']},  # Non-deterministic on 'a'
                'S1': {'b': ['S2']},
                'S2': {}
            },
            'startingState': 'S0',
            'acceptingStates': ['S2']
        }

        dfa = nfa_to_dfa(nfa)

        # Verify DFA properties
        self.assertTrue(is_deterministic(dfa))
        self.assertEqual(dfa['alphabet'], ['a', 'b'])
        self.assertIn(dfa['startingState'], dfa['states'])

        # Verify language equivalence on test strings
        test_strings = ['', 'a', 'b', 'ab', 'ba', 'aab', 'abb', 'abab', 'baba']
        for test_string in test_strings:
            nfa_result = simulate_nondeterministic_fsa(nfa, test_string)
            dfa_result = simulate_deterministic_fsa(dfa, test_string)

            nfa_accepted = isinstance(nfa_result, list)
            dfa_accepted = isinstance(dfa_result, list)

            self.assertEqual(nfa_accepted, dfa_accepted,
                             f"Disagreement on string '{test_string}'")

    def test_nfa_with_epsilon_transitions(self):
        """Test conversion of NFA with epsilon transitions"""
        # NFA that accepts 'a*b' with epsilon transitions
        nfa = {
            'states': ['S0', 'S1', 'S2', 'S3'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'': ['S1'], 'a': ['S0']},  # Epsilon to S1 or loop on 'a'
                'S1': {'': ['S2']},  # Epsilon to S2
                'S2': {'b': ['S3']},
                'S3': {}
            },
            'startingState': 'S0',
            'acceptingStates': ['S3']
        }

        dfa = nfa_to_dfa(nfa)

        # Verify DFA properties
        self.assertTrue(is_deterministic(dfa))

        # Test language equivalence
        test_strings = ['b', 'ab', 'aab', 'aaab', 'bb', 'aba', 'ba', '']
        for test_string in test_strings:
            nfa_result = simulate_nondeterministic_fsa(nfa, test_string)
            dfa_result = simulate_deterministic_fsa(dfa, test_string)

            nfa_accepted = isinstance(nfa_result, list)
            dfa_accepted = isinstance(dfa_result, list)

            self.assertEqual(nfa_accepted, dfa_accepted,
                             f"Disagreement on string '{test_string}'")

    def test_nfa_with_epsilon_loops(self):
        """Test conversion of NFA with epsilon loops"""
        # NFA with epsilon self-loop
        nfa = {
            'states': ['S0', 'S1', 'S2'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'': ['S1']},  # Epsilon to S1
                'S1': {'': ['S1'], 'a': ['S2']},  # Epsilon self-loop and 'a' to S2
                'S2': {}
            },
            'startingState': 'S0',
            'acceptingStates': ['S2']
        }

        dfa = nfa_to_dfa(nfa)

        # Verify DFA properties
        self.assertTrue(is_deterministic(dfa))

        # Test language equivalence
        test_strings = ['', 'a', 'aa', 'aaa']
        for test_string in test_strings:
            nfa_result = simulate_nondeterministic_fsa(nfa, test_string)
            dfa_result = simulate_deterministic_fsa(dfa, test_string)

            nfa_accepted = isinstance(nfa_result, list)
            dfa_accepted = isinstance(dfa_result, list)

            self.assertEqual(nfa_accepted, dfa_accepted,
                             f"Disagreement on string '{test_string}'")

    def test_already_deterministic_nfa(self):
        """Test conversion of an already deterministic NFA"""
        # DFA that accepts strings with even number of 'a's
        nfa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1'], 'b': ['S0']},
                'S1': {'a': ['S0'], 'b': ['S1']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S0']
        }

        dfa = nfa_to_dfa(nfa)

        # Verify DFA properties
        self.assertTrue(is_deterministic(dfa))

        # Should have similar number of states (possibly same structure)
        self.assertLessEqual(len(dfa['states']), len(nfa['states']) + 1)

        # Test language equivalence
        test_strings = ['', 'a', 'aa', 'aaa', 'b', 'ab', 'ba', 'aabb']
        for test_string in test_strings:
            nfa_result = simulate_nondeterministic_fsa(nfa, test_string)
            dfa_result = simulate_deterministic_fsa(dfa, test_string)

            nfa_accepted = isinstance(nfa_result, list)
            dfa_accepted = isinstance(dfa_result, list)

            self.assertEqual(nfa_accepted, dfa_accepted,
                             f"Disagreement on string '{test_string}'")

    def test_nfa_multiple_accepting_states(self):
        """Test NFA with multiple accepting states"""
        # NFA that accepts strings containing 'a' OR ending with 'b'
        nfa = {
            'states': ['S0', 'S1', 'S2'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1'], 'b': ['S0', 'S2']},  # 'b' can stay or go to accepting
                'S1': {'a': ['S1'], 'b': ['S1', 'S2']},  # Already found 'a', can do anything
                'S2': {}  # Accepting state for strings ending with 'b'
            },
            'startingState': 'S0',
            'acceptingStates': ['S1', 'S2']  # Multiple accepting states
        }

        dfa = nfa_to_dfa(nfa)

        # Verify DFA properties
        self.assertTrue(is_deterministic(dfa))
        self.assertTrue(len(dfa['acceptingStates']) > 0)

        # Test language equivalence
        test_strings = ['', 'a', 'b', 'ab', 'ba', 'aa', 'bb', 'aabb', 'baba']
        for test_string in test_strings:
            nfa_result = simulate_nondeterministic_fsa(nfa, test_string)
            dfa_result = simulate_deterministic_fsa(dfa, test_string)

            nfa_accepted = isinstance(nfa_result, list)
            dfa_accepted = isinstance(dfa_result, list)

            self.assertEqual(nfa_accepted, dfa_accepted,
                             f"Disagreement on string '{test_string}'")

    def test_nfa_no_accepting_states(self):
        """Test NFA with no accepting states"""
        nfa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1'], 'b': ['S0']},
                'S1': {'a': ['S0'], 'b': ['S1']}
            },
            'startingState': 'S0',
            'acceptingStates': []  # No accepting states
        }

        dfa = nfa_to_dfa(nfa)

        # Verify DFA properties
        self.assertTrue(is_deterministic(dfa))
        self.assertEqual(dfa['acceptingStates'], [])

        # All strings should be rejected
        test_strings = ['', 'a', 'b', 'ab', 'ba']
        for test_string in test_strings:
            dfa_result = simulate_deterministic_fsa(dfa, test_string)
            self.assertIsInstance(dfa_result, dict)
            self.assertFalse(dfa_result['accepted'])

    def test_nfa_single_state(self):
        """Test NFA with single state"""
        # Single accepting state with self-loops
        nfa = {
            'states': ['S0'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S0'], 'b': ['S0']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S0']
        }

        dfa = nfa_to_dfa(nfa)

        # Verify DFA properties
        self.assertTrue(is_deterministic(dfa))
        self.assertEqual(len(dfa['states']), 1)
        self.assertEqual(len(dfa['acceptingStates']), 1)

        # All strings should be accepted
        test_strings = ['', 'a', 'b', 'ab', 'ba', 'aabb']
        for test_string in test_strings:
            dfa_result = simulate_deterministic_fsa(dfa, test_string)
            self.assertIsInstance(dfa_result, list)

    def test_complex_nfa_conversion(self):
        """Test conversion of a more complex NFA"""
        # NFA that accepts strings that contain 'aba' as a substring
        nfa = {
            'states': ['S0', 'S1', 'S2', 'S3'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S0', 'S1'], 'b': ['S0']},  # Can stay or start pattern
                'S1': {'a': ['S1'], 'b': ['S2']},  # Found 'a', looking for 'b'
                'S2': {'a': ['S1', 'S3'], 'b': ['S0']},  # Found 'ab', looking for 'a'
                'S3': {'a': ['S3'], 'b': ['S3']}  # Found 'aba', accept everything
            },
            'startingState': 'S0',
            'acceptingStates': ['S3']
        }

        dfa = nfa_to_dfa(nfa)

        # Verify DFA properties
        self.assertTrue(is_deterministic(dfa))
        self.assertTrue(len(dfa['acceptingStates']) > 0)

        # Test language equivalence
        test_strings = ['', 'a', 'ab', 'aba', 'abab', 'baba', 'aaba', 'abaa', 'babab']
        for test_string in test_strings:
            nfa_result = simulate_nondeterministic_fsa(nfa, test_string)
            dfa_result = simulate_deterministic_fsa(dfa, test_string)

            nfa_accepted = isinstance(nfa_result, list)
            dfa_accepted = isinstance(dfa_result, list)

            self.assertEqual(nfa_accepted, dfa_accepted,
                             f"Disagreement on string '{test_string}'")

    def test_invalid_nfa_structure_raises_error(self):
        """Test that invalid NFA structure raises ValueError"""
        # Missing required key
        invalid_nfa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a'],
            'transitions': {'S0': {'a': ['S1']}, 'S1': {}},
            'startingState': 'S0'
            # Missing acceptingStates
        }

        with self.assertRaises(ValueError) as context:
            nfa_to_dfa(invalid_nfa)

        self.assertIn("Invalid NFA structure", str(context.exception))

    def test_conversion_result_structure(self):
        """Test that converted DFA has correct structure"""
        nfa = {
            'states': ['S0', 'S1', 'S2'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S0', 'S1'], 'b': ['S0']},
                'S1': {'b': ['S2']},
                'S2': {}
            },
            'startingState': 'S0',
            'acceptingStates': ['S2']
        }

        dfa = nfa_to_dfa(nfa)

        # Check all required keys are present
        required_keys = ['states', 'alphabet', 'transitions', 'startingState', 'acceptingStates']
        for key in required_keys:
            self.assertIn(key, dfa)

        # Check types
        self.assertIsInstance(dfa['states'], list)
        self.assertIsInstance(dfa['alphabet'], list)
        self.assertIsInstance(dfa['transitions'], dict)
        self.assertIsInstance(dfa['startingState'], str)
        self.assertIsInstance(dfa['acceptingStates'], list)

        # Check that start state is in states list
        self.assertIn(dfa['startingState'], dfa['states'])

        # Check that all accepting states are in states list
        for state in dfa['acceptingStates']:
            self.assertIn(state, dfa['states'])

        # Check that states are sorted
        self.assertEqual(dfa['states'], sorted(dfa['states']))

        # Check that accepting states are sorted
        self.assertEqual(dfa['acceptingStates'], sorted(dfa['acceptingStates']))