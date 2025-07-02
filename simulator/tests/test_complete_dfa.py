from django.test import TestCase
from simulator.fsa_transformations import complete_dfa
from simulator.fsa_properties import is_deterministic
from simulator.fsa_simulation import simulate_deterministic_fsa


class TestCompleteDFA(TestCase):
    """Test cases for DFA completion function"""

    def test_already_complete_dfa(self):
        """Test completing a DFA that's already complete"""
        # DFA with all transitions defined
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

        completed = complete_dfa(dfa)

        # Should remain the same since it's already complete
        self.assertEqual(len(completed['states']), 2)
        self.assertTrue(is_deterministic(completed))
        self.assertEqual(completed['alphabet'], ['a', 'b'])
        self.assertEqual(completed['startingState'], 'S0')
        self.assertEqual(completed['acceptingStates'], ['S1'])

        # Test language equivalence
        test_strings = ['', 'a', 'b', 'ab', 'ba', 'aa']
        for test_string in test_strings:
            original_result = simulate_deterministic_fsa(dfa, test_string)
            completed_result = simulate_deterministic_fsa(completed, test_string)

            original_accepted = isinstance(original_result, list)
            completed_accepted = isinstance(completed_result, list)

            self.assertEqual(original_accepted, completed_accepted,
                             f"Disagreement on string '{test_string}'")

    def test_incomplete_dfa_needs_dead_state(self):
        """Test completing a DFA that needs a dead state"""
        # DFA missing some transitions
        dfa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1']},  # Missing 'b' transition
                'S1': {'a': ['S0']}  # Missing 'b' transition
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }

        completed = complete_dfa(dfa)

        # Should add a dead state
        self.assertEqual(len(completed['states']), 3)
        self.assertTrue(is_deterministic(completed))

        # Check that all transitions are now defined
        for state in completed['states']:
            if state in completed['transitions']:
                for symbol in completed['alphabet']:
                    self.assertIn(symbol, completed['transitions'][state])
                    self.assertEqual(len(completed['transitions'][state][symbol]), 1)

        # Dead state should transition to itself
        dead_states = [s for s in completed['states'] if s not in ['S0', 'S1']]
        self.assertEqual(len(dead_states), 1)
        dead_state = dead_states[0]

        for symbol in completed['alphabet']:
            self.assertEqual(completed['transitions'][dead_state][symbol], [dead_state])

    def test_partially_incomplete_dfa(self):
        """Test completing a DFA with some missing transitions"""
        # DFA where only some states have missing transitions
        dfa = {
            'states': ['S0', 'S1', 'S2'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1'], 'b': ['S2']},  # Complete
                'S1': {'a': ['S0']},  # Missing 'b' transition
                'S2': {'a': ['S2'], 'b': ['S2']}  # Complete
            },
            'startingState': 'S0',
            'acceptingStates': ['S2']
        }

        completed = complete_dfa(dfa)

        # Should add a dead state
        self.assertEqual(len(completed['states']), 4)
        self.assertTrue(is_deterministic(completed))

        # Verify all transitions are now complete
        for state in completed['states']:
            for symbol in completed['alphabet']:
                self.assertIn(state, completed['transitions'])
                self.assertIn(symbol, completed['transitions'][state])

        # Test that valid paths still work
        result = simulate_deterministic_fsa(completed, 'b')
        self.assertIsInstance(result, list)  # Should accept 'b' (goes to S2)

    def test_single_state_dfa_completion(self):
        """Test completing a single-state DFA"""
        # Single state with missing transitions
        dfa = {
            'states': ['S0'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S0']}  # Missing 'b' transition
            },
            'startingState': 'S0',
            'acceptingStates': ['S0']
        }

        completed = complete_dfa(dfa)

        # Should add a dead state
        self.assertEqual(len(completed['states']), 2)
        self.assertTrue(is_deterministic(completed))

        # S0 should have 'b' transition to dead state
        self.assertIn('b', completed['transitions']['S0'])

    def test_empty_alphabet_dfa(self):
        """Test completing a DFA with empty alphabet"""
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

        completed = complete_dfa(dfa)

        # Should remain unchanged since no symbols to complete
        self.assertEqual(len(completed['states']), 2)
        self.assertTrue(is_deterministic(completed))
        self.assertEqual(completed['alphabet'], [])

    def test_non_deterministic_fsa_raises_error(self):
        """Test that non-deterministic FSA raises ValueError"""
        nfa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'a': ['S0', 'S1']},  # Non-deterministic
                'S1': {'a': ['S1']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }

        with self.assertRaises(ValueError) as context:
            complete_dfa(nfa)

        self.assertIn("deterministic", str(context.exception))

    def test_completion_preserves_original_structure(self):
        """Test that completion preserves the original DFA structure"""
        dfa = {
            'states': ['A', 'B'],
            'alphabet': ['0', '1'],
            'transitions': {
                'A': {'0': ['B']},  # Missing '1' transition
                'B': {'0': ['A'], '1': ['B']}  # Complete
            },
            'startingState': 'A',
            'acceptingStates': ['B']
        }

        completed = complete_dfa(dfa)

        # Check that original structure is preserved
        self.assertEqual(completed['startingState'], 'A')
        self.assertEqual(completed['acceptingStates'], ['B'])
        self.assertEqual(completed['alphabet'], ['0', '1'])

        # Original transitions should still exist
        self.assertEqual(completed['transitions']['A']['0'], ['B'])
        self.assertEqual(completed['transitions']['B']['0'], ['A'])
        self.assertEqual(completed['transitions']['B']['1'], ['B'])

        # Missing transition should now exist
        self.assertIn('1', completed['transitions']['A'])

    def test_dead_state_naming(self):
        """Test that dead state gets appropriate unique name"""
        # DFA that might conflict with common dead state names
        dfa = {
            'states': ['DEAD', 'S1'],  # Already has 'DEAD' state
            'alphabet': ['a'],
            'transitions': {
                'DEAD': {'a': ['S1']},
                'S1': {}  # Missing 'a' transition
            },
            'startingState': 'DEAD',
            'acceptingStates': ['S1']
        }

        completed = complete_dfa(dfa)

        # Should have 3 states (original DEAD, S1, and new dead state)
        self.assertEqual(len(completed['states']), 3)

        # New dead state should have different name
        dead_state_names = [s for s in completed['states'] if s != 'DEAD' and s != 'S1']
        self.assertEqual(len(dead_state_names), 1)

        # New dead state should not be named 'DEAD'
        new_dead_state = dead_state_names[0]
        self.assertNotEqual(new_dead_state, 'DEAD')